"""recs.py: loader for fdrive.lua FF_REC files.  load(path) -> (G, P): G[f] = 512 bytes at A5, P[f][idx] = 192-byte record ('c' = Cody)."""
import collections
def load(path):
    G = {}; P = collections.defaultdict(dict)
    for l in open(path):
        p = l.split()
        if p[0] == 'G': G[int(p[1])] = bytes.fromhex(p[2])
        elif p[0] == 'H': P[int(p[1])]['hud'] = bytes.fromhex(p[2])
        elif p[0] == 'Q': P[int(p[1])]['q%d' % int(p[2])] = bytes.fromhex(p[3])
        elif p[0] == 'P':
            P[int(p[1])][p[2] if p[2] == 'c' else int(p[2])] = bytes.fromhex(p[3])
    return G, P
def w(r, o): return (r[o] << 8) | r[o + 1]
def s16(v): return v - 0x10000 if v >= 0x8000 else v
def st(r): return '%02x/%02x/%02x/%02x' % (r[2], r[3], r[4], r[5])
