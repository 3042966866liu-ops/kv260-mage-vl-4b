"""Direct-loaded student baseline; historical switched-width rows are semantic controls."""
from common_adapt import *
import common_adapt as original
PROTO=RUNS/'M541-demo-adaptation-protocol-03/RESULT.json'
CAP=RUNS/'M541-demo-adaptation-capture-03'
def verify(file=PROTO):return original.verify(file)
