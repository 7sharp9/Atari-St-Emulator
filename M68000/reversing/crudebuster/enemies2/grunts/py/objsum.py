"""Summarise an objlog.txt: for every pool A record lifetime (slot continuous activity with same type/variant) print type, variant,
spawn frame, x/y at spawn, end frame, health trajectory start/min, state sequence with frame counts.
usage: objsum.py <objlog.txt> [type hex ...]"""
import sys
def parse(path):
    recs = {}  # slot -> list of (frame, bytes)
    F = {}
    for line in open(path):
        p = line.split()
        if p[0] == "A":
            recs.setdefault(int(p[2]), []).append((int(p[1]), bytes.fromhex(p[3])))
        elif p[0] == "F":
            F[int(p[1])] = p[2:]
    return recs, F
def lives(recs):
    out = []
    for slot, lst in recs.items():
        cur = None
        for f, b in lst:
            key = (b[2], b[16])
            if cur and cur["last"] == f - 1 and cur["key"] == key:
                cur["rows"].append((f, b)); cur["last"] = f
            else:
                if cur: out.append(cur)
                cur = dict(slot=slot, key=key, first=f, last=f, rows=[(f, b)])
        if cur: out.append(cur)
    return sorted(out, key=lambda c: c["first"])
if __name__ == "__main__":
    recs, F = parse(sys.argv[1])
    want = [int(a, 16) for a in sys.argv[2:]]
    for c in lives(recs):
        t, v = c["key"]
        if want and t not in want: continue
        rows = c["rows"]
        seq = []
        for f, b in rows:
            s = b[3]
            if not seq or seq[-1][0] != s: seq.append([s, 1])
            else: seq[-1][1] += 1
        hp = [b[5] for f, b in rows]
        b0 = rows[0][1]
        print(f"slot {c['slot']:2d} type {t:02x} var {v:02x} frames {c['first']}-{c['last']} ({len(rows)}) x={int.from_bytes(b0[8:10],'big'):04x} y={int.from_bytes(b0[12:14],'big'):04x} hp0={hp[0]} hpmax={max(hp)} min={min(hp)} states: " + " ".join(f"{s:x}x{n}" for s, n in seq))
