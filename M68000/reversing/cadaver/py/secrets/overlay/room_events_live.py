"""room_events_live.py: drive the room-record script blocks (room_blocks.py) live on gameplay_empire.snap (CAVERN, level 0).

Tests (each prints hit counts and RAM deltas; run from M68000/):
  entry   room 4 -> room 28 -> room 4 -> room 28 by injecting the events the rooms' own event-15 blocks answer (room 4 gate 1 =
          TELEPORT room $1c, room 28 gate 1 = TELEPORT room 4).  Producers watched: $00e8a6 (event 28 push, first visit only,
          guarded by `bset #6,23(A0)`), $00ead8 (event 6 push, every entry).  Effects watched: verb 36 CREATE (room 28's first-visit
          block makes 3) and verb 21 (room 28's every-entry event-6 block, one per visit), the room id 1166(A5), the rooms-entered counter 2118(A5), the visited bit (room record byte 23 bit 6).
  tick    idle in CAVERN: the room timer ($00909e push of event 14) fires once per room-record byte 2 passes of $00908e.
  xp      BUTTON (id 2) -> room 37: the room's event-6 block `5 c8` adds 26 XP once (non-keep), a second entry adds nothing.

Injection: an entry is [opcode.w][object ptr.l][word.w] = 8 bytes (+ a 4th long, 12 bytes, when bit 15 is set), written at the WRITE pointer 304(A5),
which is then advanced, and 1154(A5) += 1 (writing at 152(A5) alone is overwritten by the game's own pushes in level 1).
Usage: python3 reversing/cadaver/py/secrets/overlay/room_events_live.py [entry|tick|xp ...]"""
import sys, struct
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay'); sys.path.insert(0, 'reversing/cadaver/py'); sys.path.insert(0, 'tools')
from ov import *
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
SNAP = 'scratchpad/cadaver/gameplay_empire.snap'
ram0, base0 = load_ram(SNAP); regs0, _ = snapshot_regs(SNAP); A5V = regs0['a5']
ri, rd, rc = resource_type(ram0, base0, A5V, 3)
t6i, t6d, _ = resource_type(ram0, base0, A5V, 6)
room_rec = lambda s: resolve(ram0, base0, ri, rd, s)
obj_rec = lambda oid: resolve(ram0, base0, t6i, t6d, oid)
VERB = lambda v: 0xffba + struct.unpack_from('>H', ram0, 0xffba - base0 + 2 * v)[0]


def push(r, op, rec, word, long4=None):
    w = int.from_bytes(r.mem(a5(304), 4), 'big')
    wl(r, w, (op << 16) | (rec >> 16)); wl(r, w + 4, ((rec & 0xffff) << 16) | (word & 0xffff))
    n = 8
    if long4 is not None: wl(r, w + 8, long4); n = 12
    wl(r, a5(304), w + n)
    ww(r, a5(1154), r.w(a5(1154)) + 1)


def state(r):
    return dict(room=r.w(a5(1166)), entered=r.w(a5(2118)), xp=r.l(a5(1192)), gold=r.l(a5(1188)), pend=r.w(a5(1154)))


def visited(r, slot): return bool(r.b(room_rec(slot) + 23) & 0x40)


def entry():
    print('verb 36 CREATE handler $%06x  verb 37 TELEPORT $%06x' % (VERB(36), VERB(37)))
    r = Repl()
    W = [0xe8a6, 0xeae4, VERB(21), VERB(36), VERB(37), 0xe854]
    print('start', state(r), 'visited 4/28:', visited(r, 4), visited(r, 28))
    for i, (frm, ev_gate) in enumerate([(4, 1), (28, 1), (4, 1), (28, 1)]):
        push(r, 0xc00f, room_rec(frm), ev_gate, 0)
        h = r.hits(400000, *W)
        s = state(r)
        print('%d: event 15 for room %d -> room now %d  hits %s  %s  visited4/28 %s/%s' % (
            i, frm, s['room'], {hex(k): v for k, v in h.items()}, s, visited(r, 4), visited(r, 28)))
    r.close()


def tick():
    r = Repl()
    period = ram0[room_rec(0) + 2]
    print('room 0 byte 2 (period) =', period, ' ($00908e = timer pass, $00909e = event-14 push)')
    h = r.hits(int(sys.argv[-1]) if sys.argv[-1].isdigit() else 14000000, 0x908e, 0x909e, 0xfe24, VERB(36))
    print({hex(k): v for k, v in h.items()}, 'passes/pushes = %.2f' % (h.get(0x908e, 0) / max(1, h.get(0x909e, 0))))
    r.close()


def xp():
    """BUTTON (id 2) needs the four regalia in the type-8 list (poked as in treasury_gate_live.py); lever 86 goes to room 34."""
    r = Repl()
    d8 = int.from_bytes(ram0[A5V + 96 - base0:A5V + 100 - base0], 'big') + 8 * 0x12
    idx8, dat8 = struct.unpack_from('>II', ram0, d8 - base0)
    for i, oid in enumerate([16, 32, 28, 26]):
        wl(r, idx8 + 4 * i, 0x00010000 | (4 * i)); wl(r, dat8 + 4 * i, oid << 16)
    for i, oid in enumerate([2, 86, 2]):
        s0 = state(r)
        push(r, 0x0005, obj_rec(oid), 0)
        h = r.hits(400000, 0xfe24, VERB(37), 0xe854, 0xe8a6, 0xead8 + 0xc)
        s1 = state(r)
        print('%d: touch object %d: room %d -> %d, XP %d -> %d (%+d), hits %s' % (
            i, oid, s0['room'], s1['room'], s0['xp'], s1['xp'], s1['xp'] - s0['xp'], {hex(k): v for k, v in h.items()}))
    r.close()


if __name__ == '__main__':
    for t in (sys.argv[1:] or ['entry', 'tick', 'xp']):
        print('=== ' + t); globals()[t]()
