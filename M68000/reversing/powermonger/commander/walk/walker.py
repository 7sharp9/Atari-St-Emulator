"""walker.py - a per-tick model of one man in the walk modes $10/$12/$4a/$48, started from his full record state.

Transcribed from the code (listings in this dir's README/report; tools/disassemble.py --snap <snap> --all):
  $14f08 mode $10, $14ff8 mode $12, $1597a mode $4a, $158da mode $48, epilogues $161c4 / $16202 / $1622c.
State fields are the record's own bytes: x 8, y 10, sx 12, sy 13, heading 17, dwell 18, tx 20, ty 22, w28 28,
prev 30, mode 31, carried 33, sweep 40, flags 7, w42 42.

tick() returns the new state, or raises Unmodelled for: chase (prev $2e), the group hand-off ($14fa2 with a
lead whose group is in state 8: needs the group table), $4a with w28 != 0 (needs the lead's live position),
and any mode outside the four.
"""
import sys
from pathlib import Path

here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'reversing/powermonger/commander'))
import astar  # noqa: E402
from astar import s8, s16, ref  # noqa: E402

WALK = (0x10, 0x12, 0x48, 0x4a)


class Unmodelled(Exception):
    pass


FIELDS = dict(x=(8, 2, True), y=(10, 2, True), sx=(12, 1, True), sy=(13, 1, True), heading=(17, 1, False),
              dwell=(18, 2, True), tx=(20, 2, True), ty=(22, 2, True), w28=(28, 2, False), prev=(30, 1, False),
              mode=(31, 1, False), carried=(33, 1, False), sweep=(40, 2, True), flags=(7, 1, False),
              w42=(42, 2, False), speed=(16, 1, False))


def decode(rec):
    st = {}
    for k, (o, n, sg) in FIELDS.items():
        st[k] = int.from_bytes(rec[o:o + n], 'big', signed=sg)
    return st


CMP = ('x', 'y', 'sx', 'sy', 'heading', 'dwell', 'tx', 'ty', 'prev', 'mode', 'sweep')


def _clamp(x, y):
    return ref._clamp(x & 0xffff, y & 0xffff)


def tick(mp, st, group_state=None, lead_pos=None, chase_static=False):
    """one pass of the iterator over this record. group_state(w42) -> group exec state, or None.
    lead_pos: the (x, y) $4a copies into the target when w28 != 0 (a follower); None -> Unmodelled.
    chase_static: prev $2e is modelled against a chased entity standing at the target words (contact at reached
    -> mode := 'contact' marker $100, $15302 not modelled further); False -> Unmodelled."""
    s = dict(st)
    mode = s['mode']
    x, y = s['x'], s['y']
    if mode == 0x10:
        if s['prev'] == 0x2e:
            if not chase_static:
                raise Unmodelled('chase')
            sx, sy, dwell, hd = mp._step(x, y, s['tx'], s['ty'], s['speed'])
            s.update(sx=sx, sy=sy, dwell=s16(dwell), heading=hd)
            if dwell == 0:
                s['mode'] = 0x100                         # $15302 contact
                return s
            dwell = 3                                     # $14f3e
            s['dwell'] = 3
        else:
            sx, sy, dwell, hd = mp._step(x, y, s['tx'], s['ty'], s['speed'])
            s.update(sx=sx, sy=sy, dwell=s16(dwell), heading=hd)
        if dwell == 0:                                    # $14fdc
            s['mode'] = s['prev']
            nx, ny = s['tx'], s['ty']
            if s['flags'] & 0x20:
                nx, ny = _clamp(nx, ny)
                s['x'], s['y'] = s16(nx), s16(ny)
                return s
            return _epi_161c4(mp, s, nx, ny)
        if s['carried'] != 0x0a:
            px, py, d2 = x, y, dwell - 1
            while True:
                px, py = (px + sx) & 0xffff, (py + sy) & 0xffff
                if mp.sample(px, py) == 0:
                    break
                d2 -= 1
                if d2 == -1:
                    break
            if d2 >= 0:
                s['mode'] = 0x4a                          # $14f98, bra $1622c: no write-back
                return s
        if (s['flags'] & 0x10) and s['w42'] != 0:         # $14fa2
            gs = group_state(s['w42']) if group_state else None
            if gs is None:
                raise Unmodelled('handoff-unknown-group')
            if gs == 8:
                if s['dwell'] <= 0x12:
                    raise Unmodelled('handoff-1518a')
                s['dwell'] = (s['dwell'] & 0xffff) >> 1
        s['mode'] = 0x12
        mode = 0x12
    if mode == 0x12:                                      # $14ff8
        nx, ny = x + s['sx'], y + s['sy']
        s['dwell'] = s16(s['dwell'] - 1)
        if s['dwell'] <= 0:
            s['mode'] = 0x10
        return _epi_161c4(mp, s, nx, ny)
    if mode == 0x4a:                                      # $1597a
        if s['w28'] != 0:
            if lead_pos is None:
                raise Unmodelled('4a-follower')
            s['tx'], s['ty'] = lead_pos
        s['sweep'] = 8
        s['heading'] &= 0xfc
        s['mode'] = 0x48
        return _epi_161c4(mp, s, x, y)
    if mode == 0x48:                                      # $158da
        d0, d1 = ref.rotate(mp.m, 0, (-s['speed']) & 0xffff, s['heading'])
        d3, d4 = s16(d0), s16(d1)
        s['sx'], s['sy'] = s8(d0), s8(d1)
        d2 = s['dwell'] if s['dwell'] < 0x100 else 0x100
        px, py = x, y
        while True:
            px = s16(px + d3)
            if px < 0:
                break
            py = s16(py + d4)
            if py < 0:
                break
            if px >= 0x4000:
                break
            if mp.sample(px, py) == 0:
                break
            d2 = s16(d2 - 1)
            if d2 == -1:
                break
        if d2 < 0:
            s['mode'] = 0x12
            return _epi_16202(s, x, y)
        sw = s['sweep']
        s['heading'] = (s['heading'] + sw) & 0xff
        if s8(sw) >= 0:
            s['sweep'] = s16(-(sw + 4))
            return _epi_16202(s, x, y)
        if sw == 0x80:
            s['dwell'] = s16(s['dwell'] - 8)
            if s['dwell'] < 0:
                return _epi_161c4(mp, s, x, y)
            s['mode'] = 0x4a
            s['heading'] = (s['heading'] + 0x80) & 0xff
            return _epi_16202(s, x, y)
        s['sweep'] = s16(-sw + 4)
        return _epi_16202(s, x, y)
    raise Unmodelled('mode %02x' % mode)


def _epi_16202(s, x, y):
    x, y = _clamp(x, y)
    s['x'], s['y'] = s16(x), s16(y)
    return s


def _epi_161c4(mp, s, x, y):
    x, y = _clamp(x, y)
    if mp.sample(x, y) == 0:
        s['mode'] = 0                                     # $161f0, bra $1622c: no write-back
        return s
    s['flags'] &= ~0x20
    s['x'], s['y'] = s16(x), s16(y)
    return s


def simulate(mp, st, ticks, resets=None, group_state=None, lead_pos=None, chase_static=False):
    """run from state st for `ticks` ticks. resets: optional set of ticks at which an outside writer puts the man
    back in mode $10 toward the same target (the $34f2 / job re-dispatch seen live). Returns (arrived, tick, state)."""
    s = dict(st)
    for t in range(ticks):
        if resets and t in resets:
            s['mode'] = 0x10
        if s['mode'] == 0x100:
            return True, t, s
        if s['mode'] not in WALK:
            return (s['x'], s['y']) == (s['tx'], s['ty']), t, s
        s = tick(mp, s, group_state, lead_pos, chase_static)
    return False, ticks, s
