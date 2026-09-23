# -*- coding: utf-8 -*-
"""P7-B（T20260923-1810-01）SUPPORTING-1：地端佔位符正規化契約測試。

對應計畫 §6 SUPPORTING-1（確定性、作用域釘死、不新增事實）與開關
`LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT`（呼叫端只在地端收尾且開關為 True 時呼叫；
`normalize_unfilled_placeholders_ext` 本身不讀設定，維持純函式、可單測）。

本檔釘住：
  T1 開頭欄位／標題行：相鄰重複收斂（含半形／全形混用）；單一不動、不相鄰不動。
  T2 「決議事項辦理情形彙整表」資料列第 2 欄：多層括號收斂＋半形冒號改全形；
     表頭、分隔列、其他欄位、其他表格都不動；無樣式可修時逐字回傳。
  T3 找不到該表 ⇒ 原樣回傳（不報錯）。
  T4 冪等：f(f(x)) == f(x)（含所有情形的一份樣本）。
  T5 防禦：空字串回 ""、非字串原樣回傳（不丟例外）。
  T6 正文不得被動到（中段一般段落；開頭區的清單條目正文與一般段落亦不得動）。
  T7 不捏造：只收斂佔位符本身，其餘文字逐字不變、長度不增、字元不增。

測試素材為合成 fixture 與 E6b／E7C 實測行縮樣；純函式，不啟動後端、不連網。
"""

import os
import re
import tempfile

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs，
# 預設 /app/data 在 macOS 讀取失敗，故在 import backend 前備妥隔離目錄。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-p7b-ph-"))

from backend.core import text_postprocess as tp  # noqa: E402
from backend.core.text_postprocess import (  # noqa: E402
    normalize_unfilled_placeholders_ext,
)

# 開頭掃描上限（模組層契約常數）；本檔用它把「正文」放到作用域之外。
HEAD_LIMIT = tp._PLACEHOLDER_HEAD_LINE_LIMIT


def _residual(text: str) -> str:
    """移除所有佔位符（含多層括號）後剩下的文字（不捏造比對用）。"""
    return re.sub(r"[（(]+待確認[）)]+", "", text)


def _filler(lines: int) -> str:
    """無佔位符的正文填充行。"""
    return "\n".join(["（正文填充行，不含佔位符）"] * lines)


# ---------------------------------------------------------------------------
# T1 開頭欄位／標題行：相鄰重複收斂
# ---------------------------------------------------------------------------


def test_T1_開頭欄位與標題行的相鄰重複收斂():
    """T1：同一行內「相鄰」重複收斂成一個；半全形視為同一符號；單一與不相鄰不動。"""
    norm = normalize_unfilled_placeholders_ext

    assert norm("- **主席**：（待確認）（待確認）") == "- **主席**：（待確認）"
    # 半形與全形視為同一符號；保留第一個出現的樣式。
    assert norm("- **主席**：（待確認）(待確認)") == "- **主席**：（待確認）"
    assert norm("- **主席**：(待確認)（待確認）") == "- **主席**：(待確認)"
    assert norm("- **主席**：（待確認）(待確認)（待確認）") == "- **主席**：（待確認）"
    assert norm("## 開會時間：（待確認）(待確認)") == "## 開會時間：（待確認）"

    # 單一個不動；不相鄰的重複不動（中間有字）。
    assert norm("- **時間**：（待確認）") == "- **時間**：（待確認）"
    assert norm("- **地點**：（待確認）與（待確認）") == "- **地點**：（待確認）與（待確認）"

    # 實測縮樣（E6b 第 3、4 行；E7C 第 3 行）：
    assert norm("（待確認）（待確認）年（待確認）月份第（待確認）次科務會議紀錄") == (
        "（待確認）年（待確認）月份第（待確認）次科務會議紀錄"
    )
    assert norm(
        "時間：中華民國（待確認）年（待確認）月（待確認）日（待確認）（待確認）"
    ) == "時間：中華民國（待確認）年（待確認）月（待確認）日（待確認）"


# ---------------------------------------------------------------------------
# T2 「決議事項辦理情形彙整表」資料列第 2 欄
# ---------------------------------------------------------------------------

SUMMARY_TABLE_DOC = "\n".join(
    [
        "# 科務會議紀錄",
        "",
        "（待確認）年（待確認）月份第（待確認）次科務會議決議事項辦理情形彙整表",
        "決議事項：",
        "| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |",
        "| :--- | :---: | --- | --- |",
        "| 配合組織變革，預先準備系統權限及設備調整（資管股） | （（待確認））: | | |",
        "| 配合重新列印損毀之土地卡（相關承辦人） | （待確認）： | | |",
        "| 確定10/14排程（可能延至下午一點多）（（待確認）） | （待確認）： | | |",
        "| 詢問文康活動現金發放之具體程序（（待確認）） | ((待確認)): | （（待確認））: | |",
        "",
    ]
)


def test_T2_彙整表第2欄收斂與冒號轉換():
    """T2：只改該表「資料列第 2 欄」；表頭、分隔列與其他欄位逐字不動。"""
    lines = normalize_unfilled_placeholders_ext(SUMMARY_TABLE_DOC).split("\n")

    # 表頭與分隔列（含 :---:）逐字不動——分隔列不是資料列。
    assert "| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |" in lines
    assert "| :--- | :---: | --- | --- |" in lines

    # 第 2 欄：多層括號收斂成一層（全形→全形、半形→半形）＋半形冒號改全形。
    assert (
        "| 配合組織變革，預先準備系統權限及設備調整（資管股） | （待確認）： | | |"
        in lines
    )
    assert (
        "| 詢問文康活動現金發放之具體程序（（待確認）） | (待確認)： | （（待確認））: | |"
        in lines
    )
    # 已是目標樣式者逐字不變。
    assert "| 配合重新列印損毀之土地卡（相關承辦人） | （待確認）： | | |" in lines

    # 第 1 欄（案由）與第 3 欄（解除列管）不屬作用域：
    # `（（待確認））` 與半形冒號一律不動（E6 實測樣態）。
    assert (
        "| 確定10/14排程（可能延至下午一點多）（（待確認）） | （待確認）： | | |" in lines
    )


def test_T2b_該表無樣式可修時逐字回傳():
    """T2b：該表存在但無樣式可修 ⇒ 全文逐字不變（含 :---: 分隔列）。"""
    doc = "\n".join(
        [
            "決議事項辦理情形彙整表",
            "決議事項：",
            "| 案由 | 辦理情形 | 解除列管 | 繼續列管 |",
            "| :--- | :---: | --- | --- |",
            "| 某案（資管股） | 資管股： | | |",
            "",
        ]
    )
    assert normalize_unfilled_placeholders_ext(doc) == doc


def test_T2c_其他表格不動():
    """T2c：標題不含該表字串的表格（歷次列管案件）一個字都不改。"""
    doc = "\n".join(
        [
            "# 科務會議紀錄",
            "",
            "歷次科務會議決議事項繼續列管案件：（待確認）",
            "| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |",
            "| --- | --- | --- | --- |",
            "| 某案（資管股） | （（待確認））: | | |",
            "",
        ]
    )
    assert normalize_unfilled_placeholders_ext(doc) == doc


# ---------------------------------------------------------------------------
# T3 找不到該表 ⇒ 原樣回傳
# ---------------------------------------------------------------------------


def test_T3_找不到該表原樣回傳():
    """T3：沒有該表標題、標題只在正文提及、或只有表頭 ⇒ 原樣回傳、不報錯。"""
    norm = normalize_unfilled_placeholders_ext

    no_title = "# 會議紀錄\n\n時間：（待確認）\n地點：（待確認）\n"
    assert norm(no_title) == no_title

    title_in_prose = "決議事項辦理情形彙整表（見附件）\n\n（待確認）（待確認）\n"
    assert norm(title_in_prose) == title_in_prose

    header_only = "決議事項辦理情形彙整表\n| 案由 | 辦理情形 |\n| --- | --- |\n"
    assert norm(header_only) == header_only


# ---------------------------------------------------------------------------
# T4 冪等
# ---------------------------------------------------------------------------


def _full_sample() -> str:
    """含所有情形的樣本：開頭相鄰重複、表格第 2 欄、作用域外正文與其他表格。"""
    return "\n".join(
        [
            "# 科務會議紀錄",
            "",
            "（待確認）（待確認）年（待確認）月份第（待確認）次科務會議紀錄",
            "時間：中華民國（待確認）年（待確認）月（待確認）日（待確認）（待確認）",
            "地點：（待確認）",
            "主持人：（待確認）　紀錄：AI 會議助理",
            "",
            "（待確認）年（待確認）月份第（待確認）次科務會議決議事項辦理情形彙整表",
            "決議事項：",
            "| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |",
            "| --- | --- | --- | --- |",
            "| 配合組織變革（資管股） | （（待確認））: | | |",
            "| 確定10/14排程（（待確認）） | ((待確認)): | （（待確認））: | |",
            "",
            _filler(HEAD_LIMIT + 5),
            "",
            "本次討論（待確認）（待確認）相關事項，請依說明辦理。",
            "",
            "歷次科務會議決議事項繼續列管案件：（待確認）",
            "| 案由 | 辦理情形 | 解除列管 | 繼續列管 |",
            "| --- | --- | --- | --- |",
            "| 某案（資管股） | （（待確認））: | | |",
        ]
    )


def test_T4_冪等():
    """T4：f(f(x)) == f(x)（同一份樣本重複套用不得再變）。"""
    sample = _full_sample()
    once = normalize_unfilled_placeholders_ext(sample)
    assert once != sample, "前提：樣本必須真的被收斂，否則冪等測試沒有鑑別力"
    assert normalize_unfilled_placeholders_ext(once) == once


# ---------------------------------------------------------------------------
# T5 空字串／非字串防禦
# ---------------------------------------------------------------------------


def test_T5_空字串與非字串防禦():
    """T5：純函式防禦——空字串回 ""、非字串原樣回傳（不丟例外；None 不在契約內）。"""
    norm = normalize_unfilled_placeholders_ext
    assert norm("") == ""
    assert norm(None) is None
    assert norm(12345) == 12345
    assert norm(["（待確認）（待確認）"]) == ["（待確認）（待確認）"]


# ---------------------------------------------------------------------------
# T6 正文不得被動到（防作用域擴大的關鍵測試）
# ---------------------------------------------------------------------------


def test_T6_正文不得被動到():
    """T6：中段一般段落、開頭區的清單條目正文與一般段落，一律原樣保留。"""
    doc = "\n".join(
        [
            "# 科務會議紀錄",
            "",
            "時間：（待確認）",
            "- 請各股配合確認（待確認）（待確認）並回報。",
            "（待確認）（待確認）請各股配合辦理。",
            "",
            _filler(HEAD_LIMIT + 5),
            "",
            "本次討論（待確認）（待確認）相關事項，請各股依說明辦理。",
            "",
        ]
    )
    assert normalize_unfilled_placeholders_ext(doc) == doc


# ---------------------------------------------------------------------------
# T7 不捏造
# ---------------------------------------------------------------------------


def test_T7_不捏造_只收斂佔位符本身():
    """T7：輸出不得新增任何內容；只允許佔位符本身被收斂（無半形冒號轉換樣本）。"""
    src = "\n".join(
        [
            "（待確認）（待確認）年（待確認）月份第（待確認）次科務會議紀錄",
            "時間：中華民國（待確認）年（待確認）月（待確認）日（待確認）（待確認）",
            "決議事項辦理情形彙整表",
            "決議事項：",
            "| 案由 | 辦理情形 | 解除列管 | 繼續列管 |",
            "| --- | --- | --- | --- |",
            "| 某案（資管股） | （（待確認）） | | |",
            "",
        ]
    )
    out = normalize_unfilled_placeholders_ext(src)

    assert out != src, "前提：樣本必須真的被收斂，否則本測試沒有鑑別力"
    assert len(out) <= len(src)  # 只減不增
    assert set(out) <= set(src)  # 不得出現輸入沒有的字元
    # 佔位符以外逐字不變（含所有標點、標題與表頭／分隔列）。
    assert _residual(out) == _residual(src)


# ---------------------------------------------------------------------------
# T8 呼叫端接線（P7-B SUPPORTING-1 契約：只在地端收尾、可由開關關閉）
# ---------------------------------------------------------------------------


def _local_finalize(monkeypatch, text: str, *, enabled: bool, mode: str = "local"):
    """透過產品自身的收尾函式驗證接線（不直接呼叫純函式）。"""
    from backend.core.config import settings
    from backend.core.templates import get_template
    from backend.services.summarization import SummarizationService

    monkeypatch.setattr(settings, "LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT", enabled)
    service = SummarizationService()
    return service._finalize_record_text(
        text, template=get_template("section_meeting"), mode=mode
    )


def test_T8_地端收尾會呼叫_且開關可關(monkeypatch):
    """T8：`LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT` 開啟時地端收尾真的收斂；關閉時 byte 不變。"""
    src = "時間：（待確認）（待確認）\n地點：會議室\n"
    # 前置說明：`_finalize_record_text` 的第一步 `finalize_record` 會補上範本骨架
    # （v4.8.0 既有行為），因此不能拿輸入字串當期待值；改以「同一次收尾」的
    # 開／關兩版互比——差異必須**只有**相鄰重複的收斂。
    enabled = _local_finalize(monkeypatch, src, enabled=True)
    disabled = _local_finalize(monkeypatch, src, enabled=False)

    assert "（待確認）（待確認）" in disabled, "前提：關閉版必須仍留有相鄰重複"
    assert "（待確認）（待確認）" not in enabled
    assert enabled == disabled.replace("（待確認）（待確認）", "（待確認）"), (
        "開啟與關閉的唯一差異只能是相鄰重複的收斂（不得順手改到別的字）"
    )


def test_T8_雲端路徑不受開關影響(monkeypatch):
    """T8：雲端（mode="cloud"）不呼叫本步驟 ⇒ 兩種開關值下輸出完全相同。"""
    src = "時間：（待確認）（待確認）\n地點：會議室\n"
    on = _local_finalize(monkeypatch, src, enabled=True, mode="cloud")
    off = _local_finalize(monkeypatch, src, enabled=False, mode="cloud")
    assert on == off
