# -*- coding: utf-8 -*-
"""W2b：彙整表列出處標註的確定性移除（T20260922-1930-01 軌 A）。

釘住的契約：

* ``template_forbids_table_source_tags``：模板 ``forbidden_patterns`` 的標籤含
  「發言來源標註」才回 True（section_meeting 專屬；不寫死模板 id），
  ``template=None``／缺屬性一律 False。
* ``strip_source_tags_from_table_rows``：只在契約禁止時啟用，且只動
  ``^\\s*\\|`` 的 Markdown 表格列；移除 ``SOURCE_TAG_PATTERN`` 及緊接其前的
  分隔空白／頓號／逗號／分號（不留懸空標點），回報移除數量。
* 正文（含正文句末標註）與 general 模板的表格內容必須 byte 級不變。

fixture 字面取自真實基線輸出（``data/cache/e2e/p1-baseline-01/...``，gitignore 內），
一律內嵌字面、不得於 runtime 讀檔。
"""

import os
import tempfile

# 必須在 import backend 之前備妥可寫的 DATA_DIR（logger 匯入時即建立 DATA_DIR/logs）。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-table-tags-"))

from backend.core.templates import get_template  # noqa: E402
from backend.core.text_postprocess import (  # noqa: E402
    SOURCE_TAG_PATTERN,
    TABLE_ROW_PATTERN,
    strip_source_tags_from_table_rows,
    template_forbids_table_source_tags,
)

# 來源：data/cache/e2e/p1-baseline-01/backend_data/outputs/0903-科務會議_70a58030.md
# L13–L14（真實基線彙整表列；該場 13/13 列都帶出處標註，違反 section_meeting 契約）。
BASELINE_TABLE_ROWS_WITH_TAGS = """|組織異動相關系統權限、設備及業務移撥調整（地價稅科、土地增值稅科、使用牌照稅科、煙酒及稅務管理科、房稅科），請各相關股別於11月1日前完成預約準備與交接配合。（科長，00:05:36）|資管股：| | |
|土地增值稅科配合印花稅業務移撥，確認兩位承辦人交接事宜。（科長，00:05:36）|土地增值稅科承辦人：| | |"""

BASELINE_TABLE_ROWS_EXPECTED = """|組織異動相關系統權限、設備及業務移撥調整（地價稅科、土地增值稅科、使用牌照稅科、煙酒及稅務管理科、房稅科），請各相關股別於11月1日前完成預約準備與交接配合。|資管股：| | |
|土地增值稅科配合印花稅業務移撥，確認兩位承辦人交接事宜。|土地增值稅科承辦人：| | |"""

# 來源：同檔 L29（真實基線正文列；正文標註是契約要求的可查核性，不得移除）。
BASELINE_BODY_LINE_WITH_TAG = (
    "1. 土地稅科分拆為「地價稅科」與「土地增值稅科」；校費稅科改為「使用牌照稅科」。（科長，00:05:36）"
)

# 建構例（真實語料未出現；釘住「標註前的頓號一併移除、不留懸空標點」的清理語意）。
TABLE_ROW_TAG_AFTER_SEPARATOR = "| 案由（詳見紀錄）、（科長，00:12:04）|資管股：| | |"
TABLE_ROW_TAG_AFTER_SEPARATOR_EXPECTED = "| 案由（詳見紀錄）|資管股：| | |"


class TestTemplateForbidsTableSourceTags:
    def test_section_meeting禁止表格標註(self):
        assert template_forbids_table_source_tags(get_template("section_meeting")) is True

    def test_樣式與雲端發言來源絆索同式(self):
        """SOURCE_TAG_PATTERN 必須與 SummarizationService._SOURCE_TAG_PATTERN 同式。"""
        from backend.services.summarization import SummarizationService

        assert SOURCE_TAG_PATTERN.pattern == SummarizationService._SOURCE_TAG_PATTERN.pattern

    def test_其他模板與None皆不禁止(self):
        assert template_forbids_table_source_tags(get_template("general")) is False
        assert template_forbids_table_source_tags(get_template("procurement_evaluation")) is False
        assert template_forbids_table_source_tags(get_template("isms_monthly")) is False
        assert template_forbids_table_source_tags(None) is False

    def test_缺屬性物件不拋錯(self):
        assert template_forbids_table_source_tags(object()) is False


class TestStripSourceTagsFromTableRows:
    def test_真實基線表格列_移除標註且無懸空標點(self):
        cleaned, removed = strip_source_tags_from_table_rows(
            BASELINE_TABLE_ROWS_WITH_TAGS, get_template("section_meeting")
        )
        assert removed == 2
        assert cleaned == BASELINE_TABLE_ROWS_EXPECTED
        assert not SOURCE_TAG_PATTERN.search(cleaned)
        assert "。" in cleaned  # 句末標點保留，未被連帶吃掉

    def test_標註前的頓號一併移除(self):
        cleaned, removed = strip_source_tags_from_table_rows(
            TABLE_ROW_TAG_AFTER_SEPARATOR, get_template("section_meeting")
        )
        assert removed == 1
        assert cleaned == TABLE_ROW_TAG_AFTER_SEPARATOR_EXPECTED

    def test_同一列多個標註都移除並計數(self):
        row = "| （發言者1，00:12:04）案由（科長，00:12:05） | 資管股： |  |  |"
        cleaned, removed = strip_source_tags_from_table_rows(
            row, get_template("section_meeting")
        )
        assert removed == 2
        assert not SOURCE_TAG_PATTERN.search(cleaned)
        assert "案由" in cleaned and "資管股：" in cleaned

    def test_縮排的表格列同樣處理(self):
        row = "  | 案由（科長，00:12:04）|資管股：| | |"
        cleaned, removed = strip_source_tags_from_table_rows(
            row, get_template("section_meeting")
        )
        assert removed == 1
        assert cleaned == "  | 案由|資管股：| | |"

    def test_正文標註一個字都不動(self):
        text = f"{BASELINE_TABLE_ROWS_WITH_TAGS}\n{BASELINE_BODY_LINE_WITH_TAG}\n"
        cleaned, removed = strip_source_tags_from_table_rows(
            text, get_template("section_meeting")
        )
        assert removed == 2
        assert BASELINE_BODY_LINE_WITH_TAG in cleaned
        assert cleaned.split("\n")[-2] == BASELINE_BODY_LINE_WITH_TAG

    def test_general模板表格內容byte不變(self):
        cleaned, removed = strip_source_tags_from_table_rows(
            BASELINE_TABLE_ROWS_WITH_TAGS, get_template("general")
        )
        assert removed == 0
        assert cleaned == BASELINE_TABLE_ROWS_WITH_TAGS

    def test_template為None時不啟用(self):
        assert strip_source_tags_from_table_rows(BASELINE_TABLE_ROWS_WITH_TAGS) == (
            BASELINE_TABLE_ROWS_WITH_TAGS,
            0,
        )

    def test_沒有標註時原樣回傳(self):
        text = "| 案由 | 資管股： |  |  |"
        assert strip_source_tags_from_table_rows(text, get_template("section_meeting")) == (
            text,
            0,
        )
        assert strip_source_tags_from_table_rows("", get_template("section_meeting")) == ("", 0)


class TestTableRowPattern公開定義:
    """表格列定義的公開單一來源（2026-09-22 稽核修正；軌 C 量測儀器直接 import）。"""

    def test_公開符號存在且語意為行首直線(self):
        assert TABLE_ROW_PATTERN.pattern == r"^\s*\|"
        assert TABLE_ROW_PATTERN.match("| 案由 | 資管股： |  |  |") is not None
        assert TABLE_ROW_PATTERN.match("  | 縮排表格列 |") is not None

    def test_正文行不匹配(self):
        assert TABLE_ROW_PATTERN.match(BASELINE_BODY_LINE_WITH_TAG) is None
        assert TABLE_ROW_PATTERN.match("") is None

    def test_與私有別名同一個pattern物件(self):
        from backend.core import text_postprocess  # noqa: PLC0415

        assert text_postprocess._TABLE_ROW_PATTERN is TABLE_ROW_PATTERN
