"""Actual stdlib entry ordering and rejection, with explicit fake hardware import."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import m400_layer_entry_02 as entry
from m351_workflow import ROOT,BASE,encoded


class Tests(unittest.TestCase):
    def test_entry_before_all_gate_imports_and_no_import_on_rejection(self):
        source=ROOT/'deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
        frozen=(BASE/'runs/M400-source-compatibility-preparation-02/frozen_last_layer.py').read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m400') as d:
            stage=Path(d);(stage/'frozen_last_layer.py').write_bytes(frozen)
            # Deliberately poisonous target: no actual gate can import on rejection.
            (stage/'m400_tail_layer_gate.py').write_text("raise RuntimeError('UNAUTHORIZED_HARDWARE_IMPORT')\n",encoding='utf-8')
            rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(stage.iterdir())]
            manifest=stage/'PACKAGE_MANIFEST.json'
            manifest.write_bytes(encoded(dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
            digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
            with patch.object(entry,'HERE',stage),patch.object(entry,'SOURCE',source),patch.object(entry.sys,'argv',['entry',digest,'B1','--enable-tail-layer']):
                for fault in ('manifest','source','frozen','extra-file'):
                    with self.subTest(fault=fault):
                        with patch.object(entry.importlib.util,'spec_from_file_location',side_effect=AssertionError('Gate imported before source acceptance')) as imported:
                            if fault=='manifest':
                                with patch.object(entry.sys,'argv',['entry','0'*64,'B1','--enable-tail-layer']):
                                    with self.assertRaises(RuntimeError):entry.main()
                            elif fault=='source':
                                bad=stage/'wrong_source';bad.write_bytes(source.read_bytes()+b'\n')
                                # Outside package so package closure itself is still valid.
                                bad.unlink()
                                with patch.object(entry,'SOURCE',source.with_name('unavailable_source')):
                                    with self.assertRaises(FileNotFoundError):entry.main()
                            elif fault=='frozen':
                                (stage/'frozen_last_layer.py').write_bytes(frozen+b'\n')
                                with self.assertRaises(RuntimeError):entry.main()
                                (stage/'frozen_last_layer.py').write_bytes(frozen)
                            else:
                                (stage/'extra').write_bytes(b'x')
                                with self.assertRaises(RuntimeError):entry.main()
                                (stage/'extra').unlink()
                            imported.assert_not_called()
                with patch.object(entry.sys,'argv',['entry',digest,'B1']):
                    with self.assertRaises(RuntimeError):entry.main()
                proof=[];gate=SimpleNamespace(main=lambda:proof.append('FAKE_GATE_MAIN') or 0)
                def load(module):
                    proof.append('FAKE_GATE_IMPORT_AFTER_VALIDATION')
                spec=SimpleNamespace(loader=SimpleNamespace(exec_module=load))
                with patch.object(entry.importlib.util,'spec_from_file_location',return_value=spec),patch.object(entry.importlib.util,'module_from_spec',return_value=gate):
                    self.assertEqual(entry.main(),0)
                self.assertEqual(proof,['FAKE_GATE_IMPORT_AFTER_VALIDATION','FAKE_GATE_MAIN'])
        ast.parse(Path(entry.__file__).read_bytes(),feature_version=(3,10))


if __name__=='__main__':unittest.main()
