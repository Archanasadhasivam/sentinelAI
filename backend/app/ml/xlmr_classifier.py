"""
XLM-RoBERTa prompt-injection classifier — inference component only.

This is Layer C of the Prompt Injection Module (see report §4.2 / §5.2 and
docs/SCOPE_DECISIONS.md): a fine-tuned XLM-RoBERTa sequence classifier that
outputs BENIGN / PROMPT_INJECTION, sitting alongside the existing regex layer
(Layer A) and the Groq semantic layer (Layer B) in
app/detection/prompt_injection.py.

Design mirrors app/groq_client.py's graceful-degradation pattern on purpose:
- Constructing this class NEVER raises and NEVER imports torch/transformers.
  Both are optional heavy dependencies (see backend/requirements-ml.txt) —
  the API must keep booting and the demo must keep working with no
  fine-tuned checkpoint present, exactly like it works today with no
  GROQ_API_KEY.
- `is_available()` is a cheap, layered check: first a filesystem check (does
  a model directory with the expected files even exist?), and only if that
  passes does it attempt the transformers/torch import + weight load — once,
  caching the outcome so repeated calls don't retry a known failure.
- `classify()` never raises; on any failure it returns an "unavailable"
  result so the caller can fall back to its other signals.

No dataset, checkpoint, or performance numbers are bundled here. Out of the
box `is_available()` is False until you actually run train_xlmr.py and point
`XLMR_MODEL_PATH` at the resulting checkpoint directory.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

# Convention used both here and in train_xlmr.py — kept in one place so
# training and inference can never disagree about which index means what.
LABELS: dict[int, str] = {0: "BENIGN", 1: "PROMPT_INJECTION"}
LABEL2ID: dict[str, int] = {v: k for k, v in LABELS.items()}

_REQUIRED_WEIGHT_FILES = ("pytorch_model.bin", "model.safetensors")

_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # .../backend


def _resolve_model_path(raw_path: str) -> Path:
    """Relative paths (the default) resolve against the backend/ root, not
    whatever the process's cwd happens to be — same convention already used
    for app/detection/data/injection_patterns.json."""
    p = Path(raw_path)
    return p if p.is_absolute() else _BACKEND_ROOT / p


@dataclass
class XLMRClassificationResult:
    label: str  # "BENIGN" | "PROMPT_INJECTION"
    confidence: float  # probability assigned to the PROMPT_INJECTION class, 0.0-1.0
    available: bool  # False whenever no usable fine-tuned model was found/loadable
    error: str | None = None  # human-readable reason when available=False after an attempt


class XLMRPromptInjectionClassifier:
    """One instance wraps one on-disk checkpoint. Safe to construct even
    when transformers/torch aren't installed or no checkpoint exists yet."""

    def __init__(self, model_path: str | None = None, confidence_threshold: float | None = None, device: str = "cpu"):
        settings = get_settings()
        self.model_path = _resolve_model_path(model_path if model_path is not None else settings.xlmr_model_path)
        self.confidence_threshold = (
            confidence_threshold if confidence_threshold is not None else settings.xlmr_confidence_threshold
        )
        self.device = device

        self._model = None
        self._tokenizer = None
        self._load_attempted = False
        self._load_error: str | None = None

    # -- filesystem-only check: never imports torch/transformers ----------
    def _model_files_present(self) -> bool:
        if not self.model_path.is_dir():
            return False
        has_config = (self.model_path / "config.json").is_file()
        has_weights = any((self.model_path / fname).is_file() for fname in _REQUIRED_WEIGHT_FILES)
        return has_config and has_weights

    # -- heavy import + weight load, attempted at most once ----------------
    def _ensure_loaded(self) -> bool:
        if self._model is not None and self._tokenizer is not None:
            return True
        if self._load_attempted:
            return False  # already tried this process lifetime and failed

        self._load_attempted = True
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            self._load_error = (
                "transformers/torch not installed — see backend/requirements-ml.txt "
                f"(ImportError: {exc})"
            )
            return False

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            self._model = AutoModelForSequenceClassification.from_pretrained(str(self.model_path))
            self._model.eval()
            self._model.to(self.device)
        except Exception as exc:  # corrupt/incompatible checkpoint, OOM, etc.
            self._load_error = f"failed to load model from {self.model_path}: {exc}"
            self._model = None
            self._tokenizer = None
            return False

        return True

    def is_available(self) -> bool:
        if not self._model_files_present():
            return False
        return self._ensure_loaded()

    @property
    def unavailable_reason(self) -> str | None:
        if not self._model_files_present():
            return f"no fine-tuned model found at {self.model_path} (training pipeline is ready; see train_xlmr.py)"
        return self._load_error

    # -- actual forward pass; synchronous on purpose so tests can monkeypatch
    # this one method to simulate "a model is loaded" without ever touching
    # torch/transformers. ------------------------------------------------
    def _predict(self, text: str) -> float:
        import torch  # local import: only reached once _ensure_loaded() succeeded

        inputs = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            logits = self._model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]

        id2label = getattr(self._model.config, "id2label", None) or {}
        injection_idx = LABEL2ID["PROMPT_INJECTION"]
        for idx, name in id2label.items():
            if str(name).upper() == "PROMPT_INJECTION":
                injection_idx = int(idx)
                break

        return float(probs[injection_idx].item())

    async def classify(self, text: str) -> XLMRClassificationResult:
        if not self.is_available():
            return XLMRClassificationResult(
                label="BENIGN", confidence=0.0, available=False, error=self.unavailable_reason
            )

        prob_injection = await asyncio.to_thread(self._predict, text)
        label = "PROMPT_INJECTION" if prob_injection >= self.confidence_threshold else "BENIGN"
        return XLMRClassificationResult(label=label, confidence=prob_injection, available=True)


# Module-level singleton, mirroring groq_client's pattern — constructing this
# is cheap and side-effect-free even with no model present.
xlmr_classifier = XLMRPromptInjectionClassifier()
