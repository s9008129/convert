#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Owned-process true E2E runner（SUPPORTING，非 gating）。

任務：T20260827-1127-01-lmstudio-e2e-empty-summary（plan CHANGE_MAP 第 5 項：
Runtime provenance and E2E ownership）。

設計要點（plan：Independent owned-process true E2E 第 1、2、8 點）：
- 選擇 free port、隔離 temp DATA_DIR、注入 MEETINGSCRIBE_BUILD_REVISION，
  啟動並「擁有」backend child process（記錄 child PID，只終止自己啟動的
  process——child 以 start_new_session 建立獨立 process group，僅 kill 該 group）。
- Health gate：/api/health 的 build_revision 必須等於 expected Git revision；
  一般 startup/health 不因 unknown revision 失敗（null 允許），revision
  mismatch 只在本 runner（E2E harness）視為 acceptance failure。
- 記錄唯一 loaded model/instance snapshot（LM Studio /api/v1/models，
  唯讀 GET，不修改 inventory）。
- 完整 true E2E：參數化音檔上傳 → poll task 終態 → 下載逐字稿與 DOCX，
  artifacts 保存到 append-only attempt 目錄（已存在即拒絕，不覆寫舊證據）。
- 不在此執行昂貴 true E2E 作為一般 startup gate；完整 true E2E 由 Stage 05
  獨立驗收執行。--smoke 只做啟動 → health gate → 模型快照 → 乾淨終止。

用法（macOS；需先 uv sync --frozen）：
  # 最小煙霧驗證（啟動 → health gate → 終止，不上傳）
  uv run python scripts/e2e/run_owned_e2e.py --smoke

  # 完整 true E2E（Stage 05 獨立驗收用）
  uv run python scripts/e2e/run_owned_e2e.py \
      --audio /path/to/meeting.m4a \
      --artifacts-dir .agent/tasks/<task>/evidence/stage05/attempt-01

  # 只印執行計畫，不啟動
  uv run python scripts/e2e/run_owned_e2e.py --smoke --dry-run

僅使用 stdlib 與既有依賴（httpx 為後端既有依賴）；不新增第三方依賴。
"""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
TAIPEI = ZoneInfo("Asia/Taipei")
# 與 backend/core/platform_config.py 的 darwin-arm64 native 預設一致；
# runner 不 import backend 模組，避免載入 production settings 副作用。
DEFAULT_LMSTUDIO_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_ARTIFACTS_BASE = (
    REPO_ROOT / ".agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/evidence/stage05"
)
TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled"}


def taipei_now() -> datetime:
    return datetime.now(TAIPEI)


def pick_free_port(host: str) -> int:
    """向作業系統索取一個 free port（bind :0 後立即釋放）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def resolve_expected_revision(override: Optional[str]) -> str:
    """expected revision：--expected-revision 優先，否則 git rev-parse HEAD。"""
    if override:
        return override.strip()
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"無法取得 Git HEAD revision：{result.stderr.strip()}")
    return result.stdout.strip()


def normalize_base_url(value: Optional[str]) -> str:
    """正規化 LM Studio root URL（兼容舊 /v1 suffix），空值用 native 預設。"""
    value = (value or "").strip()
    if not value:
        return DEFAULT_LMSTUDIO_BASE_URL
    value = value.rstrip("/")
    if value.lower().endswith("/v1"):
        value = value[:-3].rstrip("/")
    return value or DEFAULT_LMSTUDIO_BASE_URL


def build_child_env(
    port: int,
    data_dir: Path,
    expected_revision: str,
    inject_revision: bool = True,
) -> dict:
    """組裝 child process 環境：隔離 DATA_DIR + 注入 build revision + 同源端口。

    inject_revision=False 僅供驗證 gate 本身：不注入 revision 時，
    health 的 build_revision 應為 null，gate 必須判 mismatch → FAIL。
    """
    child_env = dict(os.environ)
    pythonpath = child_env.get("PYTHONPATH")
    child_env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{pythonpath}" if pythonpath else str(REPO_ROOT)
    )
    if not inject_revision:
        child_env.pop("MEETINGSCRIBE_BUILD_REVISION", None)
    child_env.update(
        {
            "DATA_DIR": str(data_dir),
            # 同一端口值同時給 uvicorn --port 與應用環境（RC-5 actual port logging）
            "SERVICE_PORT": str(port),
            "MEETINGSCRIBE_PORT": str(port),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    if inject_revision:
        child_env["MEETINGSCRIBE_BUILD_REVISION"] = expected_revision
    return child_env


def terminate_owned_process(proc: subprocess.Popen) -> None:
    """只終止本 runner 啟動的 child（其所屬 process group）。

    child 以 start_new_session=True 啟動，pgid == child pid；killpg 不會
    波及其他 process。SIGTERM → 寬限 → SIGKILL。
    """
    if proc.poll() is not None:
        return
    if os.name == "posix":
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            return
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
    else:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def capture_model_snapshot(lmstudio_base_url: str, artifacts_dir: Path, captured_at: str) -> dict:
    """唯讀記錄 LM Studio loaded model/instance snapshot；不可達不視為啟動失敗。

    同時兼容兩種回應 shape：
    - LM Studio native：{"models": [{key, type, loaded_instances: [{id, config.context_length}]}]}
    - OpenAI 相容：{"data": [{id, ...}]}
    """
    snapshot = {"captured_at": captured_at, "base_url": lmstudio_base_url}
    try:
        resp = httpx.get(f"{lmstudio_base_url}/api/v1/models", timeout=10)
        resp.raise_for_status()
        raw = resp.json()
        loaded_llm_models = []
        loaded_instance_ids = []
        # LM Studio native shape：models[].loaded_instances（type=llm 且已載入）
        for model in raw.get("models", []) if isinstance(raw, dict) else []:
            if not isinstance(model, dict):
                continue
            instances = model.get("loaded_instances") or []
            if model.get("type") == "llm" and instances:
                loaded = []
                for inst in instances:
                    if not isinstance(inst, dict):
                        continue
                    instance_id = inst.get("id")
                    loaded_instance_ids.append(instance_id)
                    context_length = (inst.get("config") or {}).get("context_length")
                    loaded.append(
                        {"instance_id": instance_id, "context_length": context_length}
                    )
                loaded_llm_models.append({"model_key": model.get("key"), "instances": loaded})
        # OpenAI 相容 shape：data[].id
        openai_ids = [
            m.get("id") for m in (raw.get("data") or []) if isinstance(m, dict) and m.get("id")
        ]
        snapshot.update(
            {
                "reachable": True,
                "loaded_llm_models": loaded_llm_models,
                "loaded_instance_ids": sorted({i for i in loaded_instance_ids if i}),
                "unique_loaded_llm_count": len(loaded_llm_models),
                "openai_compat_model_ids": openai_ids,
                "raw_response": raw,
            }
        )
    except Exception as exc:  # snapshot 是證據記錄，不是 gate
        snapshot.update({"reachable": False, "error": f"{type(exc).__name__}: {exc}"})
    save_json(artifacts_dir / "model_snapshot.json", snapshot)
    return snapshot


def wait_for_health(
    proc: subprocess.Popen,
    base_url: str,
    timeout_seconds: float,
    poll_interval: float,
) -> dict:
    """輪詢 /api/health 直到 200 或逾時；child 提前結束立即失敗。"""
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"backend child（PID {proc.pid}）在 health gate 前提前結束（exit={proc.returncode}）"
            )
        try:
            resp = httpx.get(
                f"{base_url}/api/health",
                params={"quick": "true"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                return resp.json()
            last_error = RuntimeError(f"/api/health 回應 {resp.status_code}")
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(poll_interval)
    raise RuntimeError(f"health gate 逾時（{timeout_seconds}s），最後錯誤：{last_error}")


def run_full_e2e(
    client: httpx.Client,
    base_url: str,
    audio_path: Path,
    artifacts_dir: Path,
    processing_mode: str,
    task_timeout_seconds: float,
    poll_interval: float,
) -> tuple:
    """上傳 → poll 終態 → 下載逐字稿與 DOCX；回傳 (checks, failure_reasons)。"""
    checks = {}
    failure_reasons = []

    with open(audio_path, "rb") as fh:
        resp = client.post(
            f"{base_url}/api/upload",
            files={"file": (audio_path.name, fh)},
            data={"processing_mode": processing_mode},
        )
    if resp.status_code != 200:
        failure_reasons.append(f"上傳失敗：HTTP {resp.status_code} {resp.text[:500]}")
        save_json(
            artifacts_dir / "upload_response.json",
            {"status_code": resp.status_code, "body": resp.text[:2000]},
        )
        return {"upload_ok": False}, failure_reasons
    upload = resp.json()
    save_json(artifacts_dir / "upload_response.json", upload)
    task_id = upload.get("task_id")
    if not task_id:
        failure_reasons.append("上傳回應缺少 task_id")
        return {"upload_ok": False}, failure_reasons
    checks["upload_ok"] = True

    # Poll 到終態
    deadline = time.monotonic() + task_timeout_seconds
    task = None
    status = None
    while time.monotonic() < deadline:
        resp = client.get(f"{base_url}/api/tasks/{task_id}")
        if resp.status_code == 200:
            task = resp.json()
            status = str(task.get("status", "")).lower()
            if status in TERMINAL_TASK_STATUSES:
                break
        else:
            failure_reasons.append(f"查詢任務失敗：HTTP {resp.status_code}")
        time.sleep(poll_interval)
    if task is None:
        failure_reasons.append(f"任務 {task_id} 無法取得狀態")
        return checks, failure_reasons
    save_json(artifacts_dir / "task_final.json", task)
    if status not in TERMINAL_TASK_STATUSES:
        failure_reasons.append(f"任務逾時未達終態（最後狀態：{status}）")
        return checks, failure_reasons
    if status != "completed":
        failure_reasons.append(f"任務終態為 {status}（非 completed）")
        return checks, failure_reasons
    checks["task_completed"] = True

    # 下載逐字稿與 DOCX
    resp = client.get(f"{base_url}/api/tasks/{task_id}/transcript")
    if resp.status_code == 200:
        (artifacts_dir / "transcript.txt").write_bytes(resp.content)
        checks["transcript_downloaded"] = True
    else:
        failure_reasons.append(f"逐字稿下載失敗：HTTP {resp.status_code}")

    resp = client.get(f"{base_url}/api/tasks/{task_id}/result", params={"format": "docx"})
    if resp.status_code == 200:
        (artifacts_dir / "meeting_record.docx").write_bytes(resp.content)
        checks["docx_downloaded"] = True
    else:
        failure_reasons.append(f"DOCX 下載失敗：HTTP {resp.status_code}")

    return checks, failure_reasons


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Owned-process true E2E runner：free port + 隔離 DATA_DIR + build revision gate，"
            "啟動並擁有 backend child process（完整 true E2E 請在 Stage 05 獨立驗收執行）"
        )
    )
    parser.add_argument(
        "--audio", type=Path, default=None,
        help="上傳音檔路徑（完整 true E2E 必填；--smoke 時忽略）",
    )
    parser.add_argument(
        "--artifacts-dir", type=Path, default=None,
        help="append-only attempt 目錄（預設：evidence/stage05/attempt-<台北時間>；已存在即拒絕）",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="隔離 DATA_DIR（預設：<artifacts>/backend_data）")
    parser.add_argument("--host", default="127.0.0.1", help="backend 監聽 host（預設 127.0.0.1）")
    parser.add_argument("--port", type=int, default=None, help="backend 端口（預設自動選 free port）")
    parser.add_argument("--expected-revision", default=None, help="expected Git revision（預設 git rev-parse HEAD）")
    parser.add_argument("--processing-mode", default="local", choices=["local", "cloud"], help="上傳處理模式（預設 local）")
    parser.add_argument("--health-timeout", type=float, default=120.0, help="health gate 逾時秒數（預設 120）")
    parser.add_argument("--task-timeout", type=float, default=7200.0, help="任務終態 poll 逾時秒數（預設 7200）")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="health/task poll 間隔秒數（預設 5）")
    parser.add_argument(
        "--smoke", action="store_true",
        help="煙霧模式：啟動 → health gate → 模型快照 → 乾淨終止（不上傳）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只印執行計畫，不啟動 backend、不建立目錄")
    parser.add_argument(
        "--no-inject-revision", action="store_true",
        help="gate 自我驗證用：不注入 MEETINGSCRIBE_BUILD_REVISION；"
        "backend 應回報 null，gate 必須判 mismatch → verdict FAIL（exit 1）",
    )
    args = parser.parse_args()

    if not args.smoke and args.audio is None:
        parser.error("完整 true E2E 需要 --audio；若只想驗證啟動與 health gate 請加 --smoke")

    started_at = taipei_now().isoformat()
    host = args.host
    port = args.port or pick_free_port(host)
    expected_revision = resolve_expected_revision(args.expected_revision)

    if args.artifacts_dir is not None:
        artifacts_dir = (
            args.artifacts_dir
            if args.artifacts_dir.is_absolute()
            else (REPO_ROOT / args.artifacts_dir).resolve()
        )
    else:
        attempt_stamp = taipei_now().strftime("%Y%m%d-%H%M%S")
        artifacts_dir = DEFAULT_ARTIFACTS_BASE / f"attempt-{attempt_stamp}"
    data_dir = args.data_dir or (artifacts_dir / "backend_data")

    plan = {
        "mode": "smoke" if args.smoke else "full",
        "dry_run": args.dry_run,
        "inject_revision": not args.no_inject_revision,
        "host": host,
        "port": port,
        "expected_build_revision": expected_revision,
        "artifacts_dir": str(artifacts_dir),
        "data_dir": str(data_dir),
        "audio": str(args.audio) if args.audio else None,
        "processing_mode": args.processing_mode,
        "health_timeout_seconds": args.health_timeout,
        "task_timeout_seconds": args.task_timeout,
        "poll_interval_seconds": args.poll_interval,
    }
    if args.dry_run:
        print(
            json.dumps(
                {"plan": plan, "dry_run": True, "note": "未啟動 backend、未建立任何目錄"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    # append-only attempt 目錄：已存在即拒絕，不覆寫舊 E2E 證據
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"[FAIL] attempt 目錄已存在（append-only）：{artifacts_dir}", file=sys.stderr)
        return 1
    data_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("uploads", "outputs", "cache"):
        (data_dir / sub).mkdir(parents=True, exist_ok=True)

    child_env = build_child_env(
        port,
        data_dir,
        expected_revision,
        inject_revision=not args.no_inject_revision,
    )
    lmstudio_base_url = normalize_base_url(child_env.get("LMSTUDIO_BASE_URL"))
    base_url = f"http://{host}:{port}"

    actual_revision = None
    proc = None
    checks = {}
    failure_reasons = []
    log_handle = open(artifacts_dir / "backend.log", "ab")
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
        print(f"[INFO] backend child PID={proc.pid} port={port} DATA_DIR={data_dir}")
        print(f"[INFO] expected build_revision={expected_revision}")

        health = wait_for_health(proc, base_url, args.health_timeout, args.poll_interval)
        actual_revision = health.get("build_revision")
        save_json(
            artifacts_dir / "health_snapshot.json",
            {
                "captured_at": taipei_now().isoformat(),
                "url": f"{base_url}/api/health",
                "expected_build_revision": expected_revision,
                "actual_build_revision": actual_revision,
                "revision_match": actual_revision == expected_revision,
                "raw_response": health,
            },
        )
        checks["health_ok"] = True
        checks["build_revision_match"] = actual_revision == expected_revision
        if not checks["build_revision_match"]:
            failure_reasons.append(
                f"build revision mismatch：expected={expected_revision!r} actual={actual_revision!r}"
            )
        print(f"[INFO] /api/health 200，build_revision={actual_revision!r}")

        capture_model_snapshot(lmstudio_base_url, artifacts_dir, taipei_now().isoformat())
        checks["model_snapshot_captured"] = True

        if not args.smoke:
            more_checks, more_failures = run_full_e2e(
                client=httpx.Client(timeout=600.0),
                base_url=base_url,
                audio_path=args.audio,
                artifacts_dir=artifacts_dir,
                processing_mode=args.processing_mode,
                task_timeout_seconds=args.task_timeout,
                poll_interval=args.poll_interval,
            )
            checks.update(more_checks)
            failure_reasons.extend(more_failures)
    except Exception as exc:
        failure_reasons.append(f"{type(exc).__name__}: {exc}")
    finally:
        if proc is not None:
            terminate_owned_process(proc)
            checks["child_terminated"] = proc.poll() is not None
            print(f"[INFO] backend child（PID {proc.pid}）已終止（exit={proc.poll()}）")
        log_handle.close()

    finished_at = taipei_now().isoformat()
    required_smoke = ["backend_started", "health_ok", "build_revision_match", "child_terminated"]
    required_full = required_smoke + ["task_completed", "transcript_downloaded", "docx_downloaded"]
    required = required_full if not args.smoke else required_smoke
    missing = [name for name in required if not checks.get(name)]
    if missing:
        failure_reasons.append(f"缺少必要檢查：{missing}")

    verdict = "PASS" if not failure_reasons else "FAIL"
    summary = {
        "mode": "smoke" if args.smoke else "full",
        "started_at": started_at,
        "finished_at": finished_at,
        "port": port,
        "child_pid": proc.pid if proc else None,
        "expected_build_revision": expected_revision,
        "actual_build_revision": actual_revision,
        "artifacts_dir": str(artifacts_dir),
        "data_dir": str(data_dir),
        "checks": checks,
        "failure_reasons": failure_reasons,
        "verdict": verdict,
    }
    save_json(artifacts_dir / "run_summary.json", summary)
    print(f"[{'OK' if verdict == 'PASS' else 'FAIL'}] verdict={verdict}，artifacts：{artifacts_dir}")
    for reason in failure_reasons:
        print(f"  - {reason}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())