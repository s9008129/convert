"""
DOCX 轉換服務。

將會議記錄 Markdown 轉換為格式化的 Word (.docx) 文件。
針對會議紀錄的固定結構進行最佳化解析。

支援元素：H1/H2 標題、項目符號（一/二級）、粗體、表格（含框線）、
引用區塊、水平分隔線、HTML details/summary 標籤。
"""

import re
import os
from typing import Optional

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

from backend.core.logger import log


# CJK 字型常數
FONT_HEADING = "Microsoft JhengHei"   # 微軟正黑體
FONT_BODY = "PMingLiU"                # 新細明體
FONT_BODY_ALT = "SimSun"             # 宋體（備用）

# 粗體 pattern
BOLD_PATTERN = re.compile(r'\*\*(.+?)\*\*')

# 公文紀錄結構 pattern（v4.3.2）：
# 紀錄本文是純文字（非 markdown 標題），若不辨識結構，Word 會是一片
# 同大小的字牆。以下兩個 pattern 讓「一、報告事項」等章節與
# 「案由：/決議：」等欄位標籤在 Word 中呈現公文應有的層次。
RECORD_SECTION_PATTERN = re.compile(r'^[一二三四五六七八九十]+、')
RECORD_LABEL_PATTERN = re.compile(
    r'^(會議名稱|會議時間|會議地點|主\s*席|出席人員|列席人員|記\s*錄|'
    r'案由|說明|決議|各單位意見（多方立場）|各單位意見|'
    r'主辦單位|協辦單位|辦理期程)\s*([：:])\s*(.*)$'
)


class MarkdownToDocxConverter:
    """
    將會議紀錄 Markdown 轉換為 Word (.docx) 文件。

    設計原則：
    - 針對已知的會議紀錄 Markdown 結構進行解析（非通用轉換器）
    - 防禦性解析：未知行格式 → 當成一般段落
    - 無狀態：每次 convert() 呼叫獨立
    """

    def convert(self, md_content: str, output_path: str) -> str:
        """
        將 Markdown 內容轉換為 DOCX 檔案。

        Args:
            md_content: Markdown 原始內容
            output_path: 輸出 .docx 檔案路徑

        Returns:
            輸出檔案的絕對路徑

        Raises:
            ValueError: md_content 為空
            IOError: 無法寫入檔案
        """
        if not md_content or not md_content.strip():
            raise ValueError("Markdown 內容不可為空")

        doc = Document()
        self._setup_document_styles(doc)
        self._parse_and_build(doc, md_content)
        doc.save(output_path)

        log.info(f"[DOCX] 轉換完成: {output_path}")
        return os.path.abspath(output_path)

    def _setup_document_styles(self, doc: Document):
        """設定文件全域樣式：頁面邊距、預設字型、行距。"""
        # 頁面設定（A4 標準邊距）
        section = doc.sections[0]
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(3.17)

        # 設定預設字型（Normal 樣式）
        style = doc.styles['Normal']
        font = style.font
        font.name = FONT_BODY
        font.size = Pt(12)
        # 設定 East Asian 字型
        style.element.rPr.rFonts.set(qn('w:eastAsia'), FONT_BODY)

        # 設定行距 1.5 倍
        paragraph_format = style.paragraph_format
        paragraph_format.line_spacing = 1.5
        paragraph_format.space_after = Pt(6)

    def _parse_and_build(self, doc: Document, md_content: str):
        """逐行解析 Markdown 並建構 DOCX 內容。"""
        lines = md_content.split('\n')
        i = 0
        in_details = False
        table_rows = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 跳過空行
            if not stripped:
                # 如果正在收集表格行，先完成表格
                if table_rows:
                    self._add_table(doc, table_rows)
                    table_rows = []
                i += 1
                continue

            # HTML details/summary 標籤處理
            if stripped.startswith('<details'):
                in_details = True
                i += 1
                continue
            if stripped.startswith('</details'):
                in_details = False
                i += 1
                continue
            if stripped.startswith('<summary>'):
                # 跳過 summary 標籤，不需要在 DOCX 中顯示
                i += 1
                continue

            # 水平分隔線
            if stripped == '---' or stripped == '***' or stripped == '___':
                if table_rows:
                    self._add_table(doc, table_rows)
                    table_rows = []
                self._add_horizontal_rule(doc)
                i += 1
                continue

            # 表格行（含 | 的行）
            if stripped.startswith('|') and stripped.endswith('|'):
                # 檢查是否為分隔線行（如 | :--- | :--- |）
                if self._is_table_separator(stripped):
                    i += 1
                    continue
                table_rows.append(stripped)
                i += 1
                continue

            # 如果已收集表格但遇到非表格行，先完成表格
            if table_rows:
                self._add_table(doc, table_rows)
                table_rows = []

            # H1 標題
            if stripped.startswith('# ') and not stripped.startswith('## '):
                text = stripped[2:].strip()
                self._add_heading(doc, text, level=1)
                i += 1
                continue

            # H2 標題
            if stripped.startswith('## '):
                text = stripped[3:].strip()
                self._add_heading(doc, text, level=2)
                i += 1
                continue

            # 引用區塊
            if stripped.startswith('> '):
                text = stripped[2:].strip()
                self._add_blockquote(doc, text)
                i += 1
                continue

            # 二級項目符號（前面有空白）
            if (line.startswith('  - ') or line.startswith('    - ')
                    or line.startswith('\t- ')):
                text = stripped.lstrip('- ').strip()
                self._add_list_item(doc, text, level=2)
                i += 1
                continue

            # 一級項目符號
            if stripped.startswith('- ') or stripped.startswith('* '):
                text = stripped[2:].strip()
                self._add_list_item(doc, text, level=1)
                i += 1
                continue

            # 公文紀錄章節（一、報告事項 / 二、討論事項 / 三、主席裁示事項…）
            if RECORD_SECTION_PATTERN.match(stripped):
                self._add_record_section(doc, stripped)
                i += 1
                continue

            # 公文欄位標籤（會議名稱：/案由：/決議：…）→ 標籤加粗
            if self._try_add_labeled_paragraph(doc, stripped):
                i += 1
                continue

            # 一般段落（包括 details 內的逐字稿文字）
            self._add_paragraph(doc, stripped)
            i += 1

        # 迴圈結束後，檢查是否有未完成的表格
        if table_rows:
            self._add_table(doc, table_rows)

    def _add_heading(self, doc: Document, text: str, level: int):
        """新增標題。"""
        heading = doc.add_heading(level=level)

        if level == 1:
            heading.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            heading.paragraph_format.space_before = Pt(12)
            heading.paragraph_format.space_after = Pt(12)
        else:
            heading.paragraph_format.space_before = Pt(18)
            heading.paragraph_format.space_after = Pt(8)

        # 解析粗體並設定字型
        self._add_formatted_runs(heading, text, is_heading=True, heading_level=level)

    def _add_paragraph(self, doc: Document, text: str):
        """新增一般段落。"""
        para = doc.add_paragraph()
        self._add_formatted_runs(para, text)

    def _add_record_section(self, doc: Document, text: str):
        """公文紀錄章節列（如「一、 報告事項：」）：加粗、放大、段前留白。"""
        para = doc.add_paragraph()
        para.paragraph_format.space_before = Pt(14)
        para.paragraph_format.space_after = Pt(6)
        run = para.add_run(text)
        run.bold = True
        run.font.size = Pt(15)
        run.font.name = FONT_HEADING
        run.font.color.rgb = RGBColor(0x1A, 0x44, 0x80)
        rPr = run.font.element.rPr
        if rPr is not None:
            rPr.rFonts.set(qn('w:eastAsia'), FONT_HEADING)

    def _try_add_labeled_paragraph(self, doc: Document, text: str) -> bool:
        """公文欄位標籤列（會議名稱：/案由：/決議：…）：標籤加粗，內容照常。

        Returns:
            True 表示本行已處理；False 表示非欄位標籤列，交回一般段落流程。
        """
        match = RECORD_LABEL_PATTERN.match(text)
        if not match:
            return False

        para = doc.add_paragraph()
        label_run = para.add_run(f"{match.group(1)}{match.group(2)}")
        label_run.bold = True
        self._set_run_font(label_run)

        rest = match.group(3)
        if rest:
            self._add_formatted_runs(para, rest)
        return True

    def _add_blockquote(self, doc: Document, text: str):
        """新增引用區塊（斜體、灰色、左縮排）。"""
        para = doc.add_paragraph()
        para.paragraph_format.left_indent = Cm(1.0)

        # 處理 Markdown 換行符號（> 行末的兩個空格）
        text = text.rstrip()

        run = para.add_run(text)
        run.italic = True
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        run.font.size = Pt(11)
        self._set_run_font(run)

    def _add_list_item(self, doc: Document, text: str, level: int = 1):
        """新增項目符號。"""
        if level == 1:
            para = doc.add_paragraph(style='List Bullet')
        else:
            para = doc.add_paragraph(style='List Bullet 2')

        self._add_formatted_runs(para, text)

    def _add_table(self, doc: Document, rows: list):
        """
        新增表格，含完整框線與標題列樣式。

        確保表格在 Office 2024 / M365 中正確顯示：
        - 使用明確的 XML 框線設定（不依賴樣式繼承）
        - 表格寬度自動適應頁面
        - 標題行粗體 + 灰底
        """
        if not rows:
            return

        # 解析表格資料
        parsed_rows = []
        for row_str in rows:
            cells = [c.strip() for c in row_str.strip('|').split('|')]
            parsed_rows.append(cells)

        if not parsed_rows:
            return

        num_cols = len(parsed_rows[0])
        num_rows = len(parsed_rows)

        # 建立表格
        table = doc.add_table(rows=num_rows, cols=num_cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # 設定表格寬度為自動適應（100% 頁面寬度）
        tbl = table._tbl
        tbl_pr = tbl.tblPr if tbl.tblPr is not None else parse_xml(f'<w:tblPr {nsdecls("w")}/>')
        tbl_width = parse_xml(
            f'<w:tblW {nsdecls("w")} w:type="pct" w:w="5000"/>'
        )
        tbl_pr.append(tbl_width)

        # 設定全表框線（確保 Office 2024/M365 相容）
        self._set_table_borders(table)

        # 填充資料
        for row_idx, row_data in enumerate(parsed_rows):
            for col_idx, cell_text in enumerate(row_data):
                if col_idx >= num_cols:
                    break

                cell = table.rows[row_idx].cells[col_idx]

                # 清除預設段落
                if cell.paragraphs:
                    para = cell.paragraphs[0]
                else:
                    para = cell.add_paragraph()

                # 標題行樣式
                if row_idx == 0:
                    self._add_formatted_runs(para, cell_text, is_table_header=True)
                    # 標題行灰底
                    self._set_cell_shading(cell, "D9E2F3")
                else:
                    self._add_formatted_runs(para, cell_text)

                # 設定表格內段落格式
                para.paragraph_format.space_before = Pt(2)
                para.paragraph_format.space_after = Pt(2)
                para.paragraph_format.line_spacing = 1.15

        # 表格前後間距
        if table._tbl.getprevious() is not None:
            pass  # 表格前已有內容，依預設間距即可

    def _set_table_borders(self, table):
        """
        設定表格完整框線。

        使用直接 XML 操作確保 Office 2024 / M365 相容性。
        不依賴樣式繼承，避免不同 Word 版本的渲染差異。
        """
        tbl = table._tbl
        tbl_pr = tbl.tblPr
        if tbl_pr is None:
            tbl_pr = parse_xml(f'<w:tblPr {nsdecls("w")}/>') 
            tbl.insert(0, tbl_pr)

        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            '  <w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            '  <w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            '  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            '  <w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            '  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            '  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            '</w:tblBorders>'
        )

        # 移除既有的 tblBorders（避免重複）
        for existing in tbl_pr.findall(qn('w:tblBorders')):
            tbl_pr.remove(existing)

        tbl_pr.append(borders)

    def _set_cell_shading(self, cell, color_hex: str):
        """設定儲存格底色。"""
        shading = parse_xml(
            f'<w:shd {nsdecls("w")} w:fill="{color_hex}" w:val="clear"/>'
        )
        cell._tc.get_or_add_tcPr().append(shading)

    def _add_horizontal_rule(self, doc: Document):
        """新增水平分隔線（細灰線）。"""
        para = doc.add_paragraph()
        para.paragraph_format.space_before = Pt(6)
        para.paragraph_format.space_after = Pt(6)

        # 使用底部框線模擬水平線
        pPr = para._p.get_or_add_pPr()
        pBdr = parse_xml(
            f'<w:pBdr {nsdecls("w")}>'
            '  <w:bottom w:val="single" w:sz="6" w:space="1" w:color="CCCCCC"/>'
            '</w:pBdr>'
        )
        pPr.append(pBdr)

    def _add_formatted_runs(self, para, text: str,
                            is_heading: bool = False,
                            heading_level: int = 0,
                            is_table_header: bool = False):
        """
        解析行內格式（**粗體**）並建立 Run。

        將文字拆分為粗體與非粗體片段，分別建立 Run 並套用格式。
        """
        # 分割粗體片段
        parts = BOLD_PATTERN.split(text)
        bold_matches = BOLD_PATTERN.findall(text)

        bold_idx = 0
        for i, part in enumerate(parts):
            if not part:
                continue

            is_bold = part in bold_matches and bold_idx < len(bold_matches)
            if is_bold:
                bold_idx += 1

            run = para.add_run(part)

            if is_bold or is_table_header:
                run.bold = True

            if is_heading:
                run.font.name = FONT_HEADING
                run.font.element.rPr.rFonts.set(qn('w:eastAsia'), FONT_HEADING)
                if heading_level == 1:
                    run.font.size = Pt(22)
                    run.font.color.rgb = RGBColor(0x1A, 0x3C, 0x6D)
                else:
                    run.font.size = Pt(16)
                    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            elif is_table_header:
                run.font.name = FONT_HEADING
                run.font.element.rPr.rFonts.set(qn('w:eastAsia'), FONT_HEADING)
                run.font.size = Pt(11)
            else:
                self._set_run_font(run)

    def _set_run_font(self, run):
        """設定 Run 的 CJK 字型。"""
        run.font.name = FONT_BODY
        rPr = run.font.element.rPr
        if rPr is not None:
            rPr.rFonts.set(qn('w:eastAsia'), FONT_BODY)

    @staticmethod
    def _is_table_separator(line: str) -> bool:
        """判斷是否為表格分隔線（如 | :--- | :--- |）。"""
        cells = [c.strip() for c in line.strip('|').split('|')]
        return all(
            re.match(r'^:?-+:?$', cell.strip()) for cell in cells if cell.strip()
        )


# 全域轉換器實例
docx_converter = MarkdownToDocxConverter()
