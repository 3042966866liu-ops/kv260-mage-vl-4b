"""Preserve this explicitly supplied video as separate demonstration development."""
import pathlib,json,hashlib,shutil,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2];HERE=pathlib.Path(__file__).resolve().parent
DATA=ROOT/'data/campus_demo_20261026'
OUT=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M539-campus12-demo-media-review-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    source=pathlib.Path('C:/Users/30429/Downloads/校园操场监控视频（刀具） (12).mp4')
    assert source.is_file() and not DATA.exists() and not OUT.exists()
    before=source.stat();d=sha(source)
    DATA.mkdir();OUT.mkdir(parents=True);target=DATA/'campus_12.mp4';shutil.copyfile(source,target)
    assert sha(target)==sha(source)==d and target.stat().st_nlink==1
    after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    payload=dict(status='HASH_PRESERVED_EXPLICIT_NEW_DEMO_VIDEO',source=str(source),workspace_source=target.relative_to(ROOT).as_posix(),
        bytes=target.stat().st_size,sha256=d,label=None,label_inferred_from_filename=False,
        purpose='2026-10-26 user designated this as one of the actual demo videos;another knife video expected later.',
        split='demo_development_not_independent_test',original_knife_train_test_contract_unchanged=True,
        heldout_opened=False,training_started=False,model_runs=0,board_commands=0)
    (DATA/'INTAKE.json').open('x',encoding='utf8').write(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    script=HERE/'decode.py';compile(script.read_text(encoding='utf8'),str(script),'exec')
    cmd=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B',
        '/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+script.relative_to(ROOT).as_posix()]
    (OUT/'START.json').open('x',encoding='utf8').write(json.dumps(dict(command=cmd,source_sha256=sha(script)),indent=2)+'\n')
    with (OUT/'stdout.raw').open('xb') as a,(OUT/'stderr.raw').open('xb') as b:rc=subprocess.run(cmd,stdout=a,stderr=b,timeout=180).returncode
    result=dict(status=('COMPLETE_CPU_DECODE_VISUAL_REVIEW_PENDING' if rc==0 else 'FAIL_CPU_VIDEO_DECODE'),host_rc=rc,
        intake_sha256=sha(DATA/'INTAKE.json'),decode_sha256=sha(OUT/'DECODE_RESULT.json') if (OUT/'DECODE_RESULT.json').exists() else None,
        stdout_sha256=sha(OUT/'stdout.raw'),stderr_sha256=sha(OUT/'stderr.raw'),model_runs=0,board_commands=0)
    (OUT/'HOST_RESULT.json').open('x',encoding='utf8').write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));print((OUT/'stdout.raw').read_text(encoding='utf8',errors='replace'))
    if rc:print((OUT/'stderr.raw').read_text(encoding='utf8',errors='replace'))
    return rc
if __name__=='__main__':raise SystemExit(main())
