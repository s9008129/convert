#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WAVE-01d fail-first 測試 — chunk overlap 220-token 上限與 health build_revision provenance。

任務：T20260827-1127-01-lmstudio-e2e-empty-summary
（plan：RC-4 planner/chunker overlap model mismatch、RC-5 runtime provenance；
 CHANGE_MAP 第 4、5 項；REGRESSION_AND_ACCEPTANCE 第 6、7 組。）

測試為 production-shaped：不做真實 HTTP、不觸發真實 ASR、不呼叫外部 LLM。
- chunking 測試直接驅動 SummarizationService 的 production 切塊路徑
  （_build_local_context_plan → _split_transcript_into_chunks →
  _assemble_chunks_from_lines），並以模組自身的 _estimate_tokens 度量
  每個 chunk boundary 的 carry（overlap）estimated tokens。
- health 測試沿用 tests/test_api_routes.py 的 TestClient + mock services 慣例，
  summarization_service 的 health check 方法一律以固定值替身，不觸及外部服務。

Fail-first 預期結果（main @ b493c74，修復前）：
- test_chunk_boundary_carry_tokens_within_220_token_budget ...... 預期 FAIL：
  assembler carry 目前以 `max(12, max_input_tokens // 2)` 封頂（可達半個 chunk），
  實測 carry 272 tokens > planner 假設的 220 tokens（RC-4）。
- test_chunk_boundary_carry_respects_configured_line_cap ........ 預期 PASS（guard）：
  LOCAL_LLM_CHUNK_OVERLAP_LINES line cap 現行已生效；WAVE-03 對齊 220-token cap
  時不得使其回歸。
- test_chunk_content_coverage_preserves_order_and_sentinels ..... 預期 PASS（guard）：
  去 overlap 後串接需完整涵蓋原始逐字稿（順序、不遺失、不改動）；
  收斂 carry 時不得破壞 chunk postcondition。
- test_health_build_revision_defaults_to_null_without_env ....... 預期 FAIL：
  現行 /api/health response 無 build_revision key（RC-5）。
- test_health_build_revision_returns_configured_value ........... 預期 FAIL（同上）。
- test_health_response_model_declares_nullable_build_revision ... 預期 FAIL：
  schemas.HealthStatus 無 build_revision 欄位。

規劃假設對照：backend/services/summarization.py 的 context planner 以
`effective_chunk_step = max(chunk_input_budget - 220, 1)` 估算 chunk 數，
因此 assembler 每個 boundary 的重複 carry 不得超過 220 tokens，否則
實際 chunk 數會高於 planner 估算（放大模型呼叫與隨機空回應機率）。
"""

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import get_args
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 與 tests/test_api_routes.py 相同慣例：先隔離 DATA_DIR，再載入 backend 模組。
os.environ['DATA_DIR'] = tempfile.mkdtemp()

# 加入專案根目錄到匯入路徑。
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api.routes import router
from backend.core.config import settings
from backend.core.version import __version__
from backend.models.schemas import HealthStatus, QueueStatus
from backend.services.summarization import SummarizationService


# planner 的 overlap 假設（summarization.py：effective_chunk_step =
# max(chunk_input_budget - 220, 1)）；WAVE-03 會以共享常數
# LOCAL_LLM_CHUNK_OVERLAP_BUDGET_TOKENS 同時供 planner 與 assembler 使用。
EXPECTED_CHUNK_OVERLAP_BUDGET_TOKENS = 220

MEETINGSCRIBE_BUILD_REVISION_ENV = "MEETINGSCRIBE_BUILD_REVISION"


# =============================================================================
# Chunking fixtures / helpers
# =============================================================================

def _overlap_probe_line(index: int) -> str:
    """單行約 68 estimated tokens 的逐字稿行（唯一、無重複字面）。"""
    return (
        f"講者{index % 6}：關於第{index:03d}項議題，本段討論預算編列、時程風險與人力配置的具體安排，"
        f"請相關單位在下次會議前完成盤點，並逐項回報目前進度與待確認事項（編號{index:03d}）。"
    )


def _short_probe_line(index: int) -> str:
    """單行約 27 estimated tokens 的短逐字稿行（驗證 line cap 用）。

    刻意只含 CJK（無拉丁/數字 token），避免 joined-text 與逐行 token 估算
    的截斷差異觸發無關的 chunk postcondition gate。
    """
    speaker = "甲乙丙丁"[index % 4]
    return f"講者{speaker}：請於本週五前完成整合測試與上線公告草案的檢核作業。"


def _chunk_via_production_splitter(
    service: SummarizationService,
    lines: list,
    max_input_tokens: int,
    overlap_lines: int,
) -> tuple:
    """以 production 入口 `_split_transcript_into_chunks` 切塊，並取得
    `_assemble_chunks_from_lines` 的權威 overlaps 供 boundary 量測。

    fixture 的行皆短於 production 正規化門檻（< 600 字、tokens <= budget），
    因此正規化為恆等映射，兩條路徑輸出必須一致。
    """
    transcript = "\n".join(lines)
    chunks = service._split_transcript_into_chunks(transcript, max_input_tokens)
    direct_chunks, overlaps = service._assemble_chunks_from_lines(
        lines, max_input_tokens, overlap_lines
    )
    assert chunks == direct_chunks, (
        "量測用的 _assemble_chunks_from_lines 輸出必須與 production 切塊完全一致，"
        "否則 boundary carry 量測不具代表性"
    )
    return transcript, chunks, overlaps


def _boundary_carry_tokens(service: SummarizationService, chunks: list, overlaps: list) -> list:
    """對每個相鄰 chunk boundary 計算 carry（overlap）的 estimated tokens。

    採 summarization 模組自身的 token 估算慣例：每行以
    `_estimate_tokens(line) + 1` 計（+1 為組 chunk 時的換行）。
    """
    carries = []
    for index, overlap in enumerate(overlaps):
        carry_lines = chunks[index].split("\n")[:overlap]
        carries.append(sum(service._estimate_tokens(line) + 1 for line in carry_lines))
    return carries


# =============================================================================
# RC-4：chunk boundary carry 必須受 220-token 上限約束
# =============================================================================

class TestChunkOverlapBound:
    """RC-4：planner 以 220-token overlap 估算 step，assembler carry 不得超過。"""

    def test_chunk_boundary_carry_tokens_within_220_token_budget(self, monkeypatch):
        """每個 boundary 的重複 carry estimated tokens <= 220。

        修復前：carry 以 `max(12, max_input_tokens // 2)` 封頂（半個 chunk），
        在 production budget（>=1200）下 4 行 overlap 可達 272 tokens > 220。
        """
        service = SummarizationService()
        monkeypatch.setattr(settings, "LOCAL_LLM_CHUNK_OVERLAP_LINES", 4)

        lines = [_overlap_probe_line(i) for i in range(120)]

        # fixture sanity：預設 4 行 carry 必須足以超過 220 tokens，
        # 否則本測試無法暴露「carry 超過 220」的缺陷。
        overlap_lines = max(1, settings.LOCAL_LLM_CHUNK_OVERLAP_LINES)
        four_line_carry = sum(
            service._estimate_tokens(line) + 1 for line in lines[-overlap_lines:]
        )
        assert four_line_carry > EXPECTED_CHUNK_OVERLAP_BUDGET_TOKENS, (
            "fixture sanity：4 行 carry 應超過 220 tokens（實得 "
            f"{four_line_carry}），測試 fixture 設計錯誤"
        )

        # production planner 推導的 chunk input budget（production 上下限 [1200, 3200]）
        plan = service._build_local_context_plan("\n".join(lines), settings.DEFAULT_SYSTEM_PROMPT)
        budget = plan.chunk_input_budget_tokens
        assert 1200 <= budget <= 3200, (
            f"fixture sanity：production chunk input budget 應落在 [1200, 3200]，實得 {budget}"
        )

        transcript, chunks, overlaps = _chunk_via_production_splitter(
            service, lines, budget, overlap_lines=max(1, settings.LOCAL_LLM_CHUNK_OVERLAP_LINES)
        )

        assert len(chunks) >= 2, "fixture sanity：逐字稿應觸發 chunking 以產生 boundary"
        assert transcript.strip()  # 非空輸入

        carries = _boundary_carry_tokens(service, chunks, overlaps)
        boundary_carries = [
            (index, carry) for index, carry in enumerate(carries) if overlaps[index] > 0
        ]
        assert boundary_carries, "fixture sanity：應存在帶 overlap 的 boundary"

        for index, carry_tokens in boundary_carries:
            assert carry_tokens <= EXPECTED_CHUNK_OVERLAP_BUDGET_TOKENS, (
                f"chunk boundary {index} 的 carry 估計 {carry_tokens} tokens，"
                f"超過 planner 的 220-token overlap 假設（RC-4：assembler 以 "
                f"max(12, budget // 2) 封頂，可達半個 chunk）"
            )

    def test_chunk_boundary_carry_respects_configured_line_cap(self, monkeypatch):
        """`LOCAL_LLM_CHUNK_OVERLAP_LINES` line cap 仍須生效。

        使用短行（2 行 carry 遠低於 220 tokens）隔離驗證：token cap 不構成約束時，
        carry 行數仍須由 settings 的 line cap 決定。
        """
        service = SummarizationService()
        configured_cap = 2
        monkeypatch.setattr(settings, "LOCAL_LLM_CHUNK_OVERLAP_LINES", configured_cap)

        lines = [_short_probe_line(i) for i in range(120)]

        # fixture sanity：2 行 carry 低於 220 tokens，確保本測試隔離 line cap 行為
        two_line_carry = sum(service._estimate_tokens(line) + 1 for line in lines[:configured_cap])
        assert two_line_carry <= EXPECTED_CHUNK_OVERLAP_BUDGET_TOKENS, (
            "fixture sanity：短行 2 行 carry 應低於 220 tokens"
        )

        # 1200 為 production chunk input budget 的下限（_build_local_context_plan 的 max(1200, ...)）
        production_minimum_budget = 1200
        transcript, chunks, overlaps = _chunk_via_production_splitter(
            service, lines, production_minimum_budget, overlap_lines=configured_cap
        )

        assert len(chunks) >= 2, "fixture sanity：應觸發 chunking 以產生 boundary"
        assert all(
            overlap <= configured_cap for overlap in overlaps
        ), f"每個 boundary 的 carry 行數不得超過 LOCAL_LLM_CHUNK_OVERLAP_LINES={configured_cap}"
        assert max(overlaps) == configured_cap, (
            "至少一個 boundary 應保留完整設定的 overlap 行數，"
            "證明 line cap 由 LOCAL_LLM_CHUNK_OVERLAP_LINES 驅動"
        )


# =============================================================================
# 內容完整性：去 overlap 後須完整、有序涵蓋原始逐字稿
# =============================================================================

class TestChunkContentCoverage:
    """chunk postcondition 不得因 overlap 收斂修復而回歸。"""

    HEAD_SENTINEL = "〔SENTINEL-HEAD〕"
    MID_SENTINEL = "〔SENTINEL-MID〕"
    TAIL_SENTINEL = "〔SENTINEL-TAIL〕"

    def _sentinel_transcript(self) -> tuple:
        head = f"甲：會議開始，主席先確認上次會議決議追蹤進度與本次議程安排。{self.HEAD_SENTINEL}"
        mid = f"乙：進入中段議題，本段確認里程碑達成率與風險應變計畫執行狀態。{self.MID_SENTINEL}"
        tail = f"丁：散會前確認決議與待辦已逐項記錄於會議紀錄。{self.TAIL_SENTINEL}"
        filler = "主持人：請各單位就本項討論事項補充執行面意見，並確認後續辦理方式與責任歸屬。"

        lines = (
            [head]
            + [filler] * 60
            + [mid]
            + [filler] * 60
            + [tail]
        )
        return lines, "\n".join(lines)

    def test_chunk_content_coverage_preserves_order_and_sentinels(self, monkeypatch):
        """concatenate chunks 去除 overlap 後應涵蓋原始 transcript 全部非重複內容，
        且頭、中、尾 sentinel 都存在且順序正確。"""
        service = SummarizationService()
        monkeypatch.setattr(settings, "LOCAL_LLM_CHUNK_OVERLAP_LINES", 4)

        lines, transcript = self._sentinel_transcript()
        plan = service._build_local_context_plan(transcript, settings.DEFAULT_SYSTEM_PROMPT)
        budget = plan.chunk_input_budget_tokens

        _, chunks, overlaps = _chunk_via_production_splitter(
            service, lines, budget, overlap_lines=max(1, settings.LOCAL_LLM_CHUNK_OVERLAP_LINES)
        )

        assert len(chunks) >= 2, "fixture sanity：逐字稿應觸發 chunking"
        assert self.HEAD_SENTINEL in chunks[0], "頭端 sentinel 必須保留在第一塊"
        assert self.TAIL_SENTINEL in chunks[-1], "尾端 sentinel 不得因切塊消失"

        # 與 production _validate_chunk_postcondition 相同的去 overlap 重組
        non_overlap_lines = []
        for chunk, overlap in zip(chunks, overlaps):
            chunk_lines = [line.strip() for line in chunk.split("\n") if line.strip()]
            skip = min(overlap, len(chunk_lines) - 1, len(non_overlap_lines))
            non_overlap_lines.extend(chunk_lines[skip:])

        normalize = lambda text: re.sub(r"\s+", "", text)
        assert (
            "".join(normalize(line) for line in non_overlap_lines) == normalize(transcript)
        ), "去除 overlap 後串接必須完整涵蓋原始逐字稿（順序、不遺失、不改動內容）"

        non_overlap_text = "".join(non_overlap_lines)
        head_pos = non_overlap_text.find(self.HEAD_SENTINEL)
        mid_pos = non_overlap_text.find(self.MID_SENTINEL)
        tail_pos = non_overlap_text.find(self.TAIL_SENTINEL)
        assert 0 <= head_pos < mid_pos < tail_pos, (
            "頭、中、尾 sentinel 片段都必須存在於非 overlap 內容中，且順序正確"
        )


# =============================================================================
# RC-5：/api/health 的 nullable build_revision provenance
# =============================================================================

@pytest.fixture
def mock_health_services():
    """沿用 tests/test_api_routes.py 的 mock 慣例，隔離 /api/health 的外部依賴。"""
    with patch('backend.api.routes.device_detector') as mock_device, \
         patch('backend.api.routes.task_queue') as mock_queue, \
         patch('backend.api.routes.summarization_service') as mock_summary:
        mock_device.detect_best_device.return_value = None
        mock_device.get_device_info.return_value = {
            "current_device": "cpu",
            "compute_type": "int8",
            "fallback_count": 0,
            "gpu_name": None,
            "gpu_memory_mb": None,
            "gpu_available": False,
            "mps_available": False,
        }
        # 不呼叫真實 LLM health check：以固定值替身回應
        mock_summary.check_ollama_health = AsyncMock(return_value=True)
        mock_summary.check_lmstudio_health = AsyncMock(return_value=False)
        mock_summary.check_gemini_available.return_value = False
        mock_summary.get_local_llm_health.return_value = {
            "provider": "lmstudio",
            "server_reachable": False,
            "selection_status": "LMSTUDIO_NO_LOADED_LLM",
            "loaded_llm_count": 0,
            "selected_model": None,
            "context_length": None,
        }
        mock_queue.get_queue_status.return_value = QueueStatus(
            total_queued=0,
            processing_count=0,
            estimated_wait_seconds=0,
            max_concurrent=1,
            queue_max_size=50,
        )
        yield {
            'device_detector': mock_device,
            'task_queue': mock_queue,
            'summarization_service': mock_summary,
        }


@pytest.fixture
def health_client(mock_health_services):
    """以乾淨的 FastAPI app 掛載 production router（TestClient 慣例，非真實 HTTP）。"""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def build_revision_env(monkeypatch):
    """確保 MEETINGSCRIBE_BUILD_REVISION 未設定的基準狀態。

    若 WAVE-03 將欄位加入 Settings，同步把該欄位重置為 None；
    兩種實作（per-request 讀 env / 讀 settings 欄位）皆相容。
    """
    monkeypatch.delenv(MEETINGSCRIBE_BUILD_REVISION_ENV, raising=False)
    if hasattr(settings, "MEETINGSCRIBE_BUILD_REVISION"):
        monkeypatch.setattr(settings, "MEETINGSCRIBE_BUILD_REVISION", None)
    return monkeypatch


def _set_build_revision(monkeypatch, value: str) -> None:
    monkeypatch.setenv(MEETINGSCRIBE_BUILD_REVISION_ENV, value)
    if hasattr(settings, "MEETINGSCRIBE_BUILD_REVISION"):
        monkeypatch.setattr(settings, "MEETINGSCRIBE_BUILD_REVISION", value)


class TestHealthBuildRevision:
    """RC-5：health 需提供向後相容的 nullable build_revision。"""

    def test_health_build_revision_defaults_to_null_without_env(
        self, build_revision_env, health_client
    ):
        """未設定 MEETINGSCRIBE_BUILD_REVISION 時 build_revision 為 null，
        既有欄位與狀態碼完全不變。"""
        response = health_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # 既有欄位與狀態碼不得改變（向後相容）
        assert data["status"] == "healthy"
        assert data["version"] == __version__
        assert data["ollama_available"] is True
        assert data["lmstudio_available"] is False
        assert data["gemini_available"] is False
        assert "queue_status" in data
        assert "device_info" in data

        # RC-5：未設定時必須以 null 呈現
        assert "build_revision" in data, (
            "/api/health response 缺少向後相容的 nullable build_revision 欄位"
            "（RC-5：無法區分新舊服務的 runtime provenance）"
        )
        assert data["build_revision"] is None

    def test_health_build_revision_returns_configured_value(
        self, build_revision_env, health_client
    ):
        """設定 MEETINGSCRIBE_BUILD_REVISION 時，response 必須回傳該值。"""
        _set_build_revision(build_revision_env, "wave03-test-revision-abc")

        response = health_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "build_revision" in data, (
            "/api/health response 缺少 build_revision 欄位"
            "（RC-5：MEETINGSCRIBE_BUILD_REVISION 應成為執行期來源）"
        )
        assert data["build_revision"] == "wave03-test-revision-abc"

    def test_health_response_model_declares_nullable_build_revision(self):
        """HealthStatus response model 必須宣告 nullable 的 build_revision 欄位。"""
        field = HealthStatus.model_fields.get("build_revision")
        assert field is not None, (
            "HealthStatus response model 缺少 build_revision 欄位"
            "（RC-5：runtime provenance 無法區分 stale 與 current 服務）"
        )

        annotation = field.annotation
        allowed_types = {annotation, *get_args(annotation)}
        assert type(None) in allowed_types, (
            "build_revision 必須為 nullable（string | null），unknown revision 不得使 health 失敗"
        )