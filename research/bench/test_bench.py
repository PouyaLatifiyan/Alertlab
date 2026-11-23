"""Regression tests independent of the vectorized terminal calculations."""
import unittest
import numpy as np
from scipy.special import ndtr
from run import scores, FRACTIONS, SCENARIOS, HERE
from envelope import crossing_cdf, lower
import csv

class BenchmarkTests(unittest.TestCase):
    def test_scores_against_direct_definition(self):
        z=np.random.default_rng(45).normal(size=(3,22))
        refs=np.random.default_rng(77).normal(size=(3,9));s=scores(z,refs)
        np.testing.assert_equal(s[0],abs(z))
        for i,row in enumerate(z):
            endpoint=np.mean(abs(refs[i,None,:])<abs(row[:,None]),axis=1)/(.5+np.sqrt(np.log(4000)/18))
            for t in range(1,23):
                cus=max([0]+[sign*row[k:t].sum()-.5*(t-k) for k in range(t) for sign in (1,-1)])
                glr=max(row[k:t].sum()**2/(2*(t-k)) for k in range(max(0,t-16),t))
                wealth=[np.prod(1+eta*(endpoint[u:t]-1)) if u<t else 1 for u in (0,10,20) for eta in FRACTIONS]
                np.testing.assert_allclose([s[1][i,t-1],s[2][i,t-1],s[3][i,t-1]],[cus,glr,np.log(np.mean(wealth))],atol=1e-11)
    def test_physical_integral(self):
        grid=(np.arange(10000)+.5)/10000*.30+.85
        for c in (.3,.9,1,1.4):
            direct=np.mean(np.clip((c*grid-.85)/.30,0,1))
            self.assertAlmostEqual(float(crossing_cdf([c])[0]),direct,8)
        for s in SCENARIOS:
            l1,h=lower(s,.005);l2,_=lower(s,.08)
            self.assertGreaterEqual(l1+1e-10,l2)
            self.assertGreaterEqual(l2+1e-10,s.fault_probability*h)
    def test_pair_and_choices(self):
        with (HERE/'decisions.csv').open() as f:rows=list(csv.DictReader(f))
        default=[r for r in rows if (r['fa_cap'],r['hazard_cap'],r['slot_cap'])==('0.02','0.6','250')]
        weak=next(r for r in default if r['scenario']=='weak persistent')
        self.assertEqual(weak['status'],'no feasible candidate')
        pair=[next(r for r in default if r['scenario']==s) for s in ('moderate persistent','brief pulse')]
        self.assertEqual([p['choice'] for p in pair],['CUSUM','Shewhart'])
        self.assertEqual(set(pair[0]['outer'].split(',')) & set(pair[1]['outer'].split(',')),{'GLR16'})
if __name__=='__main__':unittest.main()
