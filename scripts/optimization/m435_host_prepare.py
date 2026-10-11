"""Strict saved-byte collector and versioned COM3 control; no board execution."""
from m351_workflow import HERE, atomic
from m427_prepare import once


def main():
    w = (HERE/'m433_workflow.py').read_text(encoding='utf-8').replace('M433','M435').replace('m433','m435')
    w = w.replace('M435-late11-complete-request-warm-01','M435-weight-read-observation-01').replace('M435-warm-performance-board-01','M435-IO-observation-board-01')
    w = w.replace('controlled-warm-complete-request-performance','fixed-BB-file-IO-residency-diagnostic').replace('PASS_M435_CONTROLLED_WARM_MEASUREMENTS_COLLECTED','PASS_M435_BB_IO_DIAGNOSTIC')
    w = w.replace("'all12_requests_completed','performance_measurements_collected'", "'all2_requests_completed','observer_checked_before_overlay','io_observer_hooks_restored'")
    w = w.replace(",'warm_conditions_established'", '')
    w = w.replace("r['vision_forward_calls']!=12 or r['model_forward_calls']!=12", "r['vision_forward_calls']!=2 or r['model_forward_calls']!=2")
    w = w.replace("r['fpga_transactions']!=11089 or r['host_calls']!=9372 or r['logical_calls']!=9336 or r['completed_language_physical']!=9372 or r['completed_visual_physical']!=1716", "r['fpga_transactions']!=2135 or r['host_calls']!=1562 or r['logical_calls']!=1556 or r['completed_language_physical']!=1562 or r['completed_visual_physical']!=572")
    start = w.index('        from m425_warm import ORDER,WarmSequence')
    end = w.index("        board=json.loads", start)
    w = w[:start]+"        samples=r['samples']\n        if len(samples)!=2 or ''.join(s['variant'] for s in samples)!='BB' or r['diagnostic_order']!='BB' or r['timings_not_performance'] is not True or r['performance_measurements_collected'] is not False:raise ValueError('Fixed diagnostic scope differs')\n"+w[end:]
    w = once(w, "        sequence=WarmSequence({},r['warm_environment_reference'],clock=lambda:0,protocol_sha=protocol_sha)\n", '')
    w = once(w, '            sequence.before(i);sequence.record(s)\n', '')
    w = once(w, "        proof=r['same_overlay_minimal_proof']", """        observation=json.loads((PKG/'OBSERVATION_PLAN.json').read_bytes())
        obs=r['read_observation']
        if obs['cache_eviction'] is not False or obs['additional_weight_cache'] is not False:raise ValueError('Unexpected cache manipulation')
        expected=[{k:x[k] for k in ('group','path','offset','bytes')} for x in observation['expected_reads']]
        for n in (1,2):
            rows=[x for x in obs['reads'] if x['request']==n]
            if [{k:x[k] for k in ('group','path','offset')}|dict(bytes=x['returned_bytes']) for x in rows]!=expected:raise ValueError('Actual file read contract differs')
            if any(x['requested_bytes']!=x['returned_bytes'] or x['elapsed_ns_diagnostic']<0 or x['io']['read_bytes']<0 for x in rows):raise ValueError('Read interval invalid')
        if len(obs['reads'])!=1472 or not obs['decodes'] or len(obs['snapshots'])!=6:raise ValueError('Narrow observation incomplete')
        from m435_io_observer import residency_change
        for n in (1,2):
            snapshots=[x for x in obs['snapshots'] if x['request']==n]
            if [x['label'] for x in snapshots]!=observation['mincore_boundaries']:raise ValueError('Residency boundaries differ')
            for a,b in zip(snapshots,snapshots[1:]):
                if len(a['files'])!=12 or len(b['files'])!=12 or [x['path'] for x in a['files']]!=sorted(x['path'] for x in observation['files']):raise ValueError('Residency file set differs')
                for x,y in zip(a['files'],b['files']):residency_change(x,y)
        probe=r['linux_residency_probe'];tests=r['observer_component_tests']
        if probe['sparse_initial_resident']!=0 or probe['buffered_write_resident']<=0 or not probe['fixture_removed'] or not probe['first_page_observed'] or not probe['maps_and_fds_closed']:raise ValueError('Linux probe unproven')
        if tests['run']!=15 or tests['skipped'] or tests['success'] is not True:raise ValueError('Board pre-resource observer tests failed')
        proof=r['same_overlay_minimal_proof']""")
    w = w.replace("latest_m435_warm_board", "latest_m435_IO_board").replace("M435 完整暖请求原始测量", "M435 固定两个B窄文件I/O观察").replace('固定四预热和八正式完整请求','固定两个B诊断请求').replace('latest_m435_performance_transfer','latest_m435_IO_transfer').replace('M435-performance-transfer-01','M435-IO-transfer-01')
    w = w.replace('candidates/M432-late11-integrated-video-02/PACKAGE_MANIFEST.json','candidates/M433-late11-complete-request-warm-01/PACKAGE_MANIFEST.json')
    w = w.replace('温度读取关闭，预定最多12请求及独立数值、DMA生命周期核对；失败不追加/不硬件重跑。三记录同步后才按预定八正式样本统计裁决，非生产晋级。', '固定两个B诊断请求，文件窗口和12文件驻留快照；原数值/七DMA释放，失败只回收不重跑。不要求零I/O、不做性能或晋级、不测温。')
    w = w.replace('原始门禁只证明预定测量/数值/释放；净收益另按冻结协议裁决，不扩层或晋级。','只用于读取与驻留归因；所有计时含观察器开销，不作性能裁决，不扩层或晋级。')
    atomic(HERE/'m435_workflow.py',w.encode('utf-8'),immutable=True)
    control=(HERE/'m433_control03.ps1').read_text(encoding='utf-8').replace('M433','M435').replace('m433','m435')
    control=control.replace('M435-late11-complete-request-warm-01','M435-weight-read-observation-01').replace('/home/ubuntu/m435_late11_warm_candidate_01','/home/ubuntu/m435_weight_read_candidate_01').replace('M435-warm-performance-board-01','M435-IO-observation-board-01')
    start=control.index('foreach ($key in @(');end=control.index('foreach ($row in $manifest.files)',start)
    control=control[:start]+"""foreach ($key in @('latest_m434_read_path_audit','latest_m432_integrated_board','latest_m435_IO_preparation','latest_m435_IO_support')) { VerifyEvidence $key }
$support=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m435_IO_support.result) | ConvertFrom-Json
if ($support.manifest_sha256 -ne $digest) { throw 'Support package differs' }
foreach ($p in $support.source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Supported host source differs' }
}
"""+control[end:]
    control=control.replace('candidates/M432-late11-integrated-video-02/PACKAGE_MANIFEST.json','candidates/M433-late11-complete-request-warm-01/PACKAGE_MANIFEST.json')
    control=control.replace('latest_m435_performance_transfer','latest_m435_IO_transfer').replace('-TimeoutSeconds 4200','-TimeoutSeconds 2100').replace('-TimeoutSeconds 1080','-TimeoutSeconds 1080')
    atomic(HERE/'m435_control.ps1',control.encode('utf-8'),immutable=True)
    print('M435_HOST_READY')


if __name__=='__main__':main()
