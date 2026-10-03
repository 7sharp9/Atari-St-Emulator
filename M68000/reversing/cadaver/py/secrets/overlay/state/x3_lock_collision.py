"""x3_lock_collision.py: PROVES that rec+15 bit 2 (the LOCK/UNLOCK state, verbs 54/55) makes an object an immovable solid for the collision routine $008868: marker byte 1(A4) of the result list at 92(A5) becomes $fd
(the same marker that sprite+24 bit 7 gives walls).  callcap of $008868 (A0 = the hero's template, A1 = hero record, D0..D2 = a box at the object's own position), once with the bit clear and once set (poked), for several objects.
usage: x3_lock_collision.py"""
import sys
from lab import *
SNAP = SN('CAVERN', 'scratchpad/cadaver/gameplay_empire.snap')
r = start(SNAP); passes(r, 2)
S = sprites(r)
hero = S[0]; hrec = hero['rec']; htmpl = int.from_bytes(hero['e'][6:10], 'big')
lst = r.l(A5 + 92)
def probe(oid):
    o = S[oid]; rec = o['rec']; e = o['e']
    # box at the object's own (x, y, z): the sprite entry holds x,y at bytes 0,1 and z at byte 5 (rec +0,+1,+2 equivalents)
    x, y, z = r.mem(rec, 3)
    res = callcap(r, 0x8868, 'D0=%x D1=%x D2=%x A0=%x A1=%x' % (x, y, z, htmpl, hrec))
    d = res['delta']
    cnt = d.get(lst, (None, r.mem(lst, 1)[0]))[1]
    mark = d.get(lst + 1, (None, r.mem(lst + 1, 1)[0]))[1]
    hit = [hex(d[a][1]) for a in sorted(d) if lst + 2 <= a < lst + 14]
    return res['ret'], cnt, mark, bytes(r.mem(lst, 16)).hex(' ') if not d else ' '.join('%02x' % d.get(lst + i, (0, r.mem(lst + i, 1)[0]))[1] for i in range(14))
print('hero template $%x, record $%x, result list at $%x' % (htmpl, hrec, lst))
for oid in (412, 168, 257, 60, 413, 5):
    if oid not in S: continue
    rec = S[oid]['rec']; f15 = r.mem(rec + 15, 1)[0]
    a = probe(oid)
    wb(r, rec + 15, f15 | 4); b = probe(oid); wb(r, rec + 15, f15)
    wb(r, rec + 15, f15 & ~4); c = probe(oid); wb(r, rec + 15, f15)
    print('obj %3d cls %02x tmpl+12 %02x +15=%02x:  bit2 as is -> count %s marker %s | bit2 SET -> count %s marker %s | bit2 CLEAR -> count %s marker %s   list %s' % (oid, S[oid]['tm'][22], S[oid]['tm'][12], f15, a[1], hex(a[2]) if a[2] is not None else None, b[1], hex(b[2]) if b[2] is not None else None, c[1], hex(c[2]) if c[2] is not None else None, b[3]))
r.close()
