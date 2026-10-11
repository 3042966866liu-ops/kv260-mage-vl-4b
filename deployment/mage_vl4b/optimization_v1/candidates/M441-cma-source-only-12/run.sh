#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "${2:-}" == "--read-source-only" ]] || exit 2
printf "%s  PACKAGE_MANIFEST.json\n" "${1:?manifest SHA}" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ $(id -u) == 0 ]] || exit 2
[[ ! -e /home/ubuntu/m441_cma_source_evidence_12 ]] || exit 2
set +e
/usr/local/share/pynq-venv/bin/python -B ./probe.py 4f2aefcfe82ef39148573834f46cf36074d7db6ddf0c95488fd08687bf8a88dc
gate_rc=$?
set -e
printf "M441C_RUN_DONE gate_rc=%s\n" "$gate_rc"
exit "$gate_rc"
