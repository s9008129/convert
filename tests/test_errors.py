#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""describe_exception 測試（v4.6.2）。

httpx 逾時類例外 str() 為空曾使會議紀錄 fallback 文件遺失「失敗原因」行，
本工具必須保證任何例外都能還原出至少類別名稱。
"""

import httpx

from backend.core.errors import describe_exception


def test_describe_exception_keeps_normal_message():
    assert describe_exception(ValueError("boom")) == "ValueError: boom"


def test_describe_exception_recovers_class_name_for_empty_httpx_timeout():
    described = describe_exception(httpx.ReadTimeout(""))

    assert described
    assert described.startswith("ReadTimeout")


def test_describe_exception_recovers_class_name_for_empty_builtin_timeout():
    described = describe_exception(TimeoutError())

    assert described
    assert described.startswith("TimeoutError")
