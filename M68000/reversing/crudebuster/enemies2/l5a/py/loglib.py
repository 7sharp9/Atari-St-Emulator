"""Parse a drive5.lua / objlog.lua log. Records are episodes: a pool A slot that is active over consecutive frames (a new episode starts when the
slot was inactive on the previous frame or its type byte changed).
usage as a module: from loglib import load; F, eps = load(path)
   F[frame] = dict(lvl, sx, sy, px, py, hp, f40, f41, n, f400, p1st, p1sub, p1b1, score)
   eps = list of Episode(slot, type, var, frames=[(frame, bytes64), ...])
CLI: loglib.py <log> [type hex]   prints a state-run summary per episode (state, frames, hp, x, y, facing) """
import sys

class Ep:
    def __init__(self, slot, ty, var):
        self.slot, self.type, self.var, self.rows = slot, ty, var, []
    def b(self, i): return [(f, r[i]) for f, r in self.rows]

def u16(b, o): return (b[o] << 8) | b[o + 1]

def load(path):
    F = {}
    eps = []
    live = {}
    last_f = -1
    for line in open(path):
        p = line.split()
        if not p: continue
        if p[0] == 'F':
            f = int(p[1])
            v = [int(p[2]), int(p[3], 16), int(p[4], 16), int(p[5], 16), int(p[6], 16), int(p[7], 16), int(p[8], 16), int(p[9], 16), int(p[10])]
            d = dict(lvl=v[0], sx=v[1], sy=v[2], px=v[3], py=v[4], hp=v[5], f40=v[6], f41=v[7], n=v[8])
            if len(p) > 11:
                d.update(f400=int(p[11], 16), p1st=int(p[12], 16), p1sub=int(p[13], 16), p1b1=int(p[14], 16), score=int(p[15], 16))
                if len(p) > 18: d.update(lptr=int(p[16], 16), f81e03=int(p[17], 16), f81e04=int(p[18], 16))
            F[f] = d
            for s in list(live):
                if live[s][1] != f: del live[s]
            last_f = f
        elif p[0] == 'A':
            f, slot, b = int(p[1]), int(p[2]), bytes.fromhex(p[3])
            e = live.get(slot)
            if e is None or e[1] != f - 1 or e[0].type != b[2]:
                ep = Ep(slot, b[2], b[16]); eps.append(ep)
            else:
                ep = e[0]
            ep.rows.append((f, b))
            live[slot] = (ep, f)
    # live[s][1] is last frame seen; drop handling above keeps only continuity
    return F, eps

def runs(ep):
    out = []
    cur = None
    for f, b in ep.rows:
        key = b[3]
        if cur and cur[0] == key and cur[2] == f - 1:
            cur[2] = f; cur[3] += 1; cur[5] = b
        else:
            cur = [key, f, f, 1, b, b]; out.append(cur)
    return out

if __name__ == '__main__':
    F, eps = load(sys.argv[1])
    want = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
    for ep in eps:
        if want is not None and ep.type != want: continue
        f0, f1 = ep.rows[0][0], ep.rows[-1][0]
        print(f"== slot {ep.slot} type {ep.type:02x} var {ep.var} frames {f0}..{f1}")
        for st, a, z, n, b0, b1 in runs(ep):
            print(f"  st {st:02x} f{a}-{z} n={n} hp {b0[5]}->{b1[5]} x {u16(b0,8)}->{u16(b1,8)} y {u16(b0,12)}->{u16(b1,12)} face {b0[4]} anim {b0[20]}")
