"""Fault checks for quiet UVM diagnostics and actual start/done pairing."""
import sys
import unittest
from pathlib import Path
from m356_collect_rtl import paired_shard_events
from m357_uvm_log_evidence import evaluate
ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'tmp/m357_candidate_q_trace/verilog'
LOG=(DIRECTORY/'m357_xsim.log').read_text(encoding='utf-8-sig',errors='replace')

def row(cycle,event,shard):return dict(cycle=str(cycle),event=event,shard=str(shard),value='0')

class CollectionTests(unittest.TestCase):
    def test_actual_quiet_log_source_audit(self):
        clean,ev=evaluate(DIRECTORY,LOG);self.assertTrue(clean);self.assertFalse(ev['summary_counts_present'])
    def test_error_with_source_filename_is_rejected(self):
        self.assertFalse(evaluate(DIRECTORY,LOG+'\nUVM_ERROR file.sv(42) @ 123: checker bad\n')[0])
    def test_fatal_without_at_is_rejected(self):
        self.assertFalse(evaluate(DIRECTORY,LOG+'\nUVM_FATAL source failure\n')[0])
    def test_nonzero_summary_rejected(self):
        self.assertFalse(evaluate(DIRECTORY,LOG+'\nUVM_ERROR : 1\nUVM_FATAL : 0\n')[0])
    def test_explicit_zero_summary_accepted(self):
        self.assertTrue(evaluate(DIRECTORY,LOG+'\nUVM_ERROR : 0\nUVM_FATAL : 0\n')[0])
    def sequence(self):
        rows=[row(1,'done',i) for i in range(4)]
        for d in range(2):
            for i in range(4):rows.extend([row(100+d*100+i*10,'start',i),row(105+d*100+i*10,'done',i)])
        return rows
    def test_exact_initial_idle_done_then_eight_pairs(self):
        starts,dones,initial,valid=paired_shard_events(self.sequence(),True)
        self.assertTrue(valid);self.assertEqual((len(starts),len(dones),len(initial)),(8,8,4))
    def test_initial_done_not_generally_ignored(self):
        self.assertFalse(paired_shard_events(self.sequence(),False)[3])
    def test_late_orphan_done_rejected(self):
        self.assertFalse(paired_shard_events(self.sequence()+[row(500,'done',0)],True)[3])
    def test_missing_final_done_rejected(self):
        self.assertFalse(paired_shard_events(self.sequence()[:-1],True)[3])
    def test_duplicate_active_start_rejected(self):
        rows=[row(10,'start',0),row(11,'start',0),row(20,'done',0)]
        self.assertFalse(paired_shard_events(rows)[3])
    def test_same_cycle_parallel_starts_preserved(self):
        rows=[row(10,'start',i) for i in range(4)]+[row(100+i,'done',i) for i in range(4)]
        self.assertTrue(paired_shard_events(rows)[3])
    def test_partial_initial_done_set_rejected(self):
        self.assertFalse(paired_shard_events(self.sequence()[1:],True)[3])

if __name__=='__main__':
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CollectionTests))
    output=ROOT/'tmp/m357_collection_test_receipt.json'
    import json
    import m351_workflow as w
    w.atomic(output,w.encoded(dict(tests_run=result.testsRun,errors=len(result.errors),failures=len(result.failures),
        status='PASS_COLLECTION_NEGATIVE_CHECKS' if result.wasSuccessful() else 'FAIL_COLLECTION_NEGATIVE_CHECKS',
        source_sha256=w.sha(Path(__file__)),collector_sha256=w.sha(ROOT/'scripts/optimization/m356_collect_rtl.py'),
        uvm_evaluator_sha256=w.sha(ROOT/'scripts/optimization/m357_uvm_log_evidence.py'))),immutable=True)
    raise SystemExit(not result.wasSuccessful())
