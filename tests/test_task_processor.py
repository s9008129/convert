#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TaskProcessor 結構修補測試。
"""

from backend.services.task_processor import TaskProcessor


def test_ensure_structure_inserts_missing_sections_and_converts_action_bullets():
    processor = TaskProcessor()
    summary = """# 會議記錄摘要

## 1. 會議概況
- **日期**：113年3月1日

## 2. 執行摘要 (Executive Summary)
會議確認專案月底上線，並交辦後續測試與公告準備。

## 4. 待辦事項
- 完成整合測試
- 提交上線公告草案
"""

    repaired = processor._ensure_structure(summary)

    assert "## 3. 詳細議題與決議 (Discussion & Decisions)" in repaired
    assert "## 5. 其他備註" in repaired
    assert "| 待辦事項 | 負責人 | 期限 |" in repaired
    assert "| 完成整合測試 | （待確認） | （待確認） |" in repaired
    assert "| 提交上線公告草案 | （待確認） | （待確認） |" in repaired


def test_ensure_structure_preserves_existing_action_table_rows():
    processor = TaskProcessor()
    summary = """# 會議記錄摘要

## 1. 會議概況
- **日期**：113年3月1日
- **參與者**：王主任、陳科長
- **會議主題**：專案進度追蹤

## 2. 執行摘要 (Executive Summary)
會議確認月底上線，並交辦兩項待辦事項。

## 3. 詳細議題與決議 (Discussion & Decisions)
- **議題 1**：專案里程碑
  - *討論重點*：確認測試與公告時程
  - *最終決議*：維持月底上線

## 4. 待辦事項 (Action Items) - 必填
| 待辦事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
| 完成整合測試 | 王主任 | 下週三 |
| 提交上線公告草案 | 陳科長 | 本週五 |

## 5. 其他備註
- 無
"""

    repaired = processor._ensure_structure(summary)

    assert repaired.count("| 完成整合測試 | 王主任 | 下週三 |") == 1
    assert repaired.count("| 提交上線公告草案 | 陳科長 | 本週五 |") == 1
    assert "本次會議未明確指派待辦事項" not in repaired


def test_language_cleanup_keeps_important_technical_terms():
    processor = TaskProcessor()
    summary = """# 會議記錄摘要

## 2. 執行摘要 (Executive Summary)
本次會議確認 OAuth2、JWT 與 GitHub Actions 將納入上線範圍，Okay。
"""

    sanitized = processor._sanitize_text_language(summary)

    assert "OAuth2" in sanitized
    assert "JWT" in sanitized
    assert "GitHub Actions" in sanitized
    assert "Okay" not in sanitized
    assert "好" in sanitized


def test_excessive_english_detection_is_not_triggered_by_mixed_technical_summary():
    processor = TaskProcessor()
    summary = """# 會議記錄摘要

## 2. 執行摘要 (Executive Summary)
本次會議主要討論 API 串接、OAuth2 驗證、GitHub Actions 部署與 AWS 資源調整，整體仍以中文敘述為主，並確認月底前完成上線。
"""

    assert processor._has_excessive_english(summary) is False
