import unittest
import numpy as np
from coupled import feasible_rival_regret

class CouplingDecisionTest(unittest.TestCase):
    def test_boundary_and_empty_robust_menu(self):
        costs=np.array([[0.,0.,1.,1.],[0.,1.,0.,0.]])
        usage=(1-costs)[:,None,:]
        poly=([],[],[[1,1,0,0],[0,0,1,1],[1,0,1,0]],[.5]*3)
        self.assertEqual(feasible_rival_regret(costs,usage,[.49],poly),[None,None])
        for cap in [.5,.55,.6,.75,1.]:
            out=feasible_rival_regret(costs,usage,[cap],poly)
            self.assertAlmostEqual(out[0],cap-.5)
            if cap<1:
                self.assertIsNone(out[1])
            else:
                self.assertAlmostEqual(out[1],0)
    def test_incompatible_input(self):
        with self.assertRaises(ValueError):
            feasible_rival_regret([[0]],[[[0]]],[1],([],[],[[1],[1]],[0,1]))

if __name__=='__main__':
    unittest.main()
