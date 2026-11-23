"""Offline checks on the clock converter and logged replay results."""
import csv
from pathlib import Path
import unittest
import numpy as np
from field_audit import receiver_seconds
BASE = Path(__file__).resolve().parent

def read(name):
    with (BASE/name).open() as fp:
        return list(csv.DictReader(fp))

class ReplayAudit(unittest.TestCase):
    def test_clock_translation(self):
        channels = np.zeros((3,14))
        channels[:,1] = [4.,4.25,4.5]
        channels[:,2] = 55
        channels[:,3] = 220
        channels[:,4] = [.1,.35,.6]
        nav = np.array([[55,220,.35],[55,220,.6]])
        result, spread = receiver_seconds(channels,nav)
        np.testing.assert_allclose(result,[4.25,4.5])
        self.assertLess(spread,1e-9)
        channels[1,1] += 1.
        with self.assertRaises(ValueError):
            receiver_seconds(channels,nav)

    def test_direct_first_crossing(self):
        pts = [(int(float(r['record_s'])),float(r['3d_position_discrepancy_m'])) for r in read('bs1_error.csv')]
        self.assertEqual(len(pts),183)
        self.assertEqual(max(pts,key=lambda x:x[1])[0],170)
        self.assertAlmostEqual(max(v for t,v in pts),98.751069,places=5)
        self.assertEqual(min(t for t,v in pts if t>=120 and v>=10),151)
        for row in read('bs1_first_crossing.csv'):
            h=(float(row['closed_upper_limit_m'])+float(row['open_lower_limit_m']))/2
            self.assertEqual(min(t for t,v in pts if t>=120 and v>=h),float(row['first_at_or_above_s_from_t120']))

    def test_policy_and_time_base(self):
        rows = {(r['record'],r['policy']):r for r in read('time_sensitivity.csv')}
        self.assertEqual([rows['ds7','common'][k] for k in ('endpoint','cash','adaptive','restart')],['silent','silent','349','318'])
        first = {r['record']: r for r in read('rrt.csv')}
        self.assertAlmostEqual(float(first['ds7']['restart_rrt_s']),353.000421,places=6)
        for record,rr in first.items():
            for k in ('endpoint','cash','adaptive','restart'):
                elapsed=rows[record,'historical'][k]
                if elapsed=='silent':
                    self.assertEqual(rr[k+'_rrt_s'],'silent')
                else:
                    self.assertLess(abs(float(rr[k+'_rrt_s'])-float(rr['first_nav_rrt_s'])-float(elapsed)),.5)

if __name__=='__main__':
    unittest.main()
