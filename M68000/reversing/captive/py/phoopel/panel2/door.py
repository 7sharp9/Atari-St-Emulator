"""[reversing/captive/py/phoopel/panel2/door.py; run from M68000 as `uv run python -I reversing/captive/py/phoopel/panel2/door.py <args>`; output under scratchpad/captive/phoopel/panel2/]
(b) $c420 under a real lock click: lock <L> (key kind 0 or 1, door kind 0) of base13.snap, labelled pokes: party cell and
facing (the cell in front of W) only; then mouse clicks as in py/phoopel/panels/panels.py. Breakpoints on $c420's branch
points log every arrival with D2/A2/68(A6); the 4-slot door table at A6+88 and D's tile are sampled every 30,000 steps.
Arms: open (cover + code bits), control (cover + one wrong bit: expect no $c420), reclose (code bit twice: shut, reopen).
usage: door.py <lock>   (9 = key 0, code 1; 17 = key 1, code 3)   output: panel2/door_L<L>.json"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
L = int(sys.argv[1])
s = StServer(R); s('load', snapshot=SNAP)
w = lambda a: int.from_bytes(s.read(a, 2), 'big')
tile = lambda x, y: s.read(TILES + y * 64 + x, 1)[0]
lk = lock_list(s)[L]; wx, wy = lk['W']; dx, dy = lk['D']; face = tile(wx, wy) & 3
assert lk['door'] == 0 and lk['key'] in (0, 1)
px, py = wx - VEC[face][0], wy - VEC[face][1]
bits = [b for b in range(16) if lk['code'] >> b & 1]
pts = {0: {0: (103, 110)}, 1: {c: (90 + 10*c + 4, 110) for c in range(3)}}[lk['key']]
PT = {0xc420: 'entry', 0xc424: 'after ada6', 0xc432: 'open-bit set, tile>$f, type&7', 0xc442: 'bsr ca64 (door type 2..6, open)',
      0xc44a: 'open: slot found -> toggle dir', 0xc452: 'rts (type 0/1/7 or found)', 0xc454: 'open: new slot -> closing (cnt 3)',
      0xc466: 'rts (full, or end of the closing branch)', 0xc468: 'closed path', 0xc470: 'closed: bsr ca64', 0xc476: 'closed: after ca64 (bne: slot already held -> rts; else falls to c478)',
      0xc478: 'closed: new slot -> open', 0xc490: 'rts'}
s('bp_set', addrs=list(PT))
log = []
def adv(n):
    while n > 0:
        r = s('run', max_steps=n); n -= r['steps']
        if r['reason'] == 'breakpoint':
            pc = s.reg('pc') & 0xffffff
            log.append(dict(pc=hex(pc), what=PT[pc], d2=hex(s.reg('d2') & 0xffff), cell=(w(A6 + 68) >> 8, w(A6 + 68) & 255)))
        elif r['reason'] != 'max_steps': break
s('poke', addr=A6 + 26, width=2, value=px); s('poke', addr=A6 + 28, width=2, value=py); s('poke', addr=A6 + 30, width=2, value=face)
adv(180000); base = s('fork')['id']
slots = lambda: [s.read(A6 + 88 + 4*i, 4).hex() for i in range(4)]
trace = []
def click(x, y, track=False):
    for _ in range(3): s('mouse', action='move', dx=-127, dy=-127); adv(30000)
    while x or y:
        mx, my = min(x, 120), min(y, 120); s('mouse', action='move', dx=mx, dy=my); adv(30000); x -= mx; y -= my
    s('mouse', action='down', button='l'); adv(60000); s('mouse', action='up', button='l')
    if track:
        last = None
        for i in range(60):
            cur = (f'{tile(dx, dy):02x}', slots()[0:4])
            if cur != last: trace.append((i * 6000, cur[0], [q for q in cur[1] if q != 'ffffffff'])); last = cur
            adv(6000)
        adv(300000 - 360000 if False else 0)
    else: adv(300000)
def watch(tag, frames=20):
    out = []
    for i in range(frames):
        out.append((i * 30000, f'{tile(dx, dy):02x}', slots())); adv(30000)
    return out
res = dict(lock=L, W=lk['W'], D=lk['D'], code=lk['code'], key=lk['key'], byte8=lk['b8'], tileD0=tile(dx, dy))
def arm(name, seq, start=None, cover=True):
    del log[:]
    s('restore', id=start if start is not None else base)
    pre = dict(tileD=tile(dx, dy), slots=slots())
    if cover: click(100, 110)
    n_cover = len(log)
    del trace[:]
    for i, b in enumerate(seq):
        click(*pts[b], track=(i == len(seq) - 1))
    c420_hits = [e for e in log if e['pc'] == '0xc420']
    r = dict(arm=name, pre=pre, c420_entries=len(c420_hits), path=[(e['what'], e['d2']) for e in log], timeline_after_last_click=list(trace), tileD_end=tile(dx, dy))
    print(f"lock {L} arm {name}: $c420 entries {len(c420_hits)}; D ${pre['tileD']:02x} -> ${tile(dx,dy):02x}; path:")
    for e in log: print('   ', e['pc'], e['what'], 'D2', e['d2'], 'cell', e['cell'])
    print('    after the last click, every 6000 steps, changes of (D tile, live slots):', trace)
    return r, s('fork')['id']
res['open'], opened = arm('open', bits)
wrong = next(b for b in sorted(pts) if b not in bits) if lk['key'] == 1 else None
res['control'], _ = arm('control', (bits[:-1] + [wrong]) if wrong is not None else [])
res['reclose'], _ = arm('reclose', [bits[-1], bits[-1]] if lk['key'] else [bits[-1], bits[-1]], start=opened, cover=False)
json.dump(res, open(os.path.join(OUT, f'door_L{L}.json'), 'w'), indent=1)
s.close()
