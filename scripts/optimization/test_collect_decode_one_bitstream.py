import unittest
from collect_decode_one_bitstream import check_route_gate


class RouteGateTests(unittest.TestCase):
    def test_positive(self):
        result = check_route_gate('build=0x4F503131 capacity_pass=false WNS=0.147 WHS=0.010 serious_drc=0\n')
        self.assertEqual(result['wns_ns'], 0.147)

    def test_reject_incomplete_or_wrong_candidate(self):
        for text in ('', 'build=0x4D395832 capacity_pass=false WNS=0.1 WHS=0.1 serious_drc=0',
                     'build=0x4F503131 capacity_pass=true WNS=0.1 WHS=0.1 serious_drc=0'):
            with self.assertRaises(ValueError):
                check_route_gate(text)

    def test_reject_bad_timing_or_drc(self):
        for wns, whs, drc in (('-0.01', '0.1', 0), ('0.1', '-0.01', 0),
                              ('nan', '0.1', 0), ('inf', '0.1', 0), ('0.1', '0.1', 1)):
            with self.assertRaises(ValueError):
                check_route_gate(f'build=0x4F503131 capacity_pass=false WNS={wns} WHS={whs} serious_drc={drc}')


if __name__ == '__main__':
    unittest.main()
