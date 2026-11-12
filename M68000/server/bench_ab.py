"""Interleaved A/B timing of two stserver builds (DEVELOPING.md "Execution profile" and "Performance").

    python3 server/bench_ab.py step <dirA> <dirB> [--pairs 5] [--n 10000000]
    python3 server/bench_ab.py read <dirA> <dirB> [--pairs 5]
    python3 server/bench_ab.py profile <dir> [--rounds 3] [--n 5000000]

Each dir holds a built stserver.dll with its M68000.dll (copy server/bin/Debug/net8.0/ aside, then overlay the other
build's stserver.dll, so the only variable is the server). From Black Tiger's play_start.snap ($BT_WORK, default
scratchpad/black_tiger; disk bt_auto.st):
  step     load, 200,000 warm-up steps, time `step n`, save the end snapshot; prints per-pair gap and whether the two
           end snapshots of each pair are byte-identical
  read     time 20 reads of 64 KB (`read`), and check both builds return the same bytes
  profile  in one server, from one fork: `step n` with and without a profile running, alternating
Order alternates per pair; `uptime` is printed per run. A gap under about 5% is noise unless it repeats in every pair.
"""
import argparse, filecmp, hashlib, os, statistics as st, subprocess, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer
WORK = os.environ.get('BT_WORK', os.path.join(ROOT, 'scratchpad', 'black_tiger'))
SNAP, DISK = os.path.join(WORK, 'play_start.snap'), os.path.join(WORK, 'bt_auto.st')

def load(d):
    up = subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip().split('averages:')[-1].strip()
    s = StServer(ROOT, dll=os.path.join(d, 'stserver.dll'))
    s('load', snapshot=SNAP, disk=DISK)
    return s, up

ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=['step', 'read', 'profile'])
ap.add_argument('dirs', nargs='+')
ap.add_argument('--pairs', type=int, default=5)
ap.add_argument('--rounds', type=int, default=3)
ap.add_argument('--n', type=int)
a = ap.parse_args()
tmp = tempfile.mkdtemp(prefix='bench_ab_')

if a.mode == 'profile':
    n = a.n or 5_000_000
    s, _ = load(a.dirs[0]); s('step', n=200000); f = s('fork')['id']
    for r in range(a.rounds):
        for prof in (False, True):
            s('restore', id=f)
            up = subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip().split('averages:')[-1].strip()
            if prof: s('profile_start')
            t = time.perf_counter(); s('step', n=n); dt = time.perf_counter() - t
            if prof: s('profile_stop', path=os.path.join(tmp, 'p.json'))
            print(r, 'profile' if prof else 'off    ', f'{dt:.2f}s', 'load', up, flush=True)
    s.close(); sys.exit(0)

A, B = a.dirs
res, same, dig = {A: [], B: []}, [], {A: set(), B: set()}
for i in range(a.pairs):
    for d in ([A, B] if i % 2 == 0 else [B, A]):
        s, up = load(d)
        if a.mode == 'step':
            s('step', n=200000)
            t = time.perf_counter(); s('step', n=a.n or 10_000_000); dt = time.perf_counter() - t
            s('save', path=os.path.join(tmp, f'{i}_{d == B}.snap'))
        else:
            s('read', addr=0, len=65536)
            h = hashlib.sha1(); t = time.perf_counter()
            for k in range(20):
                h.update(s.read(0x10000 * (k % 8), 65536))
            dt = time.perf_counter() - t
            dig[d].add(h.hexdigest())
        s.close()
        res[d].append(dt)
        print(i, 'A' if d == A else 'B', f'{dt:.3f}s', 'load', up, flush=True)
    if a.mode == 'step':
        same.append(filecmp.cmp(os.path.join(tmp, f'{i}_False.snap'), os.path.join(tmp, f'{i}_True.snap'), shallow=False))
for d, k in ((A, 'A'), (B, 'B')):
    print(k, d, 'median %.3f min %.3f' % (st.median(res[d]), min(res[d])))
for i in range(a.pairs):
    print('pair', i, 'B/A %+.1f%%' % (100 * (res[B][i] / res[A][i] - 1)), ('end snapshots identical' if same[i] else 'END SNAPSHOTS DIFFER') if same else '')
if a.mode == 'read':
    print('same bytes:', dig[A] == dig[B] and len(dig[A]) == 1)
