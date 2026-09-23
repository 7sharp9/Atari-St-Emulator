"""ai_ref.py - Python reconstruction of the Populous (Atari ST) computer-god decision routines.

Each function takes a mutable RAM image `m` (bytearray, absolute runtime addresses) plus the
routine's stack arguments, applies exactly the writes the 68000 routine makes, and returns the
routine's D0.w where the caller uses it.  Transcribed from the disassembly (see ai.md):

    think_13eda(m, side)        $13eda  walker-mode / papal-magnet strategist
    powers_13a44(m, side)       $13a44  power caster (+ target picker $13dce)
    flatten_135fc(m, cell, side) $135fc settlement-site leveller (9x9 around a house)
    level_13816(m, cell, side)  $13816  walker-cell leveller (2x2 corners under a walker)
"""
import struct

PLAYER, PSZ = 0x21e0c, 0x2e      # per-side "god" record (command + AI parameters)
SIDE = 0x3b226                   # per-side 16-byte state: leader, magnet, mode, counts, mana
WALK, WSZ = 0x3b278, 0x16        # walker / settlement array
FRAME = 0x3c4c8                  # game-tick counter (word)
SEED = 0x3d52e                   # RNG seed (word) used by $16702
HGT = 0x34be4                    # 65x65 corner-height grid, words
OBJ = 0x36e78                    # 64x64 per-cell terrain-object byte map
OCC = 0x37fd4                    # 64x64 per-cell walker occupancy (index+1)
FLAGS = 0x219b2                  # game-option flags word
COST_QUAKE, COST_SWAMP, COST_KNIGHT, COST_VOLC, COST_FLOOD, COST_ARMA = (
    0x21990, 0x21994, 0x21998, 0x2199c, 0x219a0, 0x219a4)
OFFS = 0x227d8                   # 81 signed (dx,dy) byte pairs, 9x9 search order


def rb(m, a): return m[a & 0xffffff]
def sb(m, a): v = m[a & 0xffffff]; return v - 256 if v & 0x80 else v
def rw(m, a): return struct.unpack_from('>H', m, a & 0xffffff)[0]
def sw(m, a): return struct.unpack_from('>h', m, a & 0xffffff)[0]
def rl(m, a): return struct.unpack_from('>I', m, a & 0xffffff)[0]
def sl(m, a): return struct.unpack_from('>i', m, a & 0xffffff)[0]
def wb(m, a, v): m[a & 0xffffff] = v & 0xff
def ww(m, a, v): struct.pack_into('>H', m, a & 0xffffff, v & 0xffff)
def s16(v): v &= 0xffff; return v - 0x10000 if v & 0x8000 else v
def s32(v): v &= 0xffffffff; return v - 0x100000000 if v & 0x80000000 else v


def rng(m):
    """$16702: seed = (seed*$24a1 + $24df) & $7fff; returns the new 15-bit seed (callers ext.l it)."""
    d = (rw(m, SEED) * 0x24a1) & 0xffffffff
    lo = ((d & 0xffff) + 0x24df) & 0xffff
    lo &= 0x7fff
    ww(m, SEED, lo)
    return lo


def rec(side): return PLAYER + side * PSZ
def sidest(side): return SIDE + side * 16
def other(side): return 1 if side == 0 else 0          # seq D0 ; and #1
def mode(m, side): return rw(m, sidest(side) + 4)
def magnet(m, side): return rw(m, sidest(side) + 2)
def mana(m, side): return sl(m, sidest(side) + 12)
def leader_ptr(m, side):
    i = rw(m, sidest(side))
    return 0 if i == 0 else (WALK + s16(i - 1) * WSZ) & 0xffffffff


def cmd(m, side, c, x, y, busy=True):
    r = rec(side)
    wb(m, r, c); wb(m, r + 1, x); wb(m, r + 2, y)
    if busy: ww(m, r + 8, 1)


def cmd_cell(m, side, c, cell, busy=True):
    cmd(m, side, c, cell & 0x3f, s16(cell) >> 6, busy)


def set_mode_cmd(m, side, md):
    """command 14 (icon), sub 1 = walker behaviour; x = mode (0 magnet,1 settle,2 gather,3 fight)"""
    r = rec(side)
    wb(m, r, 0xe); wb(m, r + 2, 1); wb(m, r + 1, md); ww(m, r + 8, 1)


# ---------------------------------------------------------------- $13eda
def think_13eda(m, side):
    r = rec(side)
    s = s16(rw(m, r + 22) + rw(m, r + 20))
    rating = rw(m, r + 12)
    lim = s16(rating * 2 + 15)
    cond = s < lim
    if not cond:
        rem = (rw(m, FRAME) % 0x5a) & 0xffff
        cond = rem < ((10 + rating) & 0xffff)
    if cond:
        if mode(m, side) == 0:
            r15 = rng(m)
            wb(m, r, 0xe); wb(m, r + 2, 1)
            wb(m, r + 1, 1 + (r15 % 3))
            ww(m, r + 8, 1)
        return
    a3 = leader_ptr(m, other(side))       # enemy leader
    a4 = leader_ptr(m, side)              # own leader
    if a4 == 0:
        if mode(m, side) != 0:
            wb(m, r, 0xe); wb(m, r + 2, 1); wb(m, r + 1, 0); ww(m, r + 8, 1); ww(m, r + 28, 0)
        return
    if rw(m, a4 + 8) == rw(m, r + 30) and rw(m, r + 28) != 0:
        ww(m, r + 28, rw(m, r + 28) - 1)
    if sw(m, a4 + 4) < 6000:
        if rw(m, r + 28) != 0:
            if magnet(m, side) != rw(m, r + 30):
                cmd_cell(m, side, 5, rw(m, r + 30)); return
        else:
            t = rl(m, r + 42)
            if magnet(m, side) != rw(m, t + 8):
                cmd_cell(m, side, 5, rw(m, t + 8))
                ww(m, r + 30, rw(m, t + 8)); ww(m, r + 28, 2)
                return
        if mode(m, side) != 0:
            set_mode_cmd(m, side, 0)
        return
    # own leader strength >= 6000
    if a3 != 0 and sw(m, a4 + 4) > s16(sw(m, a3 + 4) + 500) and mode(m, other(side)) == 0:
        if rw(m, r + 14) & 4:                         # CAN ATTACK LEADER
            if mode(m, side) != 0:
                set_mode_cmd(m, side, 0)
            elif magnet(m, side) != magnet(m, other(side)):
                cmd_cell(m, side, 5, magnet(m, other(side)))
        return
    if rw(m, r + 14) & 2:                             # CAN ATTACK TOWNS
        t = rl(m, r + 34)
        if magnet(m, side) != rw(m, t + 8) and rw(m, r + 28) == 0:
            cmd_cell(m, side, 5, rw(m, t + 8))
            ww(m, r + 30, rw(m, t + 8)); ww(m, r + 28, 2)
            return
        if mode(m, side) != 0:
            set_mode_cmd(m, side, 0)


# ---------------------------------------------------------------- $13dce
def target_13dce(m, side):
    r = rec(side)
    if rw(m, sidest(side)) == 0:
        mg = magnet(m, side)
        occ = rb(m, OCC + s16(mg))
        if occ != 0 and rb(m, WALK + s16(occ - 1) * WSZ + 1) != side:
            wb(m, r + 1, mg & 0x3f); wb(m, r + 2, s16(mg) >> 6)
            return
    t = rl(m, r + 38)
    x = (rw(m, t + 8) & 0x3f) - 3
    y = (sw(m, t + 8) >> 6) - 3
    wb(m, r + 1, max(x, 0)); wb(m, r + 2, max(y, 0))


# ---------------------------------------------------------------- $13a44
def powers_13a44(m, side):
    r = rec(side)
    if rw(m, r + 8) != 0:
        return
    o = rw(m, r + 14)
    mn = mana(m, side)
    if o & 0x100 and mn > s32(rl(m, COST_ARMA) + 999) and \
            sl(m, sidest(side) + 8) > sl(m, sidest(other(side)) + 8):
        wb(m, r, 0xe); wb(m, r + 2, 3); ww(m, r + 8, 1); return
    if o & 0x80 and mn > s32(rl(m, COST_FLOOD) + 1999):
        wb(m, r, 0xe); wb(m, r + 2, 4); ww(m, r + 8, 1); return
    if o & 0x20:
        lp = leader_ptr(m, side)
        if lp and sw(m, lp + 4) > 3000:
            if mn > s32(rl(m, COST_KNIGHT) + 500):
                wb(m, r, 0xe); wb(m, r + 2, 5); ww(m, r + 8, 1)
            return
    if rl(m, r + 38) == 0:
        return
    if mn > s32(rl(m, COST_VOLC) + 500) and o & 0x40:
        wb(m, r, 6); target_13dce(m, side); ww(m, r + 8, 1); ww(m, r + 18, 0); return
    c = sw(m, r + 18)
    if mn > s32(rl(m, COST_SWAMP) + 500) and o & 0x10:
        ok = not (c < sw(m, r + 26) and (o & 8))
        ok = ok and not (c > sw(m, r + 24) and (o & 0x40))
        if ok:
            e = s16(rw(m, sidest(other(side))) - 1)
            own = s16(rw(m, sidest(side)) - 1)
            if e != -1:
                if own == -1 or sw(m, WALK + e * WSZ + 4) > sw(m, WALK + own * WSZ + 4):
                    ww(m, r + 18, c + 1)
                    cell = rw(m, WALK + e * WSZ + 8)
                    wb(m, r, 4); wb(m, r + 1, cell & 0x3f); wb(m, r + 2, s16(cell) >> 6)
                    return                                # note: no busy flag
    if mn > s32(rl(m, COST_QUAKE) + 500) and rb(m, rl(m, r + 38)) == 1 and o & 8:
        if c < sw(m, r + 26) or (o & 0x50) == 0:
            wb(m, r, 3); target_13dce(m, side); ww(m, r + 8, 1); ww(m, r + 18, c + 1)


# ---------------------------------------------------------------- $135fc
def hgt(m, x, y): return sw(m, HGT + s16(x + y * 0x41) * 2)


def flatten_135fc(m, cell, side):
    """returns the low byte of D0 (stored by $db4c in walker+$14)."""
    r = rec(side)
    if not (rw(m, r + 14) & 1):
        return 0
    if rw(m, FLAGS) & 4:
        return 4
    x0, y0 = cell & 0x3f, s16(cell) >> 6
    h0 = hgt(m, x0, y0)
    for k in range(81):
        px = x0 + sb(m, OFFS + 2 * k)
        py = y0 + sb(m, OFFS + 2 * k + 1)
        if px < 0 or px > 0x40 or py < 0 or py > 0x40:
            continue
        idx = s16(px + (py << 6))
        ob = rb(m, OBJ + idx)
        if ob == 0x2f and not (rw(m, FLAGS) & 8):
            wb(m, OBJ + idx, ob + 1)
            cmd(m, side, 2, px, py); return 0
        d = s16(h0 - hgt(m, px, py))
        if d > 0:
            cmd(m, side, 1, px, py); return 0
        if (d < 0 or ob == 0x42 or ob == 0x35) and not (rw(m, FLAGS) & 8):
            cmd(m, side, 2, px, py); return 0
    return 1


# ---------------------------------------------------------------- $13816
def level_13816(m, cell, side):
    r = rec(side)
    if rw(m, r + 8) != 0: return
    if sl(m, sidest(side) + 12) < 20: return
    if sw(m, sidest(side) + 6) > 50: return
    if not (rw(m, r + 14) & 1): return
    if rw(m, FLAGS) & 4: return
    x0, y0 = cell & 0x3f, s16(cell) >> 6
    s = s16(hgt(m, x0, y0) + hgt(m, x0 + 1, y0) + hgt(m, x0 + 1, y0 + 1) + hgt(m, x0, y0 + 1))
    if s == 1: return
    q = int(s / 4)                       # divs: truncates toward zero
    rem = s - q * 4                      # remainder takes the dividend's sign
    for px in (x0, x0 + 1):
        for py in (y0, y0 + 1):
            if rem == 3:
                if hgt(m, px, py) == q:
                    cmd(m, side, 1, px, py); return
            elif rem == 1:
                if hgt(m, px, py) > q and not (rw(m, FLAGS) & 8):
                    cmd(m, side, 2, px, py); return
