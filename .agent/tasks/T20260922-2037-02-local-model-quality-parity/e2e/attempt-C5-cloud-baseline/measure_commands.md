# 本場量測可重現指令（雲端基線 C5）

```bash
cd /Users/hsiaojohnny/dev/convert
R=data/cache/e2e/p3-cloud-baseline-05/backend_data/outputs/0903-科務會議_ce67d0dc.md
T=data/cache/e2e/p3-cloud-baseline-05/backend_data/outputs/0903-科務會議_ce67d0dc_逐字稿.txt

DATA_DIR=/tmp/probe_scratch .venv/bin/python scripts/e2e/measure_coverage.py \
  --record "$R" --checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json \
  --transcript "$T" --label C5-cloud

DATA_DIR=/tmp/probe_scratch .venv/bin/python scripts/e2e/measure_record_quality.py \
  --record "$R" --transcript "$T" --template section_meeting

# DOCX 補產生（既有轉換器；與產品下載路徑同一支）
DATA_DIR=/tmp/probe_scratch .venv/bin/python -c "
from pathlib import Path
from backend.services.docx_converter import docx_converter
md = Path('$R').read_text(encoding='utf-8')
print(docx_converter.convert(md, '$R'.removesuffix('.md') + '.docx', template_id='section_meeting'))
"
```
