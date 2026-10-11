"""Exercise the actual runner's asset loader without importing Linux/PYNQ."""
import ast
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from measurement import sha256


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.package=self.root/'m181_m120_video_board_candidate'
        self.relative='text_auxiliary/tokenizer/tokenizer.json'
        self.path=self.package/self.relative
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{}')
        (self.package/'PACKAGE_MANIFEST.json').write_text(json.dumps(dict(files=[
            dict(path=self.relative,sha256=sha256(self.path))])))
        tree=ast.parse(Path(__file__).with_name('op01_board_sys.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='load_tokenizer')
        namespace=dict(ROOT=self.root,json=json,sha256=sha256)
        exec(compile(ast.Module(body=[function],type_ignores=[]),'actual_asset_loader','exec'),namespace)
        self.loader=namespace['load_tokenizer']

    def test_nested_path_loaded(self):
        calls=[]
        fake=SimpleNamespace(Tokenizer=SimpleNamespace(from_file=lambda p:calls.append(p)))
        with patch.dict('sys.modules',{'tokenizers':fake}):self.loader()
        self.assertEqual(calls,[str(self.path)])

    def test_flat_legacy_path_does_not_substitute(self):
        self.path.unlink()
        (self.package/'text_auxiliary/tokenizer.json').write_text('{}')
        fake=SimpleNamespace(Tokenizer=SimpleNamespace(from_file=lambda p:self.fail('Must not load wrong path')))
        with patch.dict('sys.modules',{'tokenizers':fake}),self.assertRaisesRegex(RuntimeError,'missing or hash mismatch'):
            self.loader()

    def test_modified_tokenizer_rejected(self):
        self.path.write_text('{"modified":true}')
        fake=SimpleNamespace(Tokenizer=SimpleNamespace(from_file=lambda p:self.fail('Must verify hash first')))
        with patch.dict('sys.modules',{'tokenizers':fake}),self.assertRaisesRegex(RuntimeError,'hash mismatch'):
            self.loader()

    def test_load_before_overlay(self):
        source=Path(__file__).with_name('op01_board_sys.py').read_text()
        self.assertLess(source.index("phase[0]='validate and load tokenizer before overlay'"),
                        source.index('board.__init__('))


if __name__=='__main__':unittest.main()
