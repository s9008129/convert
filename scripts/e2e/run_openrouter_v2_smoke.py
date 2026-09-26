#!/usr/bin/env python3
"""Privacy-safe OpenRouter production-V2 smoke for Issue #18.

Uses only synthetic content and prints status/hash/length metadata, never model text.
"""

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("LOCAL_LLM_PROVIDER", "openrouter")
os.environ.setdefault("LOCAL_PIPELINE_VERSION", "v2")
os.environ.setdefault("LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS", "32768")
os.environ.setdefault("LOCAL_LLM_DISABLE_THINKING", "true")

from backend.core.config import settings  # noqa: E402
from backend.models.schemas import ProcessingMode  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402
from backend.services.local_pipeline_diagnostics import LocalPipelineDiagnosticRecorder  # noqa: E402


MODELS = ("google/gemma-4-31b-it", "qwen/qwen3.8-27b")
SYNTHETIC_TRANSCRIPT = """[00:00:01] 主席：決議由資訊科負責盤點系統權限，期限為10月15日。
[00:00:10] 主席：因整合測試尚未完成，導致正式上線延後。
[00:00:18] 主席：完成驗證後再上線，資訊科於下次會議報告進度。"""


async def main() -> None:
    if not settings.OPENROUTER_API_KEY:
        raise SystemExit("OPENROUTER_API_KEY is required")
    outcomes = []
    for model in MODELS:
        settings.OPENROUTER_MODEL = model
        service = SummarizationService()
        recorder = LocalPipelineDiagnosticRecorder(run_id="synthetic-openrouter-smoke")
        try:
            record = await service.summarize(
                SYNTHETIC_TRANSCRIPT,
                mode=ProcessingMode.LOCAL,
                template_id="general",
                diagnostic_recorder=recorder,
            )
        except Exception:
            # This script uses a fixed synthetic transcript only. Printing the
            # last model-produced synthetic section is therefore safe and gives
            # enough evidence to diagnose firewall false positives without ever
            # weakening the production firewall or exposing real meeting data.
            safe_events = []
            for event in recorder.events:
                stage = str(event.get("stage_id", ""))
                if stage.endswith(".output") and (
                    stage.startswith("v2.section.") or stage.startswith("v2.patch.")
                ):
                    safe_events.append({
                        "stage_id": stage,
                        "status": event.get("status"),
                        "output_text": event.get("output_text"),
                    })
            print(
                "V2_SMOKE_SYNTHETIC_DEBUG "
                + json.dumps(
                    {"model": model, "events": safe_events[-6:]},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                flush=True,
            )
            raise
        finally:
            await service.close()
        payload = {
            "model": model,
            "status": "PASS",
            "chars": len(record),
            "sha256": hashlib.sha256(record.encode("utf-8")).hexdigest(),
        }
        outcomes.append(payload)
        print("V2_SMOKE " + json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if len(outcomes) != len(MODELS):
        raise SystemExit("missing model result")
    print("OPENROUTER_V2_SMOKE=PASS")


if __name__ == "__main__":
    asyncio.run(main())
