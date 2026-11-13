#!/usr/bin/env python3
"""Is the final base's LOADING a stuck loader? Replays station.py's arm 10 (labelled poke 14794(A6) = 10) from
mission1.snap, or with `natural` the base1/site.snap target-1 landing as a control, then logs from the LAND click:
every game-OS trap #9 call (breakpoints on the dispatcher $206 and epilogue $16c, as ../../system/trap9_log.py), the
FDC trace (needs ATARI_TRACE_FDC=1, written to stderr), a PC sample every 250k steps, the state words, and renders.

  ATARI_TRACE_FDC=1 TOTAL=60000000 uv run python -I reversing/captive/py/world/station/fdc.py > scratchpad/captive/station/fdc_fin.log 2>&1
  ... fdc.py natural    (control);  RENDER=3,6,13 picks the render steps in millions; TOTAL = step budget.
Run stops 3M steps after 14800(A6) turns nonzero. Renders fdc_<fin|nat>_<N>M.png under scratchpad/captive/station/."""
import os, sys, struct
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    nd = os.path.dirname(d)
    if nd == d: sys.exit('repo root not found')
    d = nd
R = os.environ.get('M68000_ROOT') or d
sys.path.insert(0, os.path.join(R, 'tools'))
from stclient import StServer
A6 = 0x1b5ce
W = os.path.join(R, 'scratchpad', 'captive')
OUT = os.path.join(W, 'station')
w16 = lambda s, o: struct.unpack('>h', s.read(A6 + o, 2))[0]
l32 = lambda s, o: struct.unpack('>I', s.read(A6 + o, 4))[0]
nat = len(sys.argv) > 1 and sys.argv[1] == 'natural'
tag = 'nat' if nat else 'fin'
s = StServer(R)
def pin():
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
def goto(px, py):
    pin(); x = y = 0
    while (x, y) != (px, py):
        dx, dy = min(127, px - x), min(127, py - y)
        s('mouse', action='move', dx=dx, dy=dy); s('step', n=30000); x += dx; y += dy
def click(px, py, settle):
    goto(px, py); s('mouse', action='down', button='l'); s('step', n=60000)
    s('mouse', action='up', button='l'); s('step', n=settle)
def party(): p = l32(s, 26); return (p >> 16, p & 0xffff)
def st(): return dict(mode=w16(s, 13564), s13410=w16(s, 13410), live410=w16(s, 410), e14800=w16(s, 14800), party=party(), face=w16(s, 30), mission=w16(s, 14776), cnt=w16(s, 14794))

if nat:
    s('load', snapshot=os.path.join(W, 'base1', 'site.snap'))
    click_orbit = lambda: (s('mouse', action='move', dx=100, dy=-34), s('step', n=30000), s('mouse', action='down', button='l'), s('step', n=60000), s('mouse', action='up', button='l'), s('step', n=30_000_000))
    click_orbit()
    s('mouse', action='move', dx=49, dy=-2); s('step', n=30000)
else:
    s('load', snapshot=os.path.join(W, 'mission1.snap'), disk=os.path.join(W, 'tmb097.st'))
    click(78, 85, 300000)
    s('poke', addr=A6 + 14794, width=2, value=10)        # LABELLED POKE (as station.py arm 10)
    click(204, 76, 0)
    for _ in range(200):
        s('step', n=500000)
        if w16(s, 14858) == 6: break
    goto(252, 75)

sys.stderr.write('MARK landing: pre-LAND\n'); sys.stderr.flush()
TOTAL = int(os.environ.get('TOTAL', 60_000_000))
s('bp_set', addrs=[0x206, 0x16c])        # game OS trap #9 dispatcher entry / epilogue (trap9_log.py)
s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l')
RENDER = [int(x) * 1_000_000 for x in os.environ.get('RENDER', '3,6,11,13,14,15').split(',')]; rdone = set()
done = 0; pend = []; calls = []; samples = []; chunk = 250_000
def log(m): sys.stderr.write(m + '\n'); sys.stderr.flush()
last_state = None
while done < TOTAL:
    r = s('run', max_steps=chunk)
    done += r['steps']
    if r['reason'] == 'breakpoint':
        g = s('regs'); x = lambda n: int(str(g[n]).lstrip('$'), 16)
        if x('pc') == 0x206:
            a0 = x('a0'); b = s.read(a0, 24).split(b'\0')[0] if 0x400 <= a0 < 0xffff0 else b''
            ts = b.decode('latin1') if b and all(32 <= c < 127 for c in b) else ''
            msg = f'T9 +{done} fn {x("d7")} d0 {x("d0"):x} d1 {x("d1"):x} a0 {a0:x} "{ts}" caller {int.from_bytes(s.read(x("a7")+2,4),"big")-2:x}'
            log(msg); calls.append(msg)
        continue
    for rp in RENDER:
        if rp not in rdone and done >= rp:
            rdone.add(rp); s('render', path=os.path.join(OUT, f'fdc_{tag}_{rp // 1000000}M.png'))
    pc = s.reg('pc') & 0xffffff
    samples.append((done, pc))
    stt = st()
    if stt != last_state or len(samples) % 8 == 0:
        log(f'MARK +{done} pc ${pc:x} {stt}')
        last_state = stt
    if stt['e14800'] != 0 and TOTAL > done + 3_000_000: TOTAL = done + 3_000_000   # stop soon after the end screen
log('SAMPLES (step, pc): ' + ' '.join(f'{a}:{p:x}' for a, p in samples[:60]))
log(f'trap9 calls: {len(calls)}')
s('render', path=os.path.join(OUT, f'fdc_{tag}_end.png'))
s.close()
