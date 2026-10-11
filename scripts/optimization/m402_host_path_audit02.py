"""Complete host path audit before any upload; no gate or serial execution."""
import ast
import contextlib
import io
import json
import tempfile
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m402_prepare_video import PKG,OLD
from m402_prepare_support import namespace

def main():
    prior=BASE/'runs/M402-tail-video-support-01/RESULT.json'
    assert prior.exists()
    workflow=(HERE/'m402_workflow.py').read_text(encoding='utf-8')
    assert "OLD=BASE/'candidates/M402-tail-text-02'" in workflow
    workflow=workflow.replace("OLD=BASE/'candidates/M402-tail-text-02'","OLD=BASE/'candidates/M401-tail-text-02'").replace('完整固定文本包传输核对','固定159视频包传输核对').replace('精确M402-01复制','精确M401-02复制')
    atomic(HERE/'m402_workflow02.py',workflow.encode('utf-8'))
    control=(HERE/'m402_control.ps1').read_text(encoding='utf-8').replace('m402_workflow.py','m402_workflow02.py')
    atomic(HERE/'m402_control02.ps1',control.encode('utf-8'))
    ast.parse(workflow,feature_version=(3,10))
    original=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    original_rows={r['path']:r for r in original['files']}
    delta=['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files'] if original_rows.get(r['path'])!=r]
    temp=ROOT/'tmp/m402/offline';temp.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp) as folder:
        fake_root=Path(folder);fake_base=fake_root/'deployment/mage_vl4b/optimization_v1'
        for source in (OLD,PKG):
            for p in source.iterdir():atomic(fake_base/'candidates'/source.name/p.name,p.read_bytes())
        logs=fake_root/'tmp/m402'
        for name in delta:
            p=PKG/name;count=(p.stat().st_size+899)//900;prefix='upload_'+name.replace('.','_')
            atomic(logs/(prefix+'_final.log'),('M212_CHUNKED_FILE_PASS '+sha(p)).encode('utf-8'))
            for i in range(1,count+1):atomic(logs/(prefix+f'_chunk_{i:05d}.log'),f'M212_CHUNK_PASS {i} {count} {min(i*900,p.stat().st_size)} fixture\n'.encode('ascii'))
        atomic(logs/'assembly_uart.log',('M402_ASSEMBLY_SHA_PASS '+sha(PKG/'PACKAGE_MANIFEST.json')+'\n__M402_ASSEMBLY_RC_0__\n').encode('ascii'))
        atomic(logs/'root_syntax_uart.log',b'__M402_SYNTAX_RC_0__\n')
        ns=namespace(HERE/'m402_workflow02.py');ns.update(ROOT=fake_root,BASE=fake_base,PKG=fake_base/'candidates/M402-tail-video-01',OLD=fake_base/'candidates/M401-tail-text-02')
        receipts=[]
        def sync_fixture(key,value,message):
            assert key=='latest_m402_tail_video_transfer'
            assert value['result']=='deployment/mage_vl4b/optimization_v1/runs/M402-tail-video-transfer-01/RESULT.json'
            assert sha(fake_root/value['result'])==value['sha256']
            saved=json.loads((fake_root/value['result']).read_bytes())
            assert saved['old_manifest_sha256']==sha(OLD/'PACKAGE_MANIFEST.json') and saved['board_gate_started'] is False
            assert [r['path'] for r in saved['new_files']]==delta
            assert '精确M401-02复制' in message and '159视频' in message
            receipts.append(value)
        ns['sync']=sync_fixture
        with contextlib.redirect_stdout(io.StringIO()):ns['transfer']()
        assert len(receipts)==1
        # Omitted receipt is fail-closed, without creating a new transfer result.
        (logs/(delta[0].replace('.','_').join(['upload_','_final.log']))).unlink()
        try:ns['transfer']()
        except (RuntimeError,OSError):pass
        else:raise AssertionError('Missing real workflow receipt accepted')
    # Actual entry default-off / complete source check and rejection before imports.
    entry=namespace(PKG/'m402_video_entry.py')
    entry['SOURCE']=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    before=[]
    class RejectImports:
        @staticmethod
        def spec_from_file_location(*args):before.append(args);raise AssertionError('Gate import must not occur')
    entry['importlib']=type('ExplicitFakeImportlib',(),{'util':RejectImports})()
    class Args:argv=['entry',sha(PKG/'PACKAGE_MANIFEST.json'),'B1']
    entry['sys']=Args
    try:entry['main']()
    except RuntimeError:pass
    else:raise AssertionError('Entry enabled by omitted flag')
    assert not before
    Args.argv=['entry','0'*64,'B1','--enable-tail-video']
    try:entry['main']()
    except RuntimeError:pass
    else:raise AssertionError('Wrong manifest accepted')
    assert not before
    # Pin both actual controller and workflow filesystem inventories, not just names.
    assert "$remote='/home/ubuntu/m402_tail_video_candidate_01'" in control
    assert 'candidates/M401-tail-text-02/PACKAGE_MANIFEST.json' in control
    for name in ('m402_assemble.py','m402_export_result.py','run_m402_tail_video.sh'):assert name in control and (PKG/name).exists()
    assert "from m402_collect import collect" in workflow
    support=json.loads(prior.read_bytes())
    value=dict(support,prior_support_sha256=sha(prior),host_path_repair_only=True,
        rejected_offline_attempts=['Windows Path string assertion corrected to as_posix; no package change','Actual host workflow prior package typo M402-tail-text-02 caught before upload; new host02 uses exact M401-tail-text-02'],
        actual_workflow_transfer_and_receipt_destination=True,missing_receipt_rejected=True,actual_entry_default_off_and_wrong_manifest_pre_import=True)
    sources=['m402_host_path_audit02.py','m402_workflow02.py','m402_control02.ps1','m402_collect.py','m402_count_scope.py','m398_collect.py','test_m402_count_scope.py','test_m402_video_wrapper.py']
    value['source_sha256']={n:sha(HERE/n) for n in sources}
    value['controller']='scripts/optimization/m402_control02.ps1';value['board_run']=False
    out=BASE/'runs/M402-tail-video-support-02/RESULT.json';atomic(out,encoded(value),immutable=True)
    report=f'''# M402 固定159视频门禁准备

不可变包 manifest `{value['manifest_sha256']}`，47载荷/852374B。前级M401固定文本已闭合，复用M398同输入视频和M400末层参考；候选预计766逻辑/767模型物理加最小事务768，少12个T32批次，保留一次缩放重试。尚未板端验证，预计计数不代表实际结果。

11项实际冻结wrapper/stream CPU检查、20项严格回收拒绝、源码检查先于硬件导入、精确旧包assembly、保存目标/同步顺序、自测控制失败必收集已通过。Linear/Attention/内存/MMIO/模型结果是明确替身；47同SHA硬件证据复用。

补充实际workflow执行的假UART文件回执检查发现旧包路径标签错误，已在新主机02文件修正。原01支持/代码和47载荷包保持；主机02按真实目录验证差分、所有分块回执、原子transfer目标和BOARD键，再核对缺失回执拒绝。Windows路径字符串检查仅改为as_posix。没有上传/资源或硬件重跑。

当前唯一板端阻塞：COM3已在shell，`sudo -n true`返回1需要密码，尚未上传或启动。使用`m402_control02.ps1`，用户续期后上传；已有执行日志或板端结果只能Collect。固定159原最后帧两视图、完整视觉/KV/logits/判断比较，全七DMA封锁与普通1GiB+64MiB预算保持，生产64MiB政策不变。双worker/PS预读/SiLU关闭。视频数值闭合后才单独准备性能，不重复旧八次对照。

支持原SHA `{sha(out)}`。裁剪候选尚无视频数值或新增性能PASS；旧并行核40.81%收益结论保持。
'''
    atomic(out.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m402_tail_video_support',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),f'## M402 实际主机transfer路径补充核对02（2026-10-04）\n\n{sha(out)}；不可变47载荷包保持。实际workflow假UART全部回执/旧M401-02 manifest/原子目标/BOARD键/缺失拒绝及stdlib入口default-off/错SHA先拒绝通过；主机02修旧包路径标签与记录文案，原01保留。11组件/20回收与已过SelfTest复用，无板端执行。只使用m402_control02.ps1继续；COM3 sudo需续期，固定159数值尚未执行。')
    # Persist the actual authorization attempt; never rerun it here.
    log=ROOT/'tmp/m402/authorization_precheck_01.log';text=log.read_text(encoding='utf-8-sig')
    assert '__M402_AUTH_RC_1__' in text and 'a password is required' in text
    auth=dict(status='BLOCKED_SAME_TERMINAL_SUDO',log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),shell_confirmed=True,sudo_rc=1,uploaded=False,overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,next_step='Wait for operator sudo-v recovery; no repeated check or password guessing.')
    p=BASE/'runs/M402-authorization-precheck-01/RESULT.json';atomic(p,encoded(auth),immutable=True)
    sync('latest_m402_authorization',dict(status=auth['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p)),f'## M402 固定视频上传前授权阻塞（2026-10-04）\n\n{sha(p)}；COM3 shell已确认，sudo原rc1需要密码。上传0/Overlay0/模型0/FPGA0；新视频包与支持02准备完成，等待人工同COM3续期，不能反复检查或猜密码。前级文本PASS及稳定恢复保持，无新增板端资源。')
    print(json.dumps(dict(status='PASS_HOST02_REAL_WORKFLOW_PATH_AUDIT_WAITING_SUDO',sha256=sha(out),board_run=False,controller=value['controller'])))

if __name__=='__main__':main()
