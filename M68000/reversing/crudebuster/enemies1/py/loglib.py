"""Parser for enemylog.txt (lua/enemylog.lua).  frames() yields dicts: f, sx, sy, f40, f41, lvl, P (bytes, 0x80 of $80100), R {slot: bytes(64)}.
Record helpers: b(rec, off), w(rec, off) big-endian."""
import sys
def frames(path):
    cur = None
    for line in open(path):
        t = line.split()
        if t[0] == "F":
            if cur: yield cur
            cur = dict(f=int(t[1]), sx=int(t[2], 16), sy=int(t[3], 16), f40=int(t[4][:2], 16), f41=int(t[4][2:], 16), lvl=int(t[5][4:]), P=None, R={}, H={})
        elif t[0] == "P": cur["P"] = bytes.fromhex(t[2])
        elif t[0] == "R": cur["R"][int(t[2])] = bytes.fromhex(t[3])
        elif t[0] == "H": cur["H"][int(t[2])] = bytes.fromhex(t[3])
        elif t[0] == "C": cur.setdefault("C", t[1])
    if cur: yield cur
def b(r, o): return r[o]
def w(r, o): return (r[o] << 8) | r[o+1]
def l(r, o): return int.from_bytes(r[o:o+4], "big")
if __name__ == "__main__":
    last = None
    for fr in frames(sys.argv[1]):
        if fr["f"] % 500 == 0:
            print(fr["f"], "sx=%04x sy=%04x f40=%02x f41=%02x P1x=%04x y=%04x" % (fr["sx"], fr["sy"], fr["f40"], fr["f41"], w(fr["P"], 8), w(fr["P"], 12)), "recs", [(i, r[2], r[3], w(r, 8), w(r, 12)) for i, r in fr["R"].items()])
