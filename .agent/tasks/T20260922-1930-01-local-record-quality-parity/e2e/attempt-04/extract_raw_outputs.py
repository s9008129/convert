"""Stage 05 附帶稽核工具（read-only）：從 LM Studio server log 抽回本次 run 的 raw
模型輸出，用以驗證「後處理是否吃掉正文標註」。只讀 server log + 生產 artifact。"""
import importlib.util
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/hsiaojohnny/dev/convert")
LOG = Path.home() / ".lmstudio/server-logs/2026-09/2026-09-22.1.log"
OUT_DIR = PROJECT_ROOT / ".agent/tasks/T20260922-1930-01-local-record-quality-parity/e2e/attempt-04"

spec = importlib.util.spec_from_file_location(
    "measure_record_quality", PROJECT_ROOT / "scripts/e2e/measure_record_quality.py"
)
mod = importlib.util.module_from_spec(spec)
sys.argv = ["measure_record_quality.py", "--record", "/dev/null"]  # avoid argparse side effects? (main guard prevents)
spec.loader.exec_module(mod)

text = LOG.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()
marker = "Generated prediction: {"
records = []
i = 0
while i < len(lines):
    if marker in lines[i]:
        ts = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", lines[i])
        block = []
        j = i + len(lines[i].split(marker, 1)[0]) and i
        # JSON starts on line i (after marker) — possibly spanning lines
        start = lines[i].index(marker) + len(marker) - 1
        buf = lines[i][start:]
        j = i + 1
        while True:
            buf += "\n" + lines[j]
            if lines[j].rstrip() == "}":
                break
            j += 1
        payload = json.loads(buf)
        content = payload["choices"][0]["message"]["content"]
        usage = payload.get("usage", {})
        records.append(
            {
                "finished_at": ts.group(1) if ts else None,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "content_chars": len(content),
                "content": content,
            }
        )
        i = j + 1
    else:
        i += 1

out = []
for r in records:
    body, table, header, nonpref = mod.count_source_tag_regions(r["content"])
    out.append({**{k: v for k, v in r.items() if k != "content"}, "body_tags": body, "table_tags": table, "header_tags": header, "nonpref_tableish_tags": nonpref})

# 只留本次 run 尾端 4 個 record-level 生成（20:23:13 之後）供對照
recent = [r for r in records if r.get("finished_at") and r["finished_at"] >= "2026-09-22 20:24:00"]
print(json.dumps(out[-6:], ensure_ascii=False, indent=2))
# dump raw contents of the last 4 large calls for tag comparison
for idx, r in enumerate(records):
    if r.get("finished_at", "") >= "2026-09-22 20:24:00" and r.get("completion_tokens", 0) > 500:
        (OUT_DIR / f"raw_model_output_{r['finished_at'].replace(':', '').replace(' ', 'T')}.md").write_text(r["content"], encoding="utf-8")
print("saved raw outputs:", sorted(p.name for p in OUT_DIR.glob("raw_model_output_*.md")))
