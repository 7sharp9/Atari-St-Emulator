"""Live check of the hero-proximity trigger boxes (`$00e5a0`) of the Amazon ambushers (README "Spawn types", item c).

    ATARI_NOTRACE=1 uv run python trigger_scan.py

`$e5a0` (D0 = x radius, D1 = y radius, D2/D3 = offset of the object) shifts the object by (D2, D3), gives the hero a
virtual hit box (centre offset (-D0, -D1), half sizes (2*D0+$20, 2*D1+$18) as bytes) and runs the `$b71a` contact test.
`$b71a` (A0 = object, A1 = hero): per axis, with d = (pos + offset)(A0) - (pos + offset)(A1), it passes when
d >= 0 and d < half-size(A1), or d < 0 and -d < half-size(A0). Both axes must pass; the result is the Z flag.

For each ambusher the script stops the emulator at `$e5e4` (right after `jsr $b71a`, before `move SR,D0`) with `bp`, keeps
going until A0 is the object under test, reads every input of the test from RAM at that moment (object x, y, offsets, half
sizes as `$e5a0` left them, the hero's virtual box) and compares Z with the formula. The hero is POKED to a spread of
positions around the predicted box (labelled: the hero is pinned at x = 192 by the camera, so it cannot be walked there).
Prints the predicted box as hero-top-left minus object-top-left, and matched/checked.
"""
import os, sys, struct, re
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl

P = 'scratchpad/impossamole/'
CASES = [  # label, snapshot, slot, (D0, D1, D2, D3) as passed by the handler
    ('111 tentacle  $015a48: D0=8 D1=8 D2=0 D3=-8', P + 'pass99/cyc5.snap', 10, (8, 8, 0, -8), 'tentacle'),
    ('129 chameleon $015cd6: D0=8 D1=8 D2=+32(10(A1)) D3=-8', P + 'pass103/room160.snap', 9, (8, 8, 32, -8), 'cham'),
    ('113 rock      $1439e: D0=0 D1=$20 D2=0 D3=$20', P + 'pass103/live_c1.snap', 7, (0, 0x20, 0, 0x20), 'rock'),
]


def contact(ax, ox, oh, hx, hh):
    """One axis of `$b71a`: A0 = object (position+offset ox, half size oh), A1 = hero (hx, hh)."""
    d = ox - hx
    return d < hh if d >= 0 else -d < oh


def regs(lines):
    out = {}
    for l in lines:
        for m in re.finditer(r'([AD]\d):([0-9a-f]{8})', l):
            out[m.group(1)] = int(m.group(2), 16)
        if l.startswith('CCR:'):
            out['CCR'] = l.split(':')[1].strip()
        if l.startswith('PC:'):
            out['PC'] = int(l.split(':')[1], 16)
    return out


def reset(r, o, kind):
    """Put the object back into its pre-trigger state (labelled poke) so its handler calls `$e5a0` again."""
    a = o['addr']
    if kind == 'tentacle':                       # waiting on its hidden second frame, unfrozen
        r.poke(a + 26, (2).to_bytes(2, 'big'))
        r.poke(a + 100, b'\0')
    elif kind == 'cham':                         # idle animation, cooldown over
        r.poke(a + 78, b'\0')
        r.poke(a + 22, (0x2208c).to_bytes(4, 'big') + (0).to_bytes(2, 'big'))
    elif kind == 'rock':
        r.poke(a + 78, b'\0')
        r.poke(a + 82, (0).to_bytes(2, 'big'))


def sample(r, addr, hx, hy, kind):
    """Reset the object, poke the hero, run until `$e5a0` finishes for object `addr`; return (Z, formula, positions)."""
    reset(r, r.obj((addr - 0x1a2ea) // 108), kind)
    r.poke(0x1a574, (hx & 0xffff).to_bytes(2, 'big') + (hy & 0xffff).to_bytes(2, 'big'))
    for _ in range(6):
        out = r.run('s 1', 'bp e5e4 400000')
        g = regs(out)
        if g.get('PC') == 0xe5e4 and g.get('A0') == addr:   # the bp really stopped here (no stale registers)
            mem = r.mem(addr, 108)
            hero = r.mem(0x1a572, 108)
            S = lambda b, o: struct.unpack_from('>h', b, o)[0]
            ox, oy = S(mem, 2) + S(mem, 8), S(mem, 4) + S(mem, 10)
            hx_, hy_ = S(hero, 2) + S(hero, 8), S(hero, 4) + S(hero, 10)
            pred = contact('x', ox, mem[12], hx_, hero[12]) and contact('y', oy, mem[13], hy_, hero[13])
            z = g['CCR'][13] == '1'
            return z, pred, (S(hero, 2), S(hero, 4), S(mem, 2), S(mem, 4))
    return None, None, None


def main():
    for label, snap, slot, d, kind in CASES:
        with Repl(snap) as r:
            r.run('w bb74 12120300')
            o = r.obj(slot)
            raw = o['raw']
            S = lambda b, k: struct.unpack_from('>h', b, k)[0]
            off8, off10, w0, h0 = S(raw, 8), S(raw, 10), raw[12], raw[13]
            D0, D1, D2, D3 = d
            W, H = (2 * D0 + 0x20) & 0xff, (2 * D1 + 0x18) & 0xff
            # hero top-left minus object top-left, open intervals from the formula (unscrolled object position)
            rx = (D2 + off8 - W + D0, D2 + off8 + w0 + D0)
            ry = (D3 + off10 - H + D1, D3 + off10 + h0 + D1)
            print(f'{label}\n   object box {w0}x{h0} off ({off8},{off10}); hero half sizes {W}x{H}; '
                  f'fires for hero-minus-object dx in ({rx[0]},{rx[1]}), dy in ({ry[0]},{ry[1]})')
            ok = n = 0
            tests = []
            cx, cy = (rx[0] + rx[1]) // 2, (ry[0] + ry[1]) // 2
            for dx in (rx[0] - 8, rx[0] - 1, rx[0] + 1, rx[0] + 8, cx, rx[1] - 8, rx[1] - 1, rx[1] + 1, rx[1] + 8):
                tests.append((dx, cy))
            for dy in (ry[0] - 8, ry[0] - 1, ry[0] + 1, ry[0] + 8, ry[1] - 8, ry[1] - 1, ry[1] + 1, ry[1] + 8):
                tests.append((cx, dy))
            for dx, dy in tests:
                o = r.obj(slot)
                z, pred, info = sample(r, o['addr'], o['x'] + dx, o['y'] + dy, kind)
                if z is None:
                    print(f'   dx {dx:4d} dy {dy:4d}: no e5a0 call seen for this object')
                    continue
                n += 1
                ok += (z == pred)
                inside = rx[0] < dx < rx[1] and ry[0] < dy < ry[1]
                print(f'   dx {dx:4d} dy {dy:4d}: formula {"hit" if pred else "miss"}, Z {"hit" if z else "miss"}, static-box {"in" if inside else "out"}')
            print(f'   {ok}/{n} b71a result equals the formula', flush=True)


if __name__ == '__main__':
    main()
