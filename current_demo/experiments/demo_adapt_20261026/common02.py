"""Accepted clean-process student evidence; original helper/source stay immutable."""
from common_adapt import *
import common_adapt as original
PROTO=RUNS/'M541-demo-adaptation-protocol-02/RESULT.json'
CAP=RUNS/'M541-demo-adaptation-capture-02'
def verify(file=PROTO):return original.verify(file)
