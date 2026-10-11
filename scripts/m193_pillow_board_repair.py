#!/usr/bin/env python3
"""Receive Pillow, repair the rejected M190 staging runtime, and rerun smoke."""

import argparse, hashlib, json, os, platform, shutil, socket, struct, subprocess, time
from pathlib import Path

ROOT = Path("/home/ubuntu/tellme_m120_m89x2_20260901")
PYTHON = Path("/usr/local/share/pynq-venv/bin/python")
PARTIAL = ROOT / "m190_mage_runtime.partial"
FINAL = ROOT / "m190_mage_runtime"
DELTA = ROOT / "m193_pillow_delta"
MAGIC = b"TELLME_M193_V1\n"
NAME = "pillow-12.1.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl"
SHA = "a40905599d8079e09f25027423aed94f2823adaf2868940de991e53a449e14a8"
SIZE = 6222593


def exact(sock, size):
    data = bytearray()
    while len(data) < size:
        block = sock.recv(size - len(data))
        if not block:
            raise RuntimeError("M193 early EOF")
        data.extend(block)
    return bytes(data)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".partial-{os.getpid()}")
    tmp.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(tmp, path)


def send_json(sock, value):
    payload = json.dumps(value, separators=(",", ":")).encode()
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = {"date":"2026-09-01","gate":"M193-M190-Pillow-ARM64-runtime-repair","status":"FAIL","classification":"Repair and runtime smoke only; not PS vision or FPGA video E2E evidence.","boot_dtb_cma_partitions_services_changed":False,"stable_rollback_preserved":True}
    connection = None
    try:
        if os.geteuid() != 0 or not PARTIAL.is_dir() or FINAL.exists() or DELTA.exists():
            raise RuntimeError("M193 exact rejected M190 staging state mismatch")
        DELTA.mkdir()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("192.168.0.2", 8769)); listener.listen(1); listener.settimeout(180)
            print("M193_BOARD_RECEIVER_READY bind=192.168.0.2 port=8769", flush=True)
            connection, peer = listener.accept()
        connection.settimeout(1800)
        if peer[0] != "192.168.0.10" or exact(connection, len(MAGIC)) != MAGIC:
            raise RuntimeError("M193 peer/protocol mismatch")
        metadata_size = struct.unpack("!I", exact(connection, 4))[0]
        metadata = json.loads(exact(connection, metadata_size))
        if metadata != {"name": NAME, "bytes": SIZE, "sha256": SHA}:
            raise RuntimeError(f"M193 wheel identity mismatch: {metadata}")
        wheel = DELTA / NAME
        h = hashlib.sha256(); remaining = SIZE
        with wheel.open("xb") as output:
            while remaining:
                block = connection.recv(min(4 << 20, remaining))
                if not block: raise RuntimeError("M193 wheel EOF")
                output.write(block); h.update(block); remaining -= len(block)
            output.flush(); os.fsync(output.fileno())
        if h.hexdigest() != SHA or sha256(wheel) != SHA:
            raise RuntimeError("M193 received wheel hash mismatch")
        pip = subprocess.run([str(PYTHON),"-m","pip","install","--no-index","--no-deps","--no-cache-dir","--no-compile","--upgrade","--target",str(PARTIAL),str(wheel)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
        result["pip_output_tail"] = pip.stdout[-6000:]
        if pip.returncode != 0: raise RuntimeError(f"M193 Pillow install failed rc={pip.returncode}")
        candidate = ROOT / "m181_m120_video_board_candidate"
        smoke = r'''
import importlib,json,os,platform,sys,types,torch,numpy,transformers,safetensors,tokenizers,huggingface_hub,pynq,PIL,PIL.Image
assert hasattr(PIL.Image,"Resampling") and PIL.__version__=="12.1.0"
torch.set_num_threads(4)
x=torch.arange(32,dtype=torch.float32).reshape(4,8)/32; w=torch.arange(64,dtype=torch.float32).reshape(8,8)/64
y32=torch.nn.functional.linear(x,w); ybf=torch.nn.functional.linear(x.to(torch.bfloat16),w.to(torch.bfloat16)).float()
assert torch.isfinite(y32).all() and torch.isfinite(ybf).all()
payload=os.path.join(os.environ["M193_CANDIDATE"],"ps_vision_payload"); name="m193_mage_payload"
package=types.ModuleType(name); package.__path__=[payload]; sys.modules[name]=package
importlib.import_module(name+".configuration_mage_vl"); importlib.import_module(name+".modeling_mage_vl")
print(json.dumps({"architecture":platform.machine(),"torch":torch.__version__,"transformers":transformers.__version__,"numpy":numpy.__version__,"Pillow":PIL.__version__,"safetensors":safetensors.__version__,"tokenizers":tokenizers.__version__,"huggingface_hub":huggingface_hub.__version__,"pynq":getattr(pynq,"__version__","present"),"bf16_max_abs_vs_fp32":float((y32-ybf).abs().max()),"mage_source_import":True}))
'''
        env=os.environ.copy(); env.update({"PYTHONPATH":str(PARTIAL),"PYTHONDONTWRITEBYTECODE":"1","TRANSFORMERS_OFFLINE":"1","HF_HUB_OFFLINE":"1","M193_CANDIDATE":str(candidate)})
        run=subprocess.run([str(PYTHON),"-c",smoke],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        result["smoke_output"] = run.stdout[-12000:]
        if run.returncode != 0: raise RuntimeError(f"M193 repaired runtime smoke failed rc={run.returncode}")
        smoke_json=json.loads(run.stdout.strip().splitlines()[-1])
        os.replace(PARTIAL,FINAL)
        result.update({"status":"PASS","peer":peer[0],"pillow_wheel_sha256":SHA,"isolated_site_packages":str(FINAL),"smoke":smoke_json,"free_bytes_after":shutil.disk_usage(ROOT).free,"next_gate":"Run only M192 fixed four-frame PS vision numerical gate."})
        send_json(connection,{"status":"PASS","pillow_wheel_sha256":SHA,"isolated_site_packages":str(FINAL)})
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"; result["next_gate"]="Repair and rerun only M193; do not run PS vision."
        if connection:
            try: send_json(connection,{"status":"FAIL","error":result["error"]})
            except OSError: pass
    finally:
        if connection: connection.close()
        result["total_ms"]=(time.monotonic()-started)*1000; atomic_json(args.result.resolve(),result)
    print("__M193_PILLOW_RESULT_BEGIN__",flush=True); print(json.dumps(result,separators=(",",":")),flush=True); print("__M193_PILLOW_RESULT_END__",flush=True)
    print("M193_PILLOW_RUNTIME_REPAIR_PASS" if result["status"]=="PASS" else "M193_PILLOW_RUNTIME_REPAIR_FAIL",flush=True)
    return 0 if result["status"]=="PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
