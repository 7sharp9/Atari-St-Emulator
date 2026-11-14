"""Gate for Virus's particle pool ($31d54, 20-byte records, count at $32a3e) and its stage-1 behaviour routine $21792.
Record: +0 x,y,z (3 words)  +6 vx,vy,vz  +12 life/flags word  +14 pad  +16 behaviour code pointer (long).
The updater $2157c walks the pool each frame: ground = height($24754) at (x,z); if ground <= y the flags $a000 are or-ed into
life; then it jumps to the record's behaviour.  Stage 1 ($21792), for a live record:
   pos += vel;  if life != 0: life -= 1  else if ground <= $320 the pointer becomes $21894 (stage 2, not modelled)
   vy -= ((y_new - ground + $280) >> 5)        (word arithmetic: a spring toward ground - $280, no gravity constant)
   vy -= vy >> 4                                (drag 1/16 on vy only; vx, vz unchanged)
   vy clamped to [-$60, $60]
Input: part_bp.txt (bp 2157c; m 32a3e 2; m 31d54 1280; m 32a3a 2 repeated).  Usage: python virus_particles.py <part_bp.txt> <snap> [--break]
"""
import os, re, struct, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'tools'))
import gfxview
s16 = lambda v: ((v & 0xffff) ^ 0x8000) - 0x8000
r0 = bytes(gfxview.load_ram(sys.argv[2])[0])
edge = 0x900
def ground(x, z):                              # $24754's height (launch pad region = $420)
    x &= 0xffff; z &= 0xffff
    if x < edge and z < 0x900: return 0x420
    return s16(((r0[0x42a58 + (x >> 8) + (z & 0xff00)]) << 3) + 0xfd68)

txt = open(sys.argv[1]).read().split('\n'); blk = []; cur = None
for l in txt:
    if l.startswith('--- breakpoint'): cur = []; blk.append(cur)
    elif cur is not None and re.fullmatch(r'([0-9a-f]{2} ?)+', l.strip()): cur.append(l.strip().replace(' ', ''))
pools = [(int(b[0], 16), bytes.fromhex(b[1])) for b in blk]
brk = '--break' in sys.argv
def rec(data, i):
    x, y, z, vx, vy, vz, life, _p, ptr = struct.unpack('>6hhhL', data[i * 20:i * 20 + 20])
    return [x, y, z, vx, vy, vz, life, ptr]
n = ok = 0; fields = [0] * 6
for (c0, d0), (c1, d1) in zip(pools, pools[1:]):
    if c0 != c1: continue                      # a removal or spawn: records move, not modelled here
    for i in range(c0):
        r = rec(d0, i)
        if r[7] != 0x21792: continue
        x, y, z, vx, vy, vz, life, ptr = r
        g = ground(x, z)
        if g <= y: continue                    # the kill path ($21764) removes it
        if life == 0 and g <= 0x320: continue  # switches to stage 2 ($21894), not modelled
        x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
        if life: life -= 1
        t = s16(y - g + 0x280) >> 5
        vy = s16(vy - t)
        vy = s16(vy - (vy >> (3 if brk else 4)))
        if vy >= 0:
            if vy >= 0x60: vy = 0x60
        elif vy <= -0x60: vy = -0x60
        got = rec(d1, i)
        exp = [x, y, z, vx, vy, vz]
        n += 1
        ok += got[:6] == exp
        for k in range(6): fields[k] += got[k] == exp[k]
print(f'{len(pools)} frames; stage-1 particle updates modelled {n}; all six fields equal {ok}/{n}; per field x y z vx vy vz {fields}')
