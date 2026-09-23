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

  # P4-D：品質儀器接線（observe＝觀察／required＝閘門；預設 off＝完全不量測）
  uv run python scripts/e2e/run_owned_e2e.py \
      --audio /path/to/meeting.m4a --template section_meeting \
      --quality-mode observe \
      --coverage-checklist .agent/tasks/<task>/quality/fact_checklist.json

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import unquote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_taipei_tz(loader=ZoneInfo):
    """建立 Asia/Taipei tzinfo（loader 可注入，預設 zoneinfo.ZoneInfo）。

    Windows 無 IANA tz database（tzdata 未列入依賴）時 ZoneInfo("Asia/Taipei")
    會在 import 直接丟 ZoneInfoNotFoundError；故退回固定 +08:00 位移——台灣自
    1979 年起無日光節約時間，對本 runner 的 now／isoformat／strftime 完全等價。
    """
    try:
        return loader("Asia/Taipei")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=8))


TAIPEI = resolve_taipei_tz()
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
# 模板感知的 DOCX 正式性檢查常數（2026-09-22 v4.8.1，W8）：
# - 只列「章節契約與 general 不同」的模板。``general``、未指定、或**未列於本表**
#   的其他模板一律沿用 ``GENERAL_REQUIRED_SECTIONS``（行為與修正前 byte 級相同；
#   未列表的模板另印一行 log 說明沿用 general 契約，屬已知限制）。
# - section_meeting 的 4 個章節級項目取自 backend/core/templates.py
#   （``_SECTION_MEETING_TEMPLATE`` 的 RecordSectionSpec.presence_pattern／
#   docx_section_pattern 章節白名單），避免 runner 寫死臆測字面。
TEMPLATE_REQUIRED_SECTIONS = {
    "section_meeting": (
        "一、科長轉知",
        "二、科長指示及提醒事項",
        "案由及承辦單位",
        "散會",
    ),
}
GENERAL_TEMPLATE_ID = "general"
# 必要章節的比對樣式（2026-09-22 v4.8.0 修正）：
# 產品契約（backend/core/templates.py 的 required_section_patterns）以容忍空白的樣式
# 驗證章節，例如 ``一、\s*報告事項``；模型輸出「一、 報告事項：」這種頓號後帶空白的
# 寫法是合法輸出路徑。舊版 runner 以字面子字串比對，會把合法紀錄誤判為「缺少章節
# 內容」（實測 attempt-01 的四條 section failure 全部由此而來），因此改為同語意樣式。
def _derive_section_patterns(sections: tuple) -> tuple:
    """由章節字面推導容忍空白樣式（與產品模板契約同語意）。"""
    return tuple(
        (label, re.compile(r"、\s*".join(re.escape(part) for part in label.split("、"))))
        for label in sections
    )


REQUIRED_SECTION_PATTERNS = _derive_section_patterns(GENERAL_REQUIRED_SECTIONS)
TEMPLATE_REQUIRED_SECTION_PATTERNS = {
    template_id: _derive_section_patterns(sections)
    for template_id, sections in TEMPLATE_REQUIRED_SECTIONS.items()
}


UPLOAD_SUCCESS_PATTERN = re.compile(
    r"檔案上傳成功:\s*(?P<original_filename>.+?)\s*->\s*(?P<stored_filename>\S+),"
    r"\s*任務ID:\s*(?P<task_id>\S+)"
)
METRICS_KEY_VALUE_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(-?\d+)")
# backend loguru 以 colorize=True 寫檔（backend/core/logger.py），行內含 ANSI 色碼；
# 解析前必須剝除，避免 task_id 尾端黏上 \x1b[0m 使 URL 建構丟 httpx.InvalidURL
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# ---------------------------------------------------------------------------
# P4-D（W3）：runner 品質閘門（--quality-mode／--coverage-checklist；plan §9.6）
# ---------------------------------------------------------------------------
QUALITY_MODES = ("off", "observe", "required")
QUALITY_INSTRUMENT_TIMEOUT_SECONDS = 120.0
RECORD_QUALITY_INSTRUMENT_PATH = REPO_ROOT / "scripts/e2e/measure_record_quality.py"
COVERAGE_INSTRUMENT_PATH = REPO_ROOT / "scripts/e2e/measure_coverage.py"
# 儀器版本釘死（設計 §2.2）：版本不符 → 不得以未知語意閘門（required fail-closed）
RECORD_QUALITY_TAG_METRIC_VERSION = "tag_traceability-1.1.0"
# body_source_tag_count ≥ 17 屬「來源標註契約」模板族（review attempt-03 N5②）；
# 對映 backend/core/templates.py 的 speaker_traceability=True 模板（現行唯一：
# section_meeting，templates.py:388）。runner 不 import backend → 以常數對齊；
# 新增來源標註模板時必須同步本集合，否則該模板品質門檻會退為觀察值。
QUALITY_SOURCE_TAG_TEMPLATES = frozenset({"section_meeting"})
# 既有門檻值（不得新增、不得放寬；plan §9.6／review attempt-03 N5②）：
# (check 名稱, metrics 欄位（可為巢狀 tuple）, 比較運算子, 門檻值)
QUALITY_TAG_THRESHOLDS = (
    ("quality_table_tag_count_zero", "table_source_tag_count", "eq", 0),
    ("quality_body_tag_count_ok", "body_source_tag_count", "ge", 17),
    ("quality_traceable_tag_ratio_ok", ("tag_traceability", "traceable_tag_ratio"), "ge", 0.95),
    ("quality_on_start_tag_ratio_ok", ("tag_traceability", "on_start_tag_ratio"), "ge", 0.95),
    (
        "quality_on_start_excluding_zero_ok",
        ("tag_traceability", "on_start_tag_ratio_excluding_zero"),
        "ge",
        0.9,
    ),
)
QUALITY_TAG_CHECK_NAMES = tuple(name for name, _field, _op, _value in QUALITY_TAG_THRESHOLDS)
# LM Studio 專屬（snapshot 讀 LM Studio /api/v1/models）；非 lmstudio provider 豁免（W-3）
PROVIDER_SPECIFIC_REQUIRED_CHECKS = ("model_inventory_unique", "model_snapshot_consistent")
# backend log（file_manager.save_result log.info）：「結果已儲存: <檔名>」
RESULT_SAVED_FILENAME_PATTERN = re.compile(r"結果已儲存[:：]\s*(?P<filename>\S+)")


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


def _section_has_substance(text: str, pattern: str, section_patterns=None) -> bool:
    """必要 section pattern 之後、到下一個必要 section 之間需有非空內容。

    v4.8.0（2026-09-22）：比對改走 ``REQUIRED_SECTION_PATTERNS`` 的容忍空白樣式，
    與產品模板契約同語意（見該常數註解）。
    v4.8.1（W8）：``section_patterns`` 可傳入模板專屬的章節樣式集
    （``TEMPLATE_REQUIRED_SECTION_PATTERNS``）；預設維持 general 樣式集，
    故 general／未指定模板的行為不變。
    """
    patterns = REQUIRED_SECTION_PATTERNS if section_patterns is None else section_patterns
    own_pattern = dict(patterns).get(pattern)
    if own_pattern is None:
        own_pattern = re.compile(re.escape(pattern))
    match = own_pattern.search(text)
    if match is None:
        return False
    rest = text[match.end():]
    end = len(rest)
    for other, other_pattern in patterns:
        if other == pattern:
            continue
        other_match = other_pattern.search(rest)
        if other_match is not None and other_match.start() < end:
            end = other_match.start()
    return bool(rest[:end].strip())


def validate_formal_docx_bytes(
    docx_bytes: bytes, content_disposition: Optional[str], template_id: Optional[str] = None
) -> list:
    """CM-01 #3：Content-Disposition 正式 label + OOZIP header + OOXML fallback 拒絕。

    v4.8.1（W8）：``template_id`` 決定必要章節契約——列於 ``TEMPLATE_REQUIRED_SECTIONS``
    的模板（目前僅 ``section_meeting``）以該模板章節判定；``general``／``None``／未列表的
    模板沿用 ``GENERAL_REQUIRED_SECTIONS``（行為 byte 級不變）。修因：驗收場若用
    ``--template section_meeting``，舊版 runner 寫死 general 章節，實際是完整科務會議
    紀錄的 DOCX 永遠被誤判 FAIL（attempt-03 baseline）。
    """
    failures = []
    disposition = content_disposition or ""
    if not disposition:
        failures.append("DOCX 下載回應缺少 Content-Disposition，無法驗證正式下載檔名")
    else:
        # Starlette 對非 ASCII 檔名送出 RFC 5987 `filename*=utf-8''<percent-encoded>`；
        # 必須先還原百分比編碼，否則「20260922184230_會議紀錄.docx」這種**正式**檔名
        # 會被誤判為「缺少正式 label」（實測 attempt-01）。fallback 標籤同理。
        decoded_disposition = unquote(disposition)
        if FALLBACK_LABEL_MARKER in decoded_disposition:
            failures.append(
                f"Content-Disposition 下載檔名含 fallback label（{FALLBACK_LABEL_MARKER}）：{disposition[:160]}"
            )
        if FORMAL_LABEL not in decoded_disposition:
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
    if template_id in TEMPLATE_REQUIRED_SECTIONS:
        required_sections = TEMPLATE_REQUIRED_SECTIONS[template_id]
        section_patterns = TEMPLATE_REQUIRED_SECTION_PATTERNS[template_id]
    else:
        required_sections = GENERAL_REQUIRED_SECTIONS
        section_patterns = REQUIRED_SECTION_PATTERNS
        if template_id and template_id != GENERAL_TEMPLATE_ID:
            # 已知限制（plan rev6 W8）：未建章的模板沒有專屬章節契約，
            # 沿用 general 契約判定；只記錄一行，不改變行為。
            print(
                f"[WARN] DOCX 正式性檢查：模板 {template_id!r} 未列於 TEMPLATE_REQUIRED_SECTIONS，"
                "沿用 general 章節契約（已知限制）",
                file=sys.stderr,
            )
    for section in required_sections:
        if not _section_has_substance(text, section, section_patterns):
            if template_id in TEMPLATE_REQUIRED_SECTIONS:
                failures.append(
                    f"DOCX OOXML 的 {template_id} 模板 section「{section}」缺少非空後續內容"
                )
            else:
                failures.append(f"DOCX OOXML 的 general 模板 section「{section}」缺少非空後續內容")
    return failures


def parse_upload_success_lines(log_text: str) -> list:
    """解析既有 backend log 的「檔案上傳成功 … 任務ID」行（不新增 endpoint）。

    backend log（loguru colorize=True）行內含 ANSI 色碼；先剝除再解析，
    避免 task_id/stored filename 尾端黏上 ANSI 序列。
    """
    matches = []
    clean_text = ANSI_ESCAPE_PATTERN.sub("", log_text or "")
    for match in UPLOAD_SUCCESS_PATTERN.finditer(clean_text):
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


# ---------------------------------------------------------------------------
# P4-D（W3）helpers：品質儀器接線（subprocess；不 import backend）＋事後斷言
# ---------------------------------------------------------------------------

def parse_result_saved_filenames(log_text: str) -> list:
    """解析 backend log 的「結果已儲存: <檔名>」行（file_manager.save_result）。"""
    clean_text = ANSI_ESCAPE_PATTERN.sub("", log_text or "")
    filenames = []
    for match in RESULT_SAVED_FILENAME_PATTERN.finditer(clean_text):
        name = match.group("filename").strip().strip("'\"")
        if name and name not in filenames:
            filenames.append(name)
    return filenames


def resolve_record_markdown(outputs_dir: Path, task_id: str, backend_log_text: str) -> tuple:
    """解析權威 Markdown（P4-D stage 7）：唯一解才採用，歧義不猜。

    1. ``data_dir/outputs/*_<task_id>.md`` 唯一命中（file_manager.save_result 命名契約）。
    2. 否則 bounded fallback：backend log「結果已儲存」行中結尾為 ``_<task_id>.md`` 且存在者。
    3. 仍無法唯一 → ``(None, 原因)``（observe：WARN；required：fail-closed）。
    """
    glob_hits = sorted(path for path in outputs_dir.glob(f"*_{task_id}.md") if path.is_file())
    if len(glob_hits) == 1:
        return glob_hits[0], "outputs glob 唯一命中"
    log_hits = []
    for filename in parse_result_saved_filenames(backend_log_text):
        if not filename.endswith(f"_{task_id}.md"):
            continue
        candidate = outputs_dir / filename
        if candidate.is_file() and candidate not in log_hits:
            log_hits.append(candidate)
    if len(log_hits) == 1:
        return log_hits[0], "backend log「結果已儲存」fallback 唯一命中"
    return None, (
        f"無法唯一決定權威 Markdown（outputs glob 命中 {len(glob_hits)} 筆；"
        f"backend log fallback 命中 {len(log_hits)} 筆）"
    )


def run_quality_instrument(
    script_path: Path,
    args: list,
    *,
    data_dir: Path,
    timeout_seconds: float = QUALITY_INSTRUMENT_TIMEOUT_SECONDS,
) -> dict:
    """以 subprocess 執行既有量尺（runner 不 import backend；顯式傳 DATA_DIR）。

    純 Python／列表引數／``sys.executable``（Windows 相容）；不依賴網路或 LM Studio。
    回傳 ``{exit_code, timed_out, stdout, stderr, error}``；啟動失敗一律 fail-soft 回報。
    """
    env = dict(os.environ)
    env.update(
        {
            "DATA_DIR": str(data_dir),
            "LOG_LEVEL": "CRITICAL",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), *args],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {
            "exit_code": None,
            "timed_out": True,
            "stdout": "",
            "stderr": "",
            "error": f"逾時（{timeout_seconds}s）",
        }
    except Exception as exc:  # fail-soft：任何啟動失敗都回報，不讓 runner 崩潰
        return {
            "exit_code": None,
            "timed_out": False,
            "stdout": "",
            "stderr": "",
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "exit_code": proc.returncode,
        "timed_out": False,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "error": None,
    }


def _load_instrument_json(out_path: Path, result: dict) -> tuple:
    """讀取儀器輸出 JSON：優先 --out／--json-out 檔，其次 stdout。回 (report|None, error|None)。"""
    if out_path.is_file():
        try:
            return json.loads(out_path.read_text(encoding="utf-8")), None
        except (OSError, ValueError) as exc:
            return None, f"輸出檔無法解析：{type(exc).__name__}: {exc}"
    try:
        return json.loads(result.get("stdout") or ""), None
    except ValueError:
        return None, "儀器未輸出可解析 JSON（--out／--json-out 檔與 stdout 皆無效）"


def _quality_metric_value(metrics, field):
    """讀取 metrics 欄位（支援巢狀 tuple）；缺漏／非數值（含 bool）回 None。"""
    current = metrics
    parts = field if isinstance(field, tuple) else (field,)
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    if isinstance(current, bool) or not isinstance(current, (int, float)):
        return None
    return current


def _quality_field_display(field) -> str:
    return ".".join(field) if isinstance(field, tuple) else str(field)


def project_record_quality_metrics(raw: dict) -> dict:
    """權威 Markdown 量測結果 → tracked 證據投影（不含紀錄／逐字稿長文）。

    ``unsupported_entities`` 只保留筆數與正規化清單的 sha256（片段內容不入
    evidence，避免敏感會議內容進 tracked 檔，DEC-EVIDENCE）；其餘欄位皆為
    儀器既有的確定性字面統計。
    """
    raw = raw if isinstance(raw, dict) else {}
    tag_metrics = raw.get("tag_traceability")
    tag_projection = None
    if isinstance(tag_metrics, dict):
        tag_projection = {
            key: value
            for key, value in tag_metrics.items()
            if (isinstance(value, (int, float)) and not isinstance(value, bool))
            or key == "metric_version"
        }
    entities = raw.get("unsupported_entities")
    entities_count = len(entities) if isinstance(entities, list) else None
    entities_sha = None
    if isinstance(entities, list):
        entities_sha = hashlib.sha256(
            json.dumps(sorted(str(entity) for entity in entities), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest()
    term_hits = raw.get("known_term_fix_hits")
    term_projection = None
    if isinstance(term_hits, dict):
        term_projection = {
            "left_hits": term_hits.get("left_hits"),
            "right_hits": term_hits.get("right_hits"),
        }
    return {
        "char_count": raw.get("char_count"),
        "body_source_tag_count": raw.get("body_source_tag_count"),
        "table_source_tag_count": raw.get("table_source_tag_count"),
        "non_prefixed_tableish_source_tag_count": raw.get(
            "non_prefixed_tableish_source_tag_count"
        ),
        "instruction_item_count": raw.get("instruction_item_count"),
        "tagged_item_ratio": raw.get("tagged_item_ratio"),
        "cross_section_duplicate_pairs": raw.get("cross_section_duplicate_pairs"),
        "known_term_fix_hits": term_projection,
        "tag_traceability": tag_projection,
        "unsupported_entities_count": entities_count,
        "unsupported_entities_sha256": entities_sha,
    }


def evaluate_quality_checks(metrics: dict, *, source_tags_applicable: bool) -> tuple:
    """以既有門檻評估五項來源標註檢查（不得新增、不得放寬；plan §9.6）。

    回傳 ``(checks, failures, notes)``：
    - ``source_tags_applicable=False``（非來源標註契約模板族）→ 五項皆 ``None``
      （不判定；required 也不列入必過清單），並附說明 note。
    - 欄位缺漏／非數值（如未提供逐字稿 → tag_traceability=None）→ 該項 ``None``
      不判定；``on_start_tag_ratio_excluding_zero=None`` 依凍結契約即「不判定」。
    - 失敗訊息逐條指名欄位、實際值與既有門檻（不放寬）。
    """
    checks = {}
    failures = []
    notes = []
    if not source_tags_applicable:
        for name in QUALITY_TAG_CHECK_NAMES:
            checks[name] = None
        notes.append(
            "模板不在來源標註契約模板族（QUALITY_SOURCE_TAG_TEMPLATES="
            f"{sorted(QUALITY_SOURCE_TAG_TEMPLATES)}）→ 五項來源標註檢查不判定"
            "（None；required 亦不列入必過清單）"
        )
        return checks, failures, notes
    for name, field, op, threshold in QUALITY_TAG_THRESHOLDS:
        value = _quality_metric_value(metrics, field)
        field_display = _quality_field_display(field)
        if value is None:
            checks[name] = None
            notes.append(f"{name}：{field_display} 缺漏或非數值 → 不判定（None）")
            continue
        if op == "eq":
            passed = value == threshold
            op_text = "=="
        else:
            passed = value >= threshold
            op_text = ">="
        checks[name] = bool(passed)
        if not passed:
            failures.append(
                f"品質閘門不合格：{name}——{field_display}={value}"
                f"（既有門檻 {op_text} {threshold}；不得放寬）"
            )
    return checks, failures, notes


def _collect_coverage_observation(
    *,
    checklist_path: Path,
    record_markdown: Optional[Path],
    transcript_path: Optional[Path],
    task_id: Optional[str],
    data_dir: Path,
    runtime_dir: Path,
) -> dict:
    """執行 measure_coverage.py → 覆蓋率觀察值（永遠 observation；不影響 verdict）。

    輸出欄位刻意用 ``observation_only``／``gate_effect="none"``，不得出現
    會被誤認為「已通過品質閘門」的欄位名。
    """
    quality_dir = runtime_dir / "quality"
    quality_dir.mkdir(parents=True, exist_ok=True)
    raw_out = quality_dir / "coverage.json"
    observation = {
        "captured": False,
        "observation_only": True,
        "gate_effect": "none",
        "label": f"runner-coverage-{task_id or 'unknown'}",
        "checklist_path": str(checklist_path),
        "checklist_sha256": None,
        "metric_version": None,
        "coverage_all": None,
        "coverage_core": None,
        "fact_core_total": None,
        "covered_core": None,
        "missing_core_ids": None,
        "warnings_count": None,
        "instrument": None,
        "errors": [],
        "notes": ["coverage 永遠只做觀測，不列入 verdict／required 清單"],
    }
    if not checklist_path.is_file():
        observation["errors"].append(f"checklist 不存在：{checklist_path}")
        return observation
    observation["checklist_sha256"] = sha256_file(checklist_path)
    if record_markdown is None:
        observation["errors"].append("無法唯一決定權威 Markdown → 略過 coverage 觀測")
        return observation
    args = [
        "--record", str(record_markdown),
        "--checklist", str(checklist_path),
        "--json-out", str(raw_out),
        "--label", observation["label"],
    ]
    if transcript_path is not None and transcript_path.is_file():
        args += ["--transcript", str(transcript_path)]
    result = run_quality_instrument(COVERAGE_INSTRUMENT_PATH, args, data_dir=data_dir)
    observation["instrument"] = {
        "script": COVERAGE_INSTRUMENT_PATH.name,
        "exit_code": result.get("exit_code"),
        "timed_out": result.get("timed_out"),
        "error": result.get("error"),
    }
    if result.get("error"):
        observation["errors"].append(f"coverage 儀器啟動失敗：{result['error']}")
        return observation
    if result.get("exit_code") != 0:
        observation["errors"].append(
            f"coverage 儀器 exit={result.get('exit_code')}"
            f"（stderr 尾段：{(result.get('stderr') or '')[-300:]}）"
        )
        return observation
    report, load_error = _load_instrument_json(raw_out, result)
    if not isinstance(report, dict):
        observation["errors"].append(f"coverage 儀器輸出不可用：{load_error}")
        return observation
    observation.update(
        {
            "captured": True,
            "metric_version": report.get("metric_version"),
            "coverage_all": report.get("coverage_all"),
            "coverage_core": report.get("coverage_core"),
            "fact_core_total": report.get("fact_core_total"),
            "covered_core": report.get("covered_core"),
            "missing_core_ids": report.get("missing_core_ids"),
            "checklist_sha256": report.get("checklist_sha256") or observation["checklist_sha256"],
            "warnings_count": len(report.get("warnings") or []),
        }
    )
    return observation


def collect_quality_evidence(
    *,
    quality_mode: str,
    template_id: Optional[str],
    task_id: Optional[str],
    data_dir: Path,
    runtime_dir: Path,
    evidence_dir: Path,
    backend_log_path: Path,
    coverage_checklist: Optional[Path],
) -> tuple:
    """P4-D stage 7：品質儀器接線（subprocess）＋required 閘門（既有門檻）。

    回傳 ``(quality_block, gate_failures)``：
    - ``off``：不執行 record 品質儀器（給定 ``--coverage-checklist`` 時仍做
      coverage 觀測）；``gate_failures`` 一律為空。
    - ``observe``：品質值寫入 ``quality_block``；儀器失敗只記 ``errors``／
      ``warnings``，永不影響 verdict（fail-soft）。
    - ``required``：儀器失敗或既有門檻不合格 → ``gate_failures`` 逐條指名
      （fail-closed；不得新增或放寬門檻）。
    """
    source_tags_applicable = template_id in QUALITY_SOURCE_TAG_TEMPLATES
    quality_block = {
        "mode": quality_mode,
        "captured": False,
        "template": template_id,
        "applicability": {
            "source_tag_contract_template": source_tags_applicable,
            "source_tag_contract_templates": sorted(QUALITY_SOURCE_TAG_TEMPLATES),
        },
        "record_markdown": None,
        "instrument": {"record_quality": None},
        "instrument_versions": {
            "expected_tag_traceability_metric_version": RECORD_QUALITY_TAG_METRIC_VERSION,
            "observed_tag_traceability_metric_version": None,
            "coverage_metric_version": None,
        },
        "metrics": None,
        "checks": {name: None for name in QUALITY_TAG_CHECK_NAMES},
        "check_failures": [],
        "observations": {"coverage": None},
        "notes": [],
        "warnings": [],
        "errors": [],
    }
    gate_failures = []

    def _record_instrument_error(message: str) -> None:
        """記儀器層錯誤；required 時同一訊息同時列入 gate_failures（逐條指名）。"""
        quality_block["errors"].append(message)
        if quality_mode == "required":
            gate_failures.append(message)

    try:
        log_text = backend_log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        log_text = ""
    if task_id:
        record_markdown, record_note = resolve_record_markdown(
            data_dir / "outputs", str(task_id), log_text
        )
    else:
        record_markdown, record_note = None, "缺少 task_id（無法解析權威 Markdown）"
    quality_block["record_markdown"] = {
        "path": str(record_markdown) if record_markdown is not None else None,
        "resolution": record_note,
        "sha256": sha256_file(record_markdown) if record_markdown is not None else None,
        "char_count": (
            len(record_markdown.read_text(encoding="utf-8", errors="ignore"))
            if record_markdown is not None
            else None
        ),
    }
    transcript_path = runtime_dir / "transcript.txt"
    if not transcript_path.is_file():
        transcript_path = None

    tag_metrics = None
    if quality_mode == "off":
        quality_block["notes"].append(
            "quality-mode=off：未執行 record 品質儀器"
            "（僅在給定 --coverage-checklist 時做覆蓋率觀測）"
        )
    elif record_markdown is None:
        _record_instrument_error(f"品質儀器失敗：{record_note}")
    else:
        quality_dir = runtime_dir / "quality"
        quality_dir.mkdir(parents=True, exist_ok=True)
        raw_out = quality_dir / "record_quality.json"
        args = ["--record", str(record_markdown), "--out", str(raw_out)]
        if template_id:
            args += ["--template", str(template_id)]
        if transcript_path is not None:
            args += ["--transcript", str(transcript_path)]
        else:
            quality_block["warnings"].append(
                "逐字稿不存在（runtime 無 transcript.txt）→ tag_traceability 不判定"
            )
        result = run_quality_instrument(RECORD_QUALITY_INSTRUMENT_PATH, args, data_dir=data_dir)
        quality_block["instrument"]["record_quality"] = {
            "script": RECORD_QUALITY_INSTRUMENT_PATH.name,
            "exit_code": result.get("exit_code"),
            "timed_out": result.get("timed_out"),
            "error": result.get("error"),
            "template": template_id,
            "transcript_provided": transcript_path is not None,
        }
        if result.get("error"):
            _record_instrument_error(
                f"品質儀器失敗：{RECORD_QUALITY_INSTRUMENT_PATH.name} 無法啟動"
                f"（{result['error']}）"
            )
        elif result.get("exit_code") != 0:
            _record_instrument_error(
                f"品質儀器失敗：{RECORD_QUALITY_INSTRUMENT_PATH.name} "
                f"exit={result.get('exit_code')}（timeout={result.get('timed_out')}；"
                f"stderr 尾段：{(result.get('stderr') or '')[-300:]}）"
            )
        else:
            report, load_error = _load_instrument_json(raw_out, result)
            if not isinstance(report, dict):
                _record_instrument_error(f"品質儀器失敗：{load_error}")
            else:
                quality_block["captured"] = True
                quality_block["metrics"] = project_record_quality_metrics(report)
                tag_metrics = report.get("tag_traceability")
                observed_version = (
                    tag_metrics.get("metric_version") if isinstance(tag_metrics, dict) else None
                )
                quality_block["instrument_versions"][
                    "observed_tag_traceability_metric_version"
                ] = observed_version
                if isinstance(tag_metrics, dict) and observed_version is None:
                    quality_block["warnings"].append(
                        "tag_traceability 未提供 metric_version → 來源標註語意無法釘版"
                    )
                elif (
                    observed_version is not None
                    and observed_version != RECORD_QUALITY_TAG_METRIC_VERSION
                ):
                    message = (
                        f"品質儀器版本不符：tag_traceability metric_version="
                        f"{observed_version!r}（期望 {RECORD_QUALITY_TAG_METRIC_VERSION!r}）"
                    )
                    quality_block["warnings"].append(message)
                    if quality_mode == "required":
                        gate_failures.append(
                            f"品質閘門不合格：{message} → 不得以未知語意閘門（fail-closed）"
                        )
                checks, check_failures, check_notes = evaluate_quality_checks(
                    quality_block["metrics"], source_tags_applicable=source_tags_applicable
                )
                quality_block["checks"] = checks
                quality_block["check_failures"] = check_failures
                quality_block["notes"].extend(check_notes)
                quality_block["notes"].append(
                    f"tag_traceability 取得={isinstance(tag_metrics, dict)}；"
                    f"transcript 提供={transcript_path is not None}"
                )
                if quality_mode == "required":
                    gate_failures.extend(check_failures)

    if quality_mode == "required":
        if not quality_block["captured"] and not gate_failures:
            gate_failures.append(
                "品質儀器失敗：品質值未取得（quality_metrics_captured=False）→ "
                "required 無法以既有門檻判定（fail-closed）"
            )
        if source_tags_applicable and quality_block["captured"] and not isinstance(tag_metrics, dict):
            gate_failures.append(
                "品質閘門不合格：tag_traceability 未取得"
                "（逐字稿缺失或儀器未輸出）→ required 無法判定來源標註比率（fail-closed）"
            )

    if coverage_checklist is not None:
        coverage_observation = _collect_coverage_observation(
            checklist_path=coverage_checklist,
            record_markdown=record_markdown,
            transcript_path=transcript_path,
            task_id=task_id,
            data_dir=data_dir,
            runtime_dir=runtime_dir,
        )
        quality_block["observations"]["coverage"] = coverage_observation
        quality_block["instrument_versions"]["coverage_metric_version"] = (
            coverage_observation.get("metric_version")
        )
        save_json(
            evidence_dir / "coverage_observation.json",
            {**coverage_observation, "generated_at": taipei_now().isoformat()},
        )

    if quality_mode != "off":
        save_json(
            evidence_dir / "record_quality.json",
            {
                **quality_block,
                "generated_at": taipei_now().isoformat(),
                "observation_only": quality_mode != "required",
                "gate_effect": "verdict" if quality_mode == "required" else "none",
            },
        )
    return quality_block, gate_failures


def capture_effective_provider(base_url: str, captured_at: str) -> dict:
    """唯讀探測後端實際 provider（GET /api/config）；不可達不 veto（fail-soft）。

    ``lmstudio_inventory_gate``：僅當有效 provider 明確為 LM Studio（含未知／
    不可達 → fail-safe 維持既有 gate）時為 True；明確非 LM Studio（ollama／auto
    等，W-3 provider 拆分）時為 False → 豁免 ``model_inventory_unique``／
    ``model_snapshot_consistent``（該兩檢查讀 LM Studio ``/api/v1/models``，
    非 LM Studio provider 時必然缺席，屬 provider 專屬可選而非共通必要）。
    """
    info = {
        "captured_at": captured_at,
        "base_url": base_url,
        "reachable": False,
        "local_llm_provider": None,
        "effective_local_llm_provider": None,
        "lmstudio_inventory_gate": True,
        "error": None,
    }
    try:
        resp = httpx.get(f"{base_url}/api/config", timeout=10.0)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError(f"/api/config 回應不是 JSON object（{type(payload).__name__}）")
        effective = payload.get("effective_local_llm_provider")
        info.update(
            {
                "reachable": True,
                "local_llm_provider": payload.get("local_llm_provider"),
                "effective_local_llm_provider": effective,
            }
        )
        effective_normalized = str(effective).strip().lower() if effective is not None else None
        info["lmstudio_inventory_gate"] = effective_normalized in (None, "", "lmstudio")
    except Exception as exc:  # 探測失敗＝provider 未知 → fail-safe（維持現行嚴格 gate）
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def validate_provider_match(provider_info: Optional[dict]) -> list:
    """事後斷言：請求 provider 與後端實際生效 provider 不符 ⇒ FAIL（W-3）。

    僅在 ``/api/config`` 明確回報 configured ∈ {lmstudio, ollama} 且 effective
    有值時判定；``auto``／不可達／缺值 → 不判定（未知不誤殺）。
    """
    info = provider_info if isinstance(provider_info, dict) else {}
    configured = str(info.get("local_llm_provider") or "").strip().lower()
    effective = str(info.get("effective_local_llm_provider") or "").strip().lower()
    if configured in ("lmstudio", "ollama") and effective and effective != configured:
        return [
            "provider 事後斷言失敗：請求 local_llm_provider="
            f"{configured!r}，後端實際 effective_local_llm_provider={effective!r}"
        ]
    return []


def validate_mode_used(mode_used, requested_mode: str) -> list:
    """事後斷言：``task_final.processing_mode`` 必須存在且等於 ``--processing-mode``。

    缺失（後端未回報實際生效模式）或不等 ⇒ FAIL；所有 quality-mode 皆生效，
    nominal 場（相符）verdict 不變。
    """
    if mode_used is None or not str(mode_used).strip():
        return [
            "mode_used 事後斷言失敗：task_final.processing_mode 缺失／為空"
            f"（無法證明後端實際生效模式等於請求 {requested_mode!r}）"
        ]
    if str(mode_used).strip().lower() != str(requested_mode).strip().lower():
        return [
            "mode_used 事後斷言失敗：請求 "
            f"{requested_mode!r}，後端實際 processing_mode={str(mode_used)!r}"
        ]
    return []


def build_engine_attribution(provider_info: Optional[dict], run_report: Optional[dict]) -> dict:
    """run_summary.engine：provider 歸屬＋mode_used 事後斷言結果（P4-D W-3）。

    只在 ``--quality-mode observe|required`` 時寫入（``off`` 不得出現新鍵）。
    """
    info = provider_info if isinstance(provider_info, dict) else {}
    report = run_report if isinstance(run_report, dict) else {}
    return {
        "requested_processing_mode": report.get("requested_processing_mode"),
        "mode_used": report.get("mode_used"),
        "mode_used_match": report.get("mode_used_match"),
        "task_terminal_observed": bool(report.get("task_terminal_observed")),
        "configured_local_llm_provider": info.get("local_llm_provider"),
        "effective_local_llm_provider": info.get("effective_local_llm_provider"),
        "provider_probe_reachable": info.get("reachable"),
        "provider_probe_error": info.get("error"),
        "lmstudio_inventory_gate_enforced": info.get("lmstudio_inventory_gate"),
    }


def run_full_e2e(
    client: httpx.Client,
    base_url: str,
    *,
    upload_mode: str,
    audio_path: Optional[Path],
    processing_mode: str,
    meeting_template: Optional[str] = None,
    expected_audio_sha: Optional[str],
    data_dir: Path,
    evidence_dir: Path,
    runtime_dir: Path,
    backend_log_path: Path,
    task_timeout_seconds: float,
    poll_interval: float,
    browser_upload_timeout: float,
    quality_mode: str = "off",
    coverage_checklist: Optional[Path] = None,
) -> tuple:
    """上傳（API）或偵測（browser）→ stored bytes SHA → 終態 → 下載 → 正式性驗收。

    meeting_template（v4.8.1）：API mode 會以表單欄位 `meeting_template` 上傳，
    並在終態後以 `task_final.json` 的 `template_id` 做「模板已生效」確定性檢查
    ——驗收場若誤用預設模板（general），產物品質會與使用者真實路徑
    （section_meeting 等）不同，這種「驗收場景與使用場景不一致」必須是 FAIL。

    API 與 browser mode 共用同一條 monitor/validation path（plan CM-02）：
    browser 模式不 POST 音檔，僅 bounded 解析 isolated backend 既有
    upload-success log 取得唯一 stored filename + task_id。
    回傳 (checks, failure_reasons, run_report)。

    P4-D（W3）：
    - ``quality_mode``（off／observe／required）：stage 7 以 subprocess 呼叫既有
      品質儀器（不 import backend）；off 不寫任何新鍵、verdict 與現行一致。
    - ``coverage_checklist``：永遠只做觀測（observation_only／gate_effect=none），
      不影響 verdict。
    - ``mode_used`` 事後斷言（所有模式生效）：``task_final.processing_mode`` 必須
      存在且等於 ``processing_mode``，否則 FAIL。
    """
    checks = {}
    failure_reasons = []
    run_report = {
        "requested_processing_mode": processing_mode,
        "mode_used": None,
        "mode_used_match": None,
        "task_terminal_observed": False,
        "quality": None,
    }
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
            return checks, failure_reasons, run_report
    else:
        upload_form = {"processing_mode": processing_mode}
        if meeting_template:
            upload_form["meeting_template"] = meeting_template
        with open(audio_path, "rb") as fh:
            resp = client.post(
                f"{base_url}/api/upload",
                files={"file": (audio_path.name, fh)},
                data=upload_form,
            )
        if resp.status_code != 200:
            failure_reasons.append(f"上傳失敗：HTTP {resp.status_code} {resp.text[:500]}")
            save_json(
                evidence_dir / "upload_response.json",
                {"status_code": resp.status_code, "body": resp.text[:2000]},
            )
            return {"upload_ok": False}, failure_reasons, run_report
        upload = resp.json()
        save_json(evidence_dir / "upload_response.json", redact_upload_response(upload))
        response_failures = validate_upload_response(upload)
        if response_failures:
            failure_reasons.extend(response_failures)
            return {"upload_ok": False}, failure_reasons, run_report
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
            return checks, failure_reasons, run_report
        if log_task_id != task_id:
            failure_reasons.append(
                f"upload log mapping 與上傳回應不一致：response task_id={task_id} "
                f"log 任務ID={log_task_id}"
            )
            return checks, failure_reasons, run_report
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
        return checks, failure_reasons, run_report
    save_json(evidence_dir / "task_final.json", task)
    # P4-D（W3）mode_used 事後斷言（所有 quality-mode 皆生效）：後端實際生效模式
    # 必須等於請求的 --processing-mode；缺失／不符 ⇒ FAIL（不得只信請求值）。
    run_report["task_terminal_observed"] = True
    run_report["mode_used"] = task.get("processing_mode")
    mode_used_failures = validate_mode_used(run_report["mode_used"], processing_mode)
    run_report["mode_used_match"] = not mode_used_failures
    failure_reasons.extend(mode_used_failures)
    # 模板生效檢查（API 與 browser mode 共用；browser mode 不 POST，只能靠此檢查）
    if meeting_template:
        actual_template = str(task.get("template_id") or "")
        if actual_template != meeting_template:
            failure_reasons.append(
                f"會議模板未生效：要求 {meeting_template!r}，實際 {actual_template or '(空)'}；"
                "驗收場景與使用場景不一致"
            )
        else:
            checks["template_applied"] = True
    if status != "completed":
        failure_reasons.append(f"任務終態為 {status}（非 completed）")
        _write_transcript_and_docx(
            client, base_url, task_id, runtime_dir, checks, failure_reasons
        )
        _write_redacted_manifest(
            evidence_dir, expected_audio_sha, stored_upload_sha, None, None
        )
        return checks, failure_reasons, run_report
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
        docx_failures = validate_formal_docx_bytes(docx_bytes, docx_disposition, meeting_template)
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

    # ---------- stage 7：P4-D 品質閘門（--quality-mode／--coverage-checklist）----------
    # off 且無 --coverage-checklist → 完全不觸發（run_summary 不得出現新鍵）。
    if quality_mode != "off" or coverage_checklist is not None:
        quality_block, quality_gate_failures = collect_quality_evidence(
            quality_mode=quality_mode,
            template_id=meeting_template,
            task_id=task_id,
            data_dir=data_dir,
            runtime_dir=runtime_dir,
            evidence_dir=evidence_dir,
            backend_log_path=backend_log_path,
            coverage_checklist=coverage_checklist,
        )
        run_report["quality"] = quality_block
        failure_reasons.extend(quality_gate_failures)
        if quality_mode == "required":
            # required：僅把「有值」的品質檢查寫進 checks（None＝不判定，不列入）
            checks["quality_metrics_captured"] = bool(quality_block["captured"])
            for name in QUALITY_TAG_CHECK_NAMES:
                value = quality_block["checks"].get(name)
                if value is not None:
                    checks[name] = value

    # ---------- redacted hash manifest（DEC-EVIDENCE）----------
    transcript_sha = sha256_file(runtime_dir / "transcript.txt") if checks.get("transcript_downloaded") else None
    docx_sha = sha256_file(runtime_dir / "meeting_record.docx") if checks.get("docx_downloaded") else None
    _write_redacted_manifest(
        evidence_dir, expected_audio_sha, stored_upload_sha, transcript_sha, docx_sha
    )
    return checks, failure_reasons, run_report


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
    parser.add_argument(
        "--template", default=None,
        help="會議模板 id（如 section_meeting／procurement_evaluation／general）。"
        "未指定＝沿用產品預設（general）；指定後會在終態驗證 task_final.template_id "
        "必須相符，不符即 FAIL（驗收場景須等於使用場景）",
    )
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
    parser.add_argument(
        "--quality-mode", default="off", choices=list(QUALITY_MODES),
        help="P4-D 品質閘門模式（預設 off）：off=run_summary 與現行完全一致"
        "（不得出現新鍵）；observe=記錄品質儀器值，verdict 不因品質值改變；"
        "required=沿用既有門檻，不合格 FAIL 且 failure_reasons 逐條指名"
        "（需要 --template；無 --template＝parser.error）",
    )
    parser.add_argument(
        "--coverage-checklist", type=Path, default=None,
        help="事實清單 JSON（scripts/e2e/measure_coverage.py 的 --checklist）；"
        "永遠只做觀測（observation_only）、不影響 verdict",
    )
    args = parser.parse_args()

    if not args.smoke and args.audio is None:
        parser.error("完整 true E2E 需要 --audio；若只想驗證啟動與 health gate 請加 --smoke")
    if args.quality_mode == "required" and not args.template:
        parser.error(
            "--quality-mode required 需要 --template：required 只在指定模板下以"
            "既有門檻判定（模板決定來源標註契約是否適用），無模板＝無判定基準"
        )

    started_at = taipei_now().isoformat()
    host = args.host
    port = args.port or pick_free_port(host)
    expected_revision = resolve_expected_revision(args.expected_revision)
    coverage_checklist = None
    if args.coverage_checklist is not None:
        coverage_checklist = (
            args.coverage_checklist
            if args.coverage_checklist.is_absolute()
            else (REPO_ROOT / args.coverage_checklist)
        )

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
    # P4-D：只在旗標實際使用時登錄（預設 off／未給 checklist → plan 與現行一致）
    if args.quality_mode != "off":
        plan["quality_mode"] = args.quality_mode
    if coverage_checklist is not None:
        plan["coverage_checklist"] = str(coverage_checklist)
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
    provider_info = None
    run_report = None
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
                # P4-D（W-3）provider 拆分：model_inventory_unique／
                # model_snapshot_consistent 讀 LM Studio /api/v1/models，屬
                # 「provider 專屬可選」；非 LM Studio provider（effective 明確為
                # ollama／auto 等）時不得因缺席而 FAIL。探測不可達／未知 → fail-safe
                # 維持現行嚴格 gate（lmstudio_inventory_gate=True）。
                provider_info = capture_effective_provider(base_url, taipei_now().isoformat())
                save_json(artifacts_dir / "provider_info.json", provider_info)
                provider_exempt = provider_info.get("lmstudio_inventory_gate") is False
                if provider_exempt:
                    print(
                        "[INFO] effective_local_llm_provider="
                        f"{provider_info.get('effective_local_llm_provider')!r}（非 LM Studio）"
                        "→ 豁免 provider 專屬檢查 model_inventory_unique／model_snapshot_consistent"
                    )
                model_gate_failures = (
                    [] if provider_exempt else validate_model_inventory_unique(snapshot_start)
                )
                if model_gate_failures:
                    failure_reasons.extend(model_gate_failures)
                else:
                    if not provider_exempt:
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
                    more_checks, more_failures, run_report = run_full_e2e(
                        client=httpx.Client(timeout=600.0),
                        base_url=base_url,
                        upload_mode=args.upload_mode,
                        audio_path=audio_path,
                        processing_mode=args.processing_mode,
                        meeting_template=args.template,
                        expected_audio_sha=expected_audio_sha,
                        data_dir=data_dir,
                        evidence_dir=artifacts_dir,
                        runtime_dir=runtime_dir,
                        backend_log_path=backend_log_path,
                        task_timeout_seconds=args.task_timeout,
                        poll_interval=args.poll_interval,
                        browser_upload_timeout=args.browser_upload_timeout,
                        quality_mode=args.quality_mode,
                        coverage_checklist=coverage_checklist,
                    )
                    checks.update(more_checks)
                    failure_reasons.extend(more_failures)
                    snapshot_end = capture_model_snapshot(
                        lmstudio_base_url, artifacts_dir, taipei_now().isoformat(), filename="model_snapshot_end.json"
                    )
                    if not provider_exempt:
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

    if run_report is None:
        run_report = {
            "requested_processing_mode": args.processing_mode,
            "mode_used": None,
            "mode_used_match": None,
            "task_terminal_observed": False,
            "quality": None,
        }
    # P4-D（W-3）provider 事後斷言：configured 明確（lmstudio／ollama）但後端
    # 實際 effective provider 不符 ⇒ FAIL（探測不可達／auto → 不判定）。
    failure_reasons.extend(validate_provider_match(provider_info))

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
        if args.template:
            required = required + ["template_applied"]
        if provider_info is not None and provider_info.get("lmstudio_inventory_gate") is False:
            # provider 專屬可選檢查（W-3）：非 LM Studio provider 不列入共通必要
            required = [name for name in required if name not in PROVIDER_SPECIFIC_REQUIRED_CHECKS]
        if args.quality_mode == "required":
            # required 只把「有值」（非 None）的品質檢查列入必過（既有門檻）
            required = required + ["quality_metrics_captured"] + [
                name for name in QUALITY_TAG_CHECK_NAMES if checks.get(name) is not None
            ]
    missing = [name for name in required if not checks.get(name)]
    if missing:
        failure_reasons.append(f"缺少必要檢查：{missing}")

    verdict = "PASS" if not failure_reasons else "FAIL"
    summary = {
        "mode": "smoke" if args.smoke else "full",
        "upload_mode": args.upload_mode,
        "meeting_template": args.template,
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
    # P4-D：新鍵只在旗標實際使用時寫入；--quality-mode off 且無 checklist →
    # run_summary 與現行完全一致（不得出現新鍵，含 engine）。
    if run_report.get("quality") is not None:
        summary["quality"] = run_report["quality"]
    if args.quality_mode != "off":
        summary["engine"] = build_engine_attribution(provider_info, run_report)
    save_json(artifacts_dir / "run_summary.json", summary)
    print(f"[{'OK' if verdict == 'PASS' else 'FAIL'}] verdict={verdict}，artifacts：{artifacts_dir}，runtime：{runtime_dir}")
    for reason in failure_reasons:
        print(f"  - {reason}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
