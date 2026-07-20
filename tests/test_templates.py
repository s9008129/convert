"""會議模板註冊表測試（v4.4.0）。

驗證重點：
1. 註冊表完整性（id 唯一、general 為預設、未知 id 拋錯）
2. general 模板與 v4.3.3 舊常數行為一致（回歸保證）
3. 採購評選會模板：local_only、機敏 forbidden patterns、結構驗證
4. 記錄級後處理（ensure_record_structure）依模板補骨架
"""

import re

import pytest

from backend.core.templates import (
    GENERAL_TEMPLATE_ID,
    get_template,
    list_templates,
    template_glossary_block,
    template_public_info,
)


class TestRegistry:
    def test_general_is_default(self):
        assert get_template(None).id == GENERAL_TEMPLATE_ID
        assert get_template("").id == GENERAL_TEMPLATE_ID
        assert get_template("general").id == GENERAL_TEMPLATE_ID

    def test_unknown_template_raises(self):
        with pytest.raises(ValueError):
            get_template("nonexistent_domain")

    def test_ids_unique_and_general_first(self):
        templates = list_templates()
        ids = [t.id for t in templates]
        assert len(ids) == len(set(ids))
        assert ids[0] == GENERAL_TEMPLATE_ID
        assert "procurement_evaluation" in ids

    def test_public_info_shape(self):
        info = template_public_info()
        assert all(
            {"id", "display_name", "description", "local_only", "is_default"} <= set(item)
            for item in info
        )
        defaults = [item for item in info if item["is_default"]]
        assert len(defaults) == 1 and defaults[0]["id"] == GENERAL_TEMPLATE_ID

    def test_missing_text_consistency(self):
        """templates._MISSING_TEXT 必須與 text_postprocess.MISSING_TEXT 同值。"""
        from backend.core import templates
        from backend.core.text_postprocess import MISSING_TEXT

        assert templates._MISSING_TEXT == MISSING_TEXT


class TestGeneralBackwardCompat:
    """general 模板必須與 v4.3.3 舊常數完全一致（byte-identical 回歸）。"""

    def test_required_patterns_match_legacy_alias(self):
        from backend.services.summarization import SummarizationService

        general = get_template("general")
        assert SummarizationService._REQUIRED_SECTION_PATTERNS == list(
            general.required_section_patterns
        )

    def test_docx_patterns_match_legacy_alias(self):
        from backend.services import docx_converter as dc

        general = get_template("general")
        assert dc.RECORD_SECTION_PATTERN is general.docx_section_pattern
        assert dc.RECORD_LABEL_PATTERN is general.docx_label_pattern

    def test_system_prompt_resolves_from_settings(self):
        from backend.core.config import settings

        assert get_template("general").resolve_system_prompt() == settings.DEFAULT_SYSTEM_PROMPT

    def test_ensure_record_structure_default_unchanged(self):
        """空輸入的骨架輸出必須與 v4.3.3 硬編碼版本完全一致。"""
        from backend.core.text_postprocess import MISSING_TEXT, ensure_record_structure

        result = ensure_record_structure("")
        fallback = f"- {MISSING_TEXT}（主辦單位：{MISSING_TEXT}，辦理期程：{MISSING_TEXT}）"
        expected = "\n".join([
            f"會議名稱：{MISSING_TEXT}",
            f"會議時間：{MISSING_TEXT}",
            f"會議地點：{MISSING_TEXT}",
            f"主  席：{MISSING_TEXT}",
            f"出席人員：{MISSING_TEXT}",
            "列席人員：無",
            "記  錄：AI 會議助理",
            "",
            "一、 報告事項：",
            "無",
            "二、 討論事項：",
            f"案由：{MISSING_TEXT}",
            f"說明：{MISSING_TEXT}",
            "各單位意見（多方立場）：",
            f"- {MISSING_TEXT}：{MISSING_TEXT}",
            "決議：",
            f"1. {MISSING_TEXT}（主辦單位：{MISSING_TEXT}，協辦單位：{MISSING_TEXT}）",
            "三、 主席裁示事項（後續管考與追蹤）：",
            fallback,
        ])
        assert result == expected

    def test_ensure_record_structure_subfield_completion(self):
        """節存在但子欄位缺漏時只補子欄位（與 v4.3.3 行為一致）。"""
        from backend.core.text_postprocess import ensure_record_structure

        partial = (
            "會議名稱：測試會議\n會議時間：115年6月4日\n會議地點：會議室\n"
            "主  席：某主管\n出席人員：全體\n列席人員：無\n記  錄：AI 會議助理\n"
            "一、 報告事項：\n無\n"
            "二、 討論事項：\n案由：測試案。\n說明：背景。\n各單位意見（多方立場）：\n- 甲單位：同意\n"
            "決議：\n1. 通過（主辦單位：甲，協辦單位：無）\n"
            "三、 主席裁示事項（後續管考與追蹤）：\n- 續辦（主辦單位：甲，辦理期程：115年7月）"
        )
        result = ensure_record_structure(partial)
        assert result == partial  # 完整輸入不應被改動


class TestProcurementTemplate:
    def setup_method(self):
        self.template = get_template("procurement_evaluation")

    def test_local_only(self):
        assert self.template.local_only is True

    def test_result_title(self):
        assert self.template.result_title == "# 採購評選會議紀錄"

    def test_system_prompt_contains_key_rules(self):
        prompt = self.template.resolve_system_prompt()
        for keyword in ("採購評選委員會", "委員提問", "廠商答詢", "機敏資訊，不列入紀錄", "（待確認）", "壹、會議時間"):
            assert keyword in prompt, f"系統提示詞缺少關鍵規則: {keyword}"

    def test_forbidden_pattern_catches_reserve_price(self):
        text = "承辦單位說明：本案底價為新臺幣500萬元。"
        assert any(p.search(text) for _, p in self.template.forbidden_patterns)

    def test_forbidden_pattern_catches_individual_score(self):
        text = "A委員評分為85分，B委員給分90。"
        assert any(p.search(text) for _, p in self.template.forbidden_patterns)

    def test_forbidden_pattern_allows_aggregate_result(self):
        """彙整後結果（序位合計值、總評分）為法定應記載事項，不得誤殺。"""
        text = (
            "拾肆、委員討論及評選結果：\n"
            "一、○○公司序位合計值為5，經出席委員過半數決議為第1優勝廠商。\n"
            "二、△△公司總評分為82分，列第2優勝廠商。"
        )
        hits = [label for label, p in self.template.forbidden_patterns if p.search(text)]
        assert not hits, f"彙整結果被誤判為機敏洩漏: {hits}"

    def test_docx_section_pattern_matches_official_numbering(self):
        pattern = self.template.docx_section_pattern
        for line in ("壹、會議時間：...", "拾參、廠商簡報及詢答事項：", "拾陸、散會：下午4時"):
            assert pattern.match(line), f"官方編號未被辨識: {line}"
        # 廠商子項（一、○○公司）不得誤判為章節
        assert not pattern.match("一、○○公司")

    def test_docx_label_pattern_matches_qa_labels(self):
        pattern = self.template.docx_label_pattern
        assert pattern.match("委員提問：本案維運人力如何配置？")
        assert pattern.match("廠商答詢：本公司配置專職工程師三名。")

    def test_ensure_record_structure_builds_official_skeleton(self):
        from backend.core.text_postprocess import ensure_record_structure

        result = ensure_record_structure("", template=self.template)
        assert "採購評選委員會第（待確認）次會議（評選會議）紀錄" in result
        for section in ("壹、會議時間：", "捌、評選方式：", "拾參、廠商簡報及詢答事項：", "拾陸、散會："):
            assert section in result, f"骨架缺少章節: {section}"
        assert "委員提問：（待確認）" in result
        assert "廠商答詢：（待確認）" in result

    def test_glossary_block_contains_corrections(self):
        block = template_glossary_block("procurement_evaluation")
        assert "最有利標" in block
        assert "最有力標 → 最有利標" in block

    def test_general_glossary_block_empty(self):
        assert template_glossary_block("general") == ""


# 近似官方範本的科務會議紀錄本文（v4.5.0 測試 fixture）
_SECTION_SAMPLE_RECORD = """嘉義縣財政稅務局電子作業科115年7月份第1次科務會議紀錄
時間：中華民國115年7月8日（星期三）上午11時20分
地點：本局電子作業科
主持人：何科長　紀錄：AI 會議助理
出席人員：如後附簽到表
歷次科務會議決議事項繼續列管案件：無
115年7月份第1次科務會議決議事項辦理情形彙整表
決議事項：
| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |
| --- | --- | --- | --- |
| 實地評核當天會議室筆電準備，請資管股負責評估 | 資管股： |  |  |
| 聯繫會議各縣市提案認領，請系統股彙整列管表 | 系統股： |  |  |
一、科長轉知局務會議工作報告及相關注意事項：（略，請參考局務會議紀錄）
二、科長指示及提醒事項：
（一）稅務節活動配合事項。
1. 全員於11時40分就座完畢，統一著局服。
（二）晶質獎實地評核事宜。
1. 7月14日本科先行演練，7月15日正式演練。
散會：上午11時58分"""


class TestSectionMeetingTemplate:
    def setup_method(self):
        self.template = get_template("section_meeting")

    def test_cloud_allowed(self):
        """科務會議屬內部行政會議，使用者確認允許雲端處理。"""
        assert self.template.local_only is False

    def test_result_title(self):
        assert self.template.result_title == "# 科務會議紀錄"

    def test_attachment_defined(self):
        attachment = self.template.attachment
        assert attachment is not None
        assert attachment.label == "列管資料"
        assert attachment.download_name == "科務會議列管資料"
        assert callable(attachment.build_markdown)

    def test_other_templates_have_no_attachment(self):
        assert get_template("general").attachment is None
        assert get_template("procurement_evaluation").attachment is None

    def test_public_info_exposes_attachment(self):
        info = {item["id"]: item for item in template_public_info()}
        assert info["section_meeting"]["has_attachment"] is True
        assert info["section_meeting"]["attachment_label"] == "列管資料"
        assert info["general"]["has_attachment"] is False
        assert info["general"]["attachment_label"] is None

    def test_system_prompt_contains_key_rules(self):
        prompt = self.template.resolve_system_prompt()
        for keyword in (
            "科務會議紀錄",
            "決議事項辦理情形彙整表",
            "案由及承辦單位",
            "科長指示及提醒事項",
            "歷次科務會議決議事項繼續列管案件",
            "（待確認）",
        ):
            assert keyword in prompt, f"系統提示詞缺少關鍵規則: {keyword}"

    def test_required_patterns_hit_official_sample(self):
        """官方範本結構必須全數命中 required patterns（不誤報缺漏）。"""
        misses = [
            label
            for label, pattern in self.template.required_section_patterns
            if not pattern.search(_SECTION_SAMPLE_RECORD)
        ]
        assert not misses, f"官方範本結構未命中: {misses}"

    def test_ensure_record_structure_builds_skeleton(self):
        from backend.core.text_postprocess import ensure_record_structure

        result = ensure_record_structure("", template=self.template)
        assert "科務會議紀錄" in result
        assert "時間：（待確認）" in result
        assert "| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |" in result
        assert "一、科長轉知局務會議工作報告及相關注意事項：" in result
        assert "二、科長指示及提醒事項：" in result
        assert "散會：（待確認）" in result

    def test_ensure_record_structure_keeps_complete_record(self):
        from backend.core.text_postprocess import ensure_record_structure

        assert ensure_record_structure(
            _SECTION_SAMPLE_RECORD, template=self.template
        ) == _SECTION_SAMPLE_RECORD

    def test_docx_section_pattern(self):
        pattern = self.template.docx_section_pattern
        assert pattern.match("一、科長轉知局務會議工作報告及相關注意事項：")
        assert pattern.match("二、科長指示及提醒事項：")
        assert not pattern.match("（一）稅務節活動配合事項。")

    def test_docx_label_pattern(self):
        pattern = self.template.docx_label_pattern
        assert pattern.match("時間：中華民國115年7月8日")
        assert pattern.match("散會：上午11時58分")
        assert pattern.match("歷次科務會議決議事項繼續列管案件：無")

    def test_glossary_block_contains_corrections(self):
        block = template_glossary_block("section_meeting")
        assert "列管" in block
        assert "課務會議 → 科務會議" in block


class TestTrackingAttachmentBuilder:
    def setup_method(self):
        from backend.core.prompt_templates.section_meeting import build_tracking_attachment

        self.build = build_tracking_attachment

    def test_inline_value_becomes_single_row_table(self):
        """「歷次…：無」行內值須組成單列表格，不得誤抓本次彙整表。"""
        attachment = self.build(_SECTION_SAMPLE_RECORD)
        previous_part = attachment.split("科務會議決議事項辦理情形彙整表")[0]
        assert "| 無 |  |  |  |" in previous_part
        assert "資管股" not in previous_part  # 本次彙整表內容不得混入歷次段

    def test_summary_table_extracted_with_title(self):
        attachment = self.build(_SECTION_SAMPLE_RECORD)
        assert "115年7月份第1次科務會議決議事項辦理情形彙整表" in attachment
        assert "決議事項：" in attachment
        assert "| 實地評核當天會議室筆電準備，請資管股負責評估 | 資管股： |  |  |" in attachment
        assert "| 聯繫會議各縣市提案認領，請系統股彙整列管表 | 系統股： |  |  |" in attachment

    def test_previous_tracking_table_extracted(self):
        record = (
            "標題科務會議紀錄\n"
            "歷次科務會議決議事項繼續列管案件：\n\n"
            "| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |\n"
            "| --- | --- | --- | --- |\n"
            "| 前次交辦之AI知識庫盤點 | 資管股： |  | V |\n\n"
            "115年8月份第1次科務會議決議事項辦理情形彙整表\n"
            "決議事項：\n"
            "| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |\n"
            "| --- | --- | --- | --- |\n"
            "| 新交辦事項 | 系統股： |  |  |"
        )
        attachment = self.build(record)
        previous_part = attachment.split("科務會議決議事項辦理情形彙整表")[0]
        assert "| 前次交辦之AI知識庫盤點 | 資管股： |  | V |" in previous_part
        assert "| 新交辦事項 | 系統股： |  |  |" in attachment

    def test_missing_sections_fall_back_to_skeleton(self):
        """兩段皆缺時補（待確認）骨架且不拋例外（附件不得阻斷本文下載）。"""
        attachment = self.build("完全無關的內容")
        assert "歷次科務會議決議事項繼續列管案件" in attachment
        assert "科務會議決議事項辦理情形彙整表" in attachment
        assert "（待確認）" in attachment

    def test_never_raises_on_empty_input(self):
        for value in ("", None):
            attachment = self.build(value)
            assert "歷次科務會議決議事項繼續列管案件" in attachment


class TestValidationWithTemplate:
    def test_procurement_validation_flags_missing_qa_and_leakage(self):
        from backend.services.summarization import SummarizationService

        service = SummarizationService()
        template = get_template("procurement_evaluation")
        summary = (
            "「示範案」案採購評選委員會第2次會議（評選會議）紀錄\n"
            "壹、會議時間：中華民國115年7月1日\n"
            "本案底價為500萬元。"
        )
        issues = service._validate_summary_quality(summary, "", min_chars=10, template=template)
        assert any("委員提問" in issue for issue in issues)
        assert any("機敏資訊洩漏" in issue for issue in issues)

    def test_general_validation_unchanged(self):
        from backend.services.summarization import SummarizationService

        service = SummarizationService()
        issues_default = service._validate_summary_quality("太短", "", min_chars=10)
        issues_explicit = service._validate_summary_quality(
            "太短", "", min_chars=10, template=get_template("general")
        )
        assert issues_default == issues_explicit
        assert any("缺少主辦單位資訊" in issue for issue in issues_default)
