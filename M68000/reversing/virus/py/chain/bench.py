"""bench.py <snap> <steps> <rounds> variants...: interleaved A/B of ways to run N steps from one snapshot.
Variants: argv (N resume snap), repl_s (REPL `s N`), repl_bp (REPL `bp 1 N`, the CensusStep path chain.py uses),
repl_chunk (REPL `s 1000000` x N/1M), st_run (stserver run max_steps N), st_step (stserver step N).
Prints wall seconds, steps/s, uptime per run; median and min per variant. Output snapshot compared for the first round."""
import os, sys, time, subprocess, json, statistics
here = os.path.abspath(os.path.dirname(__file__)); p = here
while not os.path.exists(os.path.join(p, 'tools', 'rdis.py')): p = os.path.dirname(p)
root = p; sys.path.insert(0, os.path.join(root, 'tools')); from stclient import StServer
snap, N, rounds, variants = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
env = dict(os.environ, ATARI_NOTRACE='1')
DLL = 'bin/Debug/net8.0/M68000.dll'
def up(): return subprocess.run(['uptime'], capture_output=True, text=True).stdout.split('load averages:')[1].strip()
def run(v, extra=None):
    e = dict(env); e.update(extra or {})
    t = time.time()
    if v == 'argv':
        r = subprocess.run(['dotnet', 'exec', DLL, str(N), 'resume', snap], cwd=root, env=e, capture_output=True, text=True)
    elif v.startswith('repl'):
        if v == 'repl_s': cmds = f's {N}'
        elif v == 'repl_bp': cmds = f'bp 1 {N}'
        elif v == 'repl_chunk': cmds = '\n'.join(['s 1000000'] * (N // 1000000))
        r = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl'], input=cmds + '\nq\n', cwd=root, env=e, capture_output=True, text=True)
    elif v.startswith('st_'):
        s = StServer(root); s('load', snapshot=snap)
        t = time.time()
        if v == 'st_run': s('run', max_steps=N)
        else: s('step', n=N)
        dt = time.time() - t; s.close(); return dt
    return time.time() - t
res = {v: [] for v in variants}
for r in range(rounds):
    for v in variants:
        u = up(); dt = run(v); res[v].append(dt)
        print(f'round {r} {v:11s} {dt:7.2f}s {N/dt/1e6:5.2f} Msteps/s  load {u}', flush=True)
for v in variants:
    a = res[v]; print(f'{v:11s} median {statistics.median(a):6.2f}s ({N/statistics.median(a)/1e6:.2f} M/s)  min {min(a):6.2f}s ({N/min(a)/1e6:.2f} M/s)  n={len(a)}')
