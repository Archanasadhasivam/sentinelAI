"""
Integration tests: app/detection/prompt_injection.py with Layer C wired in.

Covers two things test_xlmr_classifier.py doesn't:
1. That the detector's pre-existing behavior (regex + Groq layers, existing
   metadata keys, existing evidence) is unchanged now that Layer C exists but
   has no checkpoint configured — the default state for this repo.
2. That when a checkpoint IS available (mocked — no real model needed), its
   score correctly folds into the detector's overall max() combination and
   surfaces in evidence/metadata, without disturbing the other two layers.
"""
import pytest

import app.detection.prompt_injection as pi_module
from app.detection.fixtures.seed_payloads import BENIGN_PROMPTS, DIRECT_INJECTION_EN
from app.ml.xlmr_classifier import XLMRClassificationResult
from app.schemas import InterceptedEvent


def _event(text: str) -> InterceptedEvent:
    return InterceptedEvent(session_id="test-session", event_type="prompt", source="user", payload={"text": text})


def _force_groq_disabled(monkeypatch):
    """These tests are about Layer C's combination logic specifically, not
    about whether a live Groq call agrees with a given fixture's label — so
    force the semantic layer off regardless of whatever GROQ_API_KEY happens
    to be configured in this environment's .env. Without this, these tests'
    outcomes would depend on a real network call to a real LLM, which is
    exactly the kind of non-determinism a unit test shouldn't have."""
    monkeypatch.setattr(pi_module.groq_client, "enabled", False)


class _FakeUnavailableClassifier:
    async def classify(self, text: str) -> XLMRClassificationResult:
        return XLMRClassificationResult(label="BENIGN", confidence=0.0, available=False, error="no model")


class _FakeInjectionClassifier:
    """Simulates a trained checkpoint that confidently flags PROMPT_INJECTION."""

    def __init__(self, confidence: float = 0.93):
        self.confidence = confidence

    async def classify(self, text: str) -> XLMRClassificationResult:
        return XLMRClassificationResult(label="PROMPT_INJECTION", confidence=self.confidence, available=True)


class _FakeBenignClassifier:
    """Simulates a trained checkpoint that is available but says BENIGN."""

    async def classify(self, text: str) -> XLMRClassificationResult:
        return XLMRClassificationResult(label="BENIGN", confidence=0.12, available=True)


@pytest.mark.asyncio
async def test_no_checkpoint_preserves_existing_metadata_shape(monkeypatch):
    """When Layer C has no usable checkpoint, the new metadata keys should be
    present but inert, and every pre-existing key unchanged in meaning.

    Explicitly forced via monkeypatch rather than relying on "no checkpoint
    exists on disk" as ambient truth — that assumption breaks the moment you
    actually train one at the real default path, which isn't a code bug, just
    a test that wasn't isolated from the filesystem. This also forces Groq
    off so the test only exercises what its name says it exercises."""
    _force_groq_disabled(monkeypatch)
    monkeypatch.setattr(pi_module, "xlmr_classifier", _FakeUnavailableClassifier())

    result = await pi_module.prompt_injection_detector.analyze(_event(DIRECT_INJECTION_EN[0]["text"]))

    assert result.metadata["xlmr_layer_available"] is False
    assert result.metadata["xlmr_score"] == 0.0
    # pre-existing keys still there, doing what they always did
    assert "regex_score" in result.metadata
    assert "semantic_score" in result.metadata
    assert "semantic_layer_degraded" in result.metadata
    # this fixture is a direct regex hit, so behavior is unchanged: still triggers
    assert result.triggered is True


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", BENIGN_PROMPTS)
async def test_benign_prompts_still_not_triggered_with_layer_present_but_unavailable(monkeypatch, payload):
    """Isolated to regex-only: this test is about Layer C being a no-op when
    unavailable, not about whether a live Groq call agrees with the fixture's
    BENIGN label on a given run — that's a separate, real question (see
    test_prompt_injection.py), not what this test is named for."""
    _force_groq_disabled(monkeypatch)
    monkeypatch.setattr(pi_module, "xlmr_classifier", _FakeUnavailableClassifier())
    result = await pi_module.prompt_injection_detector.analyze(_event(payload["text"]))
    assert result.triggered is False


@pytest.mark.asyncio
async def test_xlmr_layer_alone_can_trigger_detection(monkeypatch):
    """A benign-looking-to-regex string that a (mocked) fine-tuned classifier
    confidently flags should still surface as triggered — proving the score
    combination (`max(regex, semantic, xlmr)`) actually uses Layer C's output."""
    _force_groq_disabled(monkeypatch)
    monkeypatch.setattr(pi_module, "xlmr_classifier", _FakeInjectionClassifier(confidence=0.93))

    # Ordinary-sounding text that no regex category should match.
    text = "Please summarize the quarterly report for the team."
    result = await pi_module.prompt_injection_detector.analyze(_event(text))

    assert result.metadata["xlmr_layer_available"] is True
    assert result.metadata["xlmr_score"] == pytest.approx(0.93)
    assert result.triggered is True
    assert result.score == pytest.approx(0.93)
    assert any(e.label == "classifier:xlmr" for e in result.evidence)


@pytest.mark.asyncio
async def test_available_but_benign_classifier_does_not_add_evidence_or_score(monkeypatch):
    _force_groq_disabled(monkeypatch)
    monkeypatch.setattr(pi_module, "xlmr_classifier", _FakeBenignClassifier())

    text = "What's on the agenda for today's standup?"
    result = await pi_module.prompt_injection_detector.analyze(_event(text))

    assert result.metadata["xlmr_layer_available"] is True
    assert result.metadata["xlmr_score"] == 0.0  # only contributes when label == PROMPT_INJECTION
    assert not any(e.label == "classifier:xlmr" for e in result.evidence)
    assert result.triggered is False


@pytest.mark.asyncio
async def test_xlmr_and_regex_combine_via_max_not_sum(monkeypatch):
    """DIRECT_INJECTION_EN[0] matches two distinct regex categories
    (role_override + system_prompt_exfiltration), which alone already scores
    0.9 (see prompt_injection.py). Pairing it with a *lower*-confidence xlmr
    flag (0.6) must still yield 0.9, not their sum (1.5) — confirms the
    combination rule is max(), matching the existing regex/semantic
    combination that was already in place, now extended to three layers.

    Groq forced off: with a live key configured, the semantic layer can
    independently score this text highly too (it's an unambiguous attack, so
    that's arguably *correct* LLM behavior) — which would make this test
    assert something about Groq's opinion, not about Layer C's combination
    logic, which is the one thing this test is actually meant to check."""
    _force_groq_disabled(monkeypatch)
    monkeypatch.setattr(pi_module, "xlmr_classifier", _FakeInjectionClassifier(confidence=0.6))

    result = await pi_module.prompt_injection_detector.analyze(_event(DIRECT_INJECTION_EN[0]["text"]))

    assert result.metadata["semantic_score"] == 0.0  # confirms the forced-off assumption actually held
    assert result.metadata["regex_score"] == pytest.approx(0.9)
    assert result.metadata["xlmr_score"] == pytest.approx(0.6)
    assert result.score == pytest.approx(0.9)  # max(0.9, 0.0, 0.6), not 1.5
