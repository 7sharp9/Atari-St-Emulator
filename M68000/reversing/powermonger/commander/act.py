"""act.py: REPL `w` lines for the command-buffer action interface (commander README "Action interface", proven by
gate_inject.sh 7/7).

Encoding (strategy.md "`$58016` - command buffer", with bytes 2/3 as the executor reads them: `$6c36 move.b 2(A0),D0`,
`$6c3a move.b 3(A0),D1`, i.e. x and y as two bytes, not the packed cell that table's row 2 claims):
  slot  $58016 + 6*side: +0 side, +1 order type, +2 x, +3 y, +4 state (2 = harness-owned, the AI writes only in 4), +5 pad
  acting group word $58042 + 2*side := side*$13c + $4c + 2k (strategy.md "`$6ac6`": the group the executor acts for)
`w` writes a longword, so every write covers bytes that belong to someone else (the slot's +4 longword covers the next
side's +0/+1; the acting word's longword covers the next side's word). Poker keeps a working copy of RAM, fills those
bytes from it and applies each write to it, so several actions in one script never clobber each other.

    from act import Poker; p = Poker(ram); p.take(3); p.select(3, 0); p.order(3, 0x0c, 15, 92); p.lines
    act.py <snap> gate          -> prints gate_inject.sh's arms A, B, C regenerated from the snapshot
"""
import struct, sys
from pathlib import Path

SLOTS, ACTING, GSTRIDE = 0x58016, 0x58042, 0x13c


class Poker:
    def __init__(self, ram):
        self.R = bytearray(ram); self.lines = []

    def _w(self, addr, four):
        assert addr % 2 == 0 and len(four) == 4
        self.R[addr:addr + 4] = four
        self.lines.append(f'w {addr:x} {bytes(four).hex()}')

    def slot(self, side, typ, x, y, state=2):
        """The whole slot: two longwords at slot+0 (side, type, x, y) and slot+4 (state, pad, next 2 bytes kept)."""
        assert 1 <= side <= 4 and 0 <= typ < 0x100 and 0 <= x < 64 and 0 <= y < 128
        a = SLOTS + 6 * side
        self._w(a, bytes([side, typ, x, y]))
        self._w(a + 4, bytes([state, self.R[a + 5], self.R[a + 6], self.R[a + 7]]))

    def take(self, side):
        """Slot to state 2 with no order (gate arm A): the side's AI ($6522) stops writing it."""
        self.slot(side, 0, 0, 0, 2)

    def select(self, side, k):
        """The acting group word $58042[2*side] := the offset of group k; the next side's word is kept."""
        assert 0 <= k < 6
        a = ACTING + 2 * side
        self._w(a, struct.pack('>H', side * GSTRIDE + 0x4c + 2 * k) + bytes(self.R[a + 2:a + 4]))

    def order(self, side, typ, x, y, k=None):
        """An order into a state-2 slot; with k the acting group is selected first (gate arm C order)."""
        if k is not None: self.select(side, k)
        self.slot(side, typ, x, y, 2)


def from_json(ram, actions):
    """actions: a dict or list of dicts {"side":3, "take":true} | {"side":3,"type":12,"x":15,"y":92[,"group":0]} |
    {"side":3,"select":0}. Returns the REPL lines."""
    p = Poker(ram)
    for a in actions if isinstance(actions, list) else [actions]:
        if a.get('take'): p.take(a['side'])
        elif 'select' in a: p.select(a['side'], a['select'])
        else: p.order(a['side'], a['type'], a['x'], a['y'], a.get('group'))
    return p.lines


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from observe import load
    R = load(sys.argv[1])
    if sys.argv[2:] == ['gate']:
        A = Poker(R); A.take(3)
        B = Poker(R); B.order(3, 0x0c, 15, 92)
        C = Poker(R); C.order(3, 0x0c, 15, 92, k=0)
        for n, p in (('A', A), ('B', B), ('C', C)): print(n, ' '.join(f'"{l}"' for l in p.lines))
