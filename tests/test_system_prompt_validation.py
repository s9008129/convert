#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
System Prompt 驗證測試（v4.3.0）。

重點驗證：
1. 會議紀錄系統提示詞已統一為正式公務欄位格式
2. backend / src / config.yaml 的核心規格維持一致
3. 提示詞仍保留公文體、權責欄位與待確認標記等關鍵要求
"""

import sys
from pathlib import Path
from typing import List, Tuple

import pytest
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import Settings
from src.summarizer import DEFAULT_SYSTEM_PROMPT, CONCISE_SYSTEM_PROMPT
from tests.fixtures.mock_transcripts import (
    ALL_MOCK_TRANSCRIPTS,
    MockTranscript,
    STANDARD_GOVERNMENT_MEETING,
    MEETING_WITH_AMBIGUOUS_INFO,
    VERY_SHORT_TRANSCRIPT,
    VERY_LONG_TRANSCRIPT,
)


class SystemPromptSource:
    """系統提示詞來源管理。"""

    @staticmethod
    def get_main_prompts() -> List[Tuple[str, str]]:
        settings = Settings()
        return [
            ("src/summarizer.py DEFAULT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            ("backend/core/config.py DEFAULT_SYSTEM_PROMPT", settings.DEFAULT_SYSTEM_PROMPT),
        ]

    @staticmethod
    def get_all_prompts() -> List[Tuple[str, str]]:
        settings = Settings()
        return [
            ("src/summarizer.py DEFAULT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            ("src/summarizer.py CONCISE_SYSTEM_PROMPT", CONCISE_SYSTEM_PROMPT),
            ("backend/core/config.py DEFAULT_SYSTEM_PROMPT", settings.DEFAULT_SYSTEM_PROMPT),
        ]

    @staticmethod
    def get_config_yaml_prompt() -> str:
        config_path = Path(__file__).parent.parent / "config.yaml"
        with config_path.open("r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        return config["system_prompt"]


def estimate_prompt_tokens(text: str) -> int:
    """用與服務端相近的保守方式估算 token。"""
    import re

    latin_pattern = re.compile(r"[A-Za-z0-9_]+(?:[-/:.][A-Za-z0-9_]+)*")
    latin_matches = list(latin_pattern.finditer(text))
    latin_words = len(latin_matches)
    latin_chars = sum(len(match.group(0)) for match in latin_matches)
    cjk_chars = len(re.findall(r"[\u3400-\u9fff]", text))
    other_chars = max(len(text) - cjk_chars - latin_chars, 0)
    return max(1, cjk_chars + int(latin_words * 1.2) + other_chars // 4)


class TestPromptContract:
    """驗證新提示詞核心契約。"""

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_uses_new_public_official_contract(self, source_name: str, prompt: str):
        required_phrases = [
            "資深行政秘書與公務紀錄專家",
            "會議原始文本（或逐字稿）",
            "正式公文（或會議紀錄通報）",
            "公務欄位結構",
            "主辦單位",
            "辦理期程",
        ]
        for phrase in required_phrases:
            assert phrase in prompt, f"[{source_name}] 缺少核心契約：{phrase}"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_keeps_fidelity_and_fallback_markers(self, source_name: str, prompt: str):
        assert "專有名詞" in prompt and "可保留" in prompt, \
            f"[{source_name}] 應允許必要的專有名詞或英文縮寫保留"
        assert "（待確認）" in prompt, f"[{source_name}] 應要求模糊資訊標示為（待確認）"
        assert "不得補寫" in prompt or "不得捏造" in prompt, \
            f"[{source_name}] 應明確要求忠於逐字稿"
        assert "簡體中文" in prompt, f"[{source_name}] 應明確禁止簡體中文漂移"
        assert "嚴禁輸出簡體中文" in prompt, f"[{source_name}] 應明確禁止簡體中文輸出"
        assert "<think>" in prompt, f"[{source_name}] 應明確禁止 <think> 標籤洩漏"
        assert "<thought>" in prompt, f"[{source_name}] 應明確禁止 <thought> 標籤洩漏"
        assert "<details>" in prompt, f"[{source_name}] 應明確禁止 <details> 標籤洩漏"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_contains_required_sections(self, source_name: str, prompt: str):
        # 新版提示詞移除方括號填寫模板（避免被模型原樣回吐），只保留欄位標頭字面。
        required_markers = [
            "會議名稱：",
            "會議時間：",
            "會議地點：",
            "主  席：",
            "出席人員：",
            "列席人員：",
            "記  錄：AI 會議助理",
            "一、 報告事項：",
            "二、 討論事項：",
            "案由：",
            "說明：",
            "三、 主席裁示事項（後續管考與追蹤）：",
        ]
        for marker in required_markers:
            assert marker in prompt, f"[{source_name}] 缺少輸出區塊：{marker}"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_has_no_bracket_template(self, source_name: str, prompt: str):
        # 方括號模板（[請從文本中提取…]）是提示詞被回吐到成品的主因，必須完全移除。
        assert "[請" not in prompt, f"[{source_name}] 不應殘留方括號填寫模板"
        assert "請從文本中提取" not in prompt, f"[{source_name}] 不應殘留範例模板用語"
        assert "Evaluation Criteria" not in prompt, f"[{source_name}] 不應出現會被回吐的英文評估標準"
        assert "評估標準" not in prompt, f"[{source_name}] 不應出現會被回吐的評估標準小節"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_forbids_english_preamble(self, source_name: str, prompt: str):
        # 必須有「只輸出本文、從會議名稱開頭、禁止前言/分析」的硬性規則。
        assert "會議名稱：" in prompt
        assert "前言" in prompt, f"[{source_name}] 應明確禁止前言"
        assert "分析" in prompt, f"[{source_name}] 應明確禁止分析段"
        assert ("第一個字元" in prompt or "第一行" in prompt or "開頭" in prompt), \
            f"[{source_name}] 應要求輸出自「會議名稱：」起始"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_contains_action_item_contract(self, source_name: str, prompt: str):
        assert "各單位意見（多方立場）：" in prompt, f"[{source_name}] 缺少多方意見區塊"
        assert "主辦單位" in prompt, f"[{source_name}] 缺少主辦單位欄位"
        assert "協辦單位" in prompt, f"[{source_name}] 缺少協辦單位欄位"
        assert "辦理期程" in prompt, f"[{source_name}] 缺少辦理期程欄位"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_mentions_government_document_style(self, source_name: str, prompt: str):
        keywords = ["臺灣公務機關", "公文體", "正式", "客觀", "全形標點符號"]
        found = sum(1 for keyword in keywords if keyword in prompt)
        assert found >= 3, f"[{source_name}] 應保留政府公文風格與專業語氣要求"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_token_budget_is_local_model_friendly(self, source_name: str, prompt: str):
        # v4.7.2：新增「條列編號階層規則」段落（修復地端公文編號階層不符標準）
        # 將估算 tokens 從 ~1196 推升至 ~1431；相對 8192 context 仍屬小幅佔用，
        # 上限同步放寬至 1600 以保留後續調整空間。
        estimated_tokens = estimate_prompt_tokens(prompt)
        assert estimated_tokens < 1600, \
            f"[{source_name}] Prompt 過長（估算 {estimated_tokens} tokens），不利於 8192 context"
        assert estimated_tokens > 350, \
            f"[{source_name}] Prompt 過短（估算 {estimated_tokens} tokens），可能缺少必要約束"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_no_longer_uses_xml_wrapper(self, source_name: str, prompt: str):
        assert "<system>" not in prompt and "<role>" not in prompt, \
            f"[{source_name}] 主提示詞不應再保留舊版 XML wrapper"


class TestPromptConsistency:
    """驗證多個入口的提示詞不會再次漂移。"""

    def test_main_prompts_are_identical_after_normalization(self):
        prompts = {
            name: " ".join(prompt.strip().split())
            for name, prompt in SystemPromptSource.get_main_prompts()
        }
        values = list(prompts.values())
        assert len(set(values)) == 1, "backend/core/config.py 與 src/summarizer.py 的主提示詞應保持一致"

    def test_concise_prompt_matches_default(self):
        assert CONCISE_SYSTEM_PROMPT == DEFAULT_SYSTEM_PROMPT, \
            "所有會議紀錄系統提示詞應保持一致"

    def test_config_yaml_prompt_keeps_same_core_contract(self):
        yaml_prompt = SystemPromptSource.get_config_yaml_prompt()
        required_phrases = [
            "資深行政秘書與公務紀錄專家",
            "會議原始文本（或逐字稿）",
            "正式公文（或會議紀錄通報）",
            "公務欄位結構",
            "會議名稱：",
            "主  席：",
            "記  錄：AI 會議助理",
            "三、 主席裁示事項（後續管考與追蹤）：",
        ]
        for phrase in required_phrases:
            assert phrase in yaml_prompt, f"[config.yaml] 缺少核心契約：{phrase}"
        assert "[請" not in yaml_prompt, "[config.yaml] 不應殘留方括號填寫模板"

    def test_config_yaml_prompt_matches_python_source(self):
        # 把「靠人記得同步」升級為 CI 擋住：config.yaml 與 prompts.py 正規化後須完全一致。
        from backend.core.prompts import DEFAULT_MEETING_RECORD_PROMPT

        yaml_prompt = " ".join(SystemPromptSource.get_config_yaml_prompt().split())
        py_prompt = " ".join(DEFAULT_MEETING_RECORD_PROMPT.split())
        assert yaml_prompt == py_prompt, "config.yaml 與 prompts.py 提示詞已漂移，請同步"

    def test_config_yaml_context_budget_is_synced(self):
        config_path = Path(__file__).parent.parent / "config.yaml"
        with config_path.open("r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        assert config["llm"]["ollama"]["num_ctx"] == 8192, "config.yaml 應與後端的有效 context 預設對齊"


class TestNumberingHierarchyRule:
    """v4.7.2：驗證「條列編號階層規則」已寫入共用系統提示詞。

    背景：地端模式（弱模型）產出的公文段落編號階層不符合標準（一、(一)、1、(1)…），
    雲端模式（Gemini）沒有這個問題，根因是共用提示詞從未明講階層規則。修復重點是
    把規則寫得足夠明確，讓弱模型也能照做——本測試只做字串斷言，不呼叫真實 LLM。
    """

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_contains_hierarchy_rule_section(self, source_name: str, prompt: str):
        assert "條列編號階層規則" in prompt, f"[{source_name}] 缺少條列編號階層規則段落"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_declares_full_numbering_sequence(self, source_name: str, prompt: str):
        # 完整階層序列（文書處理手冊四層＋業界通用延伸之甲乙丙兩層）皆須出現。
        required_tokens = ["一、二、三", "（一）（二）（三）", "1、2、3", "（1）（2）（3）", "甲、乙、丙", "（甲）（乙）（丙）"]
        for token in required_tokens:
            assert token in prompt, f"[{source_name}] 缺少階層序列片段：{token}"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_forbids_ad_hoc_bullet_symbols(self, source_name: str, prompt: str):
        assert "「-」" in prompt and "「•」" in prompt, \
            f"[{source_name}] 應明確禁止「-」「•」等非公文條列符號"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_requires_independent_numbering_per_field(self, source_name: str, prompt: str):
        # 對齊實測證據：雲端版每個欄位各自從「一、」起算，地端版誤將整份文件
        # 共用一組編號或直接跳用阿拉伯數字——規則必須明講「各自獨立起算」。
        assert "各自獨立自「一、」起算" in prompt, \
            f"[{source_name}] 應明講各欄位條列各自獨立從「一、」起算"

    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_allows_flexible_depth_without_skipping(self, source_name: str, prompt: str):
        assert "不必湊滿所有層級" in prompt, f"[{source_name}] 應允許依需要選用層級，不強制用滿"
        assert "不可跳層" in prompt, f"[{source_name}] 應禁止跳過中間層級"


class TestDomainTemplateHierarchyRule:
    """v4.7.2：三個領域模板（科務會議／ISMS月會／採購評選）提示詞不得再武斷宣稱
    「固定三層」，須改為「通常已足夠、如需更深可依序延伸」，避免真的遇到需要
    第四層以上內容時模型無所適從或亂編符號。"""

    def test_section_meeting_prompt_allows_extension_beyond_three_levels(self):
        from backend.core.prompt_templates.section_meeting import (
            SECTION_MEETING_SYSTEM_PROMPT,
            SECTION_MEETING_GENERATION_EXTRA,
        )

        assert "固定為" not in SECTION_MEETING_SYSTEM_PROMPT
        assert "固定" not in SECTION_MEETING_GENERATION_EXTRA
        assert "（1）" in SECTION_MEETING_SYSTEM_PROMPT
        assert "甲、" in SECTION_MEETING_SYSTEM_PROMPT

    def test_isms_meeting_prompt_allows_extension_beyond_three_levels(self):
        from backend.core.prompt_templates.isms_meeting import ISMS_MEETING_SYSTEM_PROMPT

        assert "固定為" not in ISMS_MEETING_SYSTEM_PROMPT
        assert "（1）" in ISMS_MEETING_SYSTEM_PROMPT
        assert "甲、" in ISMS_MEETING_SYSTEM_PROMPT

    def test_procurement_prompt_declares_extension_below_parenthesis_level(self):
        from backend.core.prompt_templates.procurement import (
            PROCUREMENT_SYSTEM_PROMPT,
            PROCUREMENT_GENERATION_EXTRA,
        )

        # 採購模板頂層為「壹、貳、參」，次層為「一、」，三層為「（一）（二）」；
        # 需補上再往下一層（1、2、3）的延伸規則，供詢答逐項或簡報子點使用。
        assert "1、2、3" in PROCUREMENT_SYSTEM_PROMPT or "1、2、3" in PROCUREMENT_GENERATION_EXTRA
        assert "不可跳層" in PROCUREMENT_SYSTEM_PROMPT or "不可跳層" in PROCUREMENT_GENERATION_EXTRA


class TestMockTranscriptFixtures:
    """保留對測試 fixture 的基本驗證，避免提示詞測試失去對照資料。"""

    @pytest.mark.parametrize("mock_transcript", ALL_MOCK_TRANSCRIPTS)
    def test_mock_transcript_has_content(self, mock_transcript: MockTranscript):
        assert len(mock_transcript.transcript.strip()) > 0, \
            f"模擬逐字稿 '{mock_transcript.name}' 沒有內容"

    @pytest.mark.parametrize("mock_transcript", ALL_MOCK_TRANSCRIPTS)
    def test_mock_transcript_expected_sections(self, mock_transcript: MockTranscript):
        standard_sections = ["會議名稱", "會議時間", "會議地點", "報告事項", "討論事項", "主席裁示事項"]
        for section in standard_sections:
            assert section in mock_transcript.expected_sections, \
                f"模擬逐字稿 '{mock_transcript.name}' 缺少標準區塊：{section}"

    def test_standard_government_meeting_keywords_exist(self):
        transcript = STANDARD_GOVERNMENT_MEETING
        for keyword in transcript.expected_keywords:
            assert keyword in transcript.transcript, f"標準政府機關會議逐字稿缺少關鍵字：{keyword}"

    def test_ambiguous_fixture_is_flagged(self):
        assert MEETING_WITH_AMBIGUOUS_INFO.has_ambiguous_info is True

    def test_boundary_fixture_lengths(self):
        assert len(VERY_SHORT_TRANSCRIPT.transcript.strip()) < 200
        assert len(VERY_LONG_TRANSCRIPT.transcript.strip()) > 3000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
