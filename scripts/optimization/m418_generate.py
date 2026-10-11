"""Generate layer13 lower gates; original Build, packet math and ownership retained."""
from m351_workflow import HERE,BASE,atomic

def replace(source,a,b):
    if a not in source:raise RuntimeError('Missing source anchor '+a)
    return source.replace(a,b)

def main():
    # Host modules are generated now; package preparation requires M417 PASS first.
    for old in ('m410_probe.py','m410_saved_case.py','m410_export.py','m410_workflow.py','m410_control.ps1','m410_support.py','test_m410_component.py','m410_prepare.py'):
        new=old.replace('m410','m418')
        source=(HERE/old).read_text(encoding='utf-8').replace('M410','M418').replace('m410','m418').replace('latest_m409_reference_','latest_m417_reference_').replace('PASS_M409_SAVED_MLP_EXACT_SOFTWARE_REFERENCE','PASS_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE').replace('m409_mlp_reference_01','m417_layer13_reference_01').replace('第12层','第13层').replace('原M409','原M417').replace('同M409','同M417')
        if old=='m410_probe.py':
            source=replace(source,'required_cma_free_bytes=64<<20','required_cma_free_bytes=0')
            source=replace(source,"        if row['CmaFree']<64<<20:raise MemoryError('Allocated real CMA reserve below64MiB')","        if row['CmaFree']<0:raise RuntimeError('Invalid actual CMA counter')")
        if old=='m410_workflow.py':
            source=replace(source,"x['required_cma_free_bytes']!=64<<20 or x['CmaFree']<64<<20","x['required_cma_free_bytes']!=0 or x['CmaFree']<0")
        if old=='m410_support.py':
            source=replace(source,'required_cma_free_bytes=64<<20','required_cma_free_bytes=0')
            source=replace(source,"x['memory'][3]['CmaFree']=32<<20","x['memory'][3]['CmaFree']=-1")
        if old=='test_m410_component.py':
            source=replace(source,"CmaFree=(32 if failure=='memory-fail' else 256)<<20,MemAvailable=1<<30","CmaFree=0,MemAvailable=(64<<20 if failure=='memory-fail' else 1<<30)")
        if old=='m410_prepare.py':
            source=replace(source,'encoder.layers.12.mlp.','encoder.layers.13.mlp.')
            # Freeze the actual selected shift instead of assuming layer12's shift6.
            source=replace(source,"assert first['selected_shift']==6 and first['start']==0","assert 0<=first['selected_shift']<=first['initial_shift']<=6 and first['start']==0")
            source=replace(source,'chain=chain,shift=6,windows=windows','chain=chain,shift=first[\'selected_shift\'],windows=windows')
            source=replace(source,'真实保存/原pack与七项明确fake DMA生命周期、损坏拒绝及资源前容量拒绝通过','真实保存/原pack与七项明确fake DMA生命周期、损坏拒绝和普通PS容量停止通过；诊断取消固定CMA64MiB floor，实际分配失败停止，DMA安全和生产政策保持')
        if old=='m410_control.ps1':
            anchor='        Write-Output "M418_FILE_TRANSFERRED $name"'
            source=replace(source,anchor,anchor+'''\n        & $uart -Command 'sudo -n true' -LogPath "tmp/m41801/sudo_transfer_$($name.Replace('.','_')).log" -TimeoutSeconds 15 -MarkerPrefix '__M418_SUDO_RC_'
        if (-not $?) { throw 'Sudo expired; stop transfer without retry' }''')
        atomic(HERE/new,source.encode('utf-8'),immutable=True)
    print('M418_HOST_MODULES_READY_PACKAGE_REQUIRES_M417_PASS')

if __name__=='__main__':main()
