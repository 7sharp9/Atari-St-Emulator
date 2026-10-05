"""Immunity table from a CB_INJECT=1 log: for every I line (a synthetic player hit, +6 bit 7, written when a record had been in a state for 5 frames)
compare the record at the next frame: 'hit' = health dropped or state became 1/2; 'ignored' = health and state unchanged (or state changed by the AI only).
usage: inject_check.py <log> <type hex>  -> per state: n injections, hit, ignored"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from loglib import load
log, ty = sys.argv[1], int(sys.argv[2], 16)
F, eps = load(log)
rows = {}
imm = collections.defaultdict(collections.Counter)
for e in eps:
    for f, b in e.rows:
        rows[(e.slot, f)] = b
        if e.type == ty: imm[b[3]][b[17] & 2 != 0] += 1
res = collections.defaultdict(collections.Counter)
for line in open(log):
    if not line.startswith("I "): continue
    p = line.split(); f = int(p[1]); kv = dict(x.split("=") for x in p[2:])
    if int(kv["type"], 16) != ty: continue
    slot = int(kv["slot"]); st = int(kv["state"], 16); hp = int(kv["hp"])
    b0 = rows.get((slot, f))
    if b0 is not None and (b0[0] & 8):
        res[st]["flash (+0 bit3: $22c56 ignores hits for 16 frames after a stagger)"] += 1; continue
    b1 = rows.get((slot, f + 1))
    if b1 is None: res[st]["gone"] += 1; continue
    got = b1[5] < hp or b1[3] in (1, 2)
    # prediction from the flags the handler of frame f+1 sees ($22c56 / $22ce4): +0 bit 6 (hittable), +0 bit 3 (flash), +17 bit 1 (immune), 22ce4 types ignore states b,c,d
    pred = bool(b0[0] & 0x40) and not (b0[0] & 8) and not (b0[17] & 2) and not (ty in (0x4b, 0x4d, 0x0d, 0x10) and st in (0xb, 0xc, 0xd))
    res[st]["hit" if got else "ignored"] += 1
    res[st]["prediction ok" if pred == got else "PREDICTION WRONG"] += 1
for st in sorted(res): print(f"  state {st:02x}: " + " ".join(f"{k} {v}" for k, v in sorted(res[st].items())))
print("frames per state with +17 bit1 (immune to player hits) clear/set at frame end:")
for st in sorted(imm): print(f"  state {st:02x}: clear {imm[st][False]} set {imm[st][True]}")
