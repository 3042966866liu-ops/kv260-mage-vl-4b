import unittest
from replay_io_summary import read_io_summary

def event():
    return dict(name='weight_file_read',failed=False,metadata=dict(process_io_delta=dict(rchar=20,read_bytes=10,minflt=1,majflt=0)))

class ReadSummaryTests(unittest.TestCase):
    def test_expected(self):
        result=read_io_summary([event(),event()],2)
        self.assertTrue(result['read_plan_accepted']);self.assertEqual(result['read_process_io']['read_bytes'],20)
    def test_extra_reads_retained_but_not_accepted(self):
        result=read_io_summary([event(),event()],1)
        self.assertFalse(result['read_plan_accepted']);self.assertEqual(result['read_plan_status'],'REQUIRES_PLAN_REVIEW')
        self.assertEqual(result['read_intervals'],2)
    def test_failed_or_invalid_not_summed(self):
        for field in ('failed','counter'):
            row=event()
            if field=='failed':row['failed']=True
            else:row['metadata']['process_io_delta']['read_bytes']=-1
            with self.assertRaises(ValueError):read_io_summary([row])

if __name__=='__main__':unittest.main()
