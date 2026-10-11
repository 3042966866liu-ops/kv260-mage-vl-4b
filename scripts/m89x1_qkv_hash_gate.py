#!/usr/bin/env python3
"""UART-staged M89-X1 layer-0 QKV full-output hash gate."""
from __future__ import annotations
import argparse, hashlib, json, sys, time
from pathlib import Path
import numpy as np

EXPECTED = {
 "model.language_model.layers.0.self_attn.q_proj":"c126c0aec84f437ebbce28372fe35aa63692bcda1d7dc5bb25dd780d459f5086",
 "model.language_model.layers.0.self_attn.k_proj":"0b6e089c071e7c082eb96f8bc8dafef53c88c3129f755119ae41c328d747cd12",
 "model.language_model.layers.0.self_attn.v_proj":"1d402f0405681a2420886c38ea4eda1ce4cafa12b0132097dd31bc79fea4eecd",
}

def main() -> int:
 p=argparse.ArgumentParser(); p.add_argument('--candidate',type=Path,required=True); p.add_argument('--result',type=Path,required=True); a=p.parse_args()
 root=a.candidate; sys.path.insert(0,str(root/'runtime'))
 from board_runtime import BUILD_ID,M89XBoardRuntime
 from contract_runtime import pack_chain_input
 out={"gate":"M89-X1-layer0-qkv-full-fp16-hash","status":"FAIL","base_package_manifest_sha256":"c4645fdf2ff1b299d3a7fb302fed72a8d50a95b658ad76e464c67a72a1a6cf50"}; runtime=None; began=time.monotonic()
 try:
  idx=np.arange(32*2560,dtype=np.float32).reshape(32,2560); values=(np.sin(idx*np.float32(.001))*np.float32(.25)).astype(np.float32)
  runtime=M89XBoardRuntime(root/'overlay/m89x_t32.bit',Path('/home/ubuntu/tellme_m89x_upload/m89y_language_fourport'),Path('/home/ubuntu/tellme_m89x_upload/m89z2_lmhead_w4_fourport'),root/'contracts/M89X_MERGED_RUNTIME_CONTRACT_RESULT.json',root/'contracts/M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json','staged-low-cma')
  chain=next(x for x in runtime.language_contract.chains if int(x['layer'])==0 and x['family']=='qkv')
  if hashlib.sha256(pack_chain_input(chain,values)).hexdigest()!='04457eb7f805ddb89bff1543e307844e7c6ccaa8f3593bbd18dda68cd23fa22f': raise RuntimeError('deterministic input hash mismatch')
  observed=runtime.language_family(0,'qkv',values); hashes={}
  for name,want in EXPECTED.items():
   value=observed.get(name)
   if value is None or not np.isfinite(value).all(): raise RuntimeError('invalid output '+name)
   got=hashlib.sha256(np.asarray(value,dtype='<f2').tobytes()).hexdigest()
   if got!=want: raise RuntimeError('full output hash mismatch '+name)
   hashes[name]=got
  proof=runtime.evidence()
  if proof['build_id']!=f'0x{BUILD_ID:08x}' or proof['host_calls']!=1: raise RuntimeError('build/call mismatch')
  out.update(status='PASS',build_id=proof['build_id'],evidence=proof,output_sha256_fp16=hashes)
 except Exception as e: out['error']=f'{type(e).__name__}: {e}'
 finally:
  if runtime is not None: runtime.close()
  out['total_ms']=(time.monotonic()-began)*1000; a.result.parent.mkdir(parents=True,exist_ok=True); a.result.write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out,indent=2))
 print('M89X1_QKV_HASH_GATE_PASS' if out['status']=='PASS' else 'M89X1_QKV_HASH_GATE_FAIL'); return 0 if out['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
