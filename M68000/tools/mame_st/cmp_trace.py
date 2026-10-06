#!/usr/bin/env python3
"""Loop-compressed PC-sequence comparison, MAME debugger trace vs F# ATARI_TRACE_EVENTS_ALL file.
Polling loops differ in iteration count by design (no cycle model in F#), so each stream is first reduced:
any block of period p<=PMAX (instructions) repeated k>=2 times in a row is replaced by one copy of the block.
The reduced streams are then compared; a mismatch is resynchronised by the smallest skip in either stream after
which the next L reduced PCs agree. Each entry keeps (original index, pc).
usage: tools/mame_st/cmp_trace.py <mame pc.trace> <fsharp .evt> [maxdiv] [mame_limit] [fs_limit]"""
import sys, os
root = os.path.abspath(__file__)
while not os.path.exists(os.path.join(root, "tools", "rdis.py")): root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, "tools"))
import trace_cfg
mt, ev = sys.argv[1], sys.argv[2]
import struct
VEC = os.environ.get("MAMEST_VECDUMP")   # low-RAM dump (low_fN.bin) from boot2.lua: handler entries of the autovector/MFP vectors
HANDLERS = set()
if VEC:
    d = open(VEC, "rb").read()
    for a in list(range(0x60, 0x80, 4)) + list(range(0x100, 0x140, 4)): HANDLERS.add(struct.unpack(">I", d[a:a+4])[0])
maxdiv = int(sys.argv[3]) if len(sys.argv) > 3 else 20
DETAIL = int(os.environ.get("DETAIL", "6"))
ml = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
fl = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
M, Msr = [], []
for ln in open(mt):
    if ln[0] == "@":
        a, s = ln[1:].split(); M.append(int(a, 16)); Msr.append(int(s, 16))
recs = trace_cfg.load(ev)[2]
F = [r[1] for r in recs]; Fk = [r[4] for r in recs]; Ft = [r[2] for r in recs]
M = M[:ml]; F = F[:fl]
PMAX = 12
def reduce(seq):
    out = []           # list of original indices kept
    i, n = 0, len(seq)
    while i < n:
        done = False
        for p in range(1, PMAX + 1):
            if i + 2 * p <= n and seq[i:i+p] == seq[i+p:i+2*p]:
                k = 2
                while i + (k + 1) * p <= n and seq[i:i+p] == seq[i+k*p:i+(k+1)*p]: k += 1
                out.extend(range(i, i + p)); i += k * p; done = True; break
        if not done: out.append(i); i += 1
    return out
def first_touch(seq):
    seen = set(); out = []
    for i, x in enumerate(seq):
        if x not in seen: seen.add(x); out.append(i)
    return out
if os.environ.get("MODE") == "first":
    mi, fi = first_touch(M), first_touch(F)
else:
    mi, fi = reduce(M), reduce(F)
Mr = [M[i] for i in mi]; Fr = [F[i] for i in fi]
print(f"MAME {len(M)} instrs -> {len(Mr)} reduced;  F# {len(F)} instrs -> {len(Fr)} reduced")
L, WIN = int(os.environ.get("L", "30")), int(os.environ.get("WIN", "20000"))
def agree(a, b): return Mr[a:a+L] == Fr[b:b+L] and len(Mr[a:a+L]) == L
a = b = 0; matched = 0; div = 0
CLS = {}; LINES = []; GRAM = None
while a < len(Mr) and b < len(Fr) and div < maxdiv:
    k = 0
    while a + k < len(Mr) and b + k < len(Fr) and Mr[a+k] == Fr[b+k]: k += 1
    matched += k; a += k; b += k
    if a >= len(Mr) or b >= len(Fr): break
    div += 1
    oa, ob = mi[a], fi[b]
    cls = "other"
    if Fk[ob-1] == 6: cls = "F# took interrupt here"
    elif Mr[a] in HANDLERS: cls = "MAME entered interrupt handler"
    elif Fr[b] in HANDLERS: cls = "F# entered interrupt handler"
    CLS[cls] = CLS.get(cls, 0) + 1
    detail = div <= DETAIL
    if detail:
        print(f"\nDIVERGENCE {div} [{cls}]: after {k} identical reduced instrs; MAME orig idx {oa}, F# orig idx {ob}")
        print(f"  last common pc: {Mr[a-1]:06x}   MAME next {Mr[a]:06x} (sr={Msr[oa]:04x})   F# next {Fr[b]:06x} (prev kind={Fk[ob-1]})")
        print("  MAME next 8:", " ".join(f"{x:06x}" for x in Mr[a:a+8])); print("  F#   next 8:", " ".join(f"{x:06x}" for x in Fr[b:b+8]))
    best = None
    for s_ in range(1, WIN):
        if agree(a + s_, b): best = ("skip MAME", s_, a + s_, b); break
        if agree(a, b + s_): best = ("skip F#", s_, a, b + s_); break
    if not best and os.environ.get("REANCHOR"):
        # general re-anchor: smallest (skipM + skipF) such that the next L reduced PCs agree
        if GRAM is None:
            GRAM = {}
            for q in range(len(Fr) - L): GRAM.setdefault(tuple(Fr[q:q+L]), []).append(q)
        bestc = None
        for a_ in range(a, min(len(Mr) - L, a + 200000)):
            if bestc is not None and a_ - a > bestc[0]: break
            lst = GRAM.get(tuple(Mr[a_:a_+L]))
            if lst:
                for q in lst:
                    if q >= b:
                        c = (a_ - a) + (q - b)
                        if bestc is None or c < bestc[0]: bestc = (c, a_, q)
                        break
        if bestc: best = ("re-anchor (skip both)", bestc[0], bestc[1], bestc[2])
    if not best:
        print(f"  #{div}: no resync (MAME orig {oa}, F# orig {ob})"); break
    who, s_, a2, b2 = best
    sk = (Mr[a:a+min(s_,10)] if who == "skip MAME" else Fr[b:b+min(s_,10)]) if who.startswith("skip") else Mr[a:a+4]+[0]+Fr[b:b+4]
    line = f"  #{div} [{cls}] M{oa} F{ob} common-last {Mr[a-1]:06x} M->{Mr[a]:06x} F->{Fr[b]:06x}; resync {who} {s_}: " + " ".join(f"{x:06x}" for x in sk) + (" ..." if s_ > 10 else "")
    if detail: print(line)
    else: LINES.append(line)
    a, b = a2, b2
print(f"\nreduced matched {matched}; divergences reported {div}; classes {CLS}")
if LINES: print("remaining divergences (compact):"); print("\n".join(LINES[:int(os.environ.get('SHOW', '60'))]))
print(f"final stream positions: MAME reduced {a}/{len(Mr)} (orig {mi[min(a, len(mi)-1)]}/{len(M)}), F# reduced {b}/{len(Fr)} (orig {fi[min(b, len(fi)-1)]}/{len(F)})")
