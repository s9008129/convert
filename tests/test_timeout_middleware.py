#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for request timeout middleware behavior.
"""

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.middleware.timeout import TimeoutMiddleware


def test_timeout_middleware_times_out_regular_requests():
    app = FastAPI()
    app.add_middleware(TimeoutMiddleware, timeout=0.05)

    @app.get("/slow")
    async def slow():
        await asyncio.sleep(0.1)
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/slow")

    assert response.status_code == 503
    assert response.json()["error"] == "Request timeout"


def test_timeout_middleware_skips_excluded_upload_path():
    app = FastAPI()
    app.add_middleware(
        TimeoutMiddleware,
        timeout=0.05,
        excluded_paths=("/api/upload",),
    )

    @app.post("/api/upload")
    async def upload():
        await asyncio.sleep(0.1)
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/api/upload")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
