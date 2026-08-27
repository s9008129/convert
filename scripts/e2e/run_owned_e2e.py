#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Owned-process true E2E runner（acceptance harness；Revision 3 WAVE-02 加固）。

任務：T20260827-1127-01-lmstudio-e2e-empty-summary（plan CHANGE_MAP ``CM-02``）。

設計要點（plan CM-02 / handoff WAVE-02）：
- 選擇 free port、隔離 DATA_DIR、注入 MEETINGSCRIBE_BUILD_REVISION，啟動並
  「擁有」backend child process（child 以 start_new_session 建立獨立 process
  group，僅 killpg 該 group，不觸及任何其他 process）。
- 固定 gate order（handoff WAVE-02）：clean HEAD／audio／DATA_DIR preflight
  （任何 failure 不啟動 backend，land verdict FAIL，exit 1）→ owned child →
  health exact revision（mismatch 立即終止 child、不 upload）→ 唯一 loaded
  LLM model/instance → UI ready（browser）/API upload → actual stored bytes
  SHA → task completed + summary_failed=false → transcript/DOCX 正式性 →
  bounded metrics + ending model snapshot → owned cleanup。
- `--upload-mode api|browser`（default api，維持既有 CLI 相容）：browser 模式
  不 POST 音檔；所有 pre-upload gates 通過後 stdout flush 一行
  `BROWSER_E2E_READY`（含 base_url/port/expected revision），再 bounded 解析
  isolated backend 既有「檔案上傳成功 … 任務ID」log 行，要求唯一 mapping。
  API/browser 共用同一套 task／hash／formal DOCX／metrics／model 驗收 helper。
- 證據分層（DEC-EVIDENCE）：--artifacts-dir（預設 tracked evidence 區）只放
  redacted metadata/hash（health snapshot、model snapshot、upload_response
  metadata、task_final、sha256 manifest、run_summary）；backend.log、
  transcript、DOCX 與 backend DATA_DIR 等 raw artifacts 一律放 gitignored
  runtime dir（--runtime-dir，或自動導到 REPO_ROOT/data/cache/e2e/<attempt>），
  對應關係記錄在 run_summary.json。
- `completed + summary_failed=true` 仍是產品合法 fallback 終態；但本 harness
  的 acceptance verdict 必須判 FAIL（SEMANTIC_INVARIANTS #1，產品語意不變）。
- --smoke 維持既有語意：啟動 → health gate → 模型快照（唯讀記錄，不可達不
  veto）→ 乾淨終止；不上傳、不 render acceptance verdict。

用法（macOS；需先 uv sync --frozen）：
  # 最小煙霧驗證（啟動 → health gate → 終止，不上傳）
  uv run python scripts/e2e/run_owned_e2e.py --smoke

  # 完整 true E2E（Stage 05 獨立驗收用）
  uv run python scripts/e2e/run_owned_e2e.py \
      --audio /path/to/meeting.m4a \
      --artifacts-dir .agent/tasks/<task>/e2e/attempt-01 \
      --runtime-dir data/cache/e2e/attempt-01 \
      --upload-mode browser

  # 只印執行計畫，不啟動
  uv run python scripts/e2e/run_owned_e2e.py --smoke --dry-run

僅使用 stdlib 與既有依賴（httpx 為後端既有依賴）；不新增第三方依賴。
"""

import argparse
import hashlib
import html
import io
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import zipfile
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

# Revision 3 WAVE-02 驗收常數（plan CM-01 #8 / DEGRADATION_AND_GATE_TESTS）。
LOCAL_LLM_MAX_MERGE_ROUNDS = 3
SEMANTIC_ATTEMPTS_FACTOR = 2
DOCX_OOZIP_MAGIC = b"PK\x03\x04"
FORMAL_LABEL = "會議紀錄"
FALLBACK_LABEL_MARKER = "逐字稿"
FALLBACK_DOCX_MARKERS = (
    "逐字稿（會議紀錄生成失敗）",
    "逐字稿(會議紀錄生成失敗)",
    "摘要生成失敗",
    "Traceback",
    "RuntimeError",
    "錯誤訊息",
)
GENERAL_REQUIRED_SECTIONS = ("一、報告事項", "二、討論事項", "決議", "三、主席裁示事項")
UPLOAD_SUCCESS_PATTERN = re.compile(
    r"檔案上傳成功:\s*(?P<original_filename>.+?)\s*->\s*(?P<stored_filename>\S+),"
    r"\s*任務ID:\s*(?P<task_id>\S+)"
)
METRICS_KEY_VALUE_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(-?\d+)")


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


def capture_model_snapshot(
    lmstudio_base_url: str,
    artifacts_dir: Path,
    captured_at: str,
    filename: str = "model_snapshot.json",
) -> dict:
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
    save_json(artifacts_dir / filename, snapshot)
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


# ---------------------------------------------------------------------------
# WAVE-02 acceptance helpers（pure/testable；API 與 browser mode 共用）
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_status_porcelain() -> str:
    """git status --porcelain（唯讀）。以 module attribute 參照呼叫，便於測試注入。"""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"無法取得 git status：{result.stderr.strip()}")
    return result.stdout


def check_clean_worktree(porcelain_output: str) -> dict:
    """pure helper：解析 porcelain 輸出，判定 worktree 是否 clean。"""
    entries = [line for line in (porcelain_output or "").splitlines() if line.strip()]
    return {
        "clean": len(entries) == 0,
        "dirty_entry_count": len(entries),
        "dirty_entries": entries,
    }


def validate_data_dir(data_dir: Path) -> list:
    """DATA_DIR hard preflight（CM-01 #6）：必須可建立為目錄且可寫。

    回傳明確 failure 訊息列表；任何 failure 都必須在 backend 啟動前 fail closed。
    """
    failures = []
    try:
        if data_dir.exists() and not data_dir.is_dir():
            failures.append(f"DATA_DIR 無效：{data_dir} 已存在且不是目錄（必須為目錄）")
            return failures
        data_dir.mkdir(parents=True, exist_ok=True)
    except (FileExistsError, PermissionError, OSError) as exc:
        failures.append(f"DATA_DIR 無法建立或不可寫：{data_dir}（{type(exc).__name__}: {exc}）")
        return failures
    probe = data_dir / ".e2e-write-probe"
    try:
        probe.write_text("probe", encoding="utf-8")
        probe.unlink()
    except (PermissionError, OSError) as exc:
        failures.append(f"DATA_DIR 不可寫（無法寫入 probe 檔）：{data_dir}（{type(exc).__name__}: {exc}）")
    return failures


def resolve_runtime_dir(artifacts_dir: Path, override: Optional[Path] = None) -> Path:
    """RAW 敏感 runtime 檔位置（DEC-EVIDENCE：raw 不落 tracked 目錄）。

    - 呼叫者明示 --runtime-dir → 直接使用（相對路徑以 REPO_ROOT 為基準）。
    - artifacts dir 已位於 REPO_ROOT/data/cache（gitignored runtime）→ 沿用。
    - artifacts dir 在 repo 外（如 tmp 隔離環境）→ 沿用（呼叫者自行管理隔離）。
    - 其他（含 tracked .agent 證據區）→ 導到 REPO_ROOT/data/cache/e2e/<attempt-name>。
    """
    if override is not None:
        return override if override.is_absolute() else (REPO_ROOT / override)
    try:
        rel = artifacts_dir.relative_to(REPO_ROOT)
    except ValueError:
        return artifacts_dir
    if len(rel.parts) >= 2 and rel.parts[0] == "data" and rel.parts[1] == "cache":
        return artifacts_dir
    return REPO_ROOT / "data" / "cache" / "e2e" / (artifacts_dir.name or "attempt")


def _normalized_loaded_llm_view(snapshot: dict) -> list:
    return [
        {
            "model_key": model.get("model_key"),
            "instances": [
                {
                    "instance_id": instance.get("instance_id"),
                    "context_length": instance.get("context_length"),
                }
                for instance in model.get("instances") or []
            ],
        }
        for model in snapshot.get("loaded_llm_models") or []
    ]


def validate_model_inventory_unique(snapshot: dict) -> list:
    """CM-01 #5：loaded LLM 必須恰好一 model 且恰好一 instance（否則不可歸因）。"""
    if not snapshot.get("reachable"):
        return [
            "model snapshot 不可達：loaded LLM inventory 無法歸因（必須恰好一 model／一 instance）"
        ]
    models = _normalized_loaded_llm_view(snapshot)
    failures = []
    if len(models) != 1:
        failures.append(
            f"model inventory 違規：loaded LLM model 數量={len(models)}（必須恰好一個 model）"
        )
    instance_count = sum(len(model["instances"]) for model in models)
    if instance_count != 1:
        failures.append(
            f"model snapshot 違規：loaded LLM instance 數量={instance_count}（必須恰好一個 instance）"
        )
    return failures


def validate_model_snapshot_consistency(start: Optional[dict], end: Optional[dict]) -> list:
    """CM-01 #5：run 前後 model key/instance/context snapshot 必須完全一致。"""
    if not start or not end:
        return ["model snapshot 一致性無法驗證：start 或 ending snapshot 缺失"]
    if not start.get("reachable"):
        return ["model snapshot 一致性無法驗證：starting snapshot 不可達"]
    if not end.get("reachable"):
        return ["model snapshot 一致性無法驗證：ending snapshot 不可達"]
    start_view = start["loaded_llm_models"]
    end_view = end["loaded_llm_models"]
    if start_view != end_view:
        return [
            "ending model snapshot 與 starting 不一致（model/instance/context changed）："
            f"start={start_view} end={end_view}"
        ]
    return []


def validate_task_terminal(task: dict) -> list:
    """CM-01 #2：acceptance 終態要求 completed 且 summary_failed is False。

    `completed + summary_failed=true` 仍是產品合法 fallback 終態（語意不變），
    但正式會議紀錄 E2E 必須判 FAIL（RC-3B／SEMANTIC_INVARIANTS #1）。
    """
    failures = []
    status = str(task.get("status", "")).lower()
    if status != "completed":
        failures.append(f"任務終態為 {status or '未知'}（非 completed）")
    if "summary_failed" not in task:
        failures.append("任務 JSON 缺少 summary_failed 欄位（無法證明非 transcript fallback）")
    elif task.get("summary_failed") is not False:
        failures.append(
            "summary_failed=true：transcript fallback 已安全保存，但正式會議紀錄生成失敗——"
            "E2E 驗收必須判 FAIL（產品 fallback 語意不變）"
        )
    return failures


def validate_upload_response(upload: dict) -> list:
    failures = []
    if not upload.get("task_id"):
        failures.append("上傳回應缺少 task_id")
    return failures


def redact_upload_response(upload: dict) -> dict:
    """tracked 證據只保留 upload metadata；不含任何檔案位元組或長文內容。"""
    if not isinstance(upload, dict):
        return {"non_json_upload_response": True}
    return {
        key: upload[key]
        for key in (
            "task_id",
            "filename",
            "file_size",
            "queue_position",
            "estimated_wait_seconds",
            "message",
        )
        if key in upload
    }


def extract_docx_text(docx_bytes: bytes) -> str:
    """stdlib OOXML 文字抽取（word/document.xml 的 w:t 串接）。

    機械檢查用途；語意/視覺 QA 仍由 Stage 05 執行（plan CM-02）。
    """
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as archive:
            if "word/document.xml" not in archive.namelist():
                return ""
            document_xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
    except (zipfile.BadZipFile, KeyError, OSError):
        return ""
    runs = re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", document_xml, flags=re.DOTALL)
    return html.unescape("".join(runs))


def _section_has_substance(text: str, pattern: str) -> bool:
    """必要 section pattern 之後、到下一個必要 section 之間需有非空內容。"""
    index = text.find(pattern)
    if index < 0:
        return False
    rest = text[index + len(pattern):]
    end = len(rest)
    for other in GENERAL_REQUIRED_SECTIONS:
        if other == pattern:
            continue
        position = rest.find(other)
        if 0 <= position < end:
            end = position
    return bool(rest[:end].strip())


def validate_formal_docx_bytes(docx_bytes: bytes, content_disposition: Optional[str]) -> list:
    """CM-01 #3：Content-Disposition 正式 label + OOZIP header + OOXML fallback 拒絕。"""
    failures = []
    disposition = content_disposition or ""
    if not disposition:
        failures.append("DOCX 下載回應缺少 Content-Disposition，無法驗證正式下載檔名")
    else:
        if FALLBACK_LABEL_MARKER in disposition:
            failures.append(
                f"Content-Disposition 下載檔名含 fallback label（{FALLBACK_LABEL_MARKER}）：{disposition[:160]}"
            )
        if FORMAL_LABEL not in disposition:
            failures.append(
                f"Content-Disposition 下載檔名缺少正式 label「{FORMAL_LABEL}」：{disposition[:160]}"
            )
    if not docx_bytes.startswith(DOCX_OOZIP_MAGIC):
        failures.append("DOCX 下載位元組不是 OOXML/OOZIP header（PK\\x03\\x04）")
        return failures
    text = extract_docx_text(docx_bytes)
    if not text.strip():
        failures.append("DOCX OOXML 無法解析出文字內容")
        return failures
    fallback_hits = [marker for marker in FALLBACK_DOCX_MARKERS if marker in text]
    if fallback_hits:
        failures.append(
            "DOCX OOXML 內容為 transcript fallback：偵測到 fallback title／錯誤標記（"
            + "、".join(fallback_hits)
            + "）"
        )
    if FORMAL_LABEL not in text:
        failures.append(f"DOCX OOXML 缺少 formal title「{FORMAL_LABEL}」")
    for section in GENERAL_REQUIRED_SECTIONS:
        if not _section_has_substance(text, section):
            failures.append(f"DOCX OOXML 的 general 模板 section「{section}」缺少非空後續內容")
    return failures


def parse_upload_success_lines(log_text: str) -> list:
    """解析既有 backend log 的「檔案上傳成功 … 任務ID」行（不新增 endpoint）。"""
    matches = []
    for match in UPLOAD_SUCCESS_PATTERN.finditer(log_text or ""):
        matches.append(
            {
                "original_filename": match.group("original_filename").strip(),
                "stored_filename": match.group("stored_filename").strip(),
                "task_id": match.group("task_id").strip(),
            }
        )
    return matches


def parse_browser_upload_log_mapping(log_text: str) -> tuple:
    """CM-01 #7：唯一 upload mapping（stored filename, task_id）。

    0 筆（逾時未上傳）或 >1 筆（本輪多任務）皆 raise ValueError → 判 FAIL。
    """
    matches = parse_upload_success_lines(log_text)
    if len(matches) != 1:
        raise ValueError(
            f"upload log mapping 必須恰好一筆，實際 {len(matches)} 筆"
            "（0 筆=逾時／未上傳，>1 筆=本輪出現多個 task/upload；皆 FAIL）"
        )
    match = matches[0]
    return match["stored_filename"], match["task_id"]


def wait_for_unique_upload_mapping(
    backend_log_path: Path,
    timeout_seconds: float,
    poll_interval: float = 2.0,
) -> tuple:
    """bounded poll isolated backend log，直到出現唯一 upload mapping。"""
    deadline = time.monotonic() + max(float(timeout_seconds), 0.0)
    while True:
        log_text = ""
        try:
            log_text = backend_log_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass
        matches = parse_upload_success_lines(log_text)
        if len(matches) == 1:
            return matches[0]["stored_filename"], matches[0]["task_id"]
        if len(matches) > 1:
            raise ValueError(
                f"偵測到 {len(matches)} 筆 upload mapping（>1 筆——本輪出現多個 task/upload，FAIL）"
            )
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"bounded 等待逾時（{timeout_seconds}s）：0 筆 upload mapping"
                f"（Browser 尚未上傳，或 backend log 格式與既有『檔案上傳成功 … 任務ID』行不符）"
            )
        time.sleep(max(min(poll_interval, max(deadline - time.monotonic(), 0.1)), 0.1))


def parse_pipeline_metrics_lines(log_text: str) -> list:
    """解析 backend log 的 structured success metrics 行（integer-typed key=value）。"""
    entries = []
    for line in (log_text or "").splitlines():
        if "pipeline metrics" not in line:
            continue
        pairs = {
            key: int(value)
            for key, value in METRICS_KEY_VALUE_PATTERN.findall(line)
        }
        entries.append({"raw_line": line, "pairs": pairs})
    return entries


def validate_pipeline_metrics(log_text: str) -> list:
    """CM-01 #8：metrics 必須存在、整數型別、有界，且無截斷／非收斂成功假象。"""
    text = log_text or ""
    failures = []
    entries = parse_pipeline_metrics_lines(text)
    if not entries:
        failures.append(
            "structured metrics 缺失：backend log 找不到『本地摘要 pipeline metrics』行"
            "（缺少 logical_generations／semantic_attempts／merge_rounds 驗收證據）"
        )
    for entry in entries:
        pairs = entry["pairs"]
        for key in ("logical_generations", "semantic_attempts", "merge_rounds"):
            if key not in pairs:
                failures.append(f"metrics invalid：缺整數欄位 {key}")
        logical = pairs.get("logical_generations")
        attempts = pairs.get("semantic_attempts")
        rounds = pairs.get("merge_rounds")
        if logical is not None and logical <= 0:
            failures.append(f"metrics 違規：logical_generations={logical} 必須 > 0")
        if logical is not None and attempts is not None and attempts > SEMANTIC_ATTEMPTS_FACTOR * logical:
            failures.append(
                f"metrics 違規：semantic_attempts={attempts} > {SEMANTIC_ATTEMPTS_FACTOR} * "
                f"logical_generations={logical}（超出 E2E aggregate 上限）"
            )
        if rounds is not None and rounds > LOCAL_LLM_MAX_MERGE_ROUNDS:
            failures.append(
                f"metrics 違規：merge_rounds={rounds} > LOCAL_LLM_MAX_MERGE_ROUNDS={LOCAL_LLM_MAX_MERGE_ROUNDS}"
            )
    if re.search(r"max_tokens=1\b", text):
        failures.append("diagnostics 違規：偵測到 max_tokens=1（生成預算退化；metrics/diagnostics gate FAIL）")
    if "硬截斷" in text or "hard truncation" in text.lower():
        failures.append(
            "diagnostics 違規：偵測到硬截斷標記（後段內容未進入最終生成的收斂成功假象）"
        )
    if "LOCAL_LLM_MERGE_NOT_CONVERGED" in text:
        failures.append(
            "diagnostics 違規：偵測到 LOCAL_LLM_MERGE_NOT_CONVERGED（merge non-convergence 成功假象）"
        )
    return failures


def run_full_e2e(
    client: httpx.Client,
    base_url: str,
    *,
    upload_mode: str,
    audio_path: Optional[Path],
    processing_mode: str,
    expected_audio_sha: Optional[str],
    data_dir: Path,
    evidence_dir: Path,
    runtime_dir: Path,
    backend_log_path: Path,
    task_timeout_seconds: float,
    poll_interval: float,
    browser_upload_timeout: float,
) -> tuple:
    """上傳（API）或偵測（browser）→ stored bytes SHA → 終態 → 下載 → 正式性驗收。

    API 與 browser mode 共用同一條 monitor/validation path（plan CM-02）：
    browser 模式不 POST 音檔，僅 bounded 解析 isolated backend 既有
    upload-success log 取得唯一 stored filename + task_id。
    回傳 (checks, failure_reasons)。
    """
    checks = {}
    failure_reasons = []
    stored_filename = None
    task_id = None

    # ---------- stage 1：唯一 upload mapping（stored filename + task_id）----------
    if upload_mode == "browser":
        try:
            stored_filename, task_id = wait_for_unique_upload_mapping(
                backend_log_path,
                timeout_seconds=browser_upload_timeout,
                poll_interval=min(poll_interval, 2.0),
            )
            checks["browser_upload_detected"] = True
            print(f"[INFO] browser upload mapping：stored={stored_filename} task_id={task_id}")
        except (ValueError, TimeoutError) as exc:
            failure_reasons.append(f"Browser upload-log mapping 驗證失敗：{exc}")
            return checks, failure_reasons
    else:
        with open(audio_path, "rb") as fh:
            resp = client.post(
                f"{base_url}/api/upload",
                files={"file": (audio_path.name, fh)},
                data={"processing_mode": processing_mode},
            )
        if resp.status_code != 200:
            failure_reasons.append(f"上傳失敗：HTTP {resp.status_code} {resp.text[:500]}")
            save_json(
                evidence_dir / "upload_response.json",
                {"status_code": resp.status_code, "body": resp.text[:2000]},
            )
            return {"upload_ok": False}, failure_reasons
        upload = resp.json()
        save_json(evidence_dir / "upload_response.json", redact_upload_response(upload))
        response_failures = validate_upload_response(upload)
        if response_failures:
            failure_reasons.extend(response_failures)
            return {"upload_ok": False}, failure_reasons
        task_id = str(upload.get("task_id"))
        checks["upload_ok"] = True
        # stored filename 以 isolated backend 既有 upload-success log 唯一映射取得
        #（與 browser mode 同一個 helper → 兩種 mode 一套成功語意）
        try:
            log_stored, log_task_id = wait_for_unique_upload_mapping(
                backend_log_path, timeout_seconds=10.0, poll_interval=0.5
            )
        except (ValueError, TimeoutError) as exc:
            failure_reasons.append(f"upload log mapping 唯一性驗證失敗：{exc}")
            return checks, failure_reasons
        if log_task_id != task_id:
            failure_reasons.append(
                f"upload log mapping 與上傳回應不一致：response task_id={task_id} "
                f"log 任務ID={log_task_id}"
            )
            return checks, failure_reasons
        stored_filename = log_stored

    # ---------- stage 2：actual stored bytes SHA-256 比對（CM-01 #4）----------
    stored_upload_sha = None
    if not stored_filename:
        failure_reasons.append("stored bytes SHA 驗證失敗：缺少 stored filename（upload mapping 未取得）")
    else:
        stored_path = data_dir / "uploads" / stored_filename
        if not stored_path.exists():
            failure_reasons.append(
                f"stored bytes SHA 驗證失敗：找不到 isolated 上傳檔 {stored_path}"
            )
        else:
            stored_upload_sha = sha256_file(stored_path)
            if expected_audio_sha is None:
                failure_reasons.append(
                    f"stored bytes SHA 驗證失敗：expected audio SHA-256 缺失（actual={stored_upload_sha}）"
                )
            elif stored_upload_sha != expected_audio_sha:
                failure_reasons.append(
                    "stored upload bytes SHA-256 mismatch："
                    f"expected={expected_audio_sha} actual={stored_upload_sha}"
                    "（DATA_DIR/uploads 實際位元組與來源音檔不同）"
                )
            else:
                checks["stored_upload_sha_match"] = True

    # ---------- stage 3：poll task 終態 → completed + summary_failed=false ----------
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
            break
        time.sleep(poll_interval)
    if task is None or status not in TERMINAL_TASK_STATUSES:
        failure_reasons.append(
            f"任務 {task_id} 無法在逾時內取得終態（最後狀態：{status!r}）"
        )
        _write_redacted_manifest(
            evidence_dir, expected_audio_sha, stored_upload_sha, None, None
        )
        return checks, failure_reasons
    save_json(evidence_dir / "task_final.json", task)
    if status != "completed":
        failure_reasons.append(f"任務終態為 {status}（非 completed）")
        _write_transcript_and_docx(
            client, base_url, task_id, runtime_dir, checks, failure_reasons
        )
        _write_redacted_manifest(
            evidence_dir, expected_audio_sha, stored_upload_sha, None, None
        )
        return checks, failure_reasons
    checks["task_completed"] = True
    terminal_failures = validate_task_terminal(task)
    if terminal_failures:
        failure_reasons.extend(terminal_failures)
    else:
        checks["task_summary_failed_false"] = True

    # ---------- stage 4：下載 transcript/DOCX（保存 Content-Disposition）----------
    transcript_disposition = _download_transcript(
        client, base_url, task_id, runtime_dir, checks, failure_reasons
    )
    docx_bytes, docx_disposition = _download_docx(
        client, base_url, task_id, runtime_dir, checks, failure_reasons
    )

    # ---------- stage 5：formal DOCX 驗收（CM-01 #3，API/browser 共用）----------
    if checks.get("docx_downloaded"):
        docx_failures = validate_formal_docx_bytes(docx_bytes, docx_disposition)
        if docx_failures:
            failure_reasons.extend(docx_failures)
        else:
            checks["formal_docx_valid"] = True

    # ---------- stage 6：bounded structured metrics + diagnostics（CM-01 #8）----------
    try:
        log_text = backend_log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        log_text = ""
    metrics_failures = validate_pipeline_metrics(log_text)
    if metrics_failures:
        failure_reasons.extend(metrics_failures)
    else:
        checks["metrics_valid"] = True

    # ---------- redacted hash manifest（DEC-EVIDENCE）----------
    transcript_sha = sha256_file(runtime_dir / "transcript.txt") if checks.get("transcript_downloaded") else None
    docx_sha = sha256_file(runtime_dir / "meeting_record.docx") if checks.get("docx_downloaded") else None
    _write_redacted_manifest(
        evidence_dir, expected_audio_sha, stored_upload_sha, transcript_sha, docx_sha
    )
    return checks, failure_reasons


def _download_transcript(
    client: httpx.Client,
    base_url: str,
    task_id: str,
    runtime_dir: Path,
    checks: dict,
    failure_reasons: list,
) -> Optional[str]:
    resp = client.get(f"{base_url}/api/tasks/{task_id}/transcript")
    if resp.status_code == 200:
        (runtime_dir / "transcript.txt").write_bytes(resp.content)
        checks["transcript_downloaded"] = True
        return resp.headers.get("content-disposition")
    failure_reasons.append(f"逐字稿下載失敗：HTTP {resp.status_code}")
    return None


def _download_docx(
    client: httpx.Client,
    base_url: str,
    task_id: str,
    runtime_dir: Path,
    checks: dict,
    failure_reasons: list,
) -> tuple:
    resp = client.get(f"{base_url}/api/tasks/{task_id}/result", params={"format": "docx"})
    if resp.status_code == 200:
        (runtime_dir / "meeting_record.docx").write_bytes(resp.content)
        checks["docx_downloaded"] = True
        return resp.content, resp.headers.get("content-disposition")
    failure_reasons.append(f"DOCX 下載失敗：HTTP {resp.status_code}")
    return None, None


def _write_redacted_manifest(
    evidence_dir: Path,
    source_audio_sha: Optional[str],
    stored_upload_sha: Optional[str],
    transcript_sha: Optional[str],
    docx_sha: Optional[str],
) -> None:
    save_json(
        evidence_dir / "sha256_manifest.json",
        {
            "generated_at": taipei_now().isoformat(),
            "source_audio_sha256": source_audio_sha,
            "stored_upload_sha256": stored_upload_sha,
            "transcript_sha256": transcript_sha,
            "meeting_record_docx_sha256": docx_sha,
            "note": "tracked 證據僅存 hash/redacted metadata；raw payload 於 gitignored runtime dir",
        },
    )


def _write_preflight_failure_summary(
    artifacts_dir: Path,
    started_at: str,
    plan: dict,
    failure_reasons: list,
) -> None:
    """preflight 失敗也要 land verdict（run_summary.json + exit 1），但不啟動 backend。"""
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        save_json(
            artifacts_dir / "run_summary.json",
            {
                "plan": plan,
                "started_at": started_at,
                "finished_at": taipei_now().isoformat(),
                "child_pid": None,
                "checks": {"backend_started": False},
                "failure_reasons": failure_reasons,
                "verdict": "FAIL",
                "note": "preflight fail closed：backend 未啟動、無任何 upload",
            },
        )
    except OSError as exc:
        print(f"[WARN] 無法寫入 preflight run_summary：{exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Owned-process true E2E runner：free port + 隔離 DATA_DIR + build revision gate，"
            "啟動並擁有 backend child process（完整 true E2E 請在 Stage 05 獨立驗收執行）"
        )
    )
    parser.add_argument(
        "--audio", type=Path, default=None,
        help="音檔路徑（完整 true E2E 必填，作為 expected SHA authority；--smoke 時忽略）",
    )
    parser.add_argument(
        "--artifacts-dir", type=Path, default=None,
        help="append-only attempt 目錄（預設：evidence/stage05/attempt-<台北時間>；已存在即拒絕；只放 redacted 證據）",
    )
    parser.add_argument(
        "--runtime-dir", type=Path, default=None,
        help="raw 敏感 runtime 位置：backend.log／transcript／DOCX／backend DATA_DIR"
        "（預設：artifacts 位於 gitignored data/cache 或 repo 外時沿用之，"
        "否則自動導到 data/cache/e2e/<attempt-name>）",
    )
    parser.add_argument("--data-dir", type=Path, default=None, help="隔離 DATA_DIR（預設：<runtime>/backend_data）")
    parser.add_argument(
        "--upload-mode", default="api", choices=["api", "browser"],
        help="上傳模式：api=runner 直接 POST（預設，相容既有）；browser=不 POST 音檔，"
        "gates 通過後 flush BROWSER_E2E_READY 並 bounded 解析既有 upload-success log（CM-02）",
    )
    parser.add_argument("--host", default="127.0.0.1", help="backend 監聽 host（預設 127.0.0.1）")
    parser.add_argument("--port", type=int, default=None, help="backend 端口（預設自動選 free port）")
    parser.add_argument("--expected-revision", default=None, help="expected Git revision（預設 git rev-parse HEAD）")
    parser.add_argument("--processing-mode", default="local", choices=["local", "cloud"], help="上傳處理模式（預設 local）")
    parser.add_argument("--health-timeout", type=float, default=120.0, help="health gate 逾時秒數（預設 120）")
    parser.add_argument("--task-timeout", type=float, default=7200.0, help="任務終態 poll 逾時秒數（預設 7200）")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="health/task poll 間隔秒數（預設 5）")
    parser.add_argument(
        "--browser-upload-timeout", type=float, default=7200.0,
        help="browser 模式 bounded 等待唯一 upload mapping 的秒數（預設 7200）",
    )
    parser.add_argument(
        "--smoke", action="store_true",
        help="煙霧模式：啟動 → health gate → 模型快照（唯讀記錄）→ 乾淨終止（不上傳）",
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
            else (REPO_ROOT / args.artifacts_dir)
        ).resolve()
    else:
        attempt_stamp = taipei_now().strftime("%Y%m%d-%H%M%S")
        artifacts_dir = (DEFAULT_ARTIFACTS_BASE / f"attempt-{attempt_stamp}").resolve()
    runtime_dir = resolve_runtime_dir(artifacts_dir, args.runtime_dir)
    data_dir = args.data_dir or (runtime_dir / "backend_data")
    if not data_dir.is_absolute():
        data_dir = REPO_ROOT / data_dir
    audio_path = None
    if args.audio is not None:
        audio_path = args.audio if args.audio.is_absolute() else (REPO_ROOT / args.audio)

    plan = {
        "mode": "smoke" if args.smoke else "full",
        "dry_run": args.dry_run,
        "upload_mode": args.upload_mode,
        "inject_revision": not args.no_inject_revision,
        "host": host,
        "port": port,
        "expected_build_revision": expected_revision,
        "artifacts_dir": str(artifacts_dir),
        "runtime_dir": str(runtime_dir),
        "data_dir": str(data_dir),
        "audio": str(audio_path) if audio_path else None,
        "processing_mode": args.processing_mode,
        "health_timeout_seconds": args.health_timeout,
        "task_timeout_seconds": args.task_timeout,
        "poll_interval_seconds": args.poll_interval,
        "browser_upload_timeout_seconds": args.browser_upload_timeout,
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
    #（先建立 evidence dir，再執行 preflight——DATA_DIR 驗證會 mkdir(parents=True)，
    # 不可反過來把 attempt 目錄當副作用先建立）
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"[FAIL] attempt 目錄已存在（append-only）：{artifacts_dir}", file=sys.stderr)
        return 1

    # ---------- hard preflight（固定 gate order：clean HEAD → audio → DATA_DIR）----------
    # 任何 preflight failure：不 Popen、run_summary.json land verdict FAIL、exit 1。
    preflight_failures = []
    expected_audio_sha = None
    if not args.smoke:
        try:
            clean = check_clean_worktree(git_status_porcelain())
            if not clean["clean"]:
                preflight_failures.append(
                    "repo worktree 不是 clean（E2E decision-validity gate）："
                    f"{clean['dirty_entry_count']} 個未提交變更——請先形成 clean HEAD 再驗收"
                )
        except Exception as exc:
            preflight_failures.append(f"clean worktree gate 無法執行：{type(exc).__name__}: {exc}")
        if audio_path is None or not audio_path.exists():
            preflight_failures.append(f"--audio 音檔不存在：{audio_path}（audio 存在性屬啟動前 hard preflight）")
        elif not os.access(audio_path, os.R_OK):
            preflight_failures.append(f"--audio 音檔不可讀：{audio_path}")
        else:
            expected_audio_sha = sha256_file(audio_path)
    data_dir_gate_failures = validate_data_dir(data_dir)
    preflight_failures.extend(f"DATA_DIR gate：{msg}" for msg in data_dir_gate_failures)

    if preflight_failures:
        failure_reasons = list(preflight_failures)
        print("[FAIL] preflight fail closed（backend 未啟動）：", file=sys.stderr)
        for reason in failure_reasons:
            print(f"  - {reason}", file=sys.stderr)
        _write_preflight_failure_summary(artifacts_dir, started_at, plan, failure_reasons)
        return 1

    runtime_dir.mkdir(parents=True, exist_ok=True)
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
    backend_log_path = runtime_dir / "backend.log"

    actual_revision = None
    proc = None
    checks = {}
    failure_reasons = []
    log_handle = open(backend_log_path, "ab")
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
        print(f"[INFO] /api/health 200，build_revision={actual_revision!r}")
        if actual_revision != expected_revision:
            # post-health revision gate：mismatch → 立即終止 child、不 capture 後續、不 upload
            failure_reasons.append(
                "build revision mismatch："
                f"expected={expected_revision!r} actual={actual_revision!r}"
                "（fail closed：不進入 UI ready／API upload）"
            )
        else:
            checks["build_revision_match"] = True
            snapshot_start = capture_model_snapshot(
                lmstudio_base_url, artifacts_dir, taipei_now().isoformat(), filename="model_snapshot.json"
            )
            checks["model_snapshot_captured"] = True
            if args.smoke:
                # smoke：唯讀記錄 + 回報；snapshot 不可達/非唯一不 veto（既有語意）
                print(
                    f"[INFO] model snapshot reachable={snapshot_start.get('reachable')} "
                    f"unique_loaded_llm_count={snapshot_start.get('unique_loaded_llm_count')}"
                )
            else:
                model_gate_failures = validate_model_inventory_unique(snapshot_start)
                if model_gate_failures:
                    failure_reasons.extend(model_gate_failures)
                else:
                    checks["model_inventory_unique"] = True
                    if args.upload_mode == "browser":
                        # 所有 pre-upload gates 已通過：flush 單行機器可讀 ready 訊號
                        print(
                            "BROWSER_E2E_READY "
                            f"base_url={base_url} port={port} expected_revision={expected_revision} "
                            f"expected_audio_sha256={expected_audio_sha} "
                            f"evidence_dir={artifacts_dir} runtime_dir={runtime_dir}",
                            flush=True,
                        )
                    more_checks, more_failures = run_full_e2e(
                        client=httpx.Client(timeout=600.0),
                        base_url=base_url,
                        upload_mode=args.upload_mode,
                        audio_path=audio_path,
                        processing_mode=args.processing_mode,
                        expected_audio_sha=expected_audio_sha,
                        data_dir=data_dir,
                        evidence_dir=artifacts_dir,
                        runtime_dir=runtime_dir,
                        backend_log_path=backend_log_path,
                        task_timeout_seconds=args.task_timeout,
                        poll_interval=args.poll_interval,
                        browser_upload_timeout=args.browser_upload_timeout,
                    )
                    checks.update(more_checks)
                    failure_reasons.extend(more_failures)
                    snapshot_end = capture_model_snapshot(
                        lmstudio_base_url, artifacts_dir, taipei_now().isoformat(), filename="model_snapshot_end.json"
                    )
                    consistency_failures = validate_model_snapshot_consistency(snapshot_start, snapshot_end)
                    checks["model_snapshot_consistent"] = not consistency_failures
                    failure_reasons.extend(consistency_failures)
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
    if args.smoke:
        required = required_smoke
    else:
        required = required_smoke + [
            "model_inventory_unique",
            "upload_ok",
            "stored_upload_sha_match",
            "task_completed",
            "task_summary_failed_false",
            "transcript_downloaded",
            "docx_downloaded",
            "formal_docx_valid",
            "metrics_valid",
            "model_snapshot_consistent",
        ]
    missing = [name for name in required if not checks.get(name)]
    if missing:
        failure_reasons.append(f"缺少必要檢查：{missing}")

    verdict = "PASS" if not failure_reasons else "FAIL"
    summary = {
        "mode": "smoke" if args.smoke else "full",
        "upload_mode": args.upload_mode,
        "started_at": started_at,
        "finished_at": finished_at,
        "port": port,
        "child_pid": proc.pid if proc else None,
        "expected_build_revision": expected_revision,
        "actual_build_revision": actual_revision,
        "artifacts_dir": str(artifacts_dir),
        "runtime_dir": str(runtime_dir),
        "backend_log_path": str(backend_log_path),
        "data_dir": str(data_dir),
        "source_audio_sha256": expected_audio_sha,
        "checks": checks,
        "failure_reasons": failure_reasons,
        "verdict": verdict,
    }
    save_json(artifacts_dir / "run_summary.json", summary)
    print(f"[{'OK' if verdict == 'PASS' else 'FAIL'}] verdict={verdict}，artifacts：{artifacts_dir}，runtime：{runtime_dir}")
    for reason in failure_reasons:
        print(f"  - {reason}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())