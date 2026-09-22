# -*- coding: utf-8 -*-
"""P3 波（T20260922-2037-02）：品質對齊度量與補強收斂 —— 契約測試。

對應計畫 `§8`：

- **CORE-5（R24／R26）**：出處標註吸附的兩層保證——①**全域段首保護**（時間戳
  若已是任一真實段落起點 → 原樣保留）＋②**段首命中優先**（落點一律是某段 ``start``）。
  兩者合起來才保證「一般輸入不跨段後退」與**冪等** ``f(f(x)) == f(x)``；
  只做②會被跨發言者交界（後一段屬別的發言者）擊穿（獨立審查 attempt-07 的反例）。
  ③時間戳恰為某段 ``end`` 但非任何段 ``start``（段落間空隙的邊界）仍落在真實
  段落內（不可回溯率不得因此上升）。
  （既有 `tests/test_platform_provider_routing.py` 只驗「同一輸入跑兩次相同」，
  純函式必然成立，因此抓不到這些缺陷——這裡驗的是 ``f(f(x)) == f(x)``。）
- **CORE-4（R23）**：待辦召回改為**對稱正規化 ＋ 滑窗 LCS 比例**，並在補強迴圈
  加入**不收斂保護**（問題集合與上一輪相同即停止）。
- **CORE-4b（R2 守衛）**：LCS 是字面量尺，對否定詞（實測 0.917）與數字
  （實測 0.818）不敏感 → 近似比對通過後，標籤內的否定詞與 ≥2 位數字串
  仍必須出現在**局部範圍**（最佳視窗 ∩ 最相近一句話），否則判遺漏
  （方向一律往更嚴；已知代價：國字書寫的兩位數會被判遺漏，最多多跑一輪補強）。

校準資料（真實、0903 場 27B 輸出；見計畫 §8.1 R23）：已涵蓋的改寫標籤落點
0.69–1.00、逐字稿確實沒寫的對照句落點 0.27–0.42 → 門檻取 0.6。
"""

import os
import tempfile

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs，
# 預設 /app/data 在 macOS 讀取失敗，故在 import backend 前備妥隔離目錄。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-p3-"))

from unittest.mock import AsyncMock, Mock  # noqa: E402

import pytest  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.core.templates import get_template  # noqa: E402
from backend.core.text_postprocess import (  # noqa: E402
    measure_tag_traceability,
    snap_source_tags_to_transcript,
)
from backend.services.summarization import SummarizationService  # noqa: E402

# ---------------------------------------------------------------------------
# CORE-5：吸附不倒退＋冪等
# ---------------------------------------------------------------------------

BOUNDARY_TRANSCRIPT = (
    "[00:00:00-00:00:30] 發言者1：甲。\n"
    "[00:00:30-00:01:00] 發言者1：乙。\n"
    "[00:01:00-00:01:30] 發言者2：丙。\n"
)


def test_snap_不把段首時間戳吸回前一段起點():
    """00:00:30 同時是「第 1 段 end」與「第 2 段 start」→ 必須留在段首。"""
    template = get_template("section_meeting")
    text = "1.乙（發言者1，00:00:30）。2.丙（發言者2，00:01:00）。"

    snapped, stats = snap_source_tags_to_transcript(text, BOUNDARY_TRANSCRIPT, template)

    assert snapped == text, "已是真實段首的時間戳不得被改寫"
    assert stats["tags"] == 2
    assert stats["kept_on_start"] == 2, "全域段首保護必須接住這兩個標註"
    assert stats["snapped"] == 0
    assert stats["changed"] == 0
    assert stats["backward_moves"] == 0


# 獨立審查 attempt-07（R3①／②）的最小反例：兩段、無重疊、純交界，且**交界兩側是不同發言者**。
# 「同發言者清單內段首優先」對這種情況無效——同發言者清單裡根本沒有 start == 時間戳 的段落。
CROSS_SPEAKER_TRANSCRIPT = (
    "[00:14:40-00:16:40] 發言者1：甲。\n"
    "[00:16:40-00:18:40] 發言者2：乙。\n"
)


def test_snap_跨發言者交界_段首時間戳不得被移早():
    """00:16:40 是「第 2 段 start」（別人的段）→ 不得被吸回第 1 段起點 00:14:40。"""
    template = get_template("section_meeting")
    text = "1.乙（發言者1，00:16:40）。"

    snapped, stats = snap_source_tags_to_transcript(text, CROSS_SPEAKER_TRANSCRIPT, template)

    assert snapped == text, "已是全域真實段首的時間戳不得被改寫（v1.0 會退成 00:14:40）"
    assert stats["kept_on_start"] == 1
    assert stats["changed"] == 0


def test_snap_跨發言者交界鏈不得反覆後退_冪等():
    """審查反例本體：00:18:40 → 00:16:40（一次落點）→ 再套用不得再退成 00:14:40。"""
    template = get_template("section_meeting")
    text = "1.甲（發言者1，00:18:40）。"

    once, first_stats = snap_source_tags_to_transcript(
        text, CROSS_SPEAKER_TRANSCRIPT, template
    )
    twice, second_stats = snap_source_tags_to_transcript(
        once, CROSS_SPEAKER_TRANSCRIPT, template
    )

    assert "（發言者1，00:16:40）" in once, "應落在原時間戳所屬段落的起點"
    assert "00:14:40" not in once, "不得被吸回前一段起點"
    assert first_stats["changed"] == 1
    assert twice == once, "冪等：第二次套用不得再改動任何字元"
    assert second_stats["changed"] == 0


def test_snap_是冪等的_f_fx_等於_fx():
    """吸附後再吸附一次必須完全不動（v1.0 會單向倒退一格，故非冪等）。"""
    template = get_template("section_meeting")
    text = (
        "1.甲（發言者1，00:00:12）。"
        "2.乙（發言者1，00:00:30）。"
        "3.丙（科長，00:01:05）。"
        "4.無法回溯（發言者9，05:00:00）。"
    )

    once, first_stats = snap_source_tags_to_transcript(text, BOUNDARY_TRANSCRIPT, template)
    twice, second_stats = snap_source_tags_to_transcript(
        once, BOUNDARY_TRANSCRIPT, template
    )

    assert once != text
    assert "（發言者1，00:00:00）" in once
    assert "（發言者1，00:00:30）" in once, "段首時間戳不得倒退成前一段起點"
    assert "（科長，00:01:00）" in once
    assert twice == once, "冪等：第二次套用不得再改動任何字元"
    assert second_stats["changed"] == 0
    assert first_stats["kept_on_start"] == 1, "已是段首的 00:00:30 必須走保護路徑"


GAP_TRANSCRIPT = (
    "[00:00:00-00:00:30] 發言者1：甲。\n"
    "[00:01:00-00:01:30] 發言者2：丙。\n"
)


def test_量尺與吸附共用同一份閉區間定義_空隙邊界仍可回溯():
    """時間戳恰為某段 end 且非任何段 start（段落間有空隙）→ 仍算落在真實段落內。

    半開區間會把這種時間戳打成「不可回溯」，而它其實落在真實段落內：
    C1 唯一真正被修正的 ``00:10:04 → 00:08:15`` 就屬此類（原時間戳＝該段 end）。
    """
    template = get_template("section_meeting")
    text = "1.邊界（發言者1，00:00:30）。"

    snapped, stats = snap_source_tags_to_transcript(text, GAP_TRANSCRIPT, template)
    metrics = measure_tag_traceability(text, GAP_TRANSCRIPT)

    assert metrics["tags_total"] == 1
    assert metrics["traceable_tag_ratio"] == 1.0, "空隙邊界時間戳不得變成不可回溯"
    assert stats["untraceable"] == 0
    assert stats["backward_moves"] == 1
    assert stats["max_backward_seconds"] == 30, "段落內吸附只往該段段首收 30 秒"
    # 落點仍在「原時間戳所屬的那一段」內（不是被搬到別段、也不是保留不可回溯）。
    assert "（發言者1，00:00:00）" in snapped


def test_量尺與吸附共用同一份閉區間定義_交界時間戳算段首():
    """時間戳恰為兩段交界（前段 end ＝ 後段 start）→ 段首命中優先，留在段首。"""
    template = get_template("section_meeting")
    text = "1.交界（發言者1，00:00:30）。2.段首（發言者2，00:01:00）。"

    snapped, stats = snap_source_tags_to_transcript(text, BOUNDARY_TRANSCRIPT, template)
    metrics = measure_tag_traceability(snapped, BOUNDARY_TRANSCRIPT)

    assert metrics["tags_total"] == 2
    assert metrics["tags_on_real_segment_start"] == 2
    assert metrics["traceable_tag_ratio"] == 1.0
    assert stats["changed"] == 0, "兩個時間戳都已是真實段首，不得被改寫"
    assert stats["kept_on_start"] == 2
    assert stats["backward_moves"] == 0
    assert "（發言者1，00:00:30）" in snapped, "交界時間戳不得被吸回前一段起點"


# ---------------------------------------------------------------------------
# CORE-4：待辦召回（對稱正規化＋滑窗 LCS）與不收斂保護
# ---------------------------------------------------------------------------

CALIBRATION_RECORD = """| 嚴禁將科內群組訊息（含照片）外流至任何外部渠道 | 全科同仁 | | |
1. 了解印花稅業務移轉至土地增值稅科的配合事項，並確認後續系統權限（發言者1，00:10:00）。
2. 了解房屋稅系統業務調整（稽查股／徵收股）（發言者2，00:12:00）。
3. 盤點多元支付現狀並思考AI創新方案（科長，00:20:00）。
4. 追蹤辦公室黴味處理進度與廠商報價（發言者3，00:41:00）。
"""

# 舊版「整條連續子字串」比對會把這些**已涵蓋**的待辦判成遺漏（真實案例）。
COVERED_LABELS = (
    "嚴禁轉傳科內群組訊息至外部",
    "了解印花稅業務移轉至土地增值稅科的配合事項",
    "了解房屋稅系統業務調整（稽查股/征收股）",
    "盤點多元支付現狀並思考AI創新方案",
    "追蹤辦公室黴味處理進度與廠商報價",
)

# 逐字稿中確實沒寫（對照組）：必須一律判為遺漏，否則補強會失去作用。
ABSENT_LABELS = (
    "審查資訊安全分級辦法並函報上級",
    "辦理員工在職訓練課程規劃",
    "清查公務車輛油耗與維修紀錄",
)


def _missing_keys(labels) -> tuple[set, dict]:
    keys = {SummarizationService._normalize_action_key(label) for label in labels}
    normalized_record = SummarizationService._normalize_action_key(CALIBRATION_RECORD)
    return SummarizationService._find_missing_action_keys(
        keys,
        normalized_record,
        local_sentences=SummarizationService._split_record_sentences(CALIBRATION_RECORD),
    )


def _missing_for(label: str, record: str) -> tuple[set, dict]:
    key = SummarizationService._normalize_action_key(label)
    return SummarizationService._find_missing_action_keys(
        {key},
        SummarizationService._normalize_action_key(record),
        local_sentences=SummarizationService._split_record_sentences(record),
    )


def test_待辦召回_已涵蓋的改寫不得判為遺漏():
    missing, ratios = _missing_keys(COVERED_LABELS)

    assert missing == set(), f"不得再出現假陽性遺漏：{sorted(missing)}"
    assert min(ratios.values()) >= SummarizationService.ACTION_MATCH_MIN_LCS_RATIO


def test_待辦召回_真的沒寫的仍然要判遺漏():
    missing, ratios = _missing_keys(ABSENT_LABELS)

    assert len(missing) == len(ABSENT_LABELS), (
        f"真遺漏必須仍被攔下（false negative 比白燒更糟）：{sorted(ratios.items())}"
    )
    assert max(ratios.values()) < SummarizationService.ACTION_MATCH_MIN_LCS_RATIO


def test_正規化對稱_全形半形與標點不影響比對():
    normalize = SummarizationService._normalize_action_key

    assert normalize("稽查股（A）") == normalize("稽查股(A)")
    assert normalize("系統　權限\r\n調整") == normalize("系統權限調整")
    assert normalize("") == ""
    assert SummarizationService._find_missing_action_keys({"系統權限調整"}, "系統權限調整")[0] == set()


def test_守衛_否定詞缺失時_LCS再高也要判遺漏():
    """否定詞是語意反轉、字面重疊卻很高（實測 0.917）→ 不得被近似比對吸收。"""
    label = "決議事項：嚴禁轉傳科內群組訊息至外部"
    # 改寫後字面重疊度高（順序保留），但「嚴禁」不見了 → 語意已被弱化。
    missing, ratios = _missing_for(label, "決議事項：科內群組訊息得轉傳至外部渠道。")

    assert len(missing) == 1, "否定詞缺失必須判遺漏"
    assert next(iter(ratios.values())) >= SummarizationService.ACTION_MATCH_MIN_LCS_RATIO, (
        "本案必須是「LCS 已達門檻、由守衛攔下」，否則測不到守衛"
    )


def test_守衛_否定詞保留時不得誤判():
    missing, _ratios = _missing_for(
        "嚴禁轉傳科內群組訊息至外部",
        "嚴禁將科內群組訊息（含照片）外流至任何外部渠道（發言者1，00:10:00）。",
    )

    assert missing == set()


def test_守衛_否定詞在別的子句時仍要判遺漏():
    """獨立審查 attempt-07 的 R2 反例：目標句被反轉，但別的子句還有同一個否定詞。

    只檢查「整份紀錄有沒有出現」會放行（實測 LCS 0.857）；局部判定（最佳視窗＋
    最相近一句話的交集）必須攔下。
    """
    missing, ratios = _missing_for(
        "嚴禁轉傳科內群組訊息至外部",
        "嚴禁酒駕。科內群組訊息得轉傳至外部渠道。",
    )

    assert len(missing) == 1, "別子句的否定詞不得替目標句的語意反轉背書"
    assert next(iter(ratios.values())) >= SummarizationService.ACTION_MATCH_MIN_LCS_RATIO


def test_守衛_兩位數日期被改寫必須判遺漏():
    """獨立審查 attempt-07 的 R2 反例：9月30日 → 9月20日（LCS 0.933，2 位數字是唯一差異）。"""
    missing, ratios = _missing_for("確認9月30日前完成查核", "確認9月20日前完成查核。")

    assert len(missing) == 1, "日期改寫不得被洗白成已涵蓋"
    assert next(iter(ratios.values())) >= SummarizationService.ACTION_MATCH_MIN_LCS_RATIO


def test_守衛_日期保留時不得誤判():
    missing, _ratios = _missing_for("確認9月30日前完成查核", "確認9月30日前完成查核（發言者1，00:10:00）。")

    assert missing == set()


def test_守衛_三位以上數字缺失時_LCS再高也要判遺漏():
    """金額／數量被改寫稀釋（實測 0.818；真實缺口：13600 元的算式被寫成「約一萬多元」）。"""
    missing, ratios = _missing_for(
        "確認水塔清洗及冷卻水塔保養經費13600元",
        "確認水塔清洗及冷卻水塔保養經費約一萬三千六百元。",
    )

    assert len(missing) == 1, "金額數字缺失必須判遺漏"
    assert next(iter(ratios.values())) >= SummarizationService.ACTION_MATCH_MIN_LCS_RATIO


def test_守衛_數字保留時不得誤判_含千分位對稱():
    missing, _ratios = _missing_for(
        "確認水塔清洗經費13600元",
        "確認水塔清洗經費 13,600 元（含稅）。",
    )

    assert missing == set(), "千分位逗號已在正規化折疊，不得誤判"


def test_守衛_兩位數納入的已知代價_國字書寫會被判遺漏():
    """兩位數已納入守衛（R2 修正），代價如實記錄：國字書寫的「十七台」會被判遺漏。

    方向刻意往更嚴（審查 attempt-07 R2：2 位數字是「9月30日→9月20日」唯一可辨識的
    差異）。代價＝可能多一輪補強，已由不收斂保護圍堵（最多 1 輪）。
    """
    missing, ratios = _missing_for("盤點17台冷氣運轉狀況", "盤點冷氣運轉狀況共十七台。")

    assert len(missing) == 1, f"兩位數已納入守衛（往更嚴）：{ratios}"
    assert SummarizationService._ACTION_NUMBER_PATTERN.findall(
        SummarizationService._normalize_action_key("經費13600元")
    ) == ["13600"]
    assert SummarizationService._ACTION_NUMBER_PATTERN.findall(
        SummarizationService._normalize_action_key("盤點17台冷氣運轉狀況")
    ) == ["17"], "兩位數必須被樣式命中"
    assert SummarizationService._ACTION_NUMBER_PATTERN.findall(
        SummarizationService._normalize_action_key("上午9時開始")
    ) == [], "個位數不納入（避免雜訊）"


def _notes_with_actions() -> str:
    return (
        "| 待辦事項 | 負責人 | 期限 | 備註 |\n"
        "|---|---|---|---|\n"
        "| 完成水塔清洗 | 總務 | 下週 | |\n"
    )


@pytest.mark.asyncio
async def test_補強迴圈在問題集合不變時停止_不收斂保護(monkeypatch):
    """問題集合與上一輪相同 → 不得再跑第二輪（實測 27B 白燒 710 s 的成因）。"""
    service = SummarizationService()
    template = get_template("section_meeting")
    notes = _notes_with_actions()
    transcript = "[00:00:00-00:00:20] 發言者1：請完成水塔清洗。\n" * 20
    same_issue = ["待辦事項遺漏 1 項：完成水塔清洗（未涵蓋）"]

    generated: list[str] = []

    async def _fake_generate(engine, prompt, message, **kwargs):  # noqa: ANN001, ARG001
        generated.append(message)
        return notes

    quality = Mock(side_effect=[list(same_issue), list(same_issue), list(same_issue)])
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="lmstudio"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=128000))
    monkeypatch.setattr(service, "_generate_with_local_engine", _fake_generate)
    monkeypatch.setattr(service, "_merge_notes_until_fit", AsyncMock(return_value="MERGED"))
    monkeypatch.setattr(service, "_validate_summary_quality", quality)
    monkeypatch.setattr(service, "_validate_cloud_speaker_traceability", lambda *a, **k: [])
    monkeypatch.setattr(service, "_validate_cloud_date_grounding", lambda *a, **k: [])

    await service._summarize_with_local_pipeline(
        transcript, settings.DEFAULT_SYSTEM_PROMPT, template=template
    )

    # 呼叫序：萃取筆記 1 次＋初稿 1 次＋補強 1 輪；第 2 輪必須被不收斂保護擋下。
    assert len(generated) == 3, "萃取＋初稿＋最多 1 輪補強（第 2 輪被不收斂保護擋下）"
    assert quality.call_count == 2, "驗證只跑 2 次（初稿後＋第 1 輪補強後）"


@pytest.mark.asyncio
async def test_補強迴圈在問題集合改變時仍會繼續跑滿(monkeypatch):
    """反向對照：問題集合每輪都在變（真的有進展）→ 不得被不收斂保護誤擋。"""
    service = SummarizationService()
    template = get_template("section_meeting")
    notes = _notes_with_actions()
    transcript = "[00:00:00-00:00:20] 發言者1：請完成水塔清洗。\n" * 20

    generated: list[str] = []

    async def _fake_generate(engine, prompt, message, **kwargs):  # noqa: ANN001, ARG001
        generated.append(message)
        return notes

    quality = Mock(
        side_effect=[
            ["待辦事項遺漏 3 項：A、B、C"],
            ["待辦事項遺漏 2 項：A、B"],
            ["待辦事項遺漏 1 項：A"],
            ["待辦事項遺漏 1 項：A"],
        ]
    )
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="lmstudio"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=128000))
    monkeypatch.setattr(service, "_generate_with_local_engine", _fake_generate)
    monkeypatch.setattr(service, "_merge_notes_until_fit", AsyncMock(return_value="MERGED"))
    monkeypatch.setattr(service, "_validate_summary_quality", quality)
    monkeypatch.setattr(service, "_validate_cloud_speaker_traceability", lambda *a, **k: [])
    monkeypatch.setattr(service, "_validate_cloud_date_grounding", lambda *a, **k: [])

    await service._summarize_with_local_pipeline(
        transcript, settings.DEFAULT_SYSTEM_PROMPT, template=template
    )

    # 呼叫序：萃取 1 次＋初稿 1 次＋補強跑滿 MAX 輪（每輪問題集合都在變＝有進展）。
    assert len(generated) == 2 + settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS
    assert quality.call_count == 1 + settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS
