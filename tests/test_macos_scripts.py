import re
import subprocess
from pathlib import Path

import pytest


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


# ---------------------------------------------------------------------------
# WAVE-01b fail-first 契約（plan CM-01 #9 / handoff WAVE-03 目標行為）
#
# 針對 scripts/macos/start-mac-native.sh 的 launcher provenance 契約：
# revision 推導/注入/驗證、dirty 區分、writable DATA_DIR 驗證、health JSON
# revision 精確比對、own-PID cleanup。靜態文字契約與既有測試風格一致；
# 測試不執行 launcher、不啟動 backend、不連網（bash -n 已由上方測試涵蓋）。
# 這些案例刻意對「尚未實作」上述行為的現行 launcher 呈現 red（valid red）。
# ---------------------------------------------------------------------------

# 呼叫端可用來指定「要求的 build revision」的環境變數（任一皆視為明確要求）
_REQUESTED_REVISION_VARS = (
    "MEETINGSCRIBE_BUILD_REVISION",
    "MEETINGSCRIBE_REQUESTED_REVISION",
    "MEETINGSCRIBE_EXPECTED_REVISION",
)

_WRITABLE_DATA_DIR_PROBE = re.compile(
    r'-w\s+"?\$\{?DATA_DIR'
    r'|touch\s+"?\$\{?DATA_DIR'
    r'|mktemp\s+"?\$\{?DATA_DIR'
    r'|>>?\s+"?\$\{?DATA_DIR'
)


def _launcher_lines():
    return MACOS_SCRIPTS[0].read_text(encoding="utf-8").splitlines()


def _backend_start_index(lines):
    """真正啟動 backend 的那一行（nohup ... uvicorn ...）。"""
    for index, line in enumerate(lines):
        if "nohup" in line and "uvicorn" in line:
            return index
    return None


def _trace_revision_var_families(lines):
    """沿指派鏈追蹤 revision 變數家族：derived（Git HEAD/注入值）與 health（解析 /api/health build_revision）。"""
    families = {"derived": {"MEETINGSCRIBE_BUILD_REVISION"}, "health": set()}
    derived_markers = (r"git rev-parse", r"MEETINGSCRIBE_(?:BUILD|REQUESTED|EXPECTED)_REVISION")
    health_markers = (r"build_revision",)
    for _ in range(4):
        snapshot = {name: set(members) for name, members in families.items()}
        for line in lines:
            match = re.match(
                r"\s*(?:readonly\s+|local\s+|export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.+)$", line
            )
            if not match:
                continue
            name, rhs = match.group(1), match.group(2)
            rhs_tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", rhs))
            if any(re.search(p, rhs) for p in derived_markers) or rhs_tokens & snapshot["derived"]:
                families["derived"].add(name)
            if any(re.search(p, rhs) for p in health_markers) or rhs_tokens & snapshot["health"]:
                families["health"].add(name)
        if families == snapshot:
            break
    return families


def _trace_owned_pid_vars(lines):
    """回傳可證明屬於 launcher 自己啟動的 PID 變數（$! 或 own-PID 指派鏈）。"""
    pids = {"SERVER_PID", "SERVICE_PID"}
    for line in lines:
        match = re.match(r"\s*(?:readonly\s+|local\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.+)$", line)
        if not match:
            continue
        name, rhs = match.group(1), match.group(2)
        if "$!" in rhs or "find_service_pid" in rhs or "SERVER_PID" in rhs or "SERVICE_PID" in rhs:
            pids.add(name)
    return pids


def test_launcher_derives_build_revision_from_git_head_when_git_available():
    text = "\n".join(_launcher_lines())
    assert "git rev-parse HEAD" in text, (
        "launcher 必須由 Git clean HEAD 推導 build revision（git rev-parse HEAD）"
    )


def test_launcher_exports_meetingscribe_build_revision_to_child_environment():
    lines = _launcher_lines()
    start_index = _backend_start_index(lines)
    assert start_index is not None
    export_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().startswith("export") and "MEETINGSCRIBE_BUILD_REVISION" in line
        ),
        None,
    )
    assert export_index is not None, (
        "launcher 必須 export MEETINGSCRIBE_BUILD_REVISION，將 build revision 注入 child 環境"
    )
    assert export_index < start_index, "build revision 必須在啟動 backend 之前注入 child 環境"


def test_launcher_fails_before_backend_start_when_requested_revision_differs_from_clean_head():
    lines = _launcher_lines()
    start_index = _backend_start_index(lines)
    assert start_index is not None
    pre_start = lines[:start_index]
    families = _trace_revision_var_families(pre_start)
    revision_vars = families["derived"] | set(_REQUESTED_REVISION_VARS)
    for index, line in enumerate(pre_start):
        if "!=" not in line:
            continue
        tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line))
        if not tokens & revision_vars:
            continue
        if re.search(r"\bexit\b", "\n".join(pre_start[index : index + 5])):
            return
    pytest.fail(
        "launcher 缺少 preflight：明確要求的 revision 與 clean Git HEAD 不同時，"
        "必須在啟動 backend 之前 exit 1"
    )


def test_launcher_distinguishes_dirty_worktree_from_accepted_clean_head():
    lines = _launcher_lines()
    dirty_index = next(
        (
            index
            for index, line in enumerate(lines)
            if re.search(r"git status --porcelain|git describe --dirty|git diff --quiet", line)
        ),
        None,
    )
    assert dirty_index is not None, (
        "launcher 必須偵測 dirty worktree（如 git status --porcelain）以區分 clean HEAD"
    )
    window = "\n".join(lines[dirty_index + 1 : dirty_index + 11])
    assert re.search(r"\bexit\b", window) or re.search(r"unknown|-dirty|DIRTY", window), (
        "dirty worktree 必須在啟動前明確失敗，或將 revision 標記為非 clean（-dirty/unknown）；"
        "不得把 dirty 樹的 HEAD 冒充 accepted clean SHA"
    )


def test_launcher_validates_actual_data_dir_is_writable_before_backend_start():
    lines = _launcher_lines()
    start_index = _backend_start_index(lines)
    assert start_index is not None
    pre_start = lines[:start_index]
    for index, line in enumerate(pre_start):
        if not _WRITABLE_DATA_DIR_PROBE.search(line):
            continue
        if re.search(r"\bexit\b", "\n".join(pre_start[index : index + 5])):
            return
    pytest.fail(
        "launcher 必須在啟動 backend 前驗證實際解析後的 DATA_DIR 可寫；"
        "不可寫時必須明確 exit 1 且不啟動 backend"
    )


def test_launcher_parses_health_json_and_declares_ready_only_after_exact_revision_match():
    lines = _launcher_lines()
    parse_index = next(
        (index for index, line in enumerate(lines) if "build_revision" in line), None
    )
    assert parse_index is not None, (
        "launcher 必須解析 /api/health 回應 JSON 的 build_revision 欄位（不得只看 HTTP 狀態）"
    )
    families = _trace_revision_var_families(lines)
    compared_index = None
    for index, line in enumerate(lines):
        if "!=" not in line and " = " not in line:
            continue
        tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line))
        if (tokens & families["health"]) and (tokens & families["derived"]):
            compared_index = index
            break
    assert compared_index is not None, (
        "launcher 必須將 health JSON 解析出的 revision 與注入的 build revision 精確比對"
    )
    ready_index = next(
        (
            index
            for index, line in enumerate(lines)
            if re.search(r"\b(?:info|success)\s+\"", line) and re.search(r"就緒|ready", line)
        ),
        None,
    )
    assert ready_index is not None and ready_index > compared_index, (
        "launcher 只能在 health revision 精確相符之後才宣告 ready"
    )


def test_launcher_cleanup_never_uses_broad_process_kills():
    text = "\n".join(_launcher_lines())
    assert "pkill" not in text, "禁止 pkill：只能終止自己啟動的 process"
    assert "killall" not in text, "禁止 killall：只能終止自己啟動的 process"
    for line in _launcher_lines():
        if re.search(r"(?<![\w-])kill\b", line):
            assert "lsof" not in line, "禁止以 port 反查（lsof）終止不明 process"
            assert "$" in line, "kill 必須針對自己啟動的 PID 變數，不得依名稱/port 終止不明 process"


def test_launcher_failure_paths_terminate_only_the_backend_it_started():
    lines = _launcher_lines()
    pid_vars = _trace_owned_pid_vars(lines)
    kill_indices = [
        index
        for index, line in enumerate(lines)
        if re.search(r"(?<![\w-])kill\b(?!\s+-0\b)", line)
        and any(var in line for var in pid_vars)
    ]
    assert kill_indices, (
        "launcher 在 mismatch/parse failure/timeout/early-exit 時必須 kill 自己啟動的 backend PID；"
        "目前失敗路徑直接 exit，會遺留 child process"
    )


def test_launcher_logs_root_host_port_data_dir_and_build_revision():
    logged = "\n".join(
        line
        for line in _launcher_lines()
        if re.search(r"\b(?:info|success|error)\s+\"", line)
    )
    assert re.search(r"\$\{?PORT\b", logged), "launcher 必須記錄實際 port"
    assert re.search(r"\$\{?HOST\b", logged), "launcher 必須記錄 host"
    assert re.search(r"\$\{?DATA_DIR\b", logged), "launcher 必須記錄實際 DATA_DIR"
    assert "PROJECT_ROOT" in logged, "launcher 必須記錄 repo root"
    assert re.search(r"(?:MEETINGSCRIBE_)?BUILD_REVISION", logged), (
        "launcher 必須記錄 build revision"
    )
