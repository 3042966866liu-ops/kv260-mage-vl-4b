import copy
import unittest
from summarize_decode_trace import summarize


def record():
    def row(i,name,start,end,parent=None,thread=1,own=None):
        return dict(id=i,name=name,start_ns=start,end_ns=end,parent=parent,thread=thread,
                    inclusive_ns=end-start,exclusive_ns=end-start if own is None else own,
                    failed=False,metadata={})
    before=dict(cache_identity=1,layers=[dict(key_shape=[4,2,2],value_shape=[4,2,2])])
    after=dict(cache_identity=1,layers=[dict(key_shape=[5,2,2],value_shape=[5,2,2])])
    return dict(status='RECORDED',cache_before=before,cache_after=after,
                counter_delta=dict(host_calls=2,logical_calls=2,scale_retry_count=0),
                trace=dict(events=[row(0,'decode_call',0,100,own=40),
                    row(1,'wait',20,80,0),row(2,'pack',25,75,thread=2)]))


class SummaryTests(unittest.TestCase):
    def test_worker_not_double_counted(self):
        result=summarize(record())
        self.assertAlmostEqual(sum(result['main_thread_exclusive_s'].values()),100e-9)
        self.assertEqual(result['worker_exclusive_s_not_additive']['pack'],50e-9)
    def test_tampered_exclusive_rejected(self):
        data=record();data['trace']['events'][0]['exclusive_ns']=50
        with self.assertRaises(ValueError):summarize(data)
    def test_retry_and_cache_rejected(self):
        for field in ('counter','cache'):
            data=record()
            if field=='counter':data['counter_delta']['host_calls']=3
            else:data['cache_after']['layers'][0]['key_shape'][0]=6
            with self.assertRaises(ValueError):summarize(data)
    def test_failed_span_rejected(self):
        data=record();data['trace']['events'][1]['failed']=True
        with self.assertRaises(ValueError):summarize(data)


if __name__=='__main__':unittest.main()
