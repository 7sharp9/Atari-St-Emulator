"""gate_dmg_cody.py <dump> : each drop of Cody's health word (+24 of $ff8568) in a dm.lua dump (hp topped up to +28 by the god poke after each dump, so a drop is the damage of that frame)
equals the ROM damage byte of the attacker: byte[92(A6) + word(box+8)] with A6 = DAMND (pool 4 record $ff9a68), box = its attack-box descriptor +112 (long) at that frame.
Frames where a pool-2 fighter also has an attack box are counted separately (not attributed)."""
import sys, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def rb(a): return rom[a]
def rw(a): return int.from_bytes(rom[a:a+2], 'big')
D = Dump(sys.argv[1])
ok = bad = other = 0
bybox = collections.defaultdict(lambda: [0, 0])
rows = []
for i in range(D.n):
    hp, mx = D.s16(i, P1 + 24), D.u16(i, P1 + 28)
    if D.u8(i, P1 + 2) != 2 or hp >= mx: continue
    drop = mx - hp
    b = D.u32(i, BOSS + 112) & 0xffffff
    p2 = [a for a in range(0xff86e8, 0xff86e8 + 13 * 0xc0, 0xc0) if D.u8(i, a) and D.u32(i, a + 112)]
    if not b or p2:
        other += 1; rows.append((int(D.frame(i)), drop, 'other', hex(b), len(p2))); continue
    row = rw(b + 8); a92 = D.u32(i, BOSS + 92) & 0xffffff
    exp = rb(a92 + row)
    key = 'row%02x type%02x snd%02x' % (row, rb(b + 11), rb(b + 13))
    if exp == drop: ok += 1; bybox[key][0] += 1
    else: bad += 1; bybox[key][1] += 1; rows.append((int(D.frame(i)), drop, 'exp', exp, hex(a92), key, 'lvl96=%d 168=%d' % (D.u8(i, BOSS + 96), D.u16(i, 0xff8000 + 168))))
print('Cody drops attributed to DAMND: match %d mismatch %d; unattributed %d' % (ok, bad, other))
for k, v in sorted(bybox.items()): print('  %s: match %d mismatch %d' % (k, *v))
for r in rows[:30]: print('  ', r)
