"""
DOCX 轉換器測試。

驗證 MarkdownToDocxConverter 的核心功能：
- 標題、段落、粗體、列表、表格、引用、水平線
- CJK 字型設定
- 邊界情況處理
- API 整合（format=docx）
"""

import os
import sys
import tempfile
import pytest

# 確保可匯入專案模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docx import Document
from docx.oxml.ns import qn
from backend.services.docx_converter import MarkdownToDocxConverter, FONT_HEADING, FONT_BODY


# ===== 測試用 Markdown 範本 =====

SAMPLE_MEETING_MD = """# 會議記錄摘要

## 1. 會議概況
- **日期**：2026 年 2 月 28 日
- **參與者**：張三、李四、王五
- **會議主題**：AI 自動化專案進度檢討

## 2. 執行摘要
本次會議主要討論 AI 自動化專案導入後的實際執行成效。重點在於準確率提升與使用者接受度。

## 3. 詳細議題與決議
- **議題一：系統準確率評估**
  - 討論重點：目前系統準確率約 85%，仍有提升空間
  - 最終決議：後續需進行更多訓練資料收集

- **議題二：使用者回饋整合**
  - 討論重點：使用者希望增加半自動模式
  - 最終決議：下一版本加入半自動化功能

## 4. 待辦事項
| 待辦事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
| 收集訓練資料 | 張三 | 2026 年 3 月 15 日 |
| 設計半自動介面 | 李四 | 2026 年 3 月 30 日 |
| 撰寫測試報告 | 王五 | 2026 年 4 月 1 日 |

## 5. 其他備註
- 下次會議訂於 3 月 7 日召開
- 需邀請產品經理參與下次討論

---

## 原始逐字稿

<details>
<summary>點擊展開逐字稿</summary>

這是一段測試用的逐字稿內容。
張三說：我們目前的準確率大概在 85% 左右。
李四說：使用者反映希望有半自動模式。

</details>
"""

SAMPLE_SIMPLE_MD = """# 簡單測試

## 標題一
這是一段普通文字。

## 標題二
- 項目一
- 項目二
"""

SAMPLE_TABLE_ONLY_MD = """## 待辦事項
| 事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
| 任務A | 甲 | 明天 |
| 任務B | 乙 | 下週 |
"""

SAMPLE_WITH_BLOCKQUOTE = """# 會議記錄

> 檔案：test_audio.mp3
> 處理時間：2026-02-28 10:00:00
> 處理模式：本地模式 (Ollama)

---

## 1. 會議概況
- **日期**：無
"""


@pytest.fixture
def converter():
    return MarkdownToDocxConverter()


@pytest.fixture
def tmp_docx(tmp_path):
    """回傳暫存 .docx 檔案路徑。"""
    return str(tmp_path / "test_output.docx")


# ===== 基礎轉換測試 =====

class TestBasicConversion:
    """基礎轉換功能測試。"""

    def test_full_meeting_conversion(self, converter, tmp_docx):
        """完整會議記錄 Markdown → DOCX，驗證檔案可正常開啟。"""
        result = converter.convert(SAMPLE_MEETING_MD, tmp_docx)
        assert os.path.exists(result)
        assert result.endswith('.docx')

        # 驗證可用 python-docx 開啟
        doc = Document(tmp_docx)
        assert len(doc.paragraphs) > 0

    def test_simple_conversion(self, converter, tmp_docx):
        """簡單 Markdown 轉換。"""
        converter.convert(SAMPLE_SIMPLE_MD, tmp_docx)
        doc = Document(tmp_docx)
        assert len(doc.paragraphs) > 0

    def test_empty_content_raises(self, converter, tmp_docx):
        """空內容應拋出 ValueError。"""
        with pytest.raises(ValueError, match="不可為空"):
            converter.convert("", tmp_docx)

        with pytest.raises(ValueError, match="不可為空"):
            converter.convert("   ", tmp_docx)

    def test_output_file_created(self, converter, tmp_docx):
        """轉換後檔案應存在。"""
        converter.convert(SAMPLE_SIMPLE_MD, tmp_docx)
        assert os.path.exists(tmp_docx)
        assert os.path.getsize(tmp_docx) > 0


# ===== 標題解析測試 =====

class TestHeadingParsing:
    """標題解析測試。"""

    def test_h1_heading(self, converter, tmp_docx):
        """H1 標題正確解析。"""
        converter.convert("# 測試標題\n\n內文", tmp_docx)
        doc = Document(tmp_docx)

        # 找到 Heading 1 段落
        h1_found = False
        for para in doc.paragraphs:
            if para.style.name.startswith('Heading 1'):
                assert '測試標題' in para.text
                h1_found = True
                break
        assert h1_found, "未找到 H1 標題"

    def test_h2_heading(self, converter, tmp_docx):
        """H2 標題正確解析。"""
        converter.convert("## 二級標題\n\n內文", tmp_docx)
        doc = Document(tmp_docx)

        h2_found = False
        for para in doc.paragraphs:
            if para.style.name.startswith('Heading 2'):
                assert '二級標題' in para.text
                h2_found = True
                break
        assert h2_found, "未找到 H2 標題"

    def test_multiple_headings(self, converter, tmp_docx):
        """多個標題層級同時存在。"""
        md = "# 主標題\n\n## 子標題一\n\n## 子標題二\n"
        converter.convert(md, tmp_docx)
        doc = Document(tmp_docx)

        h1_count = sum(1 for p in doc.paragraphs if p.style.name.startswith('Heading 1'))
        h2_count = sum(1 for p in doc.paragraphs if p.style.name.startswith('Heading 2'))
        assert h1_count == 1
        assert h2_count == 2


# ===== 表格解析測試 =====

class TestTableParsing:
    """表格解析測試 - 重點驗證 Office 2024/M365 相容性。"""

    def test_table_created(self, converter, tmp_docx):
        """Markdown 表格正確轉為 DOCX 表格。"""
        converter.convert(SAMPLE_TABLE_ONLY_MD, tmp_docx)
        doc = Document(tmp_docx)

        assert len(doc.tables) == 1
        table = doc.tables[0]
        # 標題行 + 2 資料行（分隔線行被跳過）
        assert len(table.rows) == 3
        assert len(table.columns) == 3

    def test_table_header_content(self, converter, tmp_docx):
        """表格標題行內容正確。"""
        converter.convert(SAMPLE_TABLE_ONLY_MD, tmp_docx)
        doc = Document(tmp_docx)
        table = doc.tables[0]

        headers = [table.rows[0].cells[i].text.strip() for i in range(3)]
        assert headers == ['事項', '負責人', '期限']

    def test_table_data_content(self, converter, tmp_docx):
        """表格資料行內容正確。"""
        converter.convert(SAMPLE_TABLE_ONLY_MD, tmp_docx)
        doc = Document(tmp_docx)
        table = doc.tables[0]

        # 第一筆資料行
        row1 = [table.rows[1].cells[i].text.strip() for i in range(3)]
        assert row1 == ['任務A', '甲', '明天']

        # 第二筆資料行
        row2 = [table.rows[2].cells[i].text.strip() for i in range(3)]
        assert row2 == ['任務B', '乙', '下週']

    def test_table_has_borders(self, converter, tmp_docx):
        """表格有完整框線（Office 2024/M365 相容）。"""
        converter.convert(SAMPLE_TABLE_ONLY_MD, tmp_docx)
        doc = Document(tmp_docx)
        table = doc.tables[0]

        # 檢查 XML 中有 tblBorders 設定
        tbl_pr = table._tbl.tblPr
        borders = tbl_pr.findall(qn('w:tblBorders'))
        assert len(borders) > 0, "表格缺少 tblBorders 設定"

        # 驗證各邊框都有設定
        border_elem = borders[0]
        for side in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
            found = border_elem.findall(qn(f'w:{side}'))
            assert len(found) > 0, f"表格缺少 {side} 框線"

    def test_table_header_has_shading(self, converter, tmp_docx):
        """表格標題行有灰底。"""
        converter.convert(SAMPLE_TABLE_ONLY_MD, tmp_docx)
        doc = Document(tmp_docx)
        table = doc.tables[0]

        # 檢查第一行的儲存格有底色
        header_cell = table.rows[0].cells[0]
        tc_pr = header_cell._tc.tcPr
        shading = tc_pr.findall(qn('w:shd'))
        assert len(shading) > 0, "表格標題行缺少底色"

    def test_full_meeting_table(self, converter, tmp_docx):
        """完整會議記錄中的待辦事項表格。"""
        converter.convert(SAMPLE_MEETING_MD, tmp_docx)
        doc = Document(tmp_docx)

        assert len(doc.tables) >= 1
        table = doc.tables[0]
        # 標題行 + 3 筆資料
        assert len(table.rows) == 4
        assert len(table.columns) == 3

        # 驗證標題
        headers = [table.rows[0].cells[i].text.strip() for i in range(3)]
        assert '待辦事項' in headers[0]
        assert '負責人' in headers[1]
        assert '期限' in headers[2]

    def test_separator_row_skipped(self, converter):
        """表格分隔線行被正確跳過。"""
        assert MarkdownToDocxConverter._is_table_separator("| :--- | :--- | :--- |")
        assert MarkdownToDocxConverter._is_table_separator("| --- | --- | --- |")
        assert MarkdownToDocxConverter._is_table_separator("| :---: | ---: | :--- |")
        assert not MarkdownToDocxConverter._is_table_separator("| 事項 | 負責人 | 期限 |")


# ===== 粗體解析測試 =====

class TestBoldParsing:
    """粗體文字解析測試。"""

    def test_bold_text(self, converter, tmp_docx):
        """**粗體** 正確轉為粗體 Run。"""
        converter.convert("## 測試\n\n- **日期**：2026 年\n", tmp_docx)
        doc = Document(tmp_docx)

        bold_found = False
        for para in doc.paragraphs:
            for run in para.runs:
                if run.bold and '日期' in run.text:
                    bold_found = True
                    break
        assert bold_found, "未找到粗體文字"

    def test_mixed_bold_normal(self, converter, tmp_docx):
        """粗體與一般文字混合。"""
        converter.convert("## 測試\n\n這是 **重要** 的文字\n", tmp_docx)
        doc = Document(tmp_docx)

        has_bold = False
        has_normal = False
        for para in doc.paragraphs:
            for run in para.runs:
                if run.bold:
                    has_bold = True
                else:
                    has_normal = True
        assert has_bold, "缺少粗體 Run"
        assert has_normal, "缺少一般 Run"


# ===== 列表項目測試 =====

class TestListItems:
    """列表項目解析測試。"""

    def test_bullet_list(self, converter, tmp_docx):
        """一級項目符號。"""
        md = "## 測試\n\n- 項目一\n- 項目二\n- 項目三\n"
        converter.convert(md, tmp_docx)
        doc = Document(tmp_docx)

        bullet_items = [p for p in doc.paragraphs if p.style.name == 'List Bullet']
        assert len(bullet_items) == 3

    def test_nested_bullet_list(self, converter, tmp_docx):
        """二級項目符號。"""
        md = "## 測試\n\n- 一級項目\n  - 二級項目 A\n  - 二級項目 B\n"
        converter.convert(md, tmp_docx)
        doc = Document(tmp_docx)

        l1_items = [p for p in doc.paragraphs if p.style.name == 'List Bullet']
        l2_items = [p for p in doc.paragraphs if p.style.name == 'List Bullet 2']
        assert len(l1_items) == 1
        assert len(l2_items) == 2


# ===== 引用區塊測試 =====

class TestBlockquote:
    """引用區塊測試。"""

    def test_blockquote_italic(self, converter, tmp_docx):
        """引用區塊應為斜體。"""
        converter.convert(SAMPLE_WITH_BLOCKQUOTE, tmp_docx)
        doc = Document(tmp_docx)

        italic_found = False
        for para in doc.paragraphs:
            for run in para.runs:
                if run.italic and '檔案' in run.text:
                    italic_found = True
                    break
        assert italic_found, "引用區塊未設定為斜體"


# ===== CJK 字型測試 =====

class TestCJKFonts:
    """CJK 字型設定測試。"""

    def test_default_font_set(self, converter, tmp_docx):
        """文件預設字型應為新細明體。"""
        converter.convert(SAMPLE_SIMPLE_MD, tmp_docx)
        doc = Document(tmp_docx)

        normal_style = doc.styles['Normal']
        assert normal_style.font.name == FONT_BODY

    def test_east_asian_font_set(self, converter, tmp_docx):
        """East Asian 字型屬性應設定正確。"""
        converter.convert(SAMPLE_SIMPLE_MD, tmp_docx)
        doc = Document(tmp_docx)

        normal_style = doc.styles['Normal']
        east_asian = normal_style.element.rPr.rFonts.get(qn('w:eastAsia'))
        assert east_asian == FONT_BODY

    def test_heading_font(self, converter, tmp_docx):
        """標題字型應為微軟正黑體。"""
        converter.convert("# 測試標題\n\n內文", tmp_docx)
        doc = Document(tmp_docx)

        for para in doc.paragraphs:
            if para.style.name.startswith('Heading'):
                for run in para.runs:
                    assert run.font.name == FONT_HEADING
                    break


# ===== 頁面設定測試 =====

class TestPageSetup:
    """頁面設定測試。"""

    def test_a4_page_size(self, converter, tmp_docx):
        """頁面應為 A4 大小。"""
        converter.convert(SAMPLE_SIMPLE_MD, tmp_docx)
        doc = Document(tmp_docx)

        section = doc.sections[0]
        # A4: 21cm x 29.7cm (允許微小誤差)
        assert abs(section.page_width.cm - 21.0) < 0.1
        assert abs(section.page_height.cm - 29.7) < 0.1


# ===== details/summary HTML 標籤測試 =====

class TestHtmlTags:
    """HTML 標籤處理測試。"""

    def test_details_tag_stripped(self, converter, tmp_docx):
        """<details> 標籤應被移除，內容保留。"""
        converter.convert(SAMPLE_MEETING_MD, tmp_docx)
        doc = Document(tmp_docx)

        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert '<details>' not in full_text
        assert '<summary>' not in full_text
        assert '</details>' not in full_text
        # 但逐字稿內容應保留
        assert '測試用的逐字稿' in full_text


# ===== 水平線測試 =====

class TestHorizontalRule:
    """水平分隔線測試。"""

    def test_horizontal_rule_present(self, converter, tmp_docx):
        """--- 應轉為段落分隔線。"""
        converter.convert(SAMPLE_WITH_BLOCKQUOTE, tmp_docx)
        doc = Document(tmp_docx)

        # 驗證文件中有段落底部框線（水平線實作方式）
        hr_found = False
        for para in doc.paragraphs:
            pPr = para._p.find(qn('w:pPr'))
            if pPr is not None:
                pBdr = pPr.find(qn('w:pBdr'))
                if pBdr is not None:
                    hr_found = True
                    break
        assert hr_found, "未找到水平分隔線"


# ===== 端到端整合測試 =====

class TestEndToEnd:
    """端到端整合測試：模擬完整會議記錄轉換流程。"""

    def test_full_pipeline_content_integrity(self, converter, tmp_docx):
        """完整轉換後，所有關鍵內容都應保留。"""
        converter.convert(SAMPLE_MEETING_MD, tmp_docx)
        doc = Document(tmp_docx)

        full_text = "\n".join(p.text for p in doc.paragraphs)

        # 標題
        assert '會議記錄摘要' in full_text
        # 會議概況
        assert '2026 年 2 月 28 日' in full_text
        assert '張三' in full_text
        # 執行摘要
        assert 'AI 自動化專案' in full_text
        # 議題
        assert '系統準確率評估' in full_text
        # 備註
        assert '3 月 7 日' in full_text

    def test_full_pipeline_table_integrity(self, converter, tmp_docx):
        """完整轉換後，待辦事項表格資料完整。"""
        converter.convert(SAMPLE_MEETING_MD, tmp_docx)
        doc = Document(tmp_docx)

        table = doc.tables[0]
        all_text = ""
        for row in table.rows:
            for cell in row.cells:
                all_text += cell.text + " "

        assert '收集訓練資料' in all_text
        assert '張三' in all_text
        assert '設計半自動介面' in all_text
        assert '李四' in all_text
        assert '撰寫測試報告' in all_text
        assert '王五' in all_text

    def test_file_size_reasonable(self, converter, tmp_docx):
        """輸出檔案大小合理（不應過大或過小）。"""
        converter.convert(SAMPLE_MEETING_MD, tmp_docx)
        size = os.path.getsize(tmp_docx)
        # DOCX 至少有基本結構 (> 5KB)，不應超過 1MB（純文字內容）
        assert size > 5000, f"檔案過小: {size} bytes"
        assert size < 1_000_000, f"檔案過大: {size} bytes"
