"""Section 7: verb 60 (the price/confirm test $00df46) on level 1's #105 (event 16: 60 c8 10f, IF SHOW #653 ELSE HEALTH -127)"""
from lib2 import *
import lib2, re

def run():
    h = H(SNAP1); r = h.r
    # callcap, unaffordable: gold 100 < 200
    r.cmd('w %x %08x' % (A5 + 1188, 100)); h.poke(A5 + 2270, [7])
    hp0 = r.w(A5 + 1174)
    d = h.call(60, [0, 0xc8, 1, 0x0f])
    chk('verb 60 [00c8 010f] with gold 100 < price 200: consumes 4 bytes; 2270(A5) 7 -> %d (false); gold unchanged; the only change is the counter (%d byte)' % (afterb(h, d, A5 + 2270), len(d['delta'])),
        d['ret'] and d['da1'] == 4 and afterb(h, d, A5 + 2270) == 0 and len(d['delta']) == 1 and afterl(h, d, A5 + 1188) == 100)
    h.close()
    def natural(gold, key, label):
        h = H(SNAP1); r = h.r
        a653 = h.obj(653); f0 = r.b(a653 + 3); r.cmd('w %x %08x' % (A5 + 1188, gold))
        inject5(h, 105, 0, 16)
        hh = r.hits(300000, 0xdfae, 0x10cd4, 0xdfa2)
        g_mid = r.l(A5 + 1188)
        if key is not None:
            r.cmd('kbd %02x' % key)
            ha = r.hits(40000, 0xdfa2, 0x10cd4)
            r.cmd('kbd %02x' % (key | 0x80))
            hb = r.hits(600000, 0xdfa2, 0x10cd4)
            hh2 = {k: ha.get(k, 0) + hb.get(k, 0) for k in set(ha) | set(hb)}
        else: hh2 = {}
        out = dict(prompt=hh.get(0xdfae, 0), death=hh.get(0x10cd4, 0) + hh2.get(0x10cd4, 0), gold=r.l(A5 + 1188), f0=f0, f1=r.b(a653 + 3), g_mid=g_mid, hp=r.w(A5 + 1174))
        h.close(); return out
    y = natural(1000, 0x15, 'Y')
    chk('natural[v60]  L1 #105 event 16, gold 1000: the confirm loop $00dfae is entered (%d); after key Y ($15): gold %d -> %d (-200), #653 flags $%02x -> $%02x (SHOW ran), no death path' % (y['prompt'], 1000, y['gold'], y['f0'], y['f1']),
        y['prompt'] == 1 and y['g_mid'] == 1000 and y['gold'] == 800 and y['f1'] == (y['f0'] & 0x7f) | 8 and y['death'] == 0, y)
    n = natural(1000, 0x31, 'N')
    chk('natural[v60]  L1 #105 event 16, gold 1000: after key N ($31): gold stays %d, #653 untouched ($%02x), the ELSE part runs (HEALTH -127 -> death routine $010cd4 hits %d)' % (n['gold'], n['f1'], n['death']),
        n['prompt'] == 1 and n['gold'] == 1000 and n['f1'] == n['f0'] and n['death'] == 1, n)
    p = natural(100, None, 'poor')
    chk('natural[v60]  L1 #105 event 16, gold 100 (< 200): no prompt (loop $00dfae hits %d), gold %d, ELSE part: death routine hits %d, #653 untouched' % (p['prompt'], p['gold'], p['death']),
        p['prompt'] == 0 and p['gold'] == 100 and p['death'] == 1 and p['f1'] == p['f0'], p)

if __name__ == '__main__':
    run(); print('ok %d bad %d' % (lib2.OK, lib2.BAD))
