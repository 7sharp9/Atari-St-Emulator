"""Every key kind's wall panel and every door kind, driven by mouse clicks in the D0 = 13 base (base13.snap).

panels.py <lock> [<lock> ...]      e.g. panels.py 9 7 22 1 17 0 18 4

Extends py/phoopel/panel13.py (key kind 3 only) to key kinds 0-2, door kinds 0-1 and the re-close on byte +8 bit 4.
Labelled pokes only: the party's x, y, facing (fed 26/28/30(A6)), onto the cell W faces (panel arms) or onto an open
cell beside D facing it (walk arms); nothing else. Switch click points come from the click handler $12b4c (pointer
x in D4, y in D5, as latched at 15152/15154(A6)):
  key kind 0  $12c9a: x $62..$6c, y $64..$78                 one switch, bchg #0 of state byte +5
  key kind 1  $12c6a: y $64..$78, col = (x - $59) / 10 <= 2   three switches, bit = col
  key kind 2  $12c2c: row = (y - $65) / 10 <= 1, col = (x - $58) >> 3 <= 3, bit = row * 4 + col
  key kind 3  $12bc2: 5 x 5 cells of 5 pixels from (90,98), bit = $12c12[row * 5 + col] - 1
After every click $12cb8 compares the state word +4 with the code word +2.
Arms per lock (each from the same poked start):
  code     cover, then the code's bits in ascending order: D should change only on the last click
  control  cover, then all but the last code bit plus one wrong bit (key kind 0: cover and no switch click)
  reclose  from the end of `code`, click the last code bit again (state != code), then once more (state = code)
  walk     from the end of `code` (door open) and of `control` (door shut): party beside D facing it, forward twice
Writes snapshots and renders under scratchpad/captive/phoopel/panels/lock<N>/ and one jsonl row per lock to
scratchpad/captive/phoopel/panels/panels.jsonl.
"""
import json, os, sys
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'tools', 'rdis.py')):
    if os.path.dirname(_d) == _d:
        sys.exit('repo root (tools/rdis.py) not found')
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'reversing', 'captive', 'py', 'ai'))
from cap import R, StServer, A6, W  # noqa: E402

OUTD = os.path.join(W, 'phoopel', 'panels')
SNAP = os.path.join(W, 'phoopel', 'base13.snap')
LOCKS, TILES, TABLE = A6 + 8628, A6 + 9242, 0x12c12
VEC = ((0, -1), (-1, 0), (0, 1), (1, 0))   # facing 0 N, 1 W, 2 S, 3 E


def switch_points(s, kind):
    """bit -> (x, y) screen point at the centre of the switch's click zone, from the zone tests of $12b4c."""
    if kind == 0:
        return {0: (103, 110)}
    if kind == 1:
        return {c: (90 + 10 * c + 4, 110) for c in range(3)}
    if kind == 2:
        return {r * 4 + c: (88 + 8 * c + 4, 101 + 10 * r + 5) for r in range(2) for c in range(4)}
    table = s.read(TABLE, 25)
    return {b - 1: (90 + 5 * (i % 5) + 2, 98 + 5 * (i // 5) + 2) for i, b in enumerate(table) if b}


def run(lock):
    od = os.path.join(OUTD, f'lock{lock}')
    os.makedirs(od, exist_ok=True)
    s = StServer(R)
    s('load', snapshot=SNAP)
    w = lambda a: int.from_bytes(s.read(a, 2), 'big')
    rec = lambda: s.read(LOCKS + 10 * lock, 10)
    tile = lambda x, y: s.read(TILES + y * 64 + x, 1)[0]
    r = rec()
    wx, wy, code, dx_, dy_, b8 = r[0], r[1], int.from_bytes(r[2:4], 'big'), r[6], r[7], r[8]
    kk, dk = b8 & 3, (b8 >> 2) & 3
    row = dict(lock=lock, W=(wx, wy), D=(dx_, dy_), code=code, byte8=b8, byte9=r[9], key_kind=kk, door_kind=dk,
               bit4=bool(b8 & 0x10), tileW=tile(wx, wy), tileD=tile(dx_, dy_))
    print(f'lock {lock}: W ({wx},{wy}) tile ${tile(wx, wy):02x} code ${code:04x} D ({dx_},{dy_}) tile ${tile(dx_, dy_):02x} '
          f'byte8 ${b8:02x} (key kind {kk}, door kind {dk}, bit4 {int(bool(b8 & 0x10))}) byte9 ${r[9]:02x}')
    pos = switch_points(s, kk)
    print('  bit -> click point:', pos)
    bits = [b for b in range(16) if code >> b & 1]
    face = tile(wx, wy) & 3
    px, py = wx - VEC[face][0], wy - VEC[face][1]
    print(f'  labelled pokes: party ({px},{py}) facing {face}; tile there ${tile(px, py):02x}')
    s('poke', addr=A6 + 26, width=2, value=px)
    s('poke', addr=A6 + 28, width=2, value=py)
    s('poke', addr=A6 + 30, width=2, value=face)
    s('step', n=180000)
    base = s('fork')['id']

    def click(x, y):
        for _ in range(3):
            s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
        while x or y:
            mx, my = min(x, 120), min(y, 120)
            s('mouse', action='move', dx=mx, dy=my); s('step', n=30000); x -= mx; y -= my
        s('mouse', action='down', button='l'); s('step', n=60000)
        at = (w(A6 + 15152), w(A6 + 15154))
        s('mouse', action='up', button='l'); s('step', n=300000)
        return at

    def park():
        # pin the pointer at the top left (over the crew portraits) so it does not hide the panel in a render
        for _ in range(3):
            s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)

    def state():
        q = rec()
        return dict(state=int.from_bytes(q[4:6], 'big'), byte8=q[8], byte9=q[9], tileD=tile(dx_, dy_), tileW=tile(wx, wy))

    def fmt(st):
        return (f'state ${st["state"]:04x} byte8 ${st["byte8"]:02x} byte9 ${st["byte9"]:02x} tile D ${st["tileD"]:02x} '
                f'tile W ${st["tileW"]:02x}')

    def arm(name, seq, start=None, cover=True):
        s('restore', id=start if start is not None else base)
        s('render', path=os.path.join(od, f'{name}_before.png'))
        log = [dict(click='start', **state())]
        if cover:
            at = click(100, 110)
            log.append(dict(click='cover', at=at, **state()))
            print(f'  {name}: cover at {at}: {fmt(log[-1])}')
            park()
            s('render', path=os.path.join(od, f'{name}_open.png'))
        for b in seq:
            at = click(*pos[b])
            log.append(dict(click=b, at=at, **state()))
            print(f'  {name}: bit {b:2d} at {at}: {fmt(log[-1])}')
        park()
        s('render', path=os.path.join(od, f'{name}_after.png'))
        s('save', path=os.path.join(od, f'{name}_after.snap'))
        return log, s('fork')['id']

    print('  arm code:', bits)
    row['code_arm'], opened = arm('code', bits)
    if kk == 0:
        ctl = []
    else:
        wrong = next(b for b in sorted(pos) if b not in bits)
        ctl = bits[:-1] + [wrong]
    print('  arm control:', ctl)
    row['control_arm'], shut = arm('control', ctl)
    print('  arm reclose: bit', bits[-1], 'twice, from the end of code')
    row['reclose_arm'], _ = arm('reclose', [bits[-1], bits[-1]], start=opened, cover=False)

    # walk: an open neighbour of D (tile $20, occupancy bit 7 clear in the base snapshot), facing D
    s('restore', id=base)
    nb = None
    for f in (3, 1, 2, 0):
        x, y = dx_ - VEC[f][0], dy_ - VEC[f][1]
        if 0 <= x < 64 and 0 <= y < 32 and tile(x, y) == 0x20:
            nb = (x, y, f); break
    row['walk'] = {}
    for name, start in (('open', opened), ('shut', shut)):
        s('restore', id=start)
        x, y, f = nb
        s('poke', addr=A6 + 26, width=2, value=x)
        s('poke', addr=A6 + 28, width=2, value=y)
        s('poke', addr=A6 + 30, width=2, value=f)
        s('step', n=180000)
        s('render', path=os.path.join(od, f'walk_{name}_view.png'))
        steps = []
        for i in range(2):
            ahead = (w(A6 + 26) + VEC[f][0], w(A6 + 28) + VEC[f][1])
            inb = 0 <= ahead[0] < 64 and 0 <= ahead[1] < 32
            waited = 0
            # a creature group on the cell ahead (occupancy bit 7) blocks the step: wait up to 6M steps for it to leave
            while inb and tile(*ahead) & 0x80 and waited < 6000000:
                s('step', n=120000); waited += 120000
            ta = tile(*ahead) if inb else None
            if waited:
                print(f'  walk {name}: waited {waited} steps for occupancy bit 7 to clear at {ahead}: tile ${ta:02x}')
            s('kbd', bytes=[0x68]); s('step', n=60000); s('kbd', bytes=[0xe8]); s('step', n=300000)
            steps.append(dict(ahead=ahead, tile_ahead=ta, waited=waited, party=(w(A6 + 26), w(A6 + 28), w(A6 + 30))))
            print(f'  walk {name} (labelled pokes: party ({x},{y}) facing {f}): forward {i + 1}: tile ahead ${ta:02x} '
                  f'-> party {steps[-1]["party"]}')
        row['walk'][name] = dict(start=(x, y, f), steps=steps)
        s('render', path=os.path.join(od, f'walk_{name}_after.png'))
    s.close()
    with open(os.path.join(OUTD, 'panels.jsonl'), 'a') as fh:
        fh.write(json.dumps(row) + '\n')


for a in sys.argv[1:] or ['9']:
    run(int(a))
