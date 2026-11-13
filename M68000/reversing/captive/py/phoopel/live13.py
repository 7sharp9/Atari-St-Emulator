"""Live checks in the emulator's own D0=13 base (base13.snap, built by enter13.repl: labelled pokes 32(A6) = 13 and
request word = 4 from ld_1.snap; the call ran with D0 = 13, D2 = 0).
1. live tile layer fed 9242(A6) vs the chained model's tile layer, bit 7 ignored;
2. the object record at (7,9) in the live object list (generator pointer 13724 = $1bf3a);
3. labelled pokes of the party (x, y, facing at fed 26/28/30(A6)) beside the door, then keypad forward ($68),
   same snapshot: towards the door (6,9) facing E, and the control (6,9) facing W into the open cell (5,9);
   and a third: (8,9) is not reachable, but standing there facing W also tests the door from the far side.
Renders each pre-step view."""
import os, sys, subprocess
import os as _os
_M = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/ai')
sys.path.insert(0, _M + '/reversing/captive/py/mapgen/full')
from cap import R, StServer, A6  # noqa: E402
import chain_run as CR  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
snap = os.path.join(HERE, 'base13.snap')
s = StServer(R)
s('load', snapshot=snap)
base = s('fork')['id']
live = s.read(A6 + 9242, 2048)
m, full, regs = CR.generate(13, 0)
t = int.from_bytes(m[13684:13688], 'big') - CR.FED
model = full[t:t + 2048]
eq = sum((a & 0x7f) == (b & 0x7f) for a, b in zip(live, model))
print(f'live tile layer == model (bit 7 ignored): {eq}/2048; model returned D0 {regs[0]}')
print('diffs:', [(i % 64, i // 64, hex(live[i]), hex(model[i])) for i in range(2048) if (live[i] & 0x7f) != (model[i] & 0x7f)][:10])
print('live tile (7,9):', hex(live[9 * 64 + 7]), 'neighbours (6,9),(8,9),(7,8),(7,10):',
      [hex(live[y * 64 + x]) for x, y in ((6, 9), (8, 9), (7, 8), (7, 10))])
# object list: header at the generator's pointer
hdr = 0x1bf3a
blk = s.read(hdr, 0x800)
p = 4
found = None
while p < 0x800:
    pos, ln = int.from_bytes(blk[p:p + 2], 'big'), int.from_bytes(blk[p + 2:p + 4], 'big')
    if ln & 0x8000 or ln == 0:
        break
    if pos == 0x0709:
        found = blk[p:p + ln].hex()
    p += ln
print('live object record at (7,9):', found)
# fed 2412(A6) per ai.md is the object list the game uses; print its pointer region for comparison
print('fed 2412(A6) = $%x' % (A6 + 2412))
w = lambda a: int.from_bytes(s.read(a, 2), 'big')
print('party at load:', w(A6 + 26), w(A6 + 28), 'face', w(A6 + 30), 'mode', w(A6 + 13564))
for name, (px, py, f) in {'toward_door_E': (6, 9, 3), 'control_W': (6, 9, 1), 'farside_W': (8, 9, 1)}.items():
    s('restore', id=base)
    s('poke', addr=A6 + 26, width=2, value=px)
    s('poke', addr=A6 + 28, width=2, value=py)
    s('poke', addr=A6 + 30, width=2, value=f)
    s('step', n=180000)
    ahead = s.read(A6 + 15408, 1)[0]
    pre = os.path.join(HERE, f'view_{name}.snap')
    s('save', path=pre)
    subprocess.run(['uv', 'run', 'python', '-I', os.path.join(R, 'tools', 'snap_render.py'), pre, pre[:-5] + '.png'],
                   cwd=R, check=True, capture_output=True)
    before = (w(A6 + 26), w(A6 + 28), w(A6 + 30))
    for _ in range(2):
        s('kbd', bytes=[0x68]); s('step', n=60000); s('kbd', bytes=[0xe8]); s('step', n=300000)
    after = (w(A6 + 26), w(A6 + 28), w(A6 + 30))
    print(f'{name}: poked ({px},{py}) f{f}; after settle {before}, cell ahead 15408(A6) ${ahead:02x}; after 2 x forward {after}')
s.close()
