"""Actual binding fixture in an isolated child, with no model or PL."""
import json,sys,tempfile
from pathlib import Path
from test_m411_binding import component
with tempfile.TemporaryDirectory(prefix='m419_component_') as temporary:
    answer=component(Path(sys.argv[1]),Path(temporary))
print('M414_COMPONENT='+json.dumps(answer),flush=True)
