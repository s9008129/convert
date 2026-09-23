# -*- coding: utf-8 -*-
"""P4-B B1（來源標註歸屬）段落邊界假陽性修補 —— 契約測試。

缺陷（E3 場 `Qwen3.8-27B-Splash` 實測、獨立驗收確認）：`_tag_owner_issues` 舊版
以「檔案序第一個含此時間戳的段落」判定歸屬；逐字稿相鄰段落的邊界必然重疊
（前段 ``end`` ＝ 後段 ``start``），而段落區間是**閉區間**（與吸附規則 0／量尺
``tags_inside_same_speaker_segment`` 共用同一份定義），因此邊界時間戳會被前後
兩段同時包含，舊版一律判給前一段 → 引用「該段起點」的標註全數成為假陽性
（E3 場 14／14 全假陽性，且與量尺對同一份紀錄的 45／45 直接矛盾）。

修補：歸屬判定改為**集合**語意 —— 只有當「所有含此時間戳的段落發言者」都不等於
標註指名者時，才算「落在他人段落內」。真歸屬錯誤（段落中段錯標、或邊界兩側皆非
指名發言者）仍必須回報；`cap`／fail-soft／`LOCAL_FIDELITY_TRIPWIRES` 開關語意
未動。
"""

import os
import tempfile

# logger 於 import 期建立 DATA_DIR/logs，故先備妥隔離目錄（同既有測試檔慣例）。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-p4b-boundary-"))

from backend.core.fidelity_checks import _tag_owner_issues, analyze_fidelity  # noqa: E402


def _header(body: str) -> str:
    return (
        "# 科務會議紀錄\n\n時間：中華民國115年9月3日\n主持人：科長\n\n"
        "一、報告事項：\n" + body
    )


# 相鄰段落（前段 end ＝ 後段 start）＝實測逐字稿的常態幾何。
CONTIGUOUS = (
    "[00:00:00-00:00:10] 發言者1：土地稅科配合辦理交接。\n"
    "[00:00:10-00:00:20] 發言者3：資管股經費說明。\n"
)
# 同一位發言者的相鄰段落（邊界兩側同人）。
SAME_SPEAKER_CONTIGUOUS = (
    "[00:00:00-00:00:10] 發言者1：土地稅科配合辦理交接。\n"
    "[00:00:10-00:00:20] 發言者1：欠稅管理股負責清查。\n"
)


# ---------------------------------------------------------------------------
# 正向：邊界時間戳的兩側都是合法引用目標 → 不得回報
# ---------------------------------------------------------------------------


def test_B1_邊界時間戳引用段落起點_不報():
    """反例（舊版假陽性）：段首時間戳同時是前段段尾；指名後段發言者不得回報。"""
    record = _header("1. 經費說明（發言者3，00:00:10）。\n")

    assert _tag_owner_issues(record, CONTIGUOUS) == []
    report = analyze_fidelity(record, CONTIGUOUS, "section_meeting")
    assert "tag_owner" not in report["attribution_kinds"]


def test_B1_邊界時間戳引用段落結尾_不報():
    """反例（對稱族）：段尾時間戳同時是後段段首；指名前段發言者不得回報。

    這一族是「起點優先」寫法會新產生的假陽性，必須一併釘住。
    """
    record = _header("1. 業務移交（發言者1，00:00:10）。\n")

    assert _tag_owner_issues(record, CONTIGUOUS) == []


def test_B1_同發言者相鄰段落邊界_不報():
    """反例：邊界兩側同一位發言者 → 指名該發言者不得回報。"""
    record = _header("1. 清查（發言者1，00:00:10）。\n")

    assert _tag_owner_issues(record, SAME_SPEAKER_CONTIGUOUS) == []


def test_B1_段落空隙不報():
    """反例（既有語意不變）：時間戳落在段落空隙＝不可回溯，不得當成歸屬錯誤。"""
    transcript = (
        "[00:00:00-00:00:20] 發言者1：科長裁示業務報告。\n"
        "[00:00:40-00:01:00] 發言者3：資管股經費說明。\n"
    )
    record = _header("1. 業務移交（發言者1，00:00:30）。\n")

    assert _tag_owner_issues(record, transcript) == []


def test_B1_標籤非發言者數字_不參與判定():
    """反例（既有語意不變）：角色名標註不進 B1（與發言者編號不同命名空間）。"""
    record = _header("1. 業務移交（科長，00:00:15）。\n")

    assert _tag_owner_issues(record, CONTIGUOUS) == []


# ---------------------------------------------------------------------------
# 反向：真歸屬錯誤仍必須回報（不得洗白）
# ---------------------------------------------------------------------------


def test_B1_段落中段錯標_仍報():
    """反例：時間戳落在他人段落中段（非邊界）→ 仍為歸屬錯誤。"""
    record = _header("1. 經費說明（發言者2，00:00:15）。\n")

    issues = _tag_owner_issues(record, CONTIGUOUS)
    assert len(issues) == 1
    assert issues[0] == "tag_owner|（發言者2，00:00:15）落在 發言者3 的逐字稿段落內"
    report = analyze_fidelity(record, CONTIGUOUS, "section_meeting")
    assert "tag_owner" in report["attribution_kinds"]
    assert "來源標註歸屬待確認" in "".join(report["problems"])


def test_B1_邊界兩側皆非指名發言者_仍報():
    """反例：邊界時間戳的兩側段落都不是指名發言者 → 仍是歸屬錯誤，並列出兩側。"""
    record = _header("1. 業務移交（發言者2，00:00:10）。\n")

    issues = _tag_owner_issues(record, CONTIGUOUS)
    assert len(issues) == 1
    assert issues[0] == "tag_owner|（發言者2，00:00:10）落在 發言者1／發言者3 的逐字稿段落內"


def test_B1_長段落內錯標_仍報():
    """反例：長段落（>1 秒）中段錯標 → 仍報（閉區間包含語意未鬆動）。"""
    transcript = (
        "[00:00:00-00:01:00] 發言者1：土地稅科配合辦理交接。\n"
        "[00:01:00-00:01:10] 發言者3：資管股經費說明。\n"
    )
    record = _header("1. 業務移交（發言者3，00:00:30）。\n")

    issues = _tag_owner_issues(record, transcript)
    assert issues == ["tag_owner|（發言者3，00:00:30）落在 發言者1 的逐字稿段落內"]


def test_B1_會議起點長段落錯標_仍報():
    """反例（真實素材型態）：雲端 C5 場真陽性「（發言者3，00:00:00）落在發言者1 段內」。"""
    transcript = "[00:00:00-00:05:36] 發言者1：組織規程與編制表修正案報告。\n"
    record = _header("1. 局長提示（發言者3，00:00:00）。\n")

    issues = _tag_owner_issues(record, transcript)
    assert issues == ["tag_owner|（發言者3，00:00:00）落在 發言者1 的逐字稿段落內"]


def test_B1_同發言者多段命中_訊息不重複列名():
    """正例＋輸出穩定性：去重後只列一次，且同輸入輸出 byte 級相同。"""
    record = _header("1. 清查（發言者2，00:00:10）。\n")

    first = _tag_owner_issues(record, SAME_SPEAKER_CONTIGUOUS)
    second = _tag_owner_issues(record, SAME_SPEAKER_CONTIGUOUS)
    assert first == second == ["tag_owner|（發言者2，00:00:10）落在 發言者1 的逐字稿段落內"]


def test_B1_單一命中的訊息格式不變():
    """off 等價：單一命中時訊息字串與修補前 byte 級相同（補強提示詞契約不變）。"""
    transcript = "[00:00:00-00:00:20] 發言者1：科長裁示業務報告。\n"
    record = _header("1. 業務移交（發言者2，00:00:10）。\n")

    assert _tag_owner_issues(record, transcript) == [
        "tag_owner|（發言者2，00:00:10）落在 發言者1 的逐字稿段落內"
    ]


def test_B1_多筆獨立錯誤依序回報():
    """正例：多筆不重疊的真歸屬錯誤各自回報（不因集合語意而互相掩蓋）。"""
    transcript = (
        "[00:00:00-00:00:10] 發言者1：土地稅科配合辦理交接。\n"
        "[00:00:10-00:00:20] 發言者3：資管股經費說明。\n"
        "[00:00:30-00:00:40] 發言者2：文康活動辦理說明。\n"
    )
    record = _header(
        "1. 業務移交（發言者2，00:00:05）。\n"
        "2. 經費說明（發言者1，00:00:35）。\n"
    )

    assert _tag_owner_issues(record, transcript) == [
        "tag_owner|（發言者2，00:00:05）落在 發言者1 的逐字稿段落內",
        "tag_owner|（發言者1，00:00:35）落在 發言者2 的逐字稿段落內",
    ]
