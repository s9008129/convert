#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
COSTAR-X Framework System Prompt 驗證測試

針對 Gemma 3 27B QAT 4-bit 模型進行完整測試與優化。

驗證項目：
1. System Prompt 結構完整性
   - XML 標籤配對正確性
   - 必要標籤存在性
   - 三明治夾擊法實作

2. 針對 Gemma 3 27B QAT 4-bit 的優化
   - 推理步驟清晰度 (Analyze → Filter → Structure → Refine)
   - 輸出格式範例具體性
   - Markdown 表格範例完整性

3. 台灣政府機關公文風格
   - 角色設定正確性
   - 語氣約束正確性
   - 繁體中文要求明確性

4. 輸出品質驗證
   - 會議概況區塊完整性
   - 執行摘要字數限制
   - 議題與決議結構正確性
   - 待辦事項表格格式正確性
   - 其他備註區塊存在性
"""
import re
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.summarizer import DEFAULT_SYSTEM_PROMPT, CONCISE_SYSTEM_PROMPT
from backend.core.config import Settings
from tests.fixtures.mock_transcripts import (
    ALL_MOCK_TRANSCRIPTS,
    MockTranscript,
    STANDARD_GOVERNMENT_MEETING,
    MEETING_WITH_AMBIGUOUS_INFO,
    VERY_SHORT_TRANSCRIPT,
    VERY_LONG_TRANSCRIPT,
)


# =============================================================================
# System Prompt 來源
# =============================================================================

class SystemPromptSource:
    """系統提示詞來源管理"""
    
    @staticmethod
    def get_all_sources() -> List[Tuple[str, str]]:
        """取得所有 System Prompt 來源"""
        settings = Settings()
        return [
            ("src/summarizer.py DEFAULT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            ("src/summarizer.py CONCISE_SYSTEM_PROMPT", CONCISE_SYSTEM_PROMPT),
            ("backend/core/config.py DEFAULT_SYSTEM_PROMPT", settings.DEFAULT_SYSTEM_PROMPT),
        ]
    
    @staticmethod
    def get_main_prompts() -> List[Tuple[str, str]]:
        """取得主要的 System Prompt（不含簡潔版）"""
        settings = Settings()
        return [
            ("src/summarizer.py DEFAULT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            ("backend/core/config.py DEFAULT_SYSTEM_PROMPT", settings.DEFAULT_SYSTEM_PROMPT),
        ]


# =============================================================================
# A. System Prompt 結構完整性測試
# =============================================================================

class TestXMLTagStructure:
    """XML 標籤結構完整性測試"""
    
    # 必要的 XML 標籤
    REQUIRED_TAGS = [
        "role",
        "instructions",
        "constraints",
        "output_format",
    ]
    
    # COSTAR-X 框架特有的標籤
    COSTARX_TAGS = [
        "system_instruction",
        "final_instruction",
    ]
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_all_sources())
    def test_xml_tags_properly_paired(self, source_name: str, prompt: str):
        """測試 XML 標籤是否正確配對"""
        # 找出所有開始標籤
        opening_tags = re.findall(r'<(\w+)>', prompt)
        # 找出所有結束標籤
        closing_tags = re.findall(r'</(\w+)>', prompt)
        
        # 檢查每個開始標籤都有對應的結束標籤
        for tag in opening_tags:
            assert tag in closing_tags, \
                f"[{source_name}] 開始標籤 <{tag}> 缺少對應的結束標籤 </{tag}>"
        
        # 檢查開始和結束標籤數量一致
        for tag in set(opening_tags):
            open_count = opening_tags.count(tag)
            close_count = closing_tags.count(tag)
            assert open_count == close_count, \
                f"[{source_name}] 標籤 <{tag}> 開始({open_count})與結束({close_count})數量不符"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_required_tags_present(self, source_name: str, prompt: str):
        """測試必要的 XML 標籤是否存在"""
        for tag in self.REQUIRED_TAGS:
            assert f"<{tag}>" in prompt, \
                f"[{source_name}] 缺少必要標籤 <{tag}>"
            assert f"</{tag}>" in prompt, \
                f"[{source_name}] 缺少必要標籤 </{tag}>"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_costarx_framework_tags_present(self, source_name: str, prompt: str):
        """測試 COSTAR-X 框架特有標籤是否存在"""
        for tag in self.COSTARX_TAGS:
            assert f"<{tag}>" in prompt, \
                f"[{source_name}] 缺少 COSTAR-X 框架標籤 <{tag}>"
            assert f"</{tag}>" in prompt, \
                f"[{source_name}] 缺少 COSTAR-X 框架標籤 </{tag}>"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_sandwich_method_final_instruction_at_end(self, source_name: str, prompt: str):
        """測試三明治夾擊法：<final_instruction> 在最後"""
        # 找出 final_instruction 結束標籤的位置
        final_instruction_end = prompt.rfind("</final_instruction>")
        
        assert final_instruction_end != -1, \
            f"[{source_name}] 找不到 </final_instruction> 標籤"
        
        # 計算結束標籤後的內容長度（去除空白）
        content_after = prompt[final_instruction_end + len("</final_instruction>"):].strip()
        
        assert len(content_after) == 0, \
            f"[{source_name}] </final_instruction> 後不應有其他內容（三明治夾擊法要求）"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_all_sources())
    def test_no_orphaned_closing_tags(self, source_name: str, prompt: str):
        """測試沒有孤立的結束標籤"""
        closing_tags = re.findall(r'</(\w+)>', prompt)
        opening_tags = re.findall(r'<(\w+)>', prompt)
        
        for tag in closing_tags:
            assert tag in opening_tags, \
                f"[{source_name}] 結束標籤 </{tag}> 沒有對應的開始標籤"


# =============================================================================
# B. 針對 Gemma 3 27B QAT 4-bit 的優化測試
# =============================================================================

class TestGemma3Optimization:
    """Gemma 3 27B QAT 4-bit 模型優化測試"""
    
    REASONING_STEPS = ["Analyze", "Filter", "Structure", "Refine"]
    REASONING_STEPS_CHINESE = ["分析", "過濾", "結構化", "修飾"]
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_explicit_reasoning_steps(self, source_name: str, prompt: str):
        """測試推理步驟是否清晰（Analyze → Filter → Structure → Refine）"""
        for step in self.REASONING_STEPS:
            assert step in prompt, \
                f"[{source_name}] 缺少推理步驟：{step}"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_chinese_reasoning_steps(self, source_name: str, prompt: str):
        """測試中文推理步驟說明是否存在"""
        for step in self.REASONING_STEPS_CHINESE:
            assert step in prompt, \
                f"[{source_name}] 缺少中文推理步驟說明：{step}"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_markdown_table_example(self, source_name: str, prompt: str):
        """測試 Markdown 表格範例是否完整且正確"""
        # 檢查表格標題行
        assert "| 待辦事項 | 負責人 | 期限 |" in prompt, \
            f"[{source_name}] 缺少待辦事項表格標題行"
        
        # 檢查表格分隔行（對齊設定）
        assert "| :---" in prompt, \
            f"[{source_name}] 缺少表格對齊分隔行"
        
        # 檢查表格範例行
        assert "[具體事項]" in prompt or "[待辦事項]" in prompt, \
            f"[{source_name}] 缺少表格範例行"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_output_format_example_completeness(self, source_name: str, prompt: str):
        """測試輸出格式範例是否足夠具體"""
        required_sections = [
            "會議概況",
            "執行摘要",
            "議題與決議",
            "待辦事項",
            "其他備註"
        ]
        
        for section in required_sections:
            assert section in prompt, \
                f"[{source_name}] 輸出格式範例缺少區塊：{section}"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_markdown_heading_format(self, source_name: str, prompt: str):
        """測試 Markdown 標題格式是否正確"""
        # 應包含不同層級的標題
        assert "# " in prompt or "## " in prompt, \
            f"[{source_name}] 缺少 Markdown 標題格式"
        
        # 檢查具體的標題格式
        assert "## 1." in prompt or "## 2." in prompt, \
            f"[{source_name}] 缺少編號標題格式"


# =============================================================================
# C. 台灣政府機關公文風格測試
# =============================================================================

class TestGovernmentDocumentStyle:
    """台灣政府機關公文風格測試"""
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_role_setting_government_official(self, source_name: str, prompt: str):
        """測試角色設定是否為政府機關相關"""
        government_keywords = ["政府機關", "承辦人員", "公文"]
        
        found = any(kw in prompt for kw in government_keywords)
        assert found, \
            f"[{source_name}] 角色設定缺少政府機關相關描述"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_tone_setting_official(self, source_name: str, prompt: str):
        """測試語氣約束是否為台灣政府機關公文風格"""
        tone_keywords = ["台灣政府機關公文", "公文風格", "正式", "客觀"]
        
        found = any(kw in prompt for kw in tone_keywords)
        assert found, \
            f"[{source_name}] 語氣設定缺少台灣政府機關公文風格描述"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_traditional_chinese_requirement(self, source_name: str, prompt: str):
        """測試繁體中文（台灣用語）要求是否明確"""
        chinese_keywords = ["繁體中文", "台灣用語", "Traditional Chinese"]
        
        found = any(kw in prompt for kw in chinese_keywords)
        assert found, \
            f"[{source_name}] 缺少繁體中文（台灣用語）要求"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_accuracy_constraint_ambiguous_marker(self, source_name: str, prompt: str):
        """測試模糊資訊標註要求是否存在"""
        ambiguous_markers = ["(待確認)", "(需確認)", "標註", "不可瞎編"]
        
        found = any(marker in prompt for marker in ambiguous_markers)
        assert found, \
            f"[{source_name}] 缺少模糊資訊標註要求"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_professional_language_constraint(self, source_name: str, prompt: str):
        """測試專業語言約束是否存在"""
        professional_keywords = ["客觀", "精準", "簡練", "不帶情緒"]
        
        found_count = sum(1 for kw in professional_keywords if kw in prompt)
        assert found_count >= 2, \
            f"[{source_name}] 專業語言約束描述不足，只找到 {found_count} 個關鍵字"


# =============================================================================
# D. 輸出品質驗證測試
# =============================================================================

class TestOutputQualityFormat:
    """輸出品質格式驗證測試"""
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_meeting_overview_section(self, source_name: str, prompt: str):
        """測試會議概況區塊完整性"""
        overview_fields = ["日期", "參與者"]
        
        for field in overview_fields:
            assert field in prompt, \
                f"[{source_name}] 會議概況區塊缺少：{field}"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_executive_summary_word_limit(self, source_name: str, prompt: str):
        """測試執行摘要字數限制是否明確"""
        # 檢查是否有字數限制說明
        word_limit_patterns = [
            r"100\s*字",
            r"100字以內",
            r"100\s*字以內"
        ]
        
        found = any(re.search(pattern, prompt) for pattern in word_limit_patterns)
        assert found, \
            f"[{source_name}] 執行摘要缺少字數限制說明（100字以內）"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_discussion_decisions_structure(self, source_name: str, prompt: str):
        """測試議題與決議結構正確性"""
        structure_elements = ["議題", "討論重點", "決議"]
        
        found_count = sum(1 for elem in structure_elements if elem in prompt)
        assert found_count >= 2, \
            f"[{source_name}] 議題與決議結構描述不完整"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_action_items_table_format(self, source_name: str, prompt: str):
        """測試待辦事項表格格式正確性"""
        # 必須包含表格的三個欄位
        table_columns = ["待辦事項", "負責人", "期限"]
        
        for column in table_columns:
            assert column in prompt, \
                f"[{source_name}] 待辦事項表格缺少欄位：{column}"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_action_items_required_marker(self, source_name: str, prompt: str):
        """測試待辦事項是否標記為必填"""
        required_markers = ["必填", "必須", "Action Items"]
        
        found = any(marker in prompt for marker in required_markers)
        assert found, \
            f"[{source_name}] 待辦事項區塊應標記為必填"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_other_notes_section(self, source_name: str, prompt: str):
        """測試其他備註區塊存在性"""
        notes_keywords = ["其他備註", "備註", "其他"]
        
        found = any(kw in prompt for kw in notes_keywords)
        assert found, \
            f"[{source_name}] 缺少其他備註區塊"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_completeness_constraint(self, source_name: str, prompt: str):
        """測試完整性約束是否存在"""
        completeness_keywords = ["每個區塊", "必須填寫", "標註「無」", "Completeness"]
        
        found = any(kw in prompt for kw in completeness_keywords)
        assert found, \
            f"[{source_name}] 缺少完整性約束說明"


# =============================================================================
# E. System Prompt 一致性測試
# =============================================================================

class TestSystemPromptConsistency:
    """System Prompt 跨檔案一致性測試"""
    
    def test_main_prompts_are_consistent(self):
        """測試主要 System Prompt 在不同檔案中是否一致"""
        sources = SystemPromptSource.get_main_prompts()
        
        # 取得所有主要 prompt，並預先正規化
        normalized_prompts = {
            name: ' '.join(prompt.strip().split())
            for name, prompt in sources
        }
        
        # 比較內容是否一致
        prompt_items = list(normalized_prompts.items())
        for i, (name1, prompt1) in enumerate(prompt_items):
            for name2, prompt2 in prompt_items[i+1:]:
                # 使用序列匹配器計算相似度
                similarity = self._calculate_similarity(prompt1, prompt2)
                
                # 主要 prompt 應該高度相似（允許些微格式差異）
                assert similarity > 0.95, \
                    f"System Prompt 在 {name1} 與 {name2} 中不一致，相似度僅 {similarity:.2%}"
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """計算兩個字串的相似度（使用序列匹配）"""
        if not s1 or not s2:
            return 0.0
        
        # 使用 difflib.SequenceMatcher 進行更精確的相似度計算
        from difflib import SequenceMatcher
        return SequenceMatcher(None, s1, s2).ratio()


# =============================================================================
# F. 模擬逐字稿驗證測試
# =============================================================================

class TestMockTranscriptValidation:
    """使用模擬逐字稿驗證 System Prompt 的有效性"""
    
    @pytest.mark.parametrize("mock_transcript", ALL_MOCK_TRANSCRIPTS)
    def test_mock_transcript_has_content(self, mock_transcript: MockTranscript):
        """測試模擬逐字稿有有效內容"""
        assert len(mock_transcript.transcript.strip()) > 0, \
            f"模擬逐字稿 '{mock_transcript.name}' 沒有內容"
    
    @pytest.mark.parametrize("mock_transcript", ALL_MOCK_TRANSCRIPTS)
    def test_mock_transcript_expected_sections(self, mock_transcript: MockTranscript):
        """測試模擬逐字稿定義了預期區塊"""
        assert len(mock_transcript.expected_sections) > 0, \
            f"模擬逐字稿 '{mock_transcript.name}' 沒有定義預期區塊"
        
        # 標準區塊應該存在
        standard_sections = ["會議概況", "執行摘要", "待辦事項"]
        for section in standard_sections:
            assert section in mock_transcript.expected_sections, \
                f"模擬逐字稿 '{mock_transcript.name}' 缺少標準預期區塊：{section}"
    
    def test_standard_government_meeting_keywords(self):
        """測試標準政府機關會議逐字稿關鍵字"""
        transcript = STANDARD_GOVERNMENT_MEETING
        
        for keyword in transcript.expected_keywords:
            assert keyword in transcript.transcript, \
                f"標準政府機關會議逐字稿缺少關鍵字：{keyword}"
    
    def test_ambiguous_meeting_has_flag(self):
        """測試含模糊資訊的會議正確標記"""
        assert MEETING_WITH_AMBIGUOUS_INFO.has_ambiguous_info is True, \
            "含模糊資訊的會議應標記 has_ambiguous_info=True"
    
    def test_very_short_transcript_length(self):
        """測試極短逐字稿長度"""
        assert len(VERY_SHORT_TRANSCRIPT.transcript.strip()) < 200, \
            "極短逐字稿應少於 200 字元"
    
    def test_very_long_transcript_length(self):
        """測試極長逐字稿長度"""
        assert len(VERY_LONG_TRANSCRIPT.transcript.strip()) > 3000, \
            "極長逐字稿應超過 3000 字元"


# =============================================================================
# G. 邊界情況測試
# =============================================================================

class TestEdgeCases:
    """邊界情況測試"""
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_all_sources())
    def test_no_empty_tags(self, source_name: str, prompt: str):
        """測試沒有空的 XML 標籤"""
        # 找出所有標籤對
        tag_pattern = r'<(\w+)>\s*</\1>'
        empty_tags = re.findall(tag_pattern, prompt)
        
        assert len(empty_tags) == 0, \
            f"[{source_name}] 發現空的 XML 標籤：{empty_tags}"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_all_sources())
    def test_no_nested_same_tags(self, source_name: str, prompt: str):
        """測試沒有相同標籤巢狀（簡化版：檢查基本的標籤配對）"""
        # 使用堆疊方式檢查標籤配對
        tag_pattern = re.compile(r'<(/?)(\w+)>')
        stack = []
        
        for match in tag_pattern.finditer(prompt):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2)
            
            if is_closing:
                # 結束標籤應該與堆疊頂部的開始標籤配對
                if stack and stack[-1] == tag_name:
                    stack.pop()
                # 如果不配對，可能是格式問題，但不一定是巢狀
            else:
                # 開始標籤
                if stack and stack[-1] == tag_name:
                    # 連續兩個相同的開始標籤，表示可能有巢狀問題
                    pytest.fail(f"[{source_name}] 發現相同標籤巢狀：<{tag_name}>")
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_not_too_short(self, source_name: str, prompt: str):
        """測試 System Prompt 長度足夠"""
        # 主要 prompt 應該有足夠的說明
        assert len(prompt) > 1000, \
            f"[{source_name}] System Prompt 過短，可能缺少必要說明"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_main_prompts())
    def test_prompt_not_too_long(self, source_name: str, prompt: str):
        """測試 System Prompt 不會過長"""
        # 避免 token 超出限制
        assert len(prompt) < 10000, \
            f"[{source_name}] System Prompt 過長，可能影響效能"
    
    def test_concise_prompt_is_shorter(self):
        """測試簡潔版 prompt 確實較短"""
        assert len(CONCISE_SYSTEM_PROMPT) < len(DEFAULT_SYSTEM_PROMPT), \
            "簡潔版 System Prompt 應該比預設版短"


# =============================================================================
# H. 特殊字元與編碼測試
# =============================================================================

class TestEncodingAndSpecialCharacters:
    """編碼與特殊字元測試"""
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_all_sources())
    def test_utf8_encoding(self, source_name: str, prompt: str):
        """測試 UTF-8 編碼正確"""
        try:
            prompt.encode('utf-8')
        except UnicodeEncodeError as e:
            pytest.fail(f"[{source_name}] UTF-8 編碼錯誤：{e}")
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_all_sources())
    def test_no_invisible_characters(self, source_name: str, prompt: str):
        """測試沒有不可見的特殊字元"""
        # 常見的問題字元
        problematic_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\ufeff',  # BOM
        ]
        
        for char in problematic_chars:
            assert char not in prompt, \
                f"[{source_name}] 發現不可見字元：{repr(char)}"
    
    @pytest.mark.parametrize("source_name,prompt", SystemPromptSource.get_all_sources())
    def test_consistent_line_endings(self, source_name: str, prompt: str):
        """測試換行符號一致"""
        # 檢查是否混用不同的換行符號
        # 先將 CRLF 替換為占位符，然後檢查是否有孤立的 CR 或 LF
        temp = prompt.replace('\r\n', '')
        has_standalone_cr = '\r' in temp
        has_standalone_lf = False  # 已經移除了 CRLF，剩下的 \n 是允許的
        
        # 如果存在孤立的 CR（不是 CRLF 的一部分），則混用了換行符號
        if has_standalone_cr:
            assert False, \
                f"[{source_name}] 換行符號不一致（混用 CR 和 LF）"


# =============================================================================
# 執行測試
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
