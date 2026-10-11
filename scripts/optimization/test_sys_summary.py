import unittest
from summarize_sys_development import summarize


def fixture():
    generation=dict(status='PASS',cpu_linear_fallback=False,start_ns=0,end_ns=4000000000,
        top_level_stages=[dict(name='vision',start_ns=0,end_ns=1000000000),
                          dict(name='prefill',start_ns=1000000000,end_ns=3000000000),
                          dict(name='decode',start_ns=3000000000,end_ns=4000000000)],
        raw_token_events=[dict(kind='valid',ready_ns=3000000000),dict(kind='valid',ready_ns=4000000000)],
        output_tokens=2,ttft_s=3.0,decode_tps=1.0,valid_128_tokens=False)
    return dict(status='PROVISIONAL',fpga_execution_verified=True,boot_unchanged=True,cmdline_unchanged=True,
        cleanup=dict(buffers_released=True),request=dict(status='PASS',generation=generation),
        board_evidence=dict(host_calls=1,logical_calls=1,scale_retry_count=0),
        transactions=[dict(ap_return=0x4D395832,current=dict(family='q'),elapsed_ns=1000000)])


class SummaryTests(unittest.TestCase):
    def test_recomputes_raw_metrics_without_promotion(self):
        r=summarize(fixture());self.assertEqual(r['metrics']['ttft_s'],3)
        self.assertEqual(r['metrics']['decode_tps'],1);self.assertIsNone(r['achieved_level'])
        self.assertFalse(r['numerical_acceptance']);self.assertFalse(r['valid_128_tokens'])

    def test_failure_not_latency(self):
        r=summarize(dict(status='FAIL',elapsed_s=111,errors=['missing file']))
        self.assertIsNone(r['metrics'])

    def test_capture_not_performance(self):
        b=fixture();b['timing_eligible']=False
        self.assertIsNone(summarize(b)['metrics'])

    def test_overlap_and_counter_tampering_rejected(self):
        b=fixture();b['request']['generation']['top_level_stages'][1]['start_ns']=0
        with self.assertRaises(ValueError):summarize(b)
        b=fixture();b['board_evidence']['scale_retry_count']=1
        with self.assertRaises(ValueError):summarize(b)

    def test_one_token_has_no_decode_throughput(self):
        b=fixture();g=b['request']['generation'];g['raw_token_events']=g['raw_token_events'][:1]
        g.update(output_tokens=1,decode_tps=None)
        self.assertIsNone(summarize(b)['metrics']['decode_tps'])


if __name__=='__main__':unittest.main()
