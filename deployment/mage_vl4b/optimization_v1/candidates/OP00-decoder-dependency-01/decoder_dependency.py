"""Pinned decoder identity, shared by download, UART bootstrap and LAN sender."""
NAME = 'opencv_python_headless-4.11.0.86-cp37-abi3-manylinux_2_17_aarch64.manylinux2014_aarch64.whl'
SHA = '6efabcaa9df731f29e5ea9051776715b1bdd1845d7c9530065c7951d2a2899eb'
SIZE = 29487060
URL = 'https://files.pythonhosted.org/packages/45/be/1438ce43ebe65317344a87e4b150865c5585f4c0db880a34cdae5ac46881/' + NAME
MAGIC = b'TELLME_OP00_DECODER_V1\n'


def exact(sock, size):
    data = bytearray()
    while len(data) < size:
        block = sock.recv(size - len(data))
        if not block:
            raise RuntimeError('Unexpected network EOF')
        data.extend(block)
    return bytes(data)
