"""Accept quiet UVM logs only with source-backed, unsuppressed error macros."""
import hashlib
import re
from pathlib import Path

VENDOR=Path('D:/AMDDesignTools/2026.1/Vivado/data/system_verilog/uvm_1.2/xlnx_uvm_package.sv')

def evaluate(directory,log):
    error_rows=re.findall(r'(?m)^\s*UVM_(?:ERROR|FATAL)\b[^\r\n]*',log)
    counts=re.findall(r'UVM_(ERROR|FATAL)\s*:\s*(\d+)\b',log)
    source_rows=[];overrides=[];direct_calls=[]
    for p in sorted(directory.rglob('*')):
        if not p.is_file() or p.suffix not in ('.v','.sv','.vh','.svh') or 'xsim.dir' in p.parts:continue
        raw=p.read_bytes();text=raw.decode('utf-8-sig')
        # Conservative: even a suspicious commented report override is rejected.
        if re.search(r'\bset_(?:report_\w*action|severity_\w*|id_action)|\buvm_report_(?:catcher|cb)|\bset_report_server',text):overrides.append(str(p))
        if re.search(r'(?<!`)\buvm_report_(?:error|fatal)\s*\(',text):direct_calls.append(str(p))
        source_rows.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest()))
    text=VENDOR.read_text(encoding='utf-8')
    vendor_checks=[
        'uvm_report_error (ID, MSG, UVM_NONE' in text,
        'uvm_report_fatal (ID, MSG, UVM_NONE' in text,
        'set_severity_action(UVM_ERROR,   UVM_DISPLAY | UVM_COUNT)' in text,
        'set_severity_action(UVM_FATAL,   UVM_DISPLAY | UVM_EXIT)' in text,
        '`uvm_info("UVM/REPORT/SERVER",`UVM_STRING_QUEUE_STREAMING_PACK(q),UVM_LOW)' in text]
    summary_present=all(any(k==s for k,_ in counts) for s in ('ERROR','FATAL'))
    # Severity-count summary rows are not emitted error reports themselves.
    emitted=[r for r in error_rows if not re.match(r'^\s*UVM_(ERROR|FATAL)\s*:\s*\d+\s*$',r)]
    clean=not emitted and all(int(n)==0 for _,n in counts) and not overrides and not direct_calls and all(vendor_checks)
    return clean,dict(summary_counts_present=summary_present,summary_counts=counts,emitted_error_rows=emitted,
        source_audit_no_report_suppression=not overrides,source_audit_all_error_calls_use_none_verbosity_macros=not direct_calls,
        override_files=overrides,direct_call_files=direct_calls,vendor_checks=vendor_checks,
        vendor_source=str(VENDOR),vendor_sha256=hashlib.sha256(VENDOR.read_bytes()).hexdigest(),sources=source_rows,
        interpretation='UVM_LOW summary is suppressed by UVM_NONE. Generated error/fatal macros use UVM_NONE with default DISPLAY actions; no suppression/catchers/direct LOW error calls in frozen source. Zero emitted errors; absent summary counts are not claimed as directly observed counters.')
