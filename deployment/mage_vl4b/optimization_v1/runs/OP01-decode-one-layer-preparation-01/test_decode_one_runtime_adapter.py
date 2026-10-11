import unittest
from types import SimpleNamespace
import numpy as np
from decode_one_runtime_adapter import runtime_class


class Parent:
    def __init__(self): self.configs = []
    def _program_static_registers(self, chain, buffers): self.configs.append(chain['config_u32'])
    def language_family_many(self, layer, family, values):
        chain = dict(config_u32='0x10428')
        self._program_static_registers(chain, [])
        self._program_static_registers(chain, [])  # same path for finite retry
        return chain
    def _execute(self, chain, values, buffers, offset=0):
        self._program_static_registers(chain, buffers)
        return chain
    def evidence(self): return dict(expected_macros=123)


class AdapterTests(unittest.TestCase):
    def make(self): return runtime_class(Parent, SimpleNamespace(BUILD_ID=0x4F503131))()
    def test_stable_rejected(self):
        with self.assertRaises(ValueError): runtime_class(Parent, SimpleNamespace(BUILD_ID=0x4D395832))
    def test_language_and_retry_config(self):
        obj = self.make(); chain = obj.language_family_many(0, 'q', np.zeros((1,2560)))
        self.assertEqual(chain['config_u32'], '0x10428')
        self.assertEqual(obj.configs, ['0x1010428']*2)
        self.assertFalse(obj._decode_scope)
    def test_lm_head(self):
        obj = self.make(); chain = dict(config_u32='0x10428')
        obj._execute(chain, np.zeros((1,2560)), [])
        self.assertEqual(obj.configs, ['0x1010428'])
        self.assertEqual(chain['config_u32'], '0x10428')
    def test_multi_token_rejected_before_registers(self):
        obj = self.make()
        with self.assertRaises(ValueError): obj.language_family_many(0,'q',np.zeros((2,2560)))
        self.assertEqual(obj.configs, [])
    def test_unscoped_register_rejected(self):
        obj = self.make()
        with self.assertRaises(RuntimeError): obj._program_static_registers(dict(config_u32='0x10428'), [])
    def test_failure_clears_scope(self):
        obj = self.make()
        with self.assertRaises(ValueError): obj._execute(dict(config_u32='0xFFFFFFFF'),np.zeros((1,2560)),[])
        self.assertFalse(obj._decode_scope)


if __name__ == '__main__': unittest.main()
