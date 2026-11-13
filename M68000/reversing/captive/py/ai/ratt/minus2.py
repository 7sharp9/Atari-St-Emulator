"""(promoted: reversing/captive/py/ai/ratt/minus2.py; outputs under scratchpad/captive/ratt/) 14800(A6) = -2 ("BASE HAS BEEN DESTROYED!", $87a6) driven by play from a real exit of the natural base.
Start phoopel/revisit/exited.snap (3M steps after the leave click in the natural base; that snapshot's own state came from labelled
pokes of party and hand, revisit.py exit). Steps: 4M steps for the compound rebuild ($90be), face N, click the compound door's code
(TL, BL, TR, BR, as revisit.py blast), walk N 4 cells to (22,18), turn E, step E onto tile $2e (23,18), the landing pad
(the cell the party starts the compound on), then the up icon (202,112). $902e (action 24 of the key/icon dispatch) sets the level-event flag
15608 ($9064) when the tile under the party is $2e and the mode is not 3; $8794 then
finds 14880 (set by $87de at the exit) nonzero and writes -2.
Control: the same walk, but 14880(A6) poked 0 (labelled) before the last step: $87a6 must not run.
Usage: minus2.py [control]"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, OUT
ctl = len(sys.argv) > 1 and sys.argv[1] == 'control'
s = StServer(R); s('load', snapshot=snappath('phoopel/revisit/exited.snap'))
w = lambda o: int.from_bytes(s.read(A6 + o, 2), 'big')
sw = lambda o: (lambda v: v - 65536 if v > 32767 else v)(w(o))
ADDRS = ['$87d6', '$9064', '$87a6', '$134b8', '$13624', '$b122', '$87b6', '$902e', '$906a', '$908c', '$90b0']
tot = {int(a[1:], 16): 0 for a in ADDRS}; first = {}
step = [0]
def run(n):
    r = s('hits', steps=n, addrs=ADDRS)
    for h in r['hits']:
        k = int(h['addr'].lstrip('$'), 16); tot[k] += h['count']
        if h['count'] and k not in first: first[k] = step[0] + h['first']
    step[0] += n
def key(k):
    s('kbd', bytes=[k]); run(60000); s('kbd', bytes=[k | 0x80]); run(600000)
def click(dx, dy):
    while dx or dy:   # a mouse packet carries at most +-127 per axis
        a = max(-127, min(127, dx)); b = max(-127, min(127, dy))
        s('mouse', action='move', dx=a, dy=b); run(30000); dx -= a; dy -= b
    s('mouse', action='down', button='l'); run(60000); s('mouse', action='up', button='l'); run(600000)
def pos(): return (w(26), w(28), w(30))
print('start: mode', w(13564), '13410', w(13410), '14880', hex(w(14880)), '14794', w(14794), '14800', sw(14800))
run(4_000_000)
print('settled: party', pos(), 'mode', w(13564), '13410', w(13410), 'door tile', hex(s.read(A6 + 9242 + 64 * 21 + 22, 1)[0]))
key(0x67); key(0x67)
for _ in range(3):
    s('mouse', action='move', dx=-127, dy=-127); run(30000)
for dx, dy in ((70, 80), (0, 65), (64, -65), (0, 65)):
    click(dx, dy)
print('after code: door tile', hex(s.read(A6 + 9242 + 64 * 21 + 22, 1)[0]), 'party', pos())
for _ in range(4):
    key(0x68)
print('after 4 N: party', pos())
key(0x69)
print('facing', pos(), 'tile ahead', hex(s.read(A6 + 15408, 1)[0]))
if ctl:
    s('poke', addr=A6 + 14880, width=2, value=0); print('CONTROL: poked 14880 = 0')
print('hits so far', {f'${k:x}': v for k, v in tot.items()}, '14880', hex(w(14880)))
s('save', path=os.path.join(OUT, 'm2_pre' + ('_ctl' if ctl else '') + '.snap'))
key(0x68)
print('after step E: party', pos(), 'mode', w(13564), '14800', sw(14800), 'cell tile', hex(s.read(A6 + 9242 + 64 * 18 + 23, 1)[0]))
for _ in range(3):
    s('mouse', action='move', dx=-127, dy=-127); run(30000)
click(202, 112)   # the lift/up icon: $902e (action 24) tests the tile under the party for $2e
print('after the up icon: 14800', sw(14800), 'mode', w(13564))
if ctl: run(3_000_000); print('control +3M: 14800', sw(14800), '14778', w(14778), 'pc', hex(s.reg('pc')))
got = False
for i in range(40):
    run(100000)
    if sw(14800) == -2 and not got:
        got = True
        p = os.path.join(OUT, 'm2_' + ('ctl' if ctl else 'screen') + '.snap'); s('save', path=p)
        subprocess.run(['uv', 'run', 'python', '-I', os.path.join(R, 'tools', 'snap_render.py'), p, p[:-5] + '.png'], cwd=R, check=True, capture_output=True)
        print(f'14800 = -2 seen after {i + 1} chunks (step {step[0]}), pc {s.reg("pc"):#x}')
if got:
    tag = 'ctl' if ctl else 'm2'
    for k in range(1, 25):
        run(500000)
        s('render', path=os.path.join(OUT, f'{tag}_t{k:02d}.png'))
        print(f'+{k * 0.5:.1f}M: 14800 {sw(14800)} 14880 {w(14880)} pc {s.reg("pc"):#x} 13624 hits {tot[0x13624]} b122 hits {tot[0xb122]} mode {w(13564)} 14778 {w(14778)} party {pos()}')
print('final: party', pos(), 'mode', w(13564), '14800', sw(14800), '14880', hex(w(14880)), '14778', w(14778))
print('hits', {f'${k:x}': v for k, v in tot.items()}, 'first (steps since the settle start)', {f'${k:x}': v for k, v in first.items()})
s.close()
