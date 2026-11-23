"""Serialize the provided frozen research tables for static browser use."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = {'coordinates':'bench/coordinate_intervals', 'pairs':'bench/paired_intervals',
         'decisions':'bench/decisions', 'limits':'bench/admissible_limits', 'thresholds':'bench/thresholds',
         'baseline':'bench/decision_baseline', 'clock':'recorded/texbat_clock',
         'crossing':'recorded/bs1_first_crossing', 'error':'recorded/bs1_error',
         'oracle':'limits/decision', 'frontier':'limits/frontier', 'regret':'case/matched_regret'}

def value(text):
    try:
        return float(text)
    except ValueError:
        return text

data = {}
for key, path in PATHS.items():
    with (ROOT / f'research/{path}.csv').open() as stream:
        data[key] = [{k:value(v) for k,v in row.items()} for row in csv.DictReader(stream)]
data['design'] = json.loads((ROOT / 'research/bench/design.json').read_text())
(ROOT / 'public/data/paper.json').write_text(json.dumps(data, separators=(',',':')))
