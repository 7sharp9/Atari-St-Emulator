"""nat_parse.py [cap.txt]: check every natural pile transfer captured by nat_capture.sh against the teardown block $39d4.

At $3a60 (registers: A0 the pile, A1 the lead, A3 the group view, D0 the shift, D6 the cell, D7 the mode) and at $3ae8 it has
the group table, the pile pool and the object array. For each stop it checks:
  cell:  D6 == ((word 10(lead) >> 2) & $1fc0) + byte 8(lead)   (the lead's map cell, $39ec..$39f6)
  word8: pile word 8 after == D6                              (the store at $3ad8)
  goods: pile word 12+2i after == before + (84+12i(A3) >> D0), group word after == before - that   (D7 != 1)
  food:  pile word 10 after == before + (36(A3) >> D0), group 36 after == before - that             (D7 != 2)
  kit:   lead byte 44 >= $e adds 1 to pile word 10 + byte44 and clears byte 44
  byte6: $2c after; no write to pile bytes 4, 5, 7 (before == after)
Prints one line per stop and the totals."""
import os, re, sys
from pathlib import Path

def root():
    p = Path(os.environ["M68000_ROOT"]) if "M68000_ROOT" in os.environ else Path(__file__).resolve()
    while not (p / "tools" / "rdis.py").exists():
        p = p.parent
    return p

CAP = sys.argv[1] if len(sys.argv) > 1 else str(root() / os.environ.get("PM_WORK", "scratchpad/pm162") / "pile" / "nat" / "cap.txt")
txt = open(CAP).read()
blocks = re.split(r"--- breakpoint \$([0-9a-f]+) hit[^\n]*\n", txt)
stops = []
for i in range(1, len(blocks), 2):
    pc = int(blocks[i], 16); body = blocks[i + 1]
    regs = dict((k, int(v, 16)) for k, v in re.findall(r"\b([DA][0-7]):([0-9a-f]{8})", body))
    dumps = [bytes.fromhex(l.replace(" ", "")) for l in body.splitlines() if re.fullmatch(r"([0-9a-f]{2} )*[0-9a-f]{2}", l.strip())]
    stops.append((pc, regs, dumps))

def w(b, o): return int.from_bytes(b[o:o + 2], "big")
GT, POOL, OBJ = 0x51538, 0x4bb4e, 0x51b66
ok = tot = 0
n = 0
for k in range(len(stops) - 1):
    pc, R, d = stops[k]
    pc2, R2, d2 = stops[k + 1]
    if pc != 0x3a60 or pc2 != 0x3ae8 or len(d) < 3 or len(d2) < 3: continue
    n += 1
    g0, p0, o0 = d[:3]; g1, p1, o1 = d2[:3]  # a final bp that never hits appends its dumps to the last stop
    A0, A1, A3, sh, D6, D7 = R["A0"], R["A1"], R["A3"], R["D0"] & 0xffff, R["D6"] & 0xffff, R["D7"] & 0xffff
    lo = A1 - OBJ; po = A0 - POOL; go = A3 - GT
    cell = (((w(o0, lo + 10) >> 2) & 0x1fc0) + o0[lo + 8]) & 0xffff
    checks = {"cell": D6 == cell, "word8": w(p1, po + 8) == D6, "byte6": p1[po + 6] == 0x2c,
              "b457": p0[po + 4:po + 6] + p0[po + 7:po + 8] == p1[po + 4:po + 6] + p1[po + 7:po + 8]}
    kit = o0[lo + 44]
    exp_p = [w(p0, po + 10 + 2 * j) for j in range(9)]
    gd = []
    if D7 != 1:
        for i in range(8):
            gb = w(g0, go + 84 + 12 * i); t = gb >> sh
            exp_p[1 + i] += t
            gd.append(w(g1, go + 84 + 12 * i) == gb - t)
        if kit >= 0xe:
            exp_p[kit // 2] += 1
            checks["kitclr"] = o1[lo + 44] == 0
    if D7 != 2:
        fb = w(g0, go + 36); t = fb >> sh
        exp_p[0] += t
        gd.append(w(g1, go + 36) == fb - t)
    checks["group"] = all(gd)
    checks["pile"] = [w(p1, po + 10 + 2 * j) for j in range(9)] == [e & 0xffff for e in exp_p]
    for v in checks.values():
        tot += 1; ok += bool(v)
    side = (go) // 0x13c
    print("stop %d: pile $%x slot %d new=%s D7=%d shift=%d lead $%x cell $%04x (x %d, y %d) group side %d food %d->%d goods %s->%s kit %d | pile w8 $%04x w10..26 %s | %s" % (
        n, A0, po // 28, p0[po + 6] != 0x2c, D7, sh, A1, D6, D6 & 63, D6 >> 6, side, w(g0, go + 36), w(g1, go + 36),
        [w(g0, go + 84 + 12 * i) for i in range(8)], [w(g1, go + 84 + 12 * i) for i in range(8)], kit,
        w(p1, po + 8), [w(p1, po + 10 + 2 * j) for j in range(9)], " ".join("%s=%s" % (a, "ok" if b else "FAIL") for a, b in checks.items())))
print("%d transfers, %d/%d checks" % (n, ok, tot))
