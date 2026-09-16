import os
import threading
from pathlib import Path

import yaml

_POLICY_PATH = Path(__file__).parent / "policies.yaml"


class PolicyEngine:
    """
    Hot-reloading policy store. At this scale (single-process, single-file
    config, infrequent edits from the /policy UI) checking the file's mtime
    on every read is simpler and just as correct as a filesystem watcher —
    documented as a scope simplification vs. any enterprise hot-reload setup.
    """

    def __init__(self, path: Path = _POLICY_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._mtime: float | None = None
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        with self._lock:
            self._data = yaml.safe_load(self._path.read_text()) or {}
            self._mtime = os.path.getmtime(self._path)

    def get(self) -> dict:
        try:
            current_mtime = os.path.getmtime(self._path)
        except OSError:
            current_mtime = self._mtime
        if current_mtime != self._mtime:
            self._load()
        return self._data

    def save(self, data: dict) -> None:
        with self._lock:
            self._path.write_text(yaml.safe_dump(data, sort_keys=False))
        self._load()


policy_engine = PolicyEngine()
