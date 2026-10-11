"""Exercise inherited failure/latching cases plus explicit candidate Build mismatch."""
import importlib.util
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'tmp/m357_board_support_01/m357_completion_observer.py'
spec=importlib.util.spec_from_file_location('completion_observer',path)
module=importlib.util.module_from_spec(spec);sys.modules['completion_observer']=module;spec.loader.exec_module(module)
from test_completion_observer import ObserverTests,snap

class CandidateObserverTests(ObserverTests):
    def test_candidate_explicit_build(self):
        _,ev=self.run_case([snap(6,True,True,ap_return=0x4d333537)],expected_build_id=0x4d333537)
        self.assertTrue(ev['completion_proven'])
    def test_stable_build_rejected_as_candidate(self):
        with self.assertRaisesRegex(module.ObservationFailure,'Build'):
            self.run_case([snap(6,True,True)],expected_build_id=0x4d333537)
    def test_candidate_rejected_as_stable(self):
        with self.assertRaisesRegex(module.ObservationFailure,'Build'):
            self.run_case([snap(6,True,True,ap_return=0x4d333537)])

if __name__=='__main__':
    # Load only the derived suite, avoiding duplicate inherited executions.
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CandidateObserverTests))
    raise SystemExit(not result.wasSuccessful())
