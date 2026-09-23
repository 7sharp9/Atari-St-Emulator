"""ai_ext.py - models of the walker-triggered AI land edits, transcribed from the disassembly.

    f6b2(m, wp, idx)                $f6b2 walker_choose_dir_magnet: full model (all writes + D0.w)
                                    except a knight whose target is invalid (that path calls $fe00:
                                    raises NotModelled)
    ef4c_lower(m, wp, dirv)         the god-record part of $ef4c after the direction routine
                                    returned dirv: the "lower the burnt field" request ($f01a..$f138)
    ef4c_uses_f6b2(m, wp)           $ef4c's choice between $f6b2 and $f2f4 ($ef50..$ef7c)

`m` is a mutable RAM image (absolute addresses), as in ai_ref.py.
"""
import ai_ref as A
from ai_ref import rb, sb, rw, sw, rl, wb, ww, s16

MAP = 0x36e78            # per-cell terrain class byte map (0 water, $2f rock, $35 swamp, $42 burnt)
DIR8 = 0x225a4           # tbl_dir8: 8 signed word cell offsets N NE E SE S SW W NW
SIGN2DIR = 0x225c8       # tbl_sign_to_dir: 3x3 words, index (sx+1)*3+sy
REVERSE = 0x22ae2        # 8 words: index of the direction stored in walker+21 after a detour
ARMA = 0x3d524           # armageddon_on
QUERY = 0x3c4c6          # query_entity (index+1)


class NotModelled(Exception):
    pass


LAST = None     # set by f6b2 / ef4c_lower: which land edit was posted ('raise_water', 'raise_swamp', 'lower_burnt')


def check(m, cell, off):
    """$18198 cell_step_check: 0 land, 1 off-map/row wrap, 2 rock $2f, 3 water."""
    off = s16(off)
    if off == 0:
        return 0
    c = s16(cell + off)
    if c < 0 or c >= 0x1000:
        return 1
    dx = off & 0x3f
    if dx > 3:
        dx -= 64
    x = (cell & 0x3f) + dx
    if x < 0 or x > 0x3f:
        return 1
    t = rb(m, MAP + c)
    return 3 if t == 0 else 2 if t == 0x2f else 0


def sgn(v): return (v > 0) - (v < 0)


def f6b2(m, wp, idx):
    """returns D0.w (direction offset, or 999)."""
    global LAST
    LAST = None
    side = rb(m, wp + 1)
    st = A.sidest(side)
    cell = sw(m, wp + 8)
    kt = rl(m, wp + 14)
    if kt:
        if (cell == sw(m, kt + 8) or sw(m, kt + 4) <= 0 or rb(m, kt + 1) == rb(m, wp + 1)
                or rb(m, kt) & 0x80):
            raise NotModelled('knight target re-acquisition ($fe00)')
        tc = sw(m, kt + 8)
    elif rw(m, st) == 0:
        mg = sw(m, st + 2)
        if mg == cell:
            ww(m, st, idx + 1)
            if rw(m, QUERY) == 0:
                ww(m, QUERY, idx + 1)
            wb(m, wp + 1, side)
        tc = sw(m, st + 2)
    elif s16(rw(m, st) - 1) == s16(idx):
        tc = sw(m, st + 2)
    else:
        lp = A.WALK + s16(rw(m, st) - 1) * A.WSZ
        tc = sw(m, lp + 8)
    sx = sgn(s16((tc & 0x3f) - (cell & 0x3f)))
    sy = sgn(s16((tc >> 6) - (cell >> 6)))
    d = sw(m, SIGN2DIR + ((sx + 1) * 3 + sy) * 2)
    off = sw(m, DIR8 + d * 2)
    r = check(m, cell, off)
    swamp_next = rb(m, MAP + s16(cell + off)) == 0x35
    if r == 0 and not (kt and swamp_next):
        wb(m, wp + 21, off)
        return sb(m, wp + 21)
    arma = rw(m, ARMA) != 0
    if r == 2 and arma:
        wb(m, wp + 21, off)
        return sb(m, wp + 21)
    rec = A.rec(side)
    flags = rw(m, A.FLAGS)
    if (rw(m, rec + 6) == 1 or arma) and (not (flags & 4) or arma):
        if r == 3:
            A.cmd(m, side, 1, cell & 0x3f, cell >> 6); LAST = 'raise_water'
        elif swamp_next and not (flags & 8) and not arma:
            c2 = s16(cell + off)
            A.cmd(m, side, 1, c2 & 0x3f, c2 >> 6); LAST = 'raise_swamp'
    d7 = s16(d - 1)
    for _ in range(8):
        if d7 < 0: d7 = 7
        if d7 > 7: d7 = 0
        o = sw(m, DIR8 + d7 * 2)
        if (check(m, cell, o) == 0 and o != sb(m, wp + 21)
                and not (kt and rb(m, MAP + s16(cell + o)) == 0x35)):
            wb(m, wp + 21, sw(m, DIR8 + sw(m, REVERSE + d7 * 2) * 2))
            return o & 0xffff if o >= 0 else o
        d7 += 1
    wb(m, wp + 21, sw(m, DIR8 + sw(m, REVERSE + d7 * 2) * 2))
    return 999


def ef4c_uses_f6b2(m, wp):
    side = rb(m, wp + 1)
    return rw(m, A.sidest(side) + 4) == 0 or rl(m, wp + 14) != 0 or rw(m, ARMA) != 0


def ef4c_lower(m, wp, dirv):
    """$ef4c after the direction call: a computer walker standing on a burnt field ($42) posts
    cmd 2 (lower) at its cell's corner when the side is not busy and flags&$c == 0. No busy set."""
    global LAST
    LAST = None
    if s16(dirv) == 999:
        return
    side = rb(m, wp + 1)
    rec = A.rec(side)
    cell = sw(m, wp + 8)
    if (rw(m, rec + 6) == 1 and rb(m, MAP + cell) == 0x42 and rw(m, rec + 8) == 0
            and not (rw(m, A.FLAGS) & 0xc)):
        wb(m, rec, 2); wb(m, rec + 1, cell & 0x3f); wb(m, rec + 2, cell >> 6); LAST = 'lower_burnt'
