"""Freeze source/ownership/budget audit, never touch board or production."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import textwrap
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m376_gate_up_workers import PINNED

OUT=BASE/'runs/M376-gate-up-worker-audit-01'
def main():
    if OUT.exists():raise RuntimeError('Immutable audit already exists')
    state={n:(ROOT/n).read_text(encoding='utf-8-sig') for n in
           ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    recovery={n:dict(sha256=sha(ROOT/n),chars=len(t)) for n,t in state.items()}
    board=json.loads(state['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    prior={}
    for key in ('latest_m375_video_wait_closure','latest_m369_light_video_closure'):
        row=board[key];assert sha(ROOT/row['result'])==row['sha256']
        assert all(row['sha256'] in state[n] for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        prior[key]=row['sha256']
    source=json.loads((BASE/'candidates/M369-light-video-01/SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    verified=[]
    for r in source['files']:
        assert sha(release/r['path'])==r['sha256'];verified.append(dict(path=r['path'],sha256=r['sha256']))
    methods={}
    for module,names in [('m238_prefill_runtime',['language_family_many']),
        ('m236_prefill_runtime',['_resolve_pending','_parse_buffer','_parse_into_and_check']),
        ('m230_prefill_runtime',['_record_phase'])]:
        p=release/source['modules'][module];t=p.read_text(encoding='utf-8');tree=ast.parse(t)
        for name in names:
            n=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
            normalized=textwrap.dedent('\n'.join(t.splitlines()[n.lineno-1:n.end_lineno])).strip()
            digest=hashlib.sha256(normalized.encode()).hexdigest();assert digest==PINNED[name]
            methods[name]=dict(file=str(p.relative_to(ROOT)),source_sha256=digest)
    scan=subprocess.run(['rg','--files','-g','*.py','-g','!**/backups/**','-g','!**/state_before_update/**',
        '-g','!**/__pycache__/**','scripts','deployment/mage_vl4b','release_staging','tmp'],cwd=ROOT,
        capture_output=True,text=True,encoding='utf-8',check=True)
    hits=[];two=[];count=0
    for name in scan.stdout.splitlines():
        p=ROOT/name
        if 'm376' in name.lower():continue
        try:t=p.read_text(encoding='utf-8-sig')
        except UnicodeError:continue
        count+=1
        for i,line in enumerate(t.splitlines(),1):
            if re.search(r'ThreadPoolExecutor\s*\(|max_workers\s*=',line) and ('parse' in t or 'gate_up' in t):
                hits.append(dict(file=name,line=i,text=line.strip(),file_sha256=sha(p)))
            if re.search(r'max_workers\s*=\s*2\b',line) and ('m238-parse' in t or 'm236-parse' in t):
                two.append(dict(file=name,line=i,text=line.strip()))
    contract=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
    chains=json.loads(contract.read_text(encoding='utf-8'))['chains'];gate=[c for c in chains if c['family']=='gate_up']
    largest=max(gate,key=lambda c:c['output_bytes']);descriptor=max(d['output_bytes'] for c in gate for d in c['descriptors'])
    fixture=dict(chain=largest,contract_sha256=sha(contract),gate_up_chain_count=len(gate))
    atomic(OUT/'GATE_UP_FIXTURE.json',encoded(fixture),immutable=True)
    result=dict(status='PASS_OFFLINE_GATE_UP_TWO_WORKER_AUDIT',target_build_id='0x4D333537',
        prior_sha256=prior,recovery=recovery,verified_release_sources=verified,pinned_methods=methods,
        old_source_files_scanned=count,parse_executor_sites=hits,old_literal_two_parse_worker_sites=two,
        identical_attempt_found=bool(two),git_history_available=(ROOT/'.git').exists(),
        ownership=['Original two DMA slots; same-slot pending.future.result and all finite retries before overwrite',
          'Each T32 block writes disjoint token rows in shared final targets; descriptors keep original row slices',
          'Both parser jobs and synchronous retry together have at most two live parsers; retry does not submit a new future',
          'Only foreground resolves shifts, counters and retry records; parse timing counters lock around updates',
          'Original executor contexts join on success/error; hung worker retains call, buffers and process'],
        memory=dict(extra_dma_bytes=0,extra_final_targets_bytes=0,maximum_descriptor_output_bytes=descriptor,
                    extra_parser_array_bound_bytes=6*descriptor+descriptor//4,extra_parser_workers=1,
                    native_thread_and_allocator_peak_unproven=True,diagnostic_budget_unchanged=True,
                    production_64mib_policy_unchanged=True),
        fixture_sha256=sha(OUT/'GATE_UP_FIXTURE.json'),source_sha256=sha(HERE/'m376_gate_up_workers.py'),
        local_tests_passed=12,scope='Source/CPU-only audit; no board or FPGA or new performance result',
        rejected_attempts=['Source-drift negative originally escaped as StopIteration; normalized-source reject fixed before packaging',
           'Initial largest-shape fixture used64-wide inputs and reference retained overlap barrier; test fixtures corrected before packaging'],
        next_step='Freeze and execute isolated CPU component on actual board Python; then one representative gate_up family, layer, fixed text, original video numerical gates; only then current one versus two-worker lightweight balanced request performance. Close if no net benefit, no thread-count scan.')
    if two:raise RuntimeError('Identical old parse width found; inspect before new experiment')
    atomic(OUT/'RESULT.json',encoded(result),immutable=True);digest=sha(OUT/'RESULT.json')
    report=f'''# M376 gate_up 双解析 worker 审计

目标Build0x4D333537，沿用已验证并行核；只在gate_up把解析线程池宽度1改为2，其他family原调用保持。双DMA缓冲、原解析算法、缩放重试、pack线程和输出所有权不变。原M36940.81%性能结论保持，新变体尚无板端数值或净收益。

核对实际发布SOURCE_CLOSURE全部{len(verified)}份源码同SHA，冻结M238/M236/M230五个方法；搜索{count}份现存源码、旧候选和tmp，未发现m238/m236解析池max_workers=2的同类尝试。此目录无Git历史，不能证明未保存历史分支无人尝试。M332是解析算法改动，仍单worker，不复用它。

当前两个任务写不同T32 token行；同输出槽先等Future并完成所有重试，才允许DMA覆写。同步重试仍主线程，另一输出槽可继续解析；活跃解析至多两个。阶段parse统计用短锁更新，解析计算不持锁；计数/缩放记录原前台顺序不变。executor上下文在错误退出也join，卡住时保留进程/缓冲，不超时kill/free。

36个gate_up chain最大descriptor输出{descriptor}B，源码保守额外数组上界6倍descriptor加有限性bool约{(6*descriptor+descriptor//4)/(1<<20):.4f}MiB；0额外CMA及最终targets。线程栈/NumPy原生内存、DDR竞争未实测，仍沿原独立诊断RSS和MemAvailable停止规则，生产64MiB不改。

12项Windows CPU检查通过：真实冻结解析/Future、尾块1/17/32/33/64/65/159、双输出并发、逐位原解析参考、两块非有限重试、DMA复用保护、另一parser活动时同步重试、强制统计交错、异常join/绑定恢复、重复请求与非gate_up保持。显式fake DMA/权重/数据；不能当板端模型数值或性能。

下一步板端CPU组件→代表gate_up family→单层→固定文本→原固定159视频数值。未改电路的硬件Build/descriptor证据复用；改变PS调度的数值范围逐级核对。通过全部数值后，用同一当前并行核、同输入、同轻量计时比较单worker与双worker；A-B-B-A及B-A-A-B，原请求每次计时后完整数值核对。无净收益则关闭此变体，不扫描更多线程数。

证据SHA {digest}。
'''
    atomic(OUT/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m376_gate_up_worker_audit',dict(status=result['status'],result=(OUT/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,board_run=False,performance_pass=False),
         f'## M376 gate_up双解析worker源码/所有权审计（2026-10-03）\n\n当前0x4D333537仅gate_up解析池1→2，原parser/双输出/重试/pack不变，parse统计短锁；{count}现存源码搜索未发现相同尝试，Git历史不可用。额外解析数组保守{(6*descriptor+descriptor//4)/(1<<20):.4f}MiB/额外CMA0，native线程峰值未证；12项Windows真实冻结parser/Future显式fake DMA检查通过，初始测试fixture/源码异常类型修正已记录。审计SHA {digest}。未上板/性能/服务晋级；原M36940.81%保持。下一步板端CPU组件及逐级数值，最后当前单/双worker完整请求交错，无净收益关闭、不扫描线程数。')
    print(json.dumps(dict(status=result['status'],sha256=digest,scanned=count,array_bound_bytes=6*descriptor+descriptor//4)))

if __name__=='__main__':main()
