#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
會議紀錄品質量測儀（deterministic metric harness；Stage 04/05 用）。

任務：T20260922-1930-01-local-record-quality-parity（plan W6）。

用途：
    對最終會議紀錄（Markdown）輸出**確定性**品質指標 JSON，供 CORE-1
    （彙整表標註＝0、正文標註不退步）與 CORE-2（已知 ASR 誤辨左側詞＝0）
    驗收引用。所有指標皆為字面統計，不含 LLM 判定。

    * ``--record``（必要）：Markdown 是權威來源。DOCX 因 python-docx 會把
      段落／表格儲存格合併成段落，行結構（表格列 vs 正文列）遺失、標註數
      不可信 → 印出 SKIP 並以 exit 0 結束（不假裝量測）。
    * ``--transcript``（選用）：提供時才有 ``unsupported_entities`` 觀察值、
      registry-aware 的 ``unsupported_entities_registry_aware``（P4-B）與 ``fidelity``
      忠實度絆索摘要，並附逐字稿的 ``known_term_fix_hits``（同一套字面規則）。
    * ``--template``（選用）：決議／主席裁示跨章節去重（W5）需要模板語意；
      未知 id 只記錄，不影響其他指標。
    * ``--out``（選用）：另寫一份 JSON 檔；stdout 一律輸出同一份 JSON。

白名單與樣式不重寫第二份（plan W6 硬性要求）：
    * 來源標註樣式＝``backend.core.text_postprocess.SOURCE_TAG_PATTERN``。
    * 彙整表列定義＝``backend.core.text_postprocess.TABLE_ROW_PATTERN``
      （``^\\s*\\|``；與 W2b 清除器 ``strip_source_tags_from_table_rows``
      及產品 ``forbidden_patterns`` 同一定義，不另立第二套）。
    * 地端紀錄級誤辨修正＝``backend.core.prompt_templates.section_meeting``
      的 ``SECTION_MEETING_RECORD_TERM_FIXES``（左側＝錯形 regex、右側＝修正字）。
    * 跨章節重複＝``backend.core.text_postprocess.dedupe_cross_section_items``。

語意邊界（plan rev6）：
    * ``unsupported_entities`` 是**觀察值**（ASR 變體重建／未落地專名），
      永不作為閘門（plan §1：字面比對無法區分捏造與 ASR 重建）。
    * ``non_prefixed_tableish_source_tag_count`` 是**觀察值**（具表格樣態但不符
      表格列定義的行——例如全形 ``｜`` 列——上的標註數），永不作為閘門；
      產品契約與清除器皆定義彙整表列為 ``^\\s*\\|``，這些形狀是已知殘餘缺口
      （P1-13 層級回報），見 ``notes``。
    * 本儀器不改任何產品行為，也不放寬任何判準。

用法：
    uv run python scripts/e2e/measure_record_quality.py \
        --record data/cache/e2e/p1-baseline-01/backend_data/outputs/0903-科務會議_70a58030.md \
        --transcript data/cache/e2e/p1-baseline-01/transcript.txt \
        --template section_meeting

退出碼：
    0 - 成功（含 DOCX SKIP）
    2 - 參數或環境錯誤（檔案不存在等）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# DATA_DIR 必須在 import backend 模組之前備妥（同 scripts/e2e/rerun_local_summarize.py
# 慣例），否則 backend.core.config 會採用 Docker 預設 /app/data。
os.environ.setdefault("DATA_DIR", str(PROJECT_ROOT / "data"))
# 主控台只留 CRITICAL，確保 stdout 是乾淨的 JSON（完整日誌仍寫入 <DATA_DIR>/logs/）；
# 需要完整日誌時：LOG_LEVEL=INFO uv run python scripts/e2e/measure_record_quality.py ...
os.environ.setdefault("LOG_LEVEL", "CRITICAL")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.prompt_templates.section_meeting import (  # noqa: E402
    SECTION_MEETING_RECORD_TERM_FIXES,
)
from backend.core.text_postprocess import (  # noqa: E402
    SOURCE_TAG_PATTERN,
    TABLE_ROW_PATTERN,
    dedupe_cross_section_items,
    measure_tag_traceability,
)
from backend.core.fidelity_checks import (  # noqa: E402
    FIDELITY_METRIC_VERSION,
    analyze_fidelity,
)

# 開頭欄位排除（plan rev6 W6 記法，不含冒號；為 summarization.py:130
# ``_RECORD_HEADER_FIELD_PATTERN``（需緊接 [:：]）的超集，排除方向保守）。
RECORD_HEADER_FIELD_PATTERN = re.compile(r"^(?:時間|地點|主持人|出席人員|紀錄)")
# 正文條目（leaf item）：行首 ``N.`` 或 ``（N）``／``(N)``；基線 33/34≈97.1%
# 即以此定義（群組標題 ``（一）`` 不算條目）。
ITEM_LINE_PATTERN = re.compile(r"^\s*(?:\d+\.|[（(]\d+[)）])")
# 章節標題邊界（一、二、三…）。
SECTION_HEADING_PATTERN = re.compile(r"^[一二三四五六七八九十]+、")
INSTRUCTION_SECTION_PATTERN = re.compile(r"指示及提醒")
# 「表格樣態」判定（僅供非閘門觀察值使用，不是表格列定義）：
# 行首即管線字元，或行內 ≥2 個管線字元（＝看起來像表格列）。
# 單一管線字元夾在正文句子中不算表格樣態，避免把正文誤報為表格殘餘。
TABLEISH_PIPE_CHARS = ("|", "｜")
# 未落地專名觀察：以官方引號（「…」）明示、且結尾為組織後綴的單位名稱。
# 高精確、低召回是刻意的——自由文本的字面啟發式會把句尾詞片段誤認為專名
# （實測：27 筆中僅 3 筆真專名），故只收引號明示者；此為觀察值，永不閘門。
QUOTED_NAME_PATTERN = re.compile(r"「([^」]{2,20})」")
ENTITY_SUFFIX_PATTERN = re.compile(r"(?:股|科|室|處|局|中心|公司)$")

DOCX_SUFFIXES = {".docx", ".doc"}


def _is_tableish_non_prefixed(line: str) -> bool:
    """行是否具「表格樣態」卻不符合 ``TABLE_ROW_PATTERN``（觀察值用，非契約）。"""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped[0] in TABLEISH_PIPE_CHARS:
        return True
    return sum(stripped.count(char) for char in TABLEISH_PIPE_CHARS) >= 2


def count_source_tag_regions(text: str) -> tuple:
    """回傳 (body, table, excluded_header, non_prefixed_tableish) 四類標註數。

    表格列判準與 W2b 清除器（``strip_source_tags_from_table_rows``）及產品
    ``forbidden_patterns`` 共用同一份公開定義
    （``backend.core.text_postprocess.TABLE_ROW_PATTERN`` ＝ ``^\\s*\\|``），
    不再用「行內任何位置含 ``|``」：舊寫法會讓正文含 ``|`` 的標註被計為表格
    ——清除器不會動那種行，``table_source_tag_count`` 可能永遠 > 0（false FAIL）；
    也會讓全形 ``｜``／非行首的真表格列改計為正文（false PASS）。軌 D 稽核 §6。

    ``body`` ＝其他行的 ``SOURCE_TAG_PATTERN`` 命中數，仍排除開頭欄位
    （``RECORD_HEADER_FIELD_PATTERN``）；``non_prefixed_tableish`` 為**觀察值**：
    具表格樣態（見 ``_is_tableish_non_prefixed``）但不符合表格列定義者，
    只回報、永不影響 ``table``／``body`` 計數語意。
    """
    body_tags = 0
    table_tags = 0
    header_tags = 0
    non_prefixed_tags = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        hits = sum(1 for _ in SOURCE_TAG_PATTERN.finditer(stripped))
        if not hits:
            continue
        if TABLE_ROW_PATTERN.match(line):
            table_tags += hits
            continue
        if _is_tableish_non_prefixed(line):
            non_prefixed_tags += hits
        if RECORD_HEADER_FIELD_PATTERN.match(stripped):
            header_tags += hits
        else:
            body_tags += hits
    return body_tags, table_tags, header_tags, non_prefixed_tags


def extract_body_items(text: str) -> list:
    """正文條目（leaf item）清單：排除表格列與開頭欄位後，行首帶編號者。"""
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or "|" in stripped:
            continue
        if RECORD_HEADER_FIELD_PATTERN.match(stripped):
            continue
        if ITEM_LINE_PATTERN.match(stripped):
            items.append(stripped)
    return items


def count_instruction_items(text: str) -> int:
    """「科長指示及提醒事項」章節內的 leaf item 數（找不到章節時以全文計）。"""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if INSTRUCTION_SECTION_PATTERN.search(line):
            start = index
            break
    if start is None:
        return len(extract_body_items(text))
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if SECTION_HEADING_PATTERN.match(lines[index].strip()):
            end = index
            break
    return len(extract_body_items("\n".join(lines[start:end])))


def count_known_term_fix_hits(text: str, fixes: tuple = SECTION_MEETING_RECORD_TERM_FIXES) -> dict:
    """已知誤辨字串的左側（錯形）與右側（修正）字面命中，分開計數。

    左側＝``SECTION_MEETING_RECORD_TERM_FIXES`` 的 regex pattern 命中數；
    右側＝其 replacement 字面出現數（同一 replacement 只計一次，避免重複累加）。
    """
    left_hits = 0
    left_by_form: dict = {}
    right_replacements: list = []
    for pattern, replacement in fixes:
        compiled = re.compile(pattern)
        count = sum(1 for _ in compiled.finditer(text))
        left_by_form[pattern] = count
        left_hits += count
        if replacement not in right_replacements:
            right_replacements.append(replacement)
    right_by_form = {replacement: text.count(replacement) for replacement in right_replacements}
    right_hits = sum(right_by_form.values())
    return {
        "left_hits": left_hits,
        "right_hits": right_hits,
        "left_by_form": left_by_form,
        "right_by_form": right_by_form,
    }


def find_unsupported_entities(record_text: str, transcript_text: str) -> list:
    """觀察值：紀錄中以「…」明示、逐字稿未出現的組織型專名（含 ASR 變體重建）。

    純字面包含比對，**不可**作為捏造或歸屬的判定依據（plan §1 已明訂：
    字面比對無法區分「模型捏造」與「ASR 變體重建」）。
    """
    candidates = {
        token
        for token in QUOTED_NAME_PATTERN.findall(record_text)
        if ENTITY_SUFFIX_PATTERN.search(token)
    }
    return sorted(token for token in candidates if token not in transcript_text)


def resolve_template(template_id: Optional[str]) -> tuple:
    """``--template`` id → MeetingTemplate（供 W5 去重）；未知 id 回 (None, 說明)。"""
    if not template_id:
        return None, "未指定 --template：跨章節去重沿用函式預設（template=None）"
    from backend.core.templates import get_template

    try:
        return get_template(template_id), f"template={template_id}"
    except ValueError as exc:
        return None, f"template={template_id} 無法解析（{exc}）；去重沿用預設，其他指標不受影響"


def measure_record_quality(
    record_text: str,
    *,
    transcript_text: Optional[str] = None,
    template_id: Optional[str] = None,
) -> dict:
    """量測入口：回傳 plan W6 定義的固定 JSON schema（＋notes 解讀欄）。"""
    body_tags, table_tags, header_tags, non_prefixed_tags = count_source_tag_regions(
        record_text
    )
    items = extract_body_items(record_text)
    tagged_items = [item for item in items if SOURCE_TAG_PATTERN.search(item)]
    tagged_item_ratio = round(len(tagged_items) / len(items), 4) if items else 0.0

    template, template_note = resolve_template(template_id)
    _, dedupe_removed = dedupe_cross_section_items(record_text, template)

    term_hits = count_known_term_fix_hits(record_text)
    # P2-1：出處標註可回溯性（與產品 snap_source_tags_to_transcript 共用同一份
    # 段落解析定義；未提供逐字稿時整欄為 null）。
    tag_traceability = (
        measure_tag_traceability(record_text, transcript_text)
        if transcript_text is not None
        else None
    )
    if transcript_text is not None:
        term_hits["transcript"] = count_known_term_fix_hits(transcript_text)
        unsupported_entities: Optional[list] = find_unsupported_entities(record_text, transcript_text)
        # P4-B（additive）：同一份 fidelity_checks 模組（產品補強清單與量尺共用）——
        # raw unsupported_entities 保留為觀察值（歷史相容），registry-aware 為新欄位。
        fidelity_report = analyze_fidelity(record_text, transcript_text, template_id)
        unsupported_entities_registry_aware: Optional[list] = fidelity_report[
            "registry_aware_unsupported_entities"
        ]
        fidelity: Optional[dict] = {
            "metric_version": fidelity_report["metric_version"],
            "entity_flags": len(fidelity_report["fabricated_entities"]),
            "entity_names": fidelity_report["fabricated_entities"],
            "entity_kinds": fidelity_report["fabricated_entity_kinds"],
            "attribution_flags": len(fidelity_report["attribution_violations"]),
            "attribution_kinds": fidelity_report["attribution_kinds"],
            "number_fabricated": len(fidelity_report["fabricated_numbers"]),
            "number_missing": len(fidelity_report["missing_numbers"]),
            "number_missing_tokens": fidelity_report["missing_numbers"],
            "attribution_overlap_median": fidelity_report["attribution_overlap_median"],
            "problems": fidelity_report["problems"],
        }
    else:
        term_hits["transcript"] = None
        unsupported_entities = None
        unsupported_entities_registry_aware = None
        fidelity = None

    notes = {
        "definitions": {
            "char_count": "Markdown 全文 len(text)（含換行）；DOCX 一律 SKIP（段落合併使行結構失真）",
            "body_source_tag_count": (
                "非表格列（不符合 TABLE_ROW_PATTERN＝^\\s*\\|）且非開頭欄位"
                "（^(時間|地點|主持人|出席人員|紀錄)，plan rev6 記法、不含冒號）的 "
                "SOURCE_TAG_PATTERN 命中數（同 summarization.py:1026-1061 排除語意）"
            ),
            "table_source_tag_count": (
                "符合 TABLE_ROW_PATTERN（^\\s*\\|）表格列的 SOURCE_TAG_PATTERN "
                "命中數（正文契約排除區；與 strip_source_tags_from_table_rows 同一定義）"
            ),
            "instruction_item_count": (
                "「科長指示及提醒事項」章節內行首為 'N.' 或 '（N）' 的 leaf item 數；"
                "找不到該章節時以全文 leaf item 計"
            ),
            "tagged_item_ratio": "正文 leaf item 中至少一個 SOURCE_TAG_PATTERN 的比率（基線 33/34≈97.1%）",
            "cross_section_duplicate_pairs": (
                "dedupe_cross_section_items 回報移除的條目數（＝決議節／主席裁示節重複對數）"
            ),
            "known_term_fix_hits": (
                "left_hits＝SECTION_MEETING_RECORD_TERM_FIXES 左側（錯形 regex）命中數；"
                "right_hits＝右側修正字面出現數；transcript＝同規則套用逐字稿（未提供時 null）"
            ),
            "tag_traceability": (
                "出處標註真實性（逐字稿段落時間表為 ground truth）："
                "traceable_tag_ratio＝時間戳落在逐字稿任一真實段落內的比例；"
                "tags_on_real_segment_start／on_start_tag_ratio＝時間戳恰為任一真實段落起點"
                "（吸附後的主指標：標註真的指到一句話的開頭）；"
                "tags_exact_segment_start／exact_tag_ratio＝再要求發言者標籤與該段一致（嚴格版）；"
                "tags_inside_same_speaker_segment＝落在標註指名發言者的段落內；"
                "zero_time_tag_count／zero_time_tag_ratio＝時間戳 00:00:00 的標註（結構上必然"
                "命中段落起點，會膨脹 on_start_tag_ratio，故單獨列出）；"
                "distinct_tag_time_count／distinct_tag_time_ratio＝不同時間戳數／比例（標註辨別力）；"
                "on_start_tag_ratio_excluding_zero＝排除 00:00:00 後的段落起點命中率"
                "（分母＝非 00:00:00 的標註數）"
            ),
        },
        "observed": {
            "excluded_header_field_tag_count": header_tags,
            "template_resolution": template_note,
            "transcript_provided": transcript_text is not None,
        },
        "unsupported_entities": (
            "觀察值：紀錄中以「…」明示、結尾為組織後綴（股／科／室／處／局／中心／公司）"
            "且逐字稿未出現的單位名稱（高精確、低召回）；**永不作為閘門**"
            "（字面比對無法區分捏造與 ASR 變體重建，plan §1／W6）。"
            "未提供 --transcript 時為 null。"
        ),
        "unsupported_entities_registry_aware": (
            "P4-B 新欄位：以與 ``unsupported_entities`` **同一份 raw 抽取**為候選，"
            "再過 ``backend.core.fidelity_checks.is_supported_entity``（fold 變體／stem 正確改寫／"
            "官方白名單 ``data/entities/entity_registry.json``＋既有 glossary）；"
            "仍未被支持者才列出。產品忠實度絆索（A 自創專名）與本欄位共用同一支函式。"
            "raw 欄位保留為觀察值；未提供 --transcript 時為 null。"
        ),
        "fidelity": (
            "P4-B 忠實度絆索摘要（``backend.core.fidelity_checks.analyze_fidelity``；"
            "metric_version＝%s）：entity_flags／attribution_flags／number_fabricated／"
            "number_missing 為各絆索計數；entity_kinds＝variant｜unsupported；"
            "attribution_overlap_median 為未校準觀察值。"
            "products 端僅取 ``problems`` 併入補強問題清單（不改寫、不刪句）。"
            "未提供 --transcript 時為 null。" % FIDELITY_METRIC_VERSION
        ),
        "non_prefixed_tableish_source_tag_count": (
            "觀察值：行內含 '|'（ASCII）或 '｜'（全形）、具表格樣態"
            "（行首為管線字元，或行內 ≥2 個管線字元）但**不符合**表格列"
            "定義（TABLE_ROW_PATTERN＝^\\s*\\|）的行上之 SOURCE_TAG_PATTERN 命中數；"
            "**永不作為閘門**。產品契約與 W2b 清除器"
            "（strip_source_tags_from_table_rows）皆定義彙整表列為 ^\\s*\\|，"
            "因此全形 '｜'／非行首的真表格列是已知殘餘缺口（P1-13 層級回報），"
            "此計數僅供可視化，不影響 table／body 計數語意。"
        ),
        "sampling_caveat": "指標為確定性字面統計；E2E 判讀仍受單次抽樣（temperature 0.7）限制。",
    }

    return {
        "char_count": len(record_text),
        "body_source_tag_count": body_tags,
        "table_source_tag_count": table_tags,
        "non_prefixed_tableish_source_tag_count": non_prefixed_tags,
        "instruction_item_count": count_instruction_items(record_text),
        "tagged_item_ratio": tagged_item_ratio,
        "cross_section_duplicate_pairs": dedupe_removed,
        "known_term_fix_hits": term_hits,
        "tag_traceability": tag_traceability,
        "unsupported_entities": unsupported_entities,
        "unsupported_entities_registry_aware": unsupported_entities_registry_aware,
        "fidelity": fidelity,
        "notes": notes,
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="measure_record_quality.py",
        description=(
            "確定性量測最終會議紀錄（Markdown 為權威）的品質指標；"
            "輸出固定 schema JSON（stdout／--out）。"
        ),
    )
    parser.add_argument(
        "--record",
        type=Path,
        required=True,
        help="最終會議紀錄 Markdown 路徑；給 .docx 時印出 SKIP（段落合併使計數不可信）並 exit 0",
    )
    parser.add_argument("--transcript", type=Path, default=None, help="逐字稿 txt（選用；提供時才輸出 unsupported_entities）")
    parser.add_argument("--template", default=None, help="會議模板 id（如 section_meeting；供 W5 跨章節去重）")
    parser.add_argument("--out", type=Path, default=None, help="另寫一份 JSON 檔（stdout 仍輸出同一份）")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    if args.record.suffix.lower() in DOCX_SUFFIXES:
        print(
            f"SKIP: {args.record} 是 DOCX；DOCX 經 python-docx/段落抽取會把表格列與"
            "正文段落合併，出處標註與條目計數不可信，因此不量測。"
            "請提供 Markdown 產物（backend_data/outputs/*.md）作為權威來源。"
        )
        return 0

    if not args.record.exists():
        print(f"ERROR: 找不到紀錄檔案：{args.record}", file=sys.stderr)
        return 2
    record_text = args.record.read_text(encoding="utf-8")

    transcript_text: Optional[str] = None
    if args.transcript is not None:
        if not args.transcript.exists():
            print(f"ERROR: 找不到逐字稿檔案：{args.transcript}", file=sys.stderr)
            return 2
        transcript_text = args.transcript.read_text(encoding="utf-8")

    result = measure_record_quality(
        record_text, transcript_text=transcript_text, template_id=args.template
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
