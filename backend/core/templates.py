"""會議模板註冊表（v4.4.0）。

每種會議類型（domain）一個 MeetingTemplate，集中定義：
- 生成用系統提示詞與萃取／生成增補規則
- 結構驗證樣式（required / extra / forbidden patterns）
- 記錄級後處理骨架（缺漏欄位補「（待確認）」）
- DOCX 公文層次辨識樣式（章節與欄位標籤）
- 領域術語表（僅注入 LLM 校正層，不進 ASR hotwords）
- local_only 旗標（機敏會議強制本地處理）

新增一種會議類型＝新增一個 prompt 模組（backend/core/prompt_templates/）
＋在本檔 _TEMPLATES 註冊一筆；驗證、後處理、DOCX、前端選單全部自動生效。

匯入紀律：本模組只允許 import config／prompts／prompt_templates，
嚴禁 import summarization／text_postprocess／docx_converter（避免循環）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Optional

from backend.core.prompt_templates import isms_meeting, procurement, section_meeting

# 與 text_postprocess.MISSING_TEXT 同值；為避免匯入循環在此重複定義，
# 由 tests/test_templates.py 驗證兩者一致。
_MISSING_TEXT = "逐字稿未提及"


@dataclass(frozen=True)
class RecordFieldSpec:
    """記錄開頭欄位：pattern 不存在時，將 line 補進紀錄開頭。"""

    line: str
    pattern: re.Pattern


@dataclass(frozen=True)
class RecordSectionSpec:
    """記錄章節：整節缺漏補 skeleton_lines；節存在時逐一檢查 subfields。

    subfields 每項為 (存在性 pattern, 缺漏時追加的行)。
    """

    presence_pattern: re.Pattern
    skeleton_lines: tuple[str, ...]
    subfields: tuple[tuple[re.Pattern, tuple[str, ...]], ...] = ()


@dataclass(frozen=True)
class AttachmentSpec:
    """模板附件定義（v4.5.0）：由紀錄本文 Markdown 確定性建構第二份文件。

    build_markdown 為純文字轉換函式（本文 md → 附件 md），
    不得依賴 LLM 二次生成，以保證本文與附件內容一致。
    """

    label: str  # 前端按鈕文字（如「列管資料」）
    download_name: str  # 下載檔名主體（如「科務會議列管資料」）
    build_markdown: Callable[[str], str]


@dataclass(frozen=True)
class FormParagraphSpec:
    """表單文件開頭段落（標題／勾選行）。text_template 可含 {欄位鍵} 插值。"""

    text_template: str
    align_center: bool = False
    bold: bool = False
    font_size_pt: int = 12


@dataclass(frozen=True)
class FormCellBlock:
    """儲存格內一個「標籤＋欄位值」區塊；field_key 空字串＝純標籤格。

    label_own_line=True 時標籤獨立成段、欄位值逐行各自成段（多行欄位）；
    False 時欄位值第一行接在標籤同段之後。
    """

    label: str = ""
    field_key: str = ""
    label_own_line: bool = False


@dataclass(frozen=True)
class FormCellSpec:
    """表單表格一個儲存格：blocks 為內容區塊、span 為水平合併欄數。"""

    blocks: tuple[FormCellBlock, ...]
    span: int = 1
    align_center: bool = False


@dataclass(frozen=True)
class FormRowSpec:
    """表單表格一列；min_height_cm 供簽名空列保留書寫高度。"""

    cells: tuple[FormCellSpec, ...]
    min_height_cm: float = 0.0


@dataclass(frozen=True)
class FormTableSpec:
    """表單表格：column_widths_cm 定義欄格線，rows 依 span 對齊欄格線。"""

    column_widths_cm: tuple[float, ...]
    rows: tuple[FormRowSpec, ...]


@dataclass(frozen=True)
class FormLayoutSpec:
    """表單式 DOCX 版面（v4.6.0）：docx_converter 依此渲染官方表格版面。

    extract_fields 為純文字轉換函式（本文 md → 欄位 dict），不得依賴
    LLM 二次生成；applicability_pattern 未命中本文時退回一般渲染
    （防摘要失敗時表單版面吞掉逐字稿）。
    """

    intro_paragraphs: tuple[FormParagraphSpec, ...]
    tables: tuple[FormTableSpec, ...]
    extract_fields: Callable[[str], dict]
    applicability_pattern: re.Pattern


@dataclass(frozen=True)
class MeetingTemplate:
    """一種會議類型的完整定義。"""

    id: str
    display_name: str
    description: str
    local_only: bool = False
    # None 表示延遲讀取 settings.DEFAULT_SYSTEM_PROMPT（讓 env 覆寫仍生效）
    system_prompt: Optional[str] = None
    extraction_prompt_extra: str = ""
    generation_message_extra: str = ""
    # 驗證層：缺少即列入補強問題清單
    required_section_patterns: tuple[tuple[str, re.Pattern], ...] = ()
    # 驗證層：額外必要欄位（general 的主辦單位／辦理期程）
    extra_field_patterns: tuple[tuple[str, re.Pattern], ...] = ()
    # 驗證層：命中即列入補強問題清單（機敏洩漏等）
    forbidden_patterns: tuple[tuple[str, re.Pattern], ...] = ()
    # 記錄級後處理骨架
    record_header_fields: tuple[RecordFieldSpec, ...] = ()
    record_sections: tuple[RecordSectionSpec, ...] = ()
    # DOCX 公文層次
    docx_section_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r"^[一二三四五六七八九十]+、")
    )
    docx_label_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r"$^")  # 預設不匹配任何行
    )
    # 領域術語（僅注入 LLM 語意校正層）
    glossary_terms: tuple[str, ...] = ()
    glossary_corrections: tuple[tuple[str, str], ...] = ()
    result_title: str = "# 會議紀錄"
    # 附件輸出（v4.5.0）：None 表示此會議類型無附件
    attachment: Optional[AttachmentSpec] = None
    # 表單式 DOCX 版面（v4.6.0）：None 表示採一般公文段落式渲染
    form_layout: Optional[FormLayoutSpec] = None

    def resolve_system_prompt(self) -> str:
        """取得系統提示詞；general 延遲讀取設定值，env 覆寫仍生效。"""
        if self.system_prompt is not None:
            return self.system_prompt
        from backend.core.config import settings

        return settings.DEFAULT_SYSTEM_PROMPT


GENERAL_TEMPLATE_ID = "general"

# ---------------------------------------------------------------------------
# general：現行公務會議紀錄格式（行為必須與 v4.3.3 完全一致）
# 以下常數自 summarization.py／text_postprocess.py／docx_converter.py 原樣搬入。
# ---------------------------------------------------------------------------

_GENERAL_FALLBACK_LINE = f"- {_MISSING_TEXT}（主辦單位：{_MISSING_TEXT}，辦理期程：{_MISSING_TEXT}）"

_GENERAL_TEMPLATE = MeetingTemplate(
    id=GENERAL_TEMPLATE_ID,
    display_name="一般會議",
    description="通用公務會議紀錄（報告事項／討論事項／主席裁示事項）",
    local_only=False,
    system_prompt=None,  # 延遲讀取 settings.DEFAULT_SYSTEM_PROMPT
    required_section_patterns=(
        ("會議名稱", re.compile(r"會議名稱\s*[:：]")),
        ("會議時間", re.compile(r"會議時間\s*[:：]")),
        ("會議地點", re.compile(r"會議地點\s*[:：]")),
        ("主席", re.compile(r"主\s*席\s*[:：]")),
        ("出席人員", re.compile(r"出席人員\s*[:：]")),
        ("列席人員", re.compile(r"列席人員\s*[:：]")),
        ("記錄", re.compile(r"記\s*錄\s*[:：]")),
        ("一、報告事項", re.compile(r"一、\s*報告事項")),
        ("二、討論事項", re.compile(r"二、\s*討論事項")),
        ("案由", re.compile(r"案由\s*[:：]")),
        ("說明", re.compile(r"說明\s*[:：]")),
        ("各單位意見", re.compile(r"各單位意見")),
        ("決議", re.compile(r"決議\s*[:：]")),
        ("三、主席裁示事項", re.compile(r"三、\s*主席裁示事項")),
    ),
    extra_field_patterns=(
        ("主辦單位", re.compile(r"主辦單位\s*[:：]")),
        ("辦理期程", re.compile(r"辦理期程\s*[:：]")),
    ),
    record_header_fields=(
        RecordFieldSpec(f"會議名稱：{_MISSING_TEXT}", re.compile(r"^會議名稱\s*[:：]", re.MULTILINE)),
        RecordFieldSpec(f"會議時間：{_MISSING_TEXT}", re.compile(r"^會議時間\s*[:：]", re.MULTILINE)),
        RecordFieldSpec(f"會議地點：{_MISSING_TEXT}", re.compile(r"^會議地點\s*[:：]", re.MULTILINE)),
        RecordFieldSpec(f"主  席：{_MISSING_TEXT}", re.compile(r"^主\s*席\s*[:：]", re.MULTILINE)),
        RecordFieldSpec(f"出席人員：{_MISSING_TEXT}", re.compile(r"^出席人員\s*[:：]", re.MULTILINE)),
        RecordFieldSpec("列席人員：無", re.compile(r"^列席人員\s*[:：]", re.MULTILINE)),
        RecordFieldSpec("記  錄：AI 會議助理", re.compile(r"^記\s*錄\s*[:：]", re.MULTILINE)),
    ),
    record_sections=(
        RecordSectionSpec(
            presence_pattern=re.compile(r"一、\s*報告事項"),
            skeleton_lines=("一、 報告事項：", "無"),
        ),
        RecordSectionSpec(
            presence_pattern=re.compile(r"二、\s*討論事項"),
            skeleton_lines=(
                "二、 討論事項：",
                f"案由：{_MISSING_TEXT}",
                f"說明：{_MISSING_TEXT}",
                "各單位意見（多方立場）：",
                f"- {_MISSING_TEXT}：{_MISSING_TEXT}",
                "決議：",
                f"1. {_MISSING_TEXT}（主辦單位：{_MISSING_TEXT}，協辦單位：{_MISSING_TEXT}）",
            ),
            subfields=(
                (re.compile(r"案由\s*[:：]"), (f"案由：{_MISSING_TEXT}",)),
                (re.compile(r"說明\s*[:：]"), (f"說明：{_MISSING_TEXT}",)),
                (
                    re.compile(r"各單位意見"),
                    ("各單位意見（多方立場）：", f"- {_MISSING_TEXT}：{_MISSING_TEXT}"),
                ),
                (
                    re.compile(r"決議\s*[:：]"),
                    ("決議：", f"1. {_MISSING_TEXT}（主辦單位：{_MISSING_TEXT}，協辦單位：{_MISSING_TEXT}）"),
                ),
            ),
        ),
        RecordSectionSpec(
            presence_pattern=re.compile(r"三、\s*主席裁示事項"),
            skeleton_lines=("三、 主席裁示事項（後續管考與追蹤）：", _GENERAL_FALLBACK_LINE),
            subfields=(
                (re.compile(r"辦理期程\s*[:：]"), (_GENERAL_FALLBACK_LINE,)),
            ),
        ),
    ),
    docx_section_pattern=re.compile(r"^[一二三四五六七八九十]+、"),
    docx_label_pattern=re.compile(
        r"^(會議名稱|會議時間|會議地點|主\s*席|出席人員|列席人員|記\s*錄|"
        r"案由|說明|決議|各單位意見（多方立場）|各單位意見|"
        r"主辦單位|協辦單位|辦理期程)\s*([：:])\s*(.*)$"
    ),
    result_title="# 會議紀錄",
)

# ---------------------------------------------------------------------------
# procurement_evaluation：採購評選會（工程會範本「壹～拾陸」結構，僅限本地）
# ---------------------------------------------------------------------------

_MISSING_CONFIRM = "（待確認）"

_PROCUREMENT_TITLE_LINE = (
    f"「{_MISSING_CONFIRM}」案採購評選委員會第{_MISSING_CONFIRM}次會議（評選會議）紀錄"
)


def _proc_section(label: str, presence: str, *skeleton: str) -> RecordSectionSpec:
    """採購模板章節速記：presence 為章節標題的容錯 regex。"""
    return RecordSectionSpec(
        presence_pattern=re.compile(presence),
        skeleton_lines=skeleton or (f"{label}{_MISSING_CONFIRM}",),
    )


_PROCUREMENT_TEMPLATE = MeetingTemplate(
    id="procurement_evaluation",
    display_name="採購評選會",
    description="政府採購評選委員會會議（工程會範本格式；涉機敏內容，僅限本地模式）",
    local_only=True,
    system_prompt=procurement.PROCUREMENT_SYSTEM_PROMPT,
    extraction_prompt_extra=procurement.PROCUREMENT_EXTRACTION_EXTRA,
    generation_message_extra=procurement.PROCUREMENT_GENERATION_EXTRA,
    # 驗證樣式只留關鍵結構（過嚴會讓本地模型補強輪耗盡）
    required_section_patterns=(
        ("紀錄標題（採購評選委員會）", re.compile(r"採購評選委員會")),
        ("壹、會議時間", re.compile(r"壹、\s*會議時間")),
        ("伍、出席委員", re.compile(r"伍、\s*出席委員")),
        ("玖、投標廠商家數及名稱", re.compile(r"玖、\s*投標廠商")),
        ("拾參、廠商簡報及詢答事項", re.compile(r"拾[參叁]、\s*廠商簡報")),
        ("委員提問（詢答成對）", re.compile(r"委員提問\s*[:：]")),
        ("廠商答詢（詢答成對）", re.compile(r"廠商答詢\s*[:：]")),
        ("拾肆、委員討論及評選結果", re.compile(r"拾肆、\s*委員討論及評選結果")),
        ("拾陸、散會", re.compile(r"拾陸、\s*散會")),
    ),
    forbidden_patterns=(
        (
            "底價相關數字（依採購法第34條不得寫入，須改為「（機敏資訊，不列入紀錄）」）",
            re.compile(r"底價[^\n]{0,12}[\d０-９]"),
        ),
        (
            "個別委員評分數字（依最有利標評選辦法第20條不得寫入，須改為「（機敏資訊，不列入紀錄）」）",
            re.compile(r"委員[^\n，。；]{0,6}(?:評分|給分|打分)[^\n]{0,8}[\d０-９]"),
        ),
    ),
    record_header_fields=(
        RecordFieldSpec(
            _PROCUREMENT_TITLE_LINE,
            re.compile(r"採購評選委員會第.*會議.*紀錄"),
        ),
    ),
    record_sections=(
        _proc_section("壹、會議時間：", r"壹、\s*會議時間"),
        _proc_section("貳、會議地點：", r"貳、\s*會議地點"),
        _proc_section("參、主持人：", r"[參叁]、\s*主持人", f"參、主持人：{_MISSING_CONFIRM}（召集人）　記錄：AI 會議助理"),
        _proc_section("肆、評選委員會組成：", r"肆、\s*評選委員會組成"),
        _proc_section("伍、出席委員：", r"伍、\s*出席委員"),
        _proc_section("陸、請假委員：", r"陸、\s*請假委員", "陸、請假委員：無"),
        _proc_section("柒、列席人員：", r"柒、\s*列席人員", "柒、列席人員：無"),
        _proc_section("捌、評選方式：", r"捌、\s*評選方式"),
        _proc_section("玖、投標廠商家數及名稱：", r"玖、\s*投標廠商"),
        _proc_section("拾、主席致詞：", r"拾、\s*主席致詞", "拾、主席致詞：（略）"),
        _proc_section("拾壹、報告事項：", r"拾壹、\s*報告事項", "拾壹、報告事項：無"),
        _proc_section("拾貳、委員確認事項：", r"拾貳、\s*委員確認事項"),
        RecordSectionSpec(
            presence_pattern=re.compile(r"拾[參叁]、\s*廠商簡報"),
            skeleton_lines=(
                "拾參、廠商簡報及詢答事項：",
                f"一、{_MISSING_CONFIRM}",
                f"（一）簡報要點：{_MISSING_CONFIRM}",
                "（二）詢答：",
                f"委員提問：{_MISSING_CONFIRM}",
                f"廠商答詢：{_MISSING_CONFIRM}",
            ),
        ),
        _proc_section("拾肆、委員討論及評選結果：", r"拾肆、\s*委員討論及評選結果"),
        _proc_section("拾伍、委員是否有不同意見：", r"拾伍、\s*委員是否有不同意見", "拾伍、委員是否有不同意見：無"),
        _proc_section("拾陸、散會：", r"拾陸、\s*散會"),
    ),
    docx_section_pattern=re.compile(r"^[壹貳參叁肆伍陸柒捌玖拾]+、"),
    docx_label_pattern=re.compile(
        r"^(委員提問|廠商答詢|簡報要點|（一）簡報要點|（二）詢答|決議)\s*([：:])\s*(.*)$"
    ),
    glossary_terms=procurement.PROCUREMENT_GLOSSARY_TERMS,
    glossary_corrections=procurement.PROCUREMENT_GLOSSARY_CORRECTIONS,
    result_title="# 採購評選會議紀錄",
)


# ---------------------------------------------------------------------------
# section_meeting：科務會議（科室內部會議；含決議事項彙整表與列管資料附件）
# 格式依據使用者提供之官方範本（115年7月份第1次科務會議紀錄／列管資料）。
# ---------------------------------------------------------------------------

_SECTION_MEETING_TEMPLATE = MeetingTemplate(
    id="section_meeting",
    display_name="科務會議",
    description="科室內部科務會議紀錄（含決議事項辦理情形彙整表與列管資料附件）",
    local_only=False,
    system_prompt=section_meeting.SECTION_MEETING_SYSTEM_PROMPT,
    extraction_prompt_extra=section_meeting.SECTION_MEETING_EXTRACTION_EXTRA,
    generation_message_extra=section_meeting.SECTION_MEETING_GENERATION_EXTRA,
    # 驗證樣式只留關鍵結構（過嚴會讓本地模型補強輪耗盡）
    required_section_patterns=(
        ("紀錄標題（科務會議）", re.compile(r"科務會議紀錄")),
        ("時間", re.compile(r"時間\s*[:：]")),
        ("主持人", re.compile(r"主持人\s*[:：]")),
        ("決議事項彙整表（表頭）", re.compile(r"案由及承辦單位")),
        ("科長指示及提醒事項", re.compile(r"指示及提醒")),
        ("散會", re.compile(r"散會\s*[:：]")),
    ),
    forbidden_patterns=(),
    record_header_fields=(
        RecordFieldSpec(
            f"{_MISSING_CONFIRM}{_MISSING_CONFIRM}年{_MISSING_CONFIRM}月份第{_MISSING_CONFIRM}次科務會議紀錄",
            re.compile(r"科務會議紀錄"),
        ),
        RecordFieldSpec(f"時間：{_MISSING_CONFIRM}", re.compile(r"^時間\s*[:：]", re.MULTILINE)),
        RecordFieldSpec(f"地點：{_MISSING_CONFIRM}", re.compile(r"^地點\s*[:：]", re.MULTILINE)),
        RecordFieldSpec(
            f"主持人：{_MISSING_CONFIRM}　紀錄：AI 會議助理",
            re.compile(r"^主持人\s*[:：]", re.MULTILINE),
        ),
        RecordFieldSpec("出席人員：如後附簽到表", re.compile(r"^出席人員\s*[:：]", re.MULTILINE)),
        RecordFieldSpec(
            f"歷次科務會議決議事項繼續列管案件：{_MISSING_CONFIRM}",
            re.compile(r"歷次.{0,14}列管案件"),
        ),
    ),
    record_sections=(
        RecordSectionSpec(
            presence_pattern=re.compile(r"決議事項辦理情形彙整表|案由及承辦單位"),
            skeleton_lines=(
                f"{_MISSING_CONFIRM}科務會議決議事項辦理情形彙整表",
                "決議事項：",
                section_meeting.TRACKING_TABLE_HEADER,
                section_meeting.TRACKING_TABLE_SEPARATOR,
                f"| {_MISSING_CONFIRM} | {_MISSING_CONFIRM}： |  |  |",
            ),
        ),
        RecordSectionSpec(
            presence_pattern=re.compile(r"科長轉知"),
            skeleton_lines=(
                f"一、科長轉知局務會議工作報告及相關注意事項：{_MISSING_CONFIRM}",
            ),
        ),
        RecordSectionSpec(
            presence_pattern=re.compile(r"指示及提醒"),
            skeleton_lines=(
                "二、科長指示及提醒事項：",
                f"（一）{_MISSING_CONFIRM}",
            ),
        ),
        RecordSectionSpec(
            presence_pattern=re.compile(r"散會\s*[:：]"),
            skeleton_lines=(f"散會：{_MISSING_CONFIRM}",),
        ),
    ),
    docx_section_pattern=re.compile(r"^[一二三四五六七八九十]+、"),
    docx_label_pattern=re.compile(
        r"^(時間|地點|主持人|出席人員|紀\s*錄|散會|決議事項|"
        r"歷次科務會議決議事項繼續列管案件)\s*([：:])\s*(.*)$"
    ),
    glossary_terms=section_meeting.SECTION_MEETING_GLOSSARY_TERMS,
    glossary_corrections=section_meeting.SECTION_MEETING_GLOSSARY_CORRECTIONS,
    result_title="# 科務會議紀錄",
    attachment=AttachmentSpec(
        label="列管資料",
        download_name="科務會議列管資料",
        build_markdown=section_meeting.build_tracking_attachment,
    ),
)


# ---------------------------------------------------------------------------
# isms_monthly：ISMS 月工作會議（資安委外維護案月會；表單式官方版面）
# 格式依據使用者提供之官方範本（ISMS_7月工作會議記錄-sample.docx）。
# ---------------------------------------------------------------------------

# 官方會議記錄表版面（欄寬以 A4 文字區約 14.66cm 計）
_ISMS_FORM_LAYOUT = FormLayoutSpec(
    intro_paragraphs=(
        FormParagraphSpec(
            "{機關名稱} 會議記錄表", align_center=True, bold=True, font_size_pt=18
        ),
        FormParagraphSpec("□專案啟動會議；■月工作會議"),
    ),
    tables=(
        # 主表格：專案名稱／會議議題／地點·主席／日期·記錄／參加人員／
        # 內容／追蹤事項／決議事項（同格含臨時動議）
        FormTableSpec(
            column_widths_cm=(2.6, 4.7, 2.6, 4.76),
            rows=(
                FormRowSpec(cells=(
                    FormCellSpec(blocks=(FormCellBlock(label="專案名稱"),)),
                    FormCellSpec(blocks=(FormCellBlock(field_key="專案名稱"),), span=3),
                )),
                FormRowSpec(cells=(
                    FormCellSpec(
                        blocks=(FormCellBlock(label="會議議題：", field_key="會議議題"),),
                        span=4,
                    ),
                )),
                FormRowSpec(cells=(
                    FormCellSpec(blocks=(FormCellBlock(label="地    點"),)),
                    FormCellSpec(blocks=(FormCellBlock(field_key="地點"),)),
                    FormCellSpec(blocks=(FormCellBlock(label="主    席"),)),
                    FormCellSpec(blocks=(FormCellBlock(field_key="主席"),)),
                )),
                FormRowSpec(cells=(
                    FormCellSpec(blocks=(FormCellBlock(label="日    期"),)),
                    FormCellSpec(blocks=(FormCellBlock(field_key="日期"),)),
                    FormCellSpec(blocks=(FormCellBlock(label="記    錄"),)),
                    FormCellSpec(blocks=(FormCellBlock(field_key="記錄"),)),
                )),
                FormRowSpec(cells=(
                    FormCellSpec(
                        blocks=(
                            FormCellBlock(
                                label="參加人員：", field_key="參加人員", label_own_line=True
                            ),
                        ),
                        span=4,
                    ),
                )),
                FormRowSpec(cells=(
                    FormCellSpec(
                        blocks=(
                            FormCellBlock(
                                label="內    容：", field_key="內容", label_own_line=True
                            ),
                        ),
                        span=4,
                    ),
                )),
                FormRowSpec(cells=(
                    FormCellSpec(
                        blocks=(
                            FormCellBlock(
                                label="追蹤事項：", field_key="追蹤事項", label_own_line=True
                            ),
                        ),
                        span=4,
                    ),
                )),
                FormRowSpec(cells=(
                    FormCellSpec(
                        blocks=(
                            FormCellBlock(
                                label="決議事項：", field_key="決議事項", label_own_line=True
                            ),
                            FormCellBlock(
                                label="臨時動議：", field_key="臨時動議", label_own_line=True
                            ),
                        ),
                        span=4,
                    ),
                )),
            ),
        ),
        # 簽到表：跨欄標題＋機關科室、廠商公司兩欄＋簽名空列
        FormTableSpec(
            column_widths_cm=(7.33, 7.33),
            rows=(
                FormRowSpec(cells=(
                    FormCellSpec(
                        blocks=(FormCellBlock(label="簽             到"),),
                        span=2,
                        align_center=True,
                    ),
                )),
                FormRowSpec(cells=(
                    FormCellSpec(
                        blocks=(FormCellBlock(field_key="機關單位"),), align_center=True
                    ),
                    FormCellSpec(
                        blocks=(FormCellBlock(field_key="廠商單位"),), align_center=True
                    ),
                )),
                FormRowSpec(
                    cells=(FormCellSpec(blocks=()), FormCellSpec(blocks=())),
                    min_height_cm=3.0,
                ),
            ),
        ),
    ),
    extract_fields=isms_meeting.extract_form_fields,
    applicability_pattern=re.compile(r"專案名稱\s*[:：]"),
)

_ISMS_MONTHLY_TEMPLATE = MeetingTemplate(
    id="isms_monthly",
    display_name="ISMS月工作會議",
    description="資通安全管理制度（ISMS）委外維護案月工作會議記錄表（表單式官方版面）",
    local_only=False,
    system_prompt=isms_meeting.ISMS_MEETING_SYSTEM_PROMPT,
    extraction_prompt_extra=isms_meeting.ISMS_MEETING_EXTRACTION_EXTRA,
    generation_message_extra=isms_meeting.ISMS_MEETING_GENERATION_EXTRA,
    # 驗證樣式只留關鍵結構（過嚴會讓本地模型補強輪耗盡）
    required_section_patterns=(
        ("專案名稱", re.compile(r"專案名稱\s*[:：]")),
        ("會議議題", re.compile(r"會議議題\s*[:：]")),
        ("參加人員", re.compile(r"參加人員\s*[:：]")),
        ("內容", re.compile(r"內\s*容\s*[:：]")),
        ("追蹤事項", re.compile(r"追蹤事項\s*[:：]")),
        ("決議事項", re.compile(r"決議事項\s*[:：]")),
        ("臨時動議", re.compile(r"臨時動議\s*[:：]")),
    ),
    forbidden_patterns=(),
    record_header_fields=(
        RecordFieldSpec(
            f"機關名稱：{_MISSING_CONFIRM}", re.compile(r"^機關名稱\s*[:：]", re.MULTILINE)
        ),
        RecordFieldSpec(
            f"專案名稱：{_MISSING_CONFIRM}", re.compile(r"^專案名稱\s*[:：]", re.MULTILINE)
        ),
        RecordFieldSpec(
            f"會議議題：{_MISSING_CONFIRM}", re.compile(r"^會議議題\s*[:：]", re.MULTILINE)
        ),
        RecordFieldSpec(
            f"地點：{_MISSING_CONFIRM}", re.compile(r"^地\s*點\s*[:：]", re.MULTILINE)
        ),
        RecordFieldSpec(
            f"主席：{_MISSING_CONFIRM}",
            re.compile(r"^(?:主\s*席|主持人)\s*[:：]", re.MULTILINE),
        ),
        RecordFieldSpec(
            f"日期：{_MISSING_CONFIRM}", re.compile(r"^日\s*期\s*[:：]", re.MULTILINE)
        ),
        RecordFieldSpec(
            f"記錄：{_MISSING_CONFIRM}", re.compile(r"^[記紀]\s*錄\s*[:：]", re.MULTILINE)
        ),
        RecordFieldSpec(
            f"機關單位：{_MISSING_CONFIRM}", re.compile(r"^機關單位\s*[:：]", re.MULTILINE)
        ),
        RecordFieldSpec(
            f"廠商單位：{_MISSING_CONFIRM}", re.compile(r"^廠商單位\s*[:：]", re.MULTILINE)
        ),
    ),
    record_sections=(
        RecordSectionSpec(
            presence_pattern=re.compile(r"參加人員\s*[:：]"),
            skeleton_lines=("參加人員：", _MISSING_CONFIRM),
        ),
        RecordSectionSpec(
            presence_pattern=re.compile(r"內\s*容\s*[:：]"),
            skeleton_lines=("內容：", f"一、{_MISSING_CONFIRM}"),
        ),
        RecordSectionSpec(
            presence_pattern=re.compile(r"追蹤事項\s*[:：]"),
            skeleton_lines=("追蹤事項：", _MISSING_CONFIRM),
        ),
        RecordSectionSpec(
            presence_pattern=re.compile(r"決議事項\s*[:：]"),
            skeleton_lines=("決議事項：", f"一、{_MISSING_CONFIRM}"),
        ),
        RecordSectionSpec(
            presence_pattern=re.compile(r"臨時動議\s*[:：]"),
            skeleton_lines=("臨時動議：", _MISSING_CONFIRM),
        ),
    ),
    docx_section_pattern=re.compile(r"^[一二三四五六七八九十]+、"),
    # 表單渲染退回一般渲染時仍保有公文層次（十四個欄位標籤）
    docx_label_pattern=re.compile(
        r"^(機關名稱|專案名稱|會議議題|地\s*點|主\s*席|主持人|日\s*期|[記紀]\s*錄|"
        r"機關單位|廠商單位|參加人員|內\s*容|追蹤事項|決議事項|臨時動議)\s*([：:])\s*(.*)$"
    ),
    glossary_terms=isms_meeting.ISMS_GLOSSARY_TERMS,
    glossary_corrections=isms_meeting.ISMS_GLOSSARY_CORRECTIONS,
    result_title="# ISMS月工作會議紀錄",
    attachment=None,
    form_layout=_ISMS_FORM_LAYOUT,
)


_TEMPLATES: dict[str, MeetingTemplate] = {
    template.id: template
    for template in (
        _GENERAL_TEMPLATE,
        _PROCUREMENT_TEMPLATE,
        _SECTION_MEETING_TEMPLATE,
        _ISMS_MONTHLY_TEMPLATE,
    )
}


def get_template(template_id: Optional[str]) -> MeetingTemplate:
    """取得會議模板；None／空字串回傳 general，未知 id 拋 ValueError。"""
    if not template_id:
        return _TEMPLATES[GENERAL_TEMPLATE_ID]
    template = _TEMPLATES.get(template_id)
    if template is None:
        raise ValueError(f"未知的會議類型: {template_id}")
    return template


def list_templates() -> list[MeetingTemplate]:
    """回傳所有模板（註冊順序，general 在前）。"""
    return list(_TEMPLATES.values())


def template_public_info() -> list[dict]:
    """給 /api/config 的公開模板資訊（前端選單資料來源）。"""
    return [
        {
            "id": template.id,
            "display_name": template.display_name,
            "description": template.description,
            "local_only": template.local_only,
            "is_default": template.id == GENERAL_TEMPLATE_ID,
            "has_attachment": template.attachment is not None,
            "attachment_label": (
                template.attachment.label if template.attachment else None
            ),
        }
        for template in list_templates()
    ]


@lru_cache(maxsize=None)
def template_glossary_block(template_id: str) -> str:
    """組出模板術語表區塊（注入 LLM 語意校正層；無術語回傳空字串）。"""
    template = get_template(template_id)
    lines: list[str] = []
    if template.glossary_terms:
        lines.append(f"本類型會議（{template.display_name}）高頻術語：")
        lines.append("、".join(template.glossary_terms))
    if template.glossary_corrections:
        lines.append("本類型會議已知固定誤辨（一律照此修正）：")
        lines.extend(f"- {wrong} → {right}" for wrong, right in template.glossary_corrections)
    return "\n".join(lines)
