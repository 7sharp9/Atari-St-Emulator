"""Does the DIE item ($1207c) give away a coded door's corner order?  And does the lock ($e270) answer per corner?

    uv run python -I reversing/captive/py/ai/die_hint.py [snap]   (default scratchpad/captive/base1/outside.snap)
    DIE_TILE=42 ... pokes the door cell's tile (the compound door is $44, kind 4; base doors are kind 2)

Part A (die): from the compound state, labelled pokes put the party on (22,20), the cell north of the coded door
(22,21) (party x, y, facing = fed 26/28/30(A6), world.md section 3), the game runs 120,000 steps so the view
refreshes the local cell copy (15408(A6) is read by $120ca), then $1207c is called N times with A0 at a scratch
4-byte record and byte 3(A0) (the die face) is tallied. This is repeated for each facing and for each count of
corners already pressed (door state low nibble, labelled poke of the list entry at fed 2330(A6) = $1bee8).
Control: the same calls with the party facing away, or the door list entry's cell word poked to a cell nobody
stands before.

Part B (lock): the click handler $e270 is called with the click position 15152/15154(A6) poked to the centre of
each corner zone and 68(A6) = the door cell, from a cleared state ($0080), for the right order (code 8: TL BL TR BR)
and for wrong first corners; the state word is printed after every press.
"""
import os
import sys
from collections import Counter


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import R, W, srv  # noqa: E402

A6 = 0x1b5ce
DOORS = A6 + 2330          # $1bee8
POSX, POSY, FACE = A6 + 26, A6 + 28, A6 + 30
CELLAHEAD = A6 + 15408
CELL68 = A6 + 68
CLICKX, CLICKY = A6 + 15152, A6 + 15154
CORNER = {'TL': (0x46, 0x50), 'TR': (0x86, 0x50), 'BL': (0x46, 0x90), 'BR': (0x86, 0x90)}
CI = {'TL': 0, 'TR': 1, 'BL': 2, 'BR': 3}
N = 300
MAP = A6 + 9242
TILE = int(os.environ['DIE_TILE'], 16) if os.environ.get('DIE_TILE') else None


def w16(s, a, v):
    s('poke', addr=a, width=2, value=v)


def r16(s, a):
    return int.from_bytes(s.read(a, 2), 'big')


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(W, 'base1', 'outside.snap')
    s = srv(snap)
    print('party', r16(s, POSX), r16(s, POSY), 'facing', r16(s, FACE), 'door list', s.read(DOORS, 32).hex())
    base = s('fork')['id']
    scratch = s.reg('a7') - 0x400
    door = s.read(DOORS, 4)
    dx, dy = door[0], door[1]
    state0 = int.from_bytes(door[2:4], 'big')
    print(f'door ({dx},{dy}) state ${state0:04x} code {(state0 >> 4) & 0x1f}')
    print('Part A: die faces (byte 3 of the record) over', N, 'calls of $1207c')
    for face in range(4):
        for pressed in range(4):
            s('restore', id=base)
            w16(s, POSX, dx)
            w16(s, POSY, dy - 1)
            w16(s, FACE, face)
            # corners pressed so far in the right order TL BL TR BR (labelled poke of the state low nibble)
            nib = 0
            for c in ['TL', 'BL', 'TR', 'BR'][:pressed]:
                nib |= 1 << CI[c]
            w16(s, DOORS + 2, (state0 & 0x1f0) | nib)
            if TILE is not None:  # labelled poke: the door cell's map tile (fed 9242(A6) = $1d9e8, y*64+x)
                s('poke', addr=MAP + dy * 64 + dx, width=1, value=TILE)
            s('step', n=120000)
            ahead = s.read(CELLAHEAD, 1)[0]
            s.sp = None
            tally = Counter()
            for _ in range(N):
                s('poke', addr=scratch, width=4, value=0)
                s.call(0x1207c, a0=scratch)
                tally[s.read(scratch + 3, 1)[0]] += 1
            print(f'  facing {face} pressed {pressed} cell-ahead tile ${ahead:02x} 68(A6)=${r16(s, CELL68):04x}:',
                  ' '.join(f'${k:02x}x{v}' for k, v in sorted(tally.items())))
    print('Part B: lock state after each press ($e270), door state starts', f'${state0 & 0x1f0:04x}')
    for seq in (['TL', 'BL', 'TR', 'BR'], ['TR', 'BL', 'TL', 'BR'], ['BR', 'TL', 'BL', 'TR'], ['TL', 'TR', 'BR', 'BL'],
                ['TL', 'TL']):
        s('restore', id=base)
        w16(s, DOORS + 2, state0 & 0x1f0)
        s.sp = None
        out = []
        for c in seq:
            x, y = CORNER[c]
            w16(s, CLICKX, x)
            w16(s, CLICKY, y)
            w16(s, CELL68, (dx << 8) | dy)
            r = s.call(0xe270, stops=[0xc420], d2=0x44)
            pc = int(str(r.get('pc', '0')).lstrip('$'), 16) if 'pc' in r else s.reg('pc')
            out.append(f'{c}->${r16(s, DOORS + 2):04x}' + (' OPEN($c420)' if pc == 0xc420 else ''))
        print('  ', ' '.join(out))
    s.close()


main()
