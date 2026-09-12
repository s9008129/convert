#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CHECK-07 Apple ASR scoped true-E2E harness（T20260912-2242-01，PLAN_REVISION 1）。

驗收問題（單一）：**Mac 上的「新上傳」是否真的走 Apple SpeechAnalyzer 本機轉錄，
且 helper 全程只被呼叫一次、無 fallback、無暫存殘留。**

與 `scripts/e2e/run_owned_e2e.py` 的關係與**刻意差異**（必須明示，避免誤讀證據）：
- 重用其 owned-child 手法：free port → 隔離 `DATA_DIR` → 以 `start_new_session`
  啟動並「擁有」uvicorn child → 只 `killpg` 自己建立的 process group。
- **刻意不套用其 clean-worktree gate**：那個 gate 是 T20260827-1127-01 為了
  「build revision 身分」的決策有效性而設；本任務的驗收問題是引擎路由與 helper
  呼叫次數，實作曲線必然未提交。provenance（HEAD sha／dirty entry 數）改為
  **記錄**而非 gating，並在報告中明示此偏離。
- **不判定 summarization 成敗**：本機 Ollama 無模型是環境事實，與本變更無關；
  `completed + summary_failed=true` 是產品合法 fallback 終態。本 harness 只驗
  ASR 階段與觀測面，summary 狀態原樣記錄、不 gating。

用法：
    uv run python .agent/tasks/T20260912-2242-01-apple-speech-analyzer-asr/e2e/run_apple_asr_e2e.py \
        --audio /tmp/apple-e2e/meeting-30min.mp3 \
        --attempt .agent/tasks/T20260912-2242-01-apple-speech-analyzer-asr/e2e/attempt-01

退出碼：0 = CORE checks 全數 pass；1 = 任一 CORE check fail。
僅使用 stdlib 與既有依賴（httpx 為後端既有依賴）。
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[4]
TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled"}

APPLE_TRANSCRIBE_OK_RE = re.compile(
    r"apple transcribe ok \| text_chars=(?P<text_chars>\d+) \| segment_count=(?P<segment_count>\d+) "
    r"\| elapsed=(?P<elapsed>[\d.]+)s \| rtf=(?P<rtf>[\d.]+) \| helper_invocations=(?P<helper_invocations>\d+) "
    r"\| conversion=(?P<conversion>\S+)"
)
APPLE_METADATA_OBSERVABILITY_RE = re.compile(r"ASR 引擎觀測：(?P<metadata>\{.*\})")
APPLE_FALLBACK_RE = re.compile(r"Apple 引擎失敗|改用 mlx_whisper|改用 transformers|改用 faster_whisper")
APPLE_TEMP_RESIDUE_RE = re.compile(r"^\..+\.[0-9a-f]{12}\.apple\.(?:wav|m4a)$")


# ---------------------------------------------------------------------------
# 基礎工具
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pick_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def collect_apple_temp_residue(data_dir: Path, since: float) -> list:
    """掃描 DATA_DIR 與系統 temp 內、本次執行後才出現的 Apple 暫存檔。"""

    residues = []
    candidates = [data_dir, Path("/tmp"), Path("/var/folders")]
    for root in candidates:
        if not root.exists():
            continue
        try:
            iterator = root.rglob("*")
            for path in iterator:
                try:
                    if not path.is_file() or not APPLE_TEMP_RESIDUE_RE.match(path.name):
                        continue
                    if path.stat().st_mtime >= since:
                        residues.append(str(path))
                except OSError:
                    continue
        except OSError:
            continue
    return sorted(set(residues))


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="CHECK-07 Apple ASR scoped true-E2E")
    parser.add_argument("--audio", type=Path, required=True, help="長音檔（≥27min MP3）")
    parser.add_argument("--attempt", type=Path, required=True, help="append-only attempt 目錄")
    parser.add_argument("--runtime-dir", type=Path, default=None, help="raw artifacts（backend.log／transcript）")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--health-timeout", type=float, default=180.0)
    parser.add_argument("--task-timeout", type=float, default=1800.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--expect-phrase", default="", help="逐字稿必須包含的片語（可重複）")
    args = parser.parse_args()

    attempt_dir = args.attempt if args.attempt.is_absolute() else REPO_ROOT / args.attempt
    audio_path = args.audio if args.audio.is_absolute() else REPO_ROOT / args.audio
    runtime_dir = (
        args.runtime_dir
        if args.runtime_dir and args.runtime_dir.is_absolute()
        else REPO_ROOT / (args.runtime_dir or "data/cache/e2e-apple-asr")
    )
    if attempt_dir.exists() and any(attempt_dir.iterdir()):
        print(f"[FAIL] attempt 目錄已存在且非空（append-only）：{attempt_dir}", file=sys.stderr)
        return 1
    attempt_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    data_dir = runtime_dir / "backend_data"
    for sub in ("uploads", "outputs", "cache"):
        (data_dir / sub).mkdir(parents=True, exist_ok=True)

    started_at = time.time()
    started_iso = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started_at))
    host = args.host
    port = args.port or pick_free_port(host)
    base_url = f"http://{host}:{port}"
    backend_log_path = runtime_dir / "backend.log"

    head_sha = git_output("rev-parse", "HEAD")
    dirty_entries = [line for line in git_output("status", "--porcelain").splitlines() if line.strip()]
    if not audio_path.exists():
        print(f"[FAIL] 音檔不存在：{audio_path}", file=sys.stderr)
        return 1
    expected_audio_sha = sha256_file(audio_path)

    provenance = {
        "head_sha": head_sha,
        "dirty_entry_count": len(dirty_entries),
        "dirty_entries": dirty_entries,
        "clean_worktree_gate_applied": False,
        "clean_worktree_gate_rationale": (
            "run_owned_e2e.py 的 clean gate 服務 T20260827-1127-01 的 build-revision 身分驗收；"
            "本任務驗收問題為引擎路由與 helper 呼叫次數，工作樹必然帶實作曲線，改以記錄 provenance 取代 gating。"
        ),
        "audio_path": str(audio_path),
        "audio_sha256": expected_audio_sha,
        "audio_bytes": audio_path.stat().st_size,
    }
    save_json(attempt_dir / "provenance.json", provenance)
    print(f"[INFO] HEAD={head_sha} dirty_entries={len(dirty_entries)} audio_sha256={expected_audio_sha[:12]}…")

    child_env = os.environ.copy()
    child_env.update(
        {
            "DATA_DIR": str(data_dir),
            "MEETINGSCRIBE_BUILD_REVISION": head_sha,
            "ASR_BACKEND": "auto",  # 明確 auto：本 E2E 驗的就是 Mac auto 預設路由
            "LOG_LEVEL": "DEBUG",  # 讓 worker stderr（內含 apple transcribe ok 觀測行）進 parent log
            "PYTHONIOENCODING": "utf-8",
        }
    )
    child_env.pop("APPLE_SPEECH_CLI_PATH", None)

    checks = {}
    failures = []
    observations = {}
    proc = None
    log_handle = open(backend_log_path, "wb")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", host, "--port", str(port)],
            cwd=str(REPO_ROOT),
            env=child_env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=(os.name == "posix"),
        )
        checks["backend_started"] = True
        print(f"[INFO] backend child pid={proc.pid} port={port} DATA_DIR={data_dir}")

        client = httpx.Client(timeout=httpx.Timeout(60.0, read=600.0))
        try:
            # ---------- gate 1：health（Mac 完整模式，含真實 probe）----------
            health = None
            deadline = time.monotonic() + args.health_timeout
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    failures.append(f"backend child 提前結束（exit={proc.returncode}）")
                    break
                try:
                    resp = client.get(f"{base_url}/api/health")
                    if resp.status_code == 200:
                        health = resp.json()
                        break
                except (httpx.HTTPError, OSError):
                    pass
                time.sleep(1.0)
            if health is None:
                failures.append("health gate 逾時（/api/health 未回 200）")
                save_json(attempt_dir / "health_snapshot.json", {"ok": False})
                return _finalize(attempt_dir, checks, failures, observations, backend_log_path)
            save_json(attempt_dir / "health_snapshot.json", health)
            checks["health_ok"] = True

            device_info = health.get("device_info") or {}
            observations["health_backend"] = health.get("asr_backend") or health.get("backend")
            observations["health_accelerator"] = device_info.get("accelerator")
            apple_helper = device_info.get("apple_helper") or {}
            observations["apple_helper"] = {
                "supported": apple_helper.get("supported"),
                "available": apple_helper.get("available"),
                "path": apple_helper.get("path"),
                "reason": apple_helper.get("reason"),
            }
            if observations["health_accelerator"] == "apple-neural":
                checks["health_accelerator_apple_neural"] = True
            else:
                failures.append(
                    f"health device_info.accelerator={observations['health_accelerator']!r}，預期 'apple-neural'"
                )
            if apple_helper.get("supported") is True and apple_helper.get("available") is True:
                checks["health_apple_helper_available"] = True
            else:
                failures.append(f"health apple_helper 未回報可用：{observations['apple_helper']}")

            # ---------- gate 2：上傳 → task_id ----------
            with open(audio_path, "rb") as handle:
                resp = client.post(
                    f"{base_url}/api/upload",
                    files={"file": (audio_path.name, handle, "audio/mpeg")},
                    data={"processing_mode": "local"},
                )
            if resp.status_code != 200:
                failures.append(f"上傳失敗：HTTP {resp.status_code} {resp.text[:500]}")
                save_json(attempt_dir / "upload_response.json", {"status_code": resp.status_code, "body": resp.text[:2000]})
                return _finalize(attempt_dir, checks, failures, observations, backend_log_path)
            upload = resp.json()
            task_id = str(upload.get("task_id"))
            save_json(attempt_dir / "upload_response.json", upload)
            checks["upload_ok"] = True
            print(f"[INFO] upload ok：task_id={task_id}")

            # ---------- gate 3：task 終態 ----------
            task = None
            status = None
            deadline = time.monotonic() + args.task_timeout
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    failures.append(f"backend child 提前結束（exit={proc.returncode}）")
                    break
                try:
                    resp = client.get(f"{base_url}/api/tasks/{task_id}")
                except (httpx.HTTPError, OSError) as exc:
                    failures.append(f"查詢任務失敗：{type(exc).__name__}: {exc}")
                    break
                if resp.status_code == 200:
                    task = resp.json()
                    status = str(task.get("status", "")).lower()
                    if status in TERMINAL_TASK_STATUSES:
                        break
                time.sleep(args.poll_interval)
            if task is None or status not in TERMINAL_TASK_STATUSES:
                failures.append(f"任務未在逾時內取得終態（最後狀態 {status!r}）")
                return _finalize(attempt_dir, checks, failures, observations, backend_log_path)
            save_json(attempt_dir / "task_final.json", task)
            observations["task_status"] = status
            observations["summary_failed"] = task.get("summary_failed")
            observations["task_duration_seconds"] = task.get("duration_seconds")
            if status == "completed":
                checks["task_completed"] = True
            else:
                failures.append(f"任務終態 {status}（非 completed）")

            # ---------- gate 4：逐字稿內容 ----------
            resp = client.get(f"{base_url}/api/tasks/{task_id}/transcript")
            if resp.status_code != 200:
                failures.append(f"取逐字稿失敗：HTTP {resp.status_code}")
            else:
                # `/tasks/{id}/transcript` 回傳 text/plain FileResponse（非 JSON）
                text = resp.text or ""
                (runtime_dir / "transcript.txt").write_text(text, encoding="utf-8")
                observations["transcript_chars"] = len(text)
                observations["transcript_head"] = text[:160]
                if len(text.strip()) >= 100:
                    checks["transcript_nonempty"] = True
                else:
                    failures.append(f"逐字稿過短（{len(text)} 字元）")
                for phrase in [p for p in args.expect_phrase if p]:
                    if phrase in text:
                        checks[f"transcript_contains:{phrase}"] = True
                    else:
                        failures.append(f"逐字稿缺少預期片語：{phrase!r}")
        finally:
            client.close()
    finally:
        log_handle.close()
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except OSError:
                pass
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except OSError:
                    pass
        checks["owned_child_cleaned"] = proc is None or proc.poll() is not None

    return _finalize(attempt_dir, checks, failures, observations, backend_log_path, started_at=started_at, data_dir=data_dir)


def _finalize(
    attempt_dir: Path,
    checks: dict,
    failures: list,
    observations: dict,
    backend_log_path: Path,
    *,
    started_at: float = None,
    data_dir: Path = None,
) -> int:
    """從 backend.log 萃取 Apple 觀測證據 → 判 CORE verdict → 寫報告。"""

    log_text = ""
    if backend_log_path.exists():
        log_text = backend_log_path.read_text(encoding="utf-8", errors="replace")

    transcribe_hits = [m.groupdict() for m in APPLE_TRANSCRIBE_OK_RE.finditer(log_text)]
    metadata_hits = [m.group("metadata") for m in APPLE_METADATA_OBSERVABILITY_RE.finditer(log_text)]
    fallback_hits = [line.strip()[:240] for line in log_text.splitlines() if APPLE_FALLBACK_RE.search(line)]

    observations["apple_transcribe_ok_count"] = len(transcribe_hits)
    observations["apple_transcribe_ok"] = transcribe_hits[-1] if transcribe_hits else None
    observations["apple_metadata_log_lines"] = metadata_hits
    observations["apple_fallback_log_lines"] = fallback_hits
    observations["backend_log_bytes"] = len(log_text.encode("utf-8"))

    # `helper_invocations`／`conversion_reason` 的權威觀測面是 parent 端
    # `ASR 引擎觀測：{...}`（跨隔離子程序邊界的凍結 metadata）；worker 內
    # `apple transcribe ok` 行（若 LOG_LEVEL 讓 worker stderr 進 parent log）為
    # 次要佐證。兩者取先出現者。
    metadata_payload = {}
    if metadata_hits:
        try:
            metadata_payload = json.loads(metadata_hits[-1])
        except json.JSONDecodeError:
            metadata_payload = {}

    observed_invocations = metadata_payload.get("helper_invocations")
    observed_conversion = metadata_payload.get("conversion_reason")
    if observed_invocations is None and transcribe_hits:
        observed_invocations = transcribe_hits[-1].get("helper_invocations")
    if observed_conversion is None and transcribe_hits:
        observed_conversion = transcribe_hits[-1].get("conversion")
    observations["observed_helper_invocations"] = observed_invocations
    observations["observed_conversion_reason"] = observed_conversion

    if str(observed_invocations) == "1" and len(transcribe_hits) <= 1 and len(metadata_hits) <= 1:
        checks["helper_invocations_single_call"] = True
    else:
        failures.append(
            "helper 呼叫次數觀測失敗：helper_invocations="
            f"{observed_invocations!r}（metadata 行數={len(metadata_hits)}、"
            f"transcribe ok 行數={len(transcribe_hits)}；預期各 ≤1 且值為 1）"
        )
    if observed_conversion == "fragile_native_container":
        checks["conversion_reason_fragile_native_container"] = True
    else:
        failures.append(
            f"conversion reason={observed_conversion!r}，預期 fragile_native_container"
        )
    if not fallback_hits:
        checks["no_apple_fallback"] = True
    else:
        failures.append(f"出現 Apple fallback 觀測行（{len(fallback_hits)} 行）")
    if metadata_hits:
        checks["apple_metadata_observable_in_parent_log"] = True
        observations["apple_metadata"] = metadata_payload or metadata_hits[-1]

    if data_dir is not None and started_at is not None:
        residues = collect_apple_temp_residue(data_dir, started_at)
        observations["apple_temp_residues"] = residues
        if not residues:
            checks["no_apple_temp_residue"] = True
        else:
            failures.append(f"Apple 暫存殘留：{residues}")

    core_checks = [
        "backend_started",
        "health_ok",
        "health_accelerator_apple_neural",
        "health_apple_helper_available",
        "upload_ok",
        "task_completed",
        "transcript_nonempty",
        "helper_invocations_single_call",
        "conversion_reason_fragile_native_container",
        "no_apple_fallback",
        "no_apple_temp_residue",
    ]
    core_failed = [name for name in core_checks if not checks.get(name)]
    verdict = "PASS" if not core_failed and not failures else "FAIL"

    report = {
        "task_id": "T20260912-2242-01-apple-speech-analyzer-asr",
        "check": "CHECK-07（Mac 實機 ≥27min MP3；Apple 引擎；helper 單次呼叫；無 fallback；無殘留）",
        "verdict": verdict,
        "core_checks": {name: bool(checks.get(name)) for name in core_checks},
        "supporting_checks": {
            name: value for name, value in checks.items() if name not in core_checks
        },
        "core_failed": core_failed,
        "failures": failures,
        "observations": observations,
        "backend_log_path": str(backend_log_path),
        "harness": str(Path(__file__).resolve()),
    }
    save_json(attempt_dir / "report.json", report)
    lines = [
        f"# CHECK-07 Apple ASR E2E — verdict {verdict}",
        "",
        f"- task: {report['task_id']}（PLAN_REVISION 1）",
        f"- harness: {report['harness']}",
        f"- core failed: {core_failed or '（無）'}",
        "",
        "## CORE checks",
    ]
    lines += [f"- {'PASS' if bool(checks.get(name)) else 'FAIL'} — {name}" for name in core_checks]
    lines += ["", "## Observations", "```json", json.dumps(observations, ensure_ascii=False, indent=2), "```"]
    if failures:
        lines += ["", "## Failures"] + [f"- {item}" for item in failures]
    (attempt_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[{verdict}] CHECK-07；core failed={core_failed or '（無）'}")
    if failures:
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
    print(f"[INFO] report={attempt_dir / 'report.json'}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
