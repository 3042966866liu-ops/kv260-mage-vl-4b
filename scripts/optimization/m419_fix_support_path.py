"""Correct host-only Windows path formatting in the final runner path assertion."""
from m351_workflow import HERE,atomic
source=(HERE/'m419_support02.py').read_text(encoding='utf-8')
before="str(Path(actual_output).parent)"
assert source.count(before)==1
source=source.replace(before,"__import__('pathlib').PurePosixPath(actual_output).parent.as_posix()")
source=source.replace("'m419_support02.py'","'m419_support03.py'")
atomic(HERE/'m419_support03.py',source.encode('utf-8'),immutable=True)
print('M419_HOST_POSIX_PATH_ASSERTION_FIXED')
