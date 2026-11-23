import unittest
from itertools import product
from math import factorial
from decision import cp,pair_interval,pair_interval_counts,select,simultaneous,pareto

class DecisionTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(cp(0,4,.1)[0],0)
        self.assertEqual(cp(4,4,.1)[1],1)
        self.assertLess(pair_interval([0]*200,[1]*200,.05)[1],0)
        self.assertLess(pair_interval([0]*200,[0]*200,.05)[0],0)
    def test_exact_small_sample_coverage(self):
        n=6
        for a,b in [(0,.3),(.1,.2),(.55,.15),(.05,.95),(0,0)]:
            mass=0.
            for i,j in product(range(n+1),repeat=2):
                if i+j>n:continue
                k=n-i-j
                prob=factorial(n)/(factorial(i)*factorial(j)*factorial(k))*a**i*b**j*max(0,1-a-b)**k
                l,u=pair_interval_counts(i,j,n,.1)
                mass+=prob*(l-1e-12<=a-b<=u+1e-12)
            self.assertGreaterEqual(mass,.9-1e-12)
    def test_unresolved_competitor(self):
        bands={'a':{'fa':(.01,.03),'hazard':(.2,.3)},'b':{'fa':(.01,.06),'hazard':(.01,.05)}}
        r=select(bands,bands,{'fa':.04})
        self.assertEqual(r['choice'],'a')
        self.assertAlmostEqual(r['candidate_excess_upper'],.29)
        self.assertFalse(r['unique_best'])
        self.assertEqual(select(bands,bands,{'fa':.005})['status'],'infeasible')
        self.assertEqual(select(bands,bands,{'fa':.015})['status'],'insufficient evidence')
    def test_simultaneous(self):
        outcomes={'a':{'hazard':[0]*80},'b':{'hazard':[1]*80}}
        intervals,pairs=simultaneous(outcomes,paired_metrics=['hazard'])
        r=select(outcomes,intervals,{},paired=pairs)
        self.assertTrue(r['unique_best'])
        self.assertEqual(r['candidate_excess_upper'],0)
        self.assertEqual(pareto(r['feasible'],list(outcomes),intervals,['hazard'],pairs)[0],['a'])
        self.assertEqual(pairs['hazard']['a','b'][1],-pairs['hazard']['b','a'][0])
if __name__=='__main__': unittest.main()
