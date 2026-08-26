import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MACOS_SCRIPTS = [
    PROJECT_ROOT / "scripts" / "macos" / "start-mac-native.sh",
    PROJECT_ROOT / "scripts" / "macos" / "stop-mac-native.sh",
    PROJECT_ROOT / "scripts" / "macos" / "restart-mac-native.sh",
]


def test_native_scripts_are_valid_shell_and_resolve_repo_root():
    for script in MACOS_SCRIPTS:
        result = subprocess.run(
            ["bash", "-n", str(script)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{script}: {result.stderr}"

    start_text = MACOS_SCRIPTS[0].read_text(encoding="utf-8")
    assert 'PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"' in start_text
    assert 'export DATA_DIR="${DATA_DIR:-$PROJECT_ROOT/data}"' in start_text
    assert "nohup uv run --no-sync uvicorn" in start_text
    assert "uv run --no-sync" in start_text


def test_compatibility_entries_use_canonical_native_lifecycle():
    root_start = (PROJECT_ROOT / "start_service.sh").read_text(encoding="utf-8")
    manager = (PROJECT_ROOT / "scripts" / "service_manager.sh").read_text(encoding="utf-8")

    assert "scripts/macos/start-mac-native.sh" in root_start
    assert "scripts/macos/start-mac-native.sh" in manager
    assert "scripts/macos/stop-mac-native.sh" in manager
    assert "scripts/macos/restart-mac-native.sh" in manager
    assert "pkill" not in manager
    assert "/Users/hsiaojohnny/dev/convert" not in root_start + manager


def test_native_scripts_do_not_manage_external_runtimes():
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in MACOS_SCRIPTS)
    for forbidden in ("ollama", "docker", "pip install", "ollama pull"):
        assert forbidden not in combined
