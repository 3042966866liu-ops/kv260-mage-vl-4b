#!/usr/bin/env python3
"""Retire only this turn's verified but incomplete v3 install before clean v4."""

import json
import os
from pathlib import Path
import shutil


TARGET = Path('/home/ubuntu/tellme_release_install_20260926')
STABLE = Path('/home/ubuntu/tellme_m120_m89x2_20260901')
EXPECTED = '10dbfe5a75f10e727e422b2a75ec5f394e2ce078a4734c95bee589c740414fb1'


def main():
    if os.geteuid() != 0 or TARGET.resolve() != TARGET or not TARGET.is_dir() or TARGET.is_symlink():
        raise RuntimeError('exact v3 install target check failed')
    if not STABLE.is_dir() or TARGET == STABLE or STABLE in TARGET.parents:
        raise RuntimeError('stable directory safety check failed')
    result = json.loads((TARGET / 'INSTALL_BOARD_RESULT.json').read_text())
    if (result.get('status') != 'PASS_INSTALLED_FILES_NOT_YET_EXECUTED' or
        result.get('archive_sha256') != EXPECTED or result.get('directory') != str(TARGET)):
        raise RuntimeError('v3 install identity check failed')
    shutil.rmtree(TARGET)
    print(json.dumps({'status': 'REMOVED_INCOMPLETE_V3_INSTALL', 'path': str(TARGET),
                      'archive_sha256': EXPECTED}), flush=True)
    print('M327_V3_INSTALL_REMOVED_PASS', flush=True)


if __name__ == '__main__':
    main()
