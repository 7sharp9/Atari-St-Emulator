"""Models for the two-hit pursuer's hit paths: the first hit `$22164` (Pursuer2_FirstHit), the damaged state `$221ac`
(Pursuer2_Damaged) and the kill path `$216d6` (Pool_KillAward). Extends `pursuer_step` of `py/behaviours/gate_pursuer.py`
(imported, not copied).

Record = [x y z vx vy vz life pad behaviour] (behaviours.md "Two pools"); `life` is the word at -8(A6) (bit 15 hit, bit 13 hit
the ground, low byte the stun count while damaged); the walker `$2157c` or-s $a000 into D6 (a register) when the ground is at
or above y, and does not store it, so a reload of -8(A6) (as `$22128` and `$221b8` do) drops the ground bits.

first_hit_step (`$22164`, entered from `$2202c` when D6 has bit 15):
  bit 13 set (ground, or the ship contact tail `$21648`) -> A0 = $384, kill path `$216d6`, no move.
  else award 200, sound 3, bit 15 cleared, stun count := 5, behaviour := `$221ac`, and the SAME pass falls into `$221ac`: the hit is
  not ignored (bit 15 now clear), count 5 -> 4 and the stunned move runs. Net: moved, drag, count 4, behaviour `$221ac`, score + 200.
damaged_step (`$221ac`, award 700):
  bit 15 (from the shot, or the ground at or above y): count (from memory) = 0 -> kill 700; else the hit is ignored (bit 15, and the
  ground bits, dropped).  Then count - 1; if it was 0 (underflow) the count stays 0 and the pass is a pursuit as `$2202c` with the
  near-ground test $300 and the near pull >> 10 (far >> 13); else the stunned pass: pos += vel, vy += g, drag, no steer, thrust,
  pull or fire, the count stored.  The shot's hit bit is set AFTER the pass (shot handler after the walker), see the gate.
kill_step: the award goes to the score long `$2708e`, the pool count `$32a3e` drops by 1, the LAST record is copied into the
killed slot (and walked there this pass), a killed last record is just dropped.
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
d = here
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    p = os.path.dirname(d)
    if p == d:
        raise SystemExit('repo root (the directory holding tools/rdis.py) not found')
    d = p
ROOT = d
PY = os.path.join(ROOT, 'reversing/virus/py')
for q in (PY, os.path.join(PY, 'behaviours'), os.path.join(PY, 'mpc')):
    sys.path.insert(0, q)
import shot as S
import gate_pursuer as GP
s16 = S.s16
P2 = 0x2202c
DAMAGED = 0x221ac
AWARD_HIT, AWARD_GROUND, AWARD_KILL = 200, 900, 700
STUN = 5
PAD_AFTER_HIT = 0xffff       # D6's high word at $22164 (the stored pad), -1 in 11/11 natural first hits; mechanism inferred


def _tilt_signed(pad, up):
    """`$22c1e` tilt: up = `addi.b #2; cmp.b #$3f; ble` (a SIGNED byte compare: $ff + 2 = 1, no clamp), down = `subi.b #2; bcc` (unsigned,
    floor 0). S._tilt (`max/min` on the unsigned byte) is the same for tilt < $7e, which is all a flying patrol or pursuer reaches;
    the first hit stores pad = $ffff, so a damaged pursuer is the first record whose tilt starts at $ff."""
    t = pad & 0xff
    if up:
        t = (t + 2) & 0xff
        if t < 0x80 and t > 0x3f: t = 0x3f
    else:
        t = t - 2 if t >= 2 else 0
    return (pad & 0xff00) | t


_TILT_ORIG = S._tilt
def use_signed_tilt(on=True):
    S._tilt = _tilt_signed if on else _TILT_ORIG
use_signed_tilt(True)


def _stunned_move(rec, g):
    x, y, z, vx, vy, vz, lw, pad, b = rec
    x, y, z = s16(x + vx), s16(y + vy), s16(z + vz)
    vy = s16(vy + g)
    vx, vy, vz = (s16(v - (v >> 5)) for v in (vx, vy, vz))
    return [x, y, z, vx, vy, vz, lw, pad, b]


def first_hit_step(a, g, control='none'):
    """a: a $2202c record whose D6 has bit 15 (life bit 15 in memory, or the ground at/above y).
    Returns (new record or None, info) with info = ('kill', award) or ('hit1', score delta)."""
    x, y, z, vx, vy, vz, life, pad, b = a
    gh = S.aground(x, z)
    lw = life & 0xffff
    if gh <= y:
        lw |= 0xa000
    assert lw & 0x8000
    if lw & 0x2000 and control != 'ground_no_kill':
        return None, ('kill', AWARD_GROUND)
    count = STUN if control != 'count4' else 4
    lw = (lw & ~0x8000 & 0xff00) | count          # bclr #15; move.b #5
    rec = [x, y, z, vx, vy, vz, lw, s16(PAD_AFTER_HIT) if control != 'pad_keep' else pad, DAMAGED]
    if control != 'nofall':                        # the same pass falls into $221ac: subq.b #1 -> 4, stunned move
        rec[6] = (lw & 0xff00) | (count - 1)
        rec = _stunned_move(rec, g)
    return [s16(v) for v in rec[:8]] + [DAMAGED], ('hit1', AWARD_HIT if control != 'award100' else 100)


def damaged_step(a, ship, g, tick48, control='none'):
    """a: a $221ac record (life in memory, bit 15 possibly set by a shot at the end of the last tick)."""
    x, y, z, vx, vy, vz, life, pad, b = a
    mem = life & 0xffff
    gh = S.aground(x, z)
    lw = mem | 0xa000 if gh <= y else mem
    if lw & 0x8000:
        if (mem & 0xff) == 0 or control == 'killall':
            return None, ('kill', AWARD_KILL)
        lw = mem if control != 'keepground' else lw  # ignored: reload of -8(A6), the ground bits are gone
    lw &= ~0x8000
    c = ((lw & 0xff) - 1) & 0xff
    if c < 0x80:                                    # bpl: stunned pass
        if control == 'stun4' and c >= 1: c -= 1
        rec = [x, y, z, vx, vy, vz, (lw & 0xff00) | c, pad, b]
        return [s16(v) for v in _stunned_move(rec, g)[:8]] + [b], ('stunned', c)
    lw &= 0xff00                                    # move.b #0,D6 : pursuit
    rec = [x, y, z, vx, vy, vz, lw, pad, b]
    got, info = GP.pursuer_step(rec, ship, g, tick48, 'nopull', nearg=0x300)
    if got is None:
        return None, info
    x, y, z, vx, vy, vz = got[:6]
    d = S.man((x, y, z), ship)
    sh = 10 if d <= 0x1900 else 13
    if control == 'shift9' and d <= 0x1900: sh = 9
    if control == 'shift12' and d > 0x1900: sh = 12
    vx = s16(vx + (s16(ship[0] - x) >> sh)); vy = s16(vy + (s16(ship[1] - y) >> sh)); vz = s16(vz + (s16(ship[2] - z) >> sh))
    got[3:6] = [vx, vy, vz]
    return got, ('pursue', 'near' if d <= 0x1900 else 'far')


def kill_step(pool, i, score, award):
    """pool: list of records; the record i is killed. Returns (new pool, new score). The last record is copied into slot i."""
    q = [list(r) for r in pool]
    last = q.pop()
    if i < len(q):
        q[i] = last
    return q, score + award
