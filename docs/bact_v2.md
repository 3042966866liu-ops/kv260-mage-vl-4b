# BACT-V2: frozen offline budget method

The selector in [bact/selector_v2.py](../bact/selector_v2.py) enumerates nine frozen candidate configurations across B4/B5/B6. Its semantic-loss proxy is an experiment fixture, not a calibrated answer-accuracy model. For the measured T32 fixed-Prefill contract, `B=ceil(N/32)` and `Calls=154*B+8`; this counts logical FPGA calls, not full latency, energy or arbitrary Decode. `bact-159` has five batches and 778 calls, versus `ratio-164` six batches and 932 calls. `count-144` also has five batches and 778 calls. A tie in calls does not imply equal time, quality or power; 159 vs 144 changes textual and visual composition, not merely visual-token count.

Reproduce frozen selector, 27 historical KV260 cost records and 12 previously seen AI-generated pilot predictions from this directory:

```sh
python3 scripts/m321_reproduce_bact_v2_evidence.py --only all
```

The command is read-only and verifies selected artifact hashes. It does not perform 12 new model forwards. The historic held-out protocol/calibration/test split is preserved as recorded, but these same 12 clips cannot be renamed a new independent set. The paired BACT-159 vs count-144 quality experiment did not establish an independent quality advantage. Prompt rewrite and two-time-view enhancement were explored but not adopted; P0/V0 remains frozen. The M277 fixed video path is not the Web's default BACT router; it uses the last-frame two-view/159-token fixture. Its 0/1 knife probe with `decode_calls=0` must not be described as free-form continuous generation.
