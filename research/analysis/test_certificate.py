"""Independent finite enumeration and LP checks. Run as python analysis/test_certificate.py."""
from pathlib import Path
from fractions import Fraction
from itertools import product
import csv
import sys
import unittest

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "selection"))
from decision import select, robust_intervals


class CertificateChecks(unittest.TestCase):
    def test_regret_and_feasibility_at_all_box_vertices(self):
        boxes = {
            "early": {"fa": (.01, .04), "hazard": (.12, .30)},
            "specific": {"fa": (.01, .025), "hazard": (.14, .27)},
            "sensitive": {"fa": (.025, .10), "hazard": (.01, .13)},
        }
        names = list(boxes)
        for budget in (.02, .025, .04, .07, .10):
            res = select(names, boxes, {"fa": budget}, oracle_lower=.005)
            for bits in product((0, 1), repeat=6):
                actual = {m: (boxes[m]["fa"][bits[2*i]], boxes[m]["hazard"][bits[2*i+1]])
                          for i, m in enumerate(names)}
                feasible = [m for m in names if actual[m][0] <= budget]
                self.assertTrue(set(res["feasible"]).issubset(feasible))
                self.assertTrue(set(feasible).isdisjoint(res["infeasible"]))
                chosen = res["choice"]
                if chosen is None:
                    continue
                optimum = min(actual[m][1] for m in feasible)
                risk = actual[chosen][1]
                l, u = res["candidate_optimum_interval"]
                self.assertLessEqual(l, optimum)
                self.assertLessEqual(optimum, u)
                self.assertLessEqual(risk-optimum, res["candidate_excess_upper"]+1e-12)

    def test_expanding_ambiguity_set(self):
        strata = {"s": {"A": {"risk": (.1, .3)}}, "t": {"A": {"risk": (.2, .9)}}}
        mid = robust_intervals(strata, [[.5, .5]])["A"]["risk"]
        full = robust_intervals(strata)["A"]["risk"]
        self.assertGreaterEqual(full[0], mid[0])
        self.assertGreaterEqual(full[1], mid[1])
        broad = robust_intervals(strata, tv_radius=.1)["A"]["risk"]
        self.assertLessEqual(broad[0], full[0])
        self.assertGreaterEqual(broad[1], full[1])

    def test_oracle_by_leaf_capacity_lp(self):
        histories = [tuple(h) for k in range(1, 4) for h in product([0, 1], repeat=k)]
        leaves = [h for h in histories if len(h)==3]
        def prob(h,p):
            return p**sum(h)*(1-p)**(len(h)-sum(h))
        healthy = np.array([prob(h,.2) for h in histories])
        timely = np.array([.6*prob(h,.6)+(.4*prob(h,.8) if len(h)==1 else 0.)
                           for h in histories])
        incidence = [[int(leaf[:len(h)]==h) for h in histories] for leaf in leaves]
        constraints = np.vstack([incidence,healthy])
        with (ROOT/"limits"/"decision.csv").open() as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            budget=float(Fraction(row["alpha"]))
            res=linprog(-timely,A_ub=constraints,b_ub=[1.]*8+[budget],bounds=(0.,1.),method="highs")
            self.assertTrue(res.success)
            exact=float(Fraction(row["optimal_causal_timely"]))
            self.assertAlmostEqual(-res.fun, exact)
            self.assertAlmostEqual(1.-.9*exact,float(Fraction(row["optimal_hazard"])))
            self.assertLessEqual(healthy@res.x, budget+1e-10)
        # At every budget boundary, the objective is nondecreasing.
        opt=[float(Fraction(r["optimal_causal_timely"])) for r in rows]
        self.assertTrue(np.all(np.diff(opt)>=0))

if __name__=="__main__":
    unittest.main()
