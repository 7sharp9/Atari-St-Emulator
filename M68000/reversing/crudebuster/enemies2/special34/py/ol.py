"""objlog.txt reader and tracer for pool A/B records.
usage: ol.py <objlog.txt> trace [--type HEX] [--fields off,off,...] [--from F] [--to F] [--pool A|B]
  prints, per record slot, one line each time one of the chosen byte offsets (default 2,3,5,16,18) changes (or the slot is (re)used).
       ol.py <objlog.txt> summary      -- per (type, variant): first/last frame, state sequence counts
Library: frames(path) -> dicts f, lvl, sx, sy, px, py, hp, f40, f41, n, A{slot: bytes}, B{slot: bytes}, C{slot: bytes}"""
import sys
def frames(path):
    A, B, C = {}, {}, {}
    for line in open(path):
        t = line.split()
        if t[0] == "A": A[int(t[2])] = bytes.fromhex(t[3])
        elif t[0] == "B": B[int(t[2])] = bytes.fromhex(t[3])
        elif t[0] == "C": C[int(t[2])] = bytes.fromhex(t[3])
        elif t[0] == "F":
            yield dict(f=int(t[1]), lvl=int(t[2]), sx=int(t[3], 16), sy=int(t[4], 16), px=int(t[5], 16), py=int(t[6], 16), hp=int(t[7], 16),
                       f40=int(t[8], 16), f41=int(t[9], 16), n=int(t[10]), ps=int(t[11], 16) if len(t) > 11 else 0, psub=int(t[12], 16) if len(t) > 12 else 0, score=int(t[13], 16) if len(t) > 13 else 0, hi=int(t[14], 16) if len(t) > 14 else 0, A=A, B=B, C=C)
            A, B, C = {}, {}, {}
def w(r, o): return (r[o] << 8) | r[o + 1]
def l(r, o): return int.from_bytes(r[o:o + 4], "big")
def trace(path, ty=None, fields=(2, 3, 5, 16, 18), f0=0, f1=1 << 30, pool="A"):
    prev = {}
    for fr in frames(path):
        if not (f0 <= fr["f"] <= f1): continue
        recs = fr[pool]
        for s, r in recs.items():
            if ty is not None and r[2] != ty: continue
            key = tuple(r[o] for o in fields)
            p = prev.get(s)
            if p is None or p[0] != key or p[1] != r[2]:
                print(f"f{fr['f']:5d} sx={fr['sx']:04x} P=({fr['px']:04x},{fr['py']:04x}) hp={fr['hp']:02x} slot{s:2d} t={r[2]:02x} x={w(r,8):04x} y={w(r,12):04x} " + " ".join(f"+{o}={r[o]:02x}" for o in fields) + f" f0={r[0]:02x} f1={r[1]:02x}")
            prev[s] = (key, r[2])
        for s in list(prev):
            if s not in recs:
                if ty is None or prev[s][1] == ty: print(f"f{fr['f']:5d}         slot{s:2d} t={prev[s][1]:02x} GONE")
                del prev[s]
if __name__ == "__main__":
    a = sys.argv
    ty = int(a[a.index("--type") + 1], 16) if "--type" in a else None
    fl = tuple(int(x) for x in a[a.index("--fields") + 1].split(",")) if "--fields" in a else (2, 3, 5, 16, 18)
    f0 = int(a[a.index("--from") + 1]) if "--from" in a else 0
    f1 = int(a[a.index("--to") + 1]) if "--to" in a else 1 << 30
    pool = a[a.index("--pool") + 1] if "--pool" in a else "A"
    if a[2] == "trace": trace(a[1], ty, fl, f0, f1, pool)
