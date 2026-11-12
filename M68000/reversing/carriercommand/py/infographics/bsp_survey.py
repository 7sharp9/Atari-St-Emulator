"""bsp_survey.py - structure of every BSP model in the table $4c4ce: planes, nodes, leaves, polygon items.
usage: bsp_survey.py [ids...]   (default all); prints one line per model. Uses py/render/model.py (build by callcap)."""
import pathlib as _pl, sys as _sys
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent)); _sys.path.insert(0, str(_here.parent / 'render'))
from ccpaths import *
from model import *

def tree(m):
    """nested structure of the BSP stream: ('node', plane, A, B, addr) or ('leaf', addr, items)"""
    def leaf(p, at):
        n = RAM[p]; p += 1; items = []
        for _ in range(n):
            st = p; f = RAM[p]; p += 1; tri = None; polys = []; end = None
            if f & 1:
                tri = tuple(RAM[p:p+3]); p += 3; end = p + RAM[p]; p += 1
            if f & 2:
                k = RAM[p]; p += 1
                for _ in range(k):
                    nv = RAM[p]; p += 1; idx = list(RAM[p:p+nv]); polys.append((p, idx, RAM[p+nv])); p += nv + 1
            if f & 4:
                k = RAM[p]; p += 1; p += 3 * k
            if f & 8:
                k = RAM[p]; p += 1; p += 4 * k
            items.append(dict(addr=st, flags=f, tri=tri, polys=polys, end=end))
        return ('leaf', at, items), p
    def node(p):
        b = RAM[p]
        if b & 0x80: return leaf(p + 1, p)
        off = (RAM[p+1] << 8) | RAM[p+2]; a = p + 3
        A, _ = node(a); B, e = node(a + off)
        return ('node', b, A, B, p), e
    return node(m['bsp'])[0]

def count(t):
    if t[0] == 'leaf': return dict(nodes=0, leaves=1, items=len(t[2]), polys=sum(len(i['polys']) for i in t[2]))
    a, b = count(t[2]), count(t[3])
    r = {k: a[k] + b[k] for k in a}; r['nodes'] += 1; return r

if __name__ == '__main__':
    ids = [int(x) for x in _sys.argv[1:]] or range(99)
    for i in ids:
        a = L(0x4c4ce + 4 * i)
        if a < 0x1000 or a > 0x80000: break
        if L(a) not in (0x8e68, 0x9066): print(i, hex(a), 'routine %x' % L(a)); continue
        try:
            b = build(a, (0, 0, 0)); m = parse(a, b); c = count(tree(m))
            print(i, hex(a), 'routine %x builder %x nv %d planes %d' % (b['routine'], b['builder'], m['nv'], len(m['planes'])), c)
        except Exception as e:
            print(i, hex(a), 'ERR', repr(e)[:80])
