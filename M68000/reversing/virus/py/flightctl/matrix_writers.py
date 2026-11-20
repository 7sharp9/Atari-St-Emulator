"""Who writes the ship matrix $270d4 under the autopilot, and why the tick model matched only 4/119 against it.

  python matrix_writers.py capture <snap> <n> <out.txt>   # REPL: watch 270d4 18; n x (bp 255d4; r; m 270b0 12; m 32a32 4; m 270d4 18)
  python matrix_writers.py analyse <out.txt> <snap>       # for each interval between two $255d4 stops, the writer PC groups in order,
                                                          # and whether the matrix at the next stop equals matrix(attitude at that stop)
  python matrix_writers.py tick <snap> <n> <out.txt>      # n x (bp 25660; r; m 270d4 18): the matrix just after the tick's own $1f646
  python matrix_writers.py tickcheck <out.txt> <snap>     # matrix(D0, D1 at $25654) == $270d4 at $25660
Writer PC groups: $1f68e..$1f6cc = Attitude_BuildMatrix ($1f646, called from the tick at $2565a and from $26262, $2618c..),
$261de..$261f0 = draw-list op $261d2 (loads a matrix from the list), $2622e..$26240 = draw-list op $26222 (same, other form).
"""
import os, re, struct, subprocess, sys
_p = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_p))
import vcommon as V
ROOT = V.ROOT
WORK = V.work('flightctl')
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(_p), 'mpc'))
import exact

def run(snap, lines, out):
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', os.path.join(ROOT, 'bin/Debug/net8.0/M68000.dll'), 'resume', snap, 'repl'],
                       input='\n'.join(lines + ['q']) + '\n', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT, env=env, timeout=3000)
    open(out, 'w').write(p.stdout)

GROUP = {0x1f68e: 'build', 0x1f698: 'build', 0x1f6a8: 'build', 0x1f6b4: 'build', 0x1f6bc: 'build', 0x1f6c0: 'build', 0x1f6c4: 'build',
         0x1f6c8: 'build', 0x1f6cc: 'build', 0x261de: 'op261d2', 0x261e6: 'op261d2', 0x261f0: 'op261d2',
         0x2622e: 'op26222', 0x26236: 'op26222', 0x26240: 'op26222'}

def parse(out):
    stops = []; cur = None; cum = 0; events = []
    for l in open(out).read().split('\n'):
        mh = re.match(r'--- (?:breakpoint|gave up) .*?after (\d+) step', l)
        if mh: cum += int(mh.group(1))
        if l.startswith('--- breakpoint'):
            cur = {'reg': {}, 'mem': [], 'w': [], 'step': cum}; stops.append(cur); continue
        if l.startswith('--- gave up'): cur = None; continue
        m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+)', l)
        if m: events.append((int(m.group(1)), int(m.group(2), 16)))
        if cur is None: continue
        for k, v in re.findall(r'\b([DA]\d):([0-9a-f]{8})', l): cur['reg'][k] = int(v, 16)
        if re.fullmatch(r'([0-9a-f]{2} )+[0-9a-f]{2}', l.strip()) or re.fullmatch(r'[0-9a-f]{2}', l.strip()):
            cur['mem'].append(bytes.fromhex(l.strip().replace(' ', '')))
    return stops, events

def matrix_words(b): return {o: struct.unpack('>H', b[o:o + 2])[0] for o in range(0, 18, 2)}

def analyse(out, snap):
    """Last writer of $270d4 before each $255d4 stop, against whether the matrix there equals matrix(attitude).
    Writes are labelled by PC: $1f68e is Attitude_BuildMatrix, which the tick calls 47 steps after $255d4 and Autopilot_Steer
    ($22c1e, an actor pass) calls elsewhere; $261de / $2622e are the draw-list ops $261d2 / $26222.  Stop steps are cumulative
    'after N step(s)' sums anchored on the first tick build (+47 from the first stop); they are good to a step or two."""
    exact.load(snap)
    st, ev = parse(out)
    first = [e for e in ev if e[1] == 0x1f68e][0][0]
    s0 = first - 47 - st[0]['step']
    for q in st: q['step'] += s0
    stopsteps = [q['step'] for q in st]
    lab = []
    for step, pc in ev:
        if pc == 0x1f68e: lab.append((step, 'tick_build' if any(abs(step - t - 47) <= 3 for t in stopsteps) else 'steer_build'))
        elif pc == 0x261de: lab.append((step, 'op261d2'))
        elif pc == 0x2622e: lab.append((step, 'op26222'))
    tally = {}
    for q in st[1:]:
        if len(q['mem']) < 3: continue
        before = [l for t, l in lab if t < q['step']]
        last = before[-1] if before else None
        att = struct.unpack('>2h', q['mem'][1]); m = exact.matrix(att[0], att[1]); got = matrix_words(q['mem'][2])
        eq = all(m[o] == got[o] for o in m)
        t = tally.setdefault(last, [0, 0]); t[0] += 1; t[1] += eq
    n = sum(v[0] for v in tally.values())
    print(f'{n} stops; matrix at the stop equals matrix(attitude): {sum(v[1] for v in tally.values())}/{n}.  By last writer before the stop:')
    for k, (c, e) in sorted(tally.items(), key=lambda kv: -kv[1][0]): print(f'  last writer {k}: {c} stops, matrix equal in {e}')
    nb = sum(1 for _, l in lab if l == 'tick_build'); ns = sum(1 for _, l in lab if l == 'steer_build')
    print(f'  writes of $1f68e in the log: {nb} within 47 steps (+-3) of a stop (tick), {ns} elsewhere (steering); stops {len(st)}')

def tickcheck(out, snap):
    exact.load(snap); allst, _ = parse(out)
    pairs = [(a, b) for a, b in zip(allst[::2], allst[1::2]) if 'D0' in a['reg'] and b['mem']]
    ok = ctl = 0
    for a, b in pairs:
        # $25654 stop: D0 = new yaw, D1 = new pitch just before the jsr; $25660 stop: the matrix the call wrote
        yaw, pitch = [struct.unpack('>h', struct.pack('>H', a['reg'][k] & 0xffff))[0] for k in ('D0', 'D1')]
        got = matrix_words(b['mem'][0])
        m = exact.matrix(yaw, pitch); ok += all(m[o] == got[o] for o in m)
        m2 = exact.matrix(pitch, yaw); ctl += all(m2[o] == got[o] for o in m2)
    print(f'{len(pairs)} ticks: matrix(D0,D1 at $25654) equals $270d4 at $25660 in {ok}/{len(pairs)}; control matrix(D1,D0) {ctl}/{len(pairs)}')

if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'capture':
        L = ['watch 270d4 18']
        for i in range(int(sys.argv[3])): L += ['bp 255d4 200000', 'r', 'm 270b0 12', 'm 32a32 4', 'm 270d4 18']
        run(sys.argv[2], L, sys.argv[4])
    elif c == 'tick':
        L = []
        for i in range(int(sys.argv[3])): L += ['bp 25654 200000', 'r', 'bp 25660 1000', 'm 270d4 18']
        run(sys.argv[2], L, sys.argv[4])
    elif c == 'analyse': analyse(sys.argv[2], sys.argv[3])
    else: tickcheck(sys.argv[2], sys.argv[3])
