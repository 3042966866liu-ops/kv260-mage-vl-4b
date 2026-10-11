"""Run the unchanged M277 gate with a bounded language-Prefill tracer."""
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True

import board_runtime
import m276_video_runtime
import m277_fixed_window_gate
from board_safety import safe_to_release
from decode_io_trace import DecodeIOTrace
from prefill_diagnostic import PrefillDiagnostic

ORIGINAL_RUNTIME = m276_video_runtime.M276ShortPromptBinaryRuntime
HERE = Path(__file__).resolve().parent
TRACE_PATH = HERE / 'results/baseline/prefill_trace.json'


def save(value):
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    partial = TRACE_PATH.with_suffix('.partial')
    partial.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    os.replace(partial, TRACE_PATH)


class DiagnosticRuntime(ORIGINAL_RUNTIME):
    def load(self):
        super().load()
        if not isinstance(self.language, PrefillDiagnostic):
            self.language = PrefillDiagnostic(self.language, self.board, board_runtime,
                                              trace_factory=DecodeIOTrace)
            print('M339_DIAGNOSTIC_ATTACHED_REAL_M241', flush=True)

    def close(self):
        # The gate reaches close after its token/complete timestamps or failure.
        report = dict(status='NO_PREFILL', numerical_acceptance=False, performance_pass=False)
        if isinstance(self.language, PrefillDiagnostic) and self.language.record is not None:
            report = self.language.finalize()
        if self.board is not None:
            snapshot = board_runtime.transaction_snapshot(self.board.kernel, self.board.dma)
            report['release_snapshot'] = snapshot
            if self.board.host_calls and not safe_to_release(snapshot):
                report['status'] = 'FAIL_UNSAFE_DMA_RETAINED'
                save(report)
                print('M339_RECOVERY_REQUIRED '+json.dumps(snapshot), flush=True)
                # Retain DMA buffers and process until explicit operator recovery.
                import time
                while True: time.sleep(30)
        save(report)
        print('M339_PREFILL_TRACE_SAVED_AFTER_TOKEN', flush=True)
        return super().close()


def main():
    if TRACE_PATH.exists(): raise RuntimeError('Immutable trace exists')
    m276_video_runtime.M276ShortPromptBinaryRuntime = DiagnosticRuntime
    return m277_fixed_window_gate.main()


if __name__ == '__main__': raise SystemExit(main())
