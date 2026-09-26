# Environment matrix

| Role | Known evidence | Unknown/not supplied |
| --- | --- | --- |
| Development host | Windows PowerShell; historical WSL distro explicitly `Ubuntu-24.04`; Vitis/Vivado source scripts present | Clean build from this snapshot not run; exact installed tool versions at first release not proven |
| Offline BACT evidence | Python standard library and copied `bact/` modules; M321 reproduced within release directory | GPU software-reference environment is separate and not recreated |
| KV260 target | Ubuntu 22.04.4 LTS/AArch64 observed, Python 3.10, XRT 2.13.0, PYNQ environment; historical 800 MiB CMA used for specific stable boot | Fresh board image install and this new launcher not verified |

The board gate historically requires root, `XILINX_XRT=/usr`, `TMPDIR=/dev/shm`, `/usr/local/share/pynq-venv/bin/xclbinutil` first in `PATH`, one `xclProbe()` and one PYNQ device, and exact package hashes. Do not use `/usr/bin/xclbinutil` on the historical board. Serial COM3 was used for control; Ethernet transfer, if ever used, was temporary and hash-checked. This release does not configure networking or a boot/CMA setting. Do not assume 800 MiB CMA is a general KV260 default.

See [dependency files](../requirements/README.md). Device packages are not installed by this repository. No guessed general-purpose `pip install -r` is presented as a verified board setup.
