"""The $c194 item branch driven live (Captive). A FLAMBOS ($5a) or BATTERY ($1a) dropped into a flame cell (tile $26)
gets its SHOTS count set to $3c = 60; ACID ($59) dropped on tile $1e gets $32 = 50 (`mapgen.md` "Sealed keys").

$c194 is entered from $c0e6 with A1 = the target cell's tile byte; the record being placed is 172(A6) = hand slot
404(A6) << 8 (byte 0 type, byte 1 = hand byte 2, byte 2 = hand byte 3 = SHOTS, byte 3 = sub-position from $ce24).
Arms, all from one snapshot, labelled pokes: party cell and facing (26/28/30(A6)), hand slot 404(A6) = $80 <type> $07
$11. Click methods: 'drop' (pointer y 138: cell ahead, $dbee/$c0d6), 'foot' (y 155: own cell, $c0de), 'throw' (y 105,
$def0/$f3b4). Signals: hits on the branch addresses, write watches on the target and party cells, the object-list
record (list at 2412(A6)), a second click with an empty hand to pick the record up, renders.
Usage (from M68000/): uv run python -I reversing/captive/py/items/itemdrop.py [snap]
  default snap scratchpad/captive/agents/curios/base30.snap
Output: scratchpad/captive/items/<arm>_{before,after,picked}.png"""
import os, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    nd = os.path.dirname(d)
    if nd == d:
        sys.exit('repo root not found')
    d = nd
R = os.environ.get('M68000_ROOT', d)
sys.path.insert(0, os.path.join(R, 'reversing/captive/py/ai'))
from cap import StServer, A6, W, snappath  # noqa: E402

OUTD = os.path.join(W, 'items')
os.makedirs(OUTD, exist_ok=True)

SNAP = sys.argv[1] if len(sys.argv) > 1 else 'agents/curios/base30.snap'
# party cell: (50,15) is tile $26 to the S (facing 2), (49,14) is $20 to the W (facing 1)
ARMS = [  # (name, hand type, facing, click method); control items EXPLOSIVES $1b, ACID $59 (not $5a/$1a); control cell facing 1 (tile $20)
    ('drop_flambos_26', 0x5a, 2, 'drop'), ('drop_battery_26', 0x1a, 2, 'drop'), ('drop_explosives_26', 0x1b, 2, 'drop'),
    ('drop_acid_26', 0x59, 2, 'drop'), ('drop_flambos_20', 0x5a, 1, 'drop'), ('drop_battery_20', 0x1a, 1, 'drop'),
    ('foot_flambos_20', 0x5a, 1, 'foot'), ('foot_flambos_26ahead', 0x5a, 2, 'foot'), ('throw_flambos_26', 0x5a, 2, 'throw'), ('throw_flambos_20', 0x5a, 1, 'throw'),
]
EXTRA = [('drop_acid_1e', 0x59, 'drop'), ('drop_flambos_1e', 0x5a, 'drop')]   # tile $1e: the $c1be/$c1c6 branch, ACID -> byte 3 = $32
CLICK = {'drop': (110, 138), 'foot': (50, 155), 'throw': (100, 105)}  # pointer = hotspot - (8,7): $dbee band y in [$8a,$98) = cell ahead; y >= $98 = own cell
ADDRS = ['$db7e', '$dbb2', '$dbee', '$def0', '$f3b4', '$f7b0', '$c0d6', '$c0de', '$c0e6', '$c194', '$c1b0', '$c1c6', '$c1cc', '$c1e2', '$c21e', '$dbd0']
VEC = ((0, -1), (-1, 0), (0, 1), (1, 0))
s = StServer(R)
s('load', snapshot=snappath(SNAP))
base = s('fork')['id']
rd = lambda off, n=2: s.read(A6 + off, n)
w = lambda off: int.from_bytes(rd(off), 'big')
tile = lambda x, y: s.read(A6 + 9242 + y * 64 + x, 1)[0]
counts = {}


def run(n):
    h = s('hits', steps=n, addrs=ADDRS)
    for a in h['hits']:
        k = '$%04x' % int(a['addr'].lstrip('$'), 16); counts[k] = counts.get(k, 0) + a['count']


def click(x, y):
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); run(30000)
    while x or y:
        mx, my = min(x, 120), min(y, 120)
        s('mouse', action='move', dx=mx, dy=my); run(30000); x -= mx; y -= my
    s('mouse', action='down', button='l'); run(60000); s('mouse', action='up', button='l'); run(120000)


def objrec(x, y):
    """Records of the object list at 2412(A6) for cell (x,y): walk as $c17a does (word cell, word length, ...)."""
    a = A6 + 2412 + 4
    out = []
    for _ in range(400):
        c = int.from_bytes(s.read(a, 2), 'big'); ln = int.from_bytes(s.read(a + 2, 2), 'big', signed=True)
        if c == (x << 8 | y):
            out.append(s.read(a + 4, max(0, min(ln - 4, 16))).hex())
        if ln < 0 or ln == 0:
            break
        a += ln
    return out


T0 = s.read(A6 + 9242, 2048)
spot = next((i % 64 - dx, i // 64 - dy, f) for i in range(2048) if T0[i] == 0x1e
            for f, (dx, dy) in enumerate(VEC)
            if 0 <= i % 64 - dx < 64 and 0 <= i // 64 - dy < 32 and T0[(i // 64 - dy) * 64 + i % 64 - dx] in (0x20, 0x21))
print('tile $1e spot (party x, y, facing):', spot)
for name, typ, how in EXTRA:
    ARMS.append((name, typ, None, how))
for name, typ, face, how in ARMS:
    s('restore', id=base)
    PX, PY = (50, 14) if face is not None else spot[:2]
    face = face if face is not None else spot[2]
    ax, ay = PX + VEC[face][0], PY + VEC[face][1]
    for off, v in ((26, PX), (28, PY), (30, face)):
        s('poke', addr=A6 + off, width=2, value=v)
    s('poke', addr=A6 + 404, width=4, value=0x80000000 | typ << 16 | 0x0711)
    s('step', n=180000)
    cell_addr = A6 + 9242 + ay * 64 + ax
    pre = f'tile ahead ({ax},{ay}) ${tile(ax, ay):02x}, 15408(A6) ${rd(15408, 1)[0]:02x}, hand ${s.read(A6 + 404, 4).hex()}'
    before = objrec(ax, ay)
    png = os.path.join(OUTD, f'{name}_before.png'); s('render', path=png)
    pc_addr = A6 + 9242 + PY * 64 + PX
    wids = [s('watch_add', lo=a_, hi=a_ + 1, kind='w')['id'] for a_ in (cell_addr, pc_addr)]
    counts.clear()
    click(*CLICK[how])
    ev = [(e['pc'], e['addr'], e['value']) for i in wids for e in s('watch_events', id=i)[0]['events']]
    for i in wids:
        s('watch_remove', id=i)
    after = objrec(ax, ay); after_party = objrec(PX, PY)
    s('render', path=os.path.join(OUTD, f'{name}_after.png'))
    print(f'arm {name}: {pre}')
    print(f'  hits ' + ' '.join(f'{a}:{counts.get(a, 0)}' for a in ADDRS))
    print(f'  cell tile after ${tile(ax, ay):02x}; hand after ${s.read(A6 + 404, 4).hex()}; object records ahead-cell before {before} after {after}, party-cell after {after_party}; tile party cell ${tile(PX, PY):02x}')
    ahead_ev = [e for e in ev if int(e[1].lstrip('$'), 16) == cell_addr]
    print(f'  172(A6) ${s.read(A6 + 172, 4).hex()}; writes to the cell ahead (pc, addr, value) {ahead_ev}; writes to the party cell {len(ev) - len(ahead_ev)} (pcs {sorted({e[0] for e in ev if e not in ahead_ev})})')
    if how == 'drop':      # the same click with an empty hand picks the record up again ($dbe0): its byte 3 is the "SHOTS" count
        click(*CLICK[how])
        print(f'  second click, empty hand (picks the record up, $dbe0): hand ${s.read(A6 + 404, 4).hex()}, tile ahead ${tile(ax, ay):02x}')
        s('render', path=os.path.join(OUTD, f'{name}_picked.png'))
s.close()
