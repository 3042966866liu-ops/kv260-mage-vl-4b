"""Run only one frozen collector/shell-support stage with bounded evidence I/O."""
import json
import runpy
import sys
from pathlib import Path
from m441_host_io08 import atomic, observation

ALLOW = {'m441_collect_core_ooc07.py', 'm441_prepare_shell07.py',
         'm441_record_hwh07.py', 'm441_aux_readback07.py', 'm441_collect_shell07.py'}

if __name__ == '__main__':
    name, expected, *args = sys.argv[1:]
    assert name in ALLOW, 'No HLS, simulation, board or core launch allowed'
    import m351_workflow as workflow
    assert workflow.sha(workflow.HERE / name) == expected, 'Frozen stage SHA differs'
    workflow.atomic = atomic
    import m441_supervisor04 as supervisor
    saved_reader = supervisor.log_snapshot
    supervisor.log_snapshot = lambda path: observation(saved_reader, path)
    sys.argv = [str(workflow.HERE / name), *args]
    runpy.run_path(str(workflow.HERE / name), run_name='__main__')
