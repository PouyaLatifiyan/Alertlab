"""Replay held-out changed draws in bench/run.py, preserving physical RNG draws."""
import csv
import json
import sys
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'research' / 'bench'))
import run as benchmark

def export():
    with (root / 'research/bench/thresholds.csv').open() as stream:
        thresholds = {(r['scenario'], r['method'], float(r['budget'])): float(r['threshold']) for r in csv.DictReader(stream)}
    seeds = np.random.SeedSequence(benchmark.SEED).spawn(3*len(benchmark.SCENARIOS))
    output = {}
    for index, scenario in enumerate(benchmark.SCENARIOS):
        rng = np.random.default_rng(seeds[3*index+2])
        thresholds_for_policy = [[thresholds[(scenario.name, name, cap)] for cap in benchmark.BUDGET] for name in benchmark.METHODS]
        chunks, onsets, eligible = [], [], []
        for count in benchmark.chunk(benchmark.TEST_N):
            scores, onset, age = benchmark.trial(rng, count, scenario, True)
            alarms = np.stack([benchmark.first(score[:,None,:] > np.asarray(thresholds_for_policy[j])[None,:,None])
                               for j,score in enumerate(scores)],axis=1)
            _, misses, need, _ = benchmark.physical(rng, scenario, age, alarms, onset)
            onsets.append(onset)
            chunks.append(alarms)
            eligible.append(need[:,None,None] & ~misses)
        alarms, onset, opportunity = np.concatenate(chunks), np.concatenate(onsets), np.concatenate(eligible)
        output[scenario.name] = {}
        for j, name in enumerate(benchmark.METHODS):
            output[scenario.name][name] = {}
            for i, budget in enumerate(benchmark.BUDGET):
                times = alarms[:,j,i]
                post = (times >= onset) & (times <= benchmark.T)
                histogram = np.bincount((times-onset)[post],minlength=benchmark.T).tolist()
                output[scenario.name][name][str(budget)] = dict(post=int(post.sum()), premature=int((times<onset).sum()),
                    silent=int((times>benchmark.T).sum()), actionable=int(opportunity[:,j,i].sum()), histogram=histogram)
    (root/'public/data/delays.json').write_text(json.dumps(output,separators=(',',':')))

if __name__ == '__main__':
    export()
