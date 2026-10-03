"""x10_invulnerable.py: PROVES inst+6 bit 0 (cleared by verb 89 UNINV) is the 'invulnerable' flag read by the spell code: callcap of the MAGIC MISSILE class handler in the level overlay ($004cd94,
A4 = creature record, A1+D1 = the spell's data with the damage in byte 1) on creature 237 (class 3, inst+0 = hit points $0c): bit clear -> hp - damage (and the kill event 23 queued when it underflows);
bit set -> no change.   usage: x10_invulnerable.py"""
import sys
from lab import *
r = start(SN('WATER30', 'scratchpad/cadaver/s85/explore/ck_g_water1.snap')); passes(r, 2)
c = rec_of(r, 237); h = r.mem(c, 16); ib = c + h[12]
BUF = 0x7f000
ok = n = 0
for dmg, flag in ((5, 0), (5, 1), (0x20, 0), (0x20, 1)):
    for i, b in enumerate((0, dmg, 0, 0)): wb(r, BUF + i, b)
    wb(r, ib + 6, flag); hp0 = r.mem(ib, 1)[0]
    res = callcap(r, 0x4cd94, 'A4=%x A1=%x D1=0' % (c, BUF))
    d = res['delta']; hp = d.get(ib, (0, hp0))[1]
    ring = [hex(v[1]) for a, v in sorted(d.items()) if A5 + 1154 <= a <= A5 + 1155]
    q = d.get(A5 + 1155, (0, None))[1]
    kill = any(v[1] == 0x17 for a, v in d.items() if r.l(A5 + 152) <= a < r.l(A5 + 152) + 1600)
    exp = hp0 if flag else (hp0 - dmg) & 0xff
    good = hp == exp and (kill == (not flag and dmg > hp0))
    n += 1; ok += good
    print('damage %2d, inst+6 bit0=%d: hp %02x -> %02x (expected %02x), kill event 23 queued: %s' % (dmg, flag, hp0, hp, exp, kill), 'ok' if good else 'BAD')
print('matches %d of %d' % (ok, n)); r.close()
