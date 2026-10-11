import unittest
from decode_io_trace import DecodeIOTrace

class IOTraceTests(unittest.TestCase):
    def test_counter_boundary_no_arithmetic_change(self):
        values=iter([dict(read_bytes=10,rchar=20),dict(read_bytes=14,rchar=30)])
        trace=DecodeIOTrace(snapshot=lambda:next(values))
        with trace.span('decode_call'):
            with trace.span('weight_file_read') as event:value=3+4
        self.assertEqual(value,7)
        self.assertEqual(event['metadata']['process_io_delta'],dict(read_bytes=4,rchar=10))
        self.assertEqual(trace.report()['status'],'RECORDED')
    def test_failed_read_remains_failed(self):
        trace=DecodeIOTrace(snapshot=lambda:dict(read_bytes=0))
        with self.assertRaises(ValueError):
            with trace.span('weight_file_read'):raise ValueError('short')
        self.assertTrue(trace.events[0]['failed'])

if __name__=='__main__':unittest.main()
