"""Validate actual delta assembler and recovery alongside clean staging component."""
from m351_workflow import HERE,atomic
source=(HERE/'m417_support.py').read_text(encoding='utf-8')
source=source.replace('m417_workflow as','m417_workflow02 as').replace('m417_control.ps1','m417_control02.ps1').replace('m417_workflow.py','m417_workflow02.py').replace('m417_support.py','m417_support02.py').replace('tmp/m41701','tmp/m41702').replace('M417-layer13-reference-support-01','M417-layer13-reference-support-02').replace('latest_m417_reference_support','latest_m417_reference_support02').replace("'latest_m417_reference_board'","'latest_m417_reference_board02'").replace('M417-layer13-saved-reference-01/run_m417_reference.sh','M417-layer13-saved-reference-02/run_m417_reference.sh')
source=source.replace("    from m417_prepare import PKG","    PKG=workflow.PKG")
source=source.replace("assert checked['actual_packaged_entry']", "assert checked['new_actual_packaged_entry'] and checked['isolated_parent'] and checked['old_missing_dependency_reproduced'] and checked['no_developer_directory_on_child_path']")
source=source.replace("for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in m['files']]:","for name in ['PACKAGE_MANIFEST.json']+json.loads((pkg/'TRANSFER_FILES.json').read_bytes())['files']:")
anchor="        (receipts/'syntax.log').write_text('__M417_SYNTAX_RC_0__',encoding='utf-8')"
assert source.count(anchor)==1
assembly="""        # Execute the actual assembler, adapting only its two filesystem roots.
        import shutil
        from unittest.mock import patch
        old_packet=BASE/'candidates/M417-layer13-saved-reference-01'
        asmold=folder/'asmold';asmnew=folder/'asmnew'
        shutil.copytree(old_packet,asmold);asmnew.mkdir()
        names=['PACKAGE_MANIFEST.json']+json.loads((pkg/'TRANSFER_FILES.json').read_bytes())['files']
        for name in names:shutil.copyfile(pkg/name,asmnew/name)
        assembler=(pkg/'assemble_m417.py').read_text(encoding='utf-8')
        assert assembler.count('HERE=Path(__file__).resolve().parent')==1 and assembler.count("OLD=Path('/home/ubuntu/m417_layer13_reference_candidate_01')")==1
        fixture_code=assembler.replace('HERE=Path(__file__).resolve().parent','HERE=Path('+repr(str(asmnew))+')').replace("OLD=Path('/home/ubuntu/m417_layer13_reference_candidate_01')",'OLD=Path('+repr(str(asmold))+')')
        def execute_assembler():
            old_argv=sys.argv;sys.argv=['assemble_m417.py',digest];output=io.StringIO()
            try:
                with patch('os.geteuid',return_value=0,create=True),contextlib.redirect_stdout(output):exec(compile(fixture_code,str(pkg/'assemble_m417.py'),'exec'),dict(__name__='explicit_self_owned_assembler_fixture'))
            finally:sys.argv=old_argv
            return output.getvalue()
        assembly_text=execute_assembler()
        assert all(sha(asmnew/r['path'])==r['sha256'] for r in m['files'])
        (receipts/'assembly.log').write_text(assembly_text,encoding='utf-8')
        witness=asmold/'EXPECTED.json';saved=witness.read_bytes();witness.write_bytes(saved+b'corruption')
        try:execute_assembler()
        except RuntimeError:rejects+=1
        else:raise AssertionError('Corrupt old source accepted')
        witness.write_bytes(saved)
        extra=asmnew/'unexpected';extra.write_bytes(b'extra')
        try:execute_assembler()
        except RuntimeError:rejects+=1
        else:raise AssertionError('Unexpected staging file accepted')
        extra.unlink()
"""
source=source.replace(anchor,assembly+anchor)
source=source.replace("assert len(workflow.transfer(receipts,False)['files'])==m['file_count']+1","assert len(workflow.transfer(receipts,False)['files'])==len(names)")
source=source.replace('actual_default_off_export_save_capture_load=True,','actual_delta_assembler_with_filesystem_root_substitution_only=True,actual_default_off_export_save_capture_load=True,')
atomic(HERE/'m417_support02.py',source.encode('utf-8'),immutable=True)
print('M417_SUPPORT02_READY')
