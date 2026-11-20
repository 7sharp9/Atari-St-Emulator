"""Model of Virus's mouse input routine $254aa (Input_Mouse), proved against REPL runs with `mouse move`.

  python mouse_model.py run  <snap> <n> <seed> <out.txt>   # drive: n x (mouse move dx dy; s 4000; bp 255d4; r; m 1fa4a 6)
  python mouse_model.py check <snap> <out.txt>             # compare model with D0/D1/D2 at each $255d4 stop
  python mouse_model.py acc <n> <seed> <out.txt>           # accumulator = previous + the mouse move, adjacent stops

$254aa: tst.b $62a5b (nonzero: keyboard reader $2554a).  Else jsr $1fa54 -> D0 = x, D1 = y words at $1fa4a/$1fa4c
(accumulated IKBD deltas, start $80), D2 = buttons.  Offsets (v-$80)<<8 as words; sign bits go into an octant
word D2; heading = octant + atan table $d8fa[(min<<16)/max >> 8 & ~1]; tilt = 2*min($3fff, table $d9fa[
((dx^2 + dy^2) >> 16) >> 4 & ~1]).  Returns D0 = tilt (target from vertical), D1 = heading, D2 = buttons.
"""
import os, random, struct, subprocess, sys, re
_p = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_p))
import vcommon as V
ROOT = V.ROOT
WORK = V.work('flightctl')
os.makedirs(WORK, exist_ok=True)
import gfxview
w16 = lambda v: v & 0xffff

def tables(snap):
    r = bytes(gfxview.load_ram(snap)[0])
    return (struct.unpack('>128H', r[0xd8fa:0xd8fa + 256]), struct.unpack('>1100H', r[0xd9fa:0xd9fa + 2200]))

def model(x, y, T, variant=None):
    """-> (D0 tilt, D1 heading) for accumulator words x, y."""
    atan, rad = T
    d0 = w16((x - 0x80) << 8); d1 = w16((y - 0x80) << 8)
    if variant == 'swap': d0, d1 = d1, d0                      # control: axes exchanged
    o = 0
    if d0 & 0x8000: o ^= 0x6000; d0 = w16(-d0)
    if d1 & 0x8000: o ^= 0xe000; d1 = w16(-d1)
    a, b = d0, d1                                              # saved |dx|, |dy|
    if d0 == d1:
        h = 0x2000
    else:
        if d0 < d1: o ^= 0x2000; d0, d1 = d1, d0
        h = 0
        if d0:
            q = ((d1 << 16) // d0) & 0xffff                    # divu; d1 < d0 so no overflow
            h = atan[((q >> 8) & 0xfe) // 2]
    if o & 0x2000: o = w16(o + 0x2000); h = w16(-h)
    heading = w16(h + o)
    m2 = (a * a + b * b) & 0xffffffff
    idx = (((m2 >> 16) >> 4) & 0xfffe) // 2
    t = rad[idx]
    if variant == 'tilt5': t = rad[(((m2 >> 16) >> 5) & 0xfffe) // 2]   # control: wrong shift
    tilt = w16(min(t, 0x3fff) << 1)
    return tilt, heading

def moves(n, seed):
    rnd = random.Random(seed); out = []
    for i in range(n):
        k = rnd.random()
        if k < 0.1: dx, dy = rnd.choice([-1, 1]) * rnd.randint(30, 127), 0       # axis-aligned and equal cases
        elif k < 0.2: dx = dy = rnd.choice([-1, 1]) * rnd.randint(1, 60)
        elif k < 0.25: dx, dy = 0, rnd.choice([-1, 1]) * rnd.randint(30, 127)
        else: dx, dy = rnd.randint(-40, 40), rnd.randint(-40, 40)
        out.append((dx, dy))
    return out

def gen(snap, n, seed, out):
    lines = []
    for dx, dy in moves(n, seed):
        lines += [f'mouse move {dx} {dy}', 's 4000', 'bp 255d4 400000', 'r', 'm 1fa4a 6']
    lines.append('q')
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', os.path.join(ROOT, 'bin', 'Debug', 'net8.0', 'M68000.dll'), 'resume', snap, 'repl'],
                       input='\n'.join(lines) + '\n', capture_output=True, text=True, cwd=ROOT, env=env, timeout=3000)
    open(out, 'w').write(p.stdout + p.stderr)

def parse(out):
    txt = open(out).read().split('\n')
    stops = []; cur = None; moved = None
    for l in txt:
        if l.startswith('--- breakpoint'):
            cur = {'reg': {}, 'mem': None}; stops.append(cur)
        elif l.startswith('--- gave up'):
            cur = None                                     # cap reached: the registers that follow are not a tick
        if cur is None: continue
        for k, v in re.findall(r'\b([DA]\d):([0-9a-f]{8})', l): cur['reg'][k] = int(v, 16)
        m = re.fullmatch(r'([0-9a-f]{2}(?: [0-9a-f]{2}){5})', l.strip())
        if m: cur['mem'] = bytes.fromhex(m.group(1).replace(' ', ''))
    return stops

def acc_check(n, seed, out):
    """The accumulator at each stop equals the one at the previous stop plus the trial's mouse move (adjacent trials)."""
    mv = moves(n, seed); txt = open(out).read().split('\n'); trial = -1; prev = None; ok = bad = 0; pend = False
    for l in txt:
        if l.startswith('--- breakpoint'): trial += 1; pend = True; hit = True
        elif l.startswith('--- gave up'): trial += 1; pend = False; prev = None
        m = re.fullmatch(r'([0-9a-f]{2}(?: [0-9a-f]{2}){5})', l.strip())
        if m and pend:
            x, y = struct.unpack('>2h', bytes.fromhex(m.group(1).replace(' ', ''))[:4]); pend = False
            if prev is not None:
                if (x - prev[0], y - prev[1]) == mv[trial]: ok += 1
                else: bad += 1
            prev = (x, y)
    print(f'accumulator = previous + mouse move: {ok} of {ok + bad} adjacent stop pairs')

def check(snap, out):
    T = tables(snap)
    st = [s for s in parse(out) if s['mem'] and 'D0' in s['reg']]
    res = {None: 0, 'swap': 0, 'tilt5': 0}; nonzero = 0
    for s in st:
        x, y = struct.unpack('>2H', s['mem'][:4])
        want = (s['reg']['D0'] & 0xffff, s['reg']['D1'] & 0xffff)
        for v in res: res[v] += model(x, y, T, v) == want
        nonzero += want != (0, 0x2000)
    print(f'{len(st)} stops, {nonzero} with a non-centred target; model equal {res[None]}/{len(st)}; '
          f'control axes swapped {res["swap"]}/{len(st)}; control tilt shift 5 {res["tilt5"]}/{len(st)}')
    return st

if __name__ == '__main__':
    if sys.argv[1] == 'run': gen(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif sys.argv[1] == 'acc': acc_check(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    else: check(sys.argv[2], sys.argv[3])
