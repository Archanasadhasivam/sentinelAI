"""
Session isolation tests.

- Path-guard and container-config tests run everywhere (a fake Docker client
  stands in, so no Docker is needed).
- The real-container tests at the bottom only run when Docker is up AND
  SENTINELAI_DOCKER_TESTS=1 is set, e.g. on Windows PowerShell:
      $env:SENTINELAI_DOCKER_TESTS="1"; python -m pytest tests/test_session_isolation.py -v
"""
import os
import uuid

import pytest

from app.sandbox import container_manager as cm
from app.sandbox.container_manager import ContainerManager, PathOutsideWorkspace, resolve_workspace_path


# --- path guard --------------------------------------------------------------

@pytest.mark.parametrize("path,expected", [
    ("notes.txt", "/workspace/notes.txt"),
    ("inbox/newsletter.html", "/workspace/inbox/newsletter.html"),
    ("./a/../b.txt", "/workspace/b.txt"),
    ("/workspace/x.txt", "/workspace/x.txt"),
    ("dir\\file.txt", "/workspace/dir/file.txt"),
])
def test_paths_inside_workspace_are_allowed(path, expected):
    assert resolve_workspace_path(path) == expected


@pytest.mark.parametrize("path", [
    "../etc/passwd", "/etc/passwd", "a/../../etc/shadow", "..\\..\\etc\\passwd",
    "/workspace/../root", "", "   ", "/workspace", "x\x00y",
])
def test_paths_escaping_workspace_are_rejected(path):
    with pytest.raises(PathOutsideWorkspace):
        resolve_workspace_path(path)


# --- container config (fake docker client) --------------------------------------

class _ExecResult:
    def __init__(self, exit_code=0, output=b""):
        self.exit_code, self.output = exit_code, output


class _FakeContainer:
    def __init__(self):
        self.status = "running"
        self.id = "fake123"
        self.execs = []

    def exec_run(self, cmd, **kwargs):
        self.execs.append(cmd)
        return _ExecResult()


class _FakeContainers:
    def __init__(self):
        self.run_kwargs = None
        self.container = _FakeContainer()

    def run(self, image, **kwargs):
        self.run_kwargs = {"image": image, **kwargs}
        return self.container

    def list(self, **kwargs):
        return [self.container]


class _FakeImages:
    def get(self, name):
        return object()


class _FakeClient:
    def __init__(self):
        self.containers = _FakeContainers()
        self.images = _FakeImages()


def test_container_is_created_with_isolation_settings():
    manager = ContainerManager()
    fake = _FakeClient()
    manager._client = fake
    manager.create("sess-1")

    kw = fake.containers.run_kwargs
    assert kw["image"] == cm.SANDBOX_IMAGE
    assert kw["network_mode"] == "none"
    assert kw["read_only"] is True
    assert cm.WORKSPACE in kw["tmpfs"]
    assert kw["cap_drop"] == ["ALL"]
    assert "no-new-privileges" in kw["security_opt"]
    assert kw["user"] == cm.CONTAINER_USER
    assert kw["mem_limit"] == cm.MEM_LIMIT
    assert kw["pids_limit"] == cm.PIDS_LIMIT
    assert kw["labels"] == {cm.LABEL_KEY: "sess-1"}
    # every seed file was written into /workspace
    assert len(fake.containers.container.execs) == len(cm.SEED_FILES)


def test_shell_command_is_wrapped_in_timeout_and_passed_as_argv():
    manager = ContainerManager()
    fake = _FakeClient()
    manager._client = fake
    manager.run_shell("sess-1", "echo hi; rm -rf /")
    cmd = fake.containers.container.execs[-1]
    assert cmd[:2] == ["timeout", str(cm.SHELL_TIMEOUT_SECONDS)]
    assert cmd[2:] == ["sh", "-c", "echo hi; rm -rf /"]


# --- real Docker (opt-in) ---------------------------------------------------------

_real = pytest.mark.skipif(
    os.environ.get("SENTINELAI_DOCKER_TESTS") != "1" or not ContainerManager().is_available(),
    reason="set SENTINELAI_DOCKER_TESTS=1 with Docker running to test real containers",
)


@pytest.fixture
def real_sessions():
    manager = ContainerManager()
    a, b = f"test-{uuid.uuid4().hex[:8]}", f"test-{uuid.uuid4().hex[:8]}"
    manager.create(a)
    manager.create(b)
    yield manager, a, b
    manager.remove(a)
    manager.remove(b)


@_real
def test_real_seed_files_and_file_tools(real_sessions):
    manager, a, _ = real_sessions
    assert "standup" in manager.read_file(a, "notes.txt")
    assert manager.write_file(a, "out/report.txt", "hello").startswith("OK")
    assert manager.read_file(a, "out/report.txt") == "hello"


@_real
def test_real_sessions_cannot_see_each_other(real_sessions):
    manager, a, b = real_sessions
    manager.write_file(a, "secret.txt", "only-for-a")
    assert manager.read_file(b, "secret.txt").startswith("ERROR")


@_real
def test_real_container_has_no_network(real_sessions):
    manager, a, _ = real_sessions
    out = manager.run_shell(a, "wget -T 3 -q -O- http://example.com || echo NO_NETWORK")
    assert "NO_NETWORK" in out


@_real
def test_real_root_filesystem_is_read_only(real_sessions):
    manager, a, _ = real_sessions
    out = manager.run_shell(a, "touch /etc/pwned && echo WROTE || echo READ_ONLY")
    assert "READ_ONLY" in out


@_real
def test_real_shell_timeout(real_sessions):
    manager, a, _ = real_sessions
    assert "timed out" in manager.run_shell(a, "sleep 30")
