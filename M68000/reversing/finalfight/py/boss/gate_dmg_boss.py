"""gate_dmg_boss.py <dump> : each drop of DAMND's health word (+24 of $ff9a68) while it is alive equals the scaled damage of the hit (frame.md "Damage dispatch", $79d8):
dmg = byte[92(attacker) + word(attack box +8)]; if +55 of the victim is non-zero, drop = word[$cea74 + (dmg << 6) + 2 * def]. Attacker = player 1 (record $ff8568, box = its +112 at that frame).
Also lists the hit type (+63), attack id (+22) and the next state of each hit."""
import sys, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
rb = lambda a: rom[a]
rw = lambda a: int.from_bytes(rom[a:a+2], 'big')
D = Dump(sys.argv[1]); fr = D.frames()
ok = bad = 0; rows = []
prev = None
for i in range(1, D.n):
    if not D.u8(i, BOSS) or not D.u8(i - 1, BOSS) or D.u8(i, BOSS + 2) == 0: continue
    h0, h1 = D.s16(i - 1, BOSS + 24), D.s16(i, BOSS + 24)
    if h1 >= h0 or D.u16(i - 1, BOSS + 24) == 0 and D.u8(i - 1, BOSS + 2) == 0: continue
    drop = h0 - h1
    box = D.u32(i, P1 + 112) & 0xffffff
    if not box: rows.append((int(fr[i]), 'no box', drop)); bad += 1; continue
    a92 = D.u32(i, P1 + 92) & 0xffffff
    dmg = rb(a92 + rw(box + 8)); d = D.u8(i, BOSS + 55)
    exp = rw(0xcea74 + (dmg << 6) + 2 * d) if d else dmg
    typ = rb(box + 11) & 0x7f
    nxt = (D.u8(i + 1, BOSS + 2), D.u8(i + 1, BOSS + 3)) if i + 1 < D.n else None
    rows.append((int(fr[i]), drop, exp, 'raw', dmg, 'def', d, 'lvl', D.u8(i, BOSS + 96), 'row%04x' % rw(box + 8), 'type', typ, '+63=', D.u8(i, BOSS + 63), '+22=', D.u8(i, BOSS + 22), 'hp', h1, 'st', '%02x%02x' % (D.u8(i, BOSS+2), D.u8(i, BOSS+3)), 'next', nxt))
    if exp == drop: ok += 1
    else: bad += 1
print('DAMND health drops: match %d mismatch %d' % (ok, bad))
for r in rows: print(*r)
