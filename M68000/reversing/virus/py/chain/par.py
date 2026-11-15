"""par.py <snap> <steps> <rounds> <k>...: throughput of k concurrent REPL `s N` emulators (each its own process) from one snapshot.
Prints per-k wall time of the slowest process, aggregate Msteps/s, and uptime."""
import os, sys, time, subprocess, statistics
p = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(p, 'tools', 'rdis.py')): p = os.path.dirname(p)
root = p
snap, N, rounds, ks = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), [int(x) for x in sys.argv[4:]]
env = dict(os.environ, ATARI_NOTRACE='1')
def up(): return subprocess.run(['uptime'], capture_output=True, text=True).stdout.split('load averages:')[1].strip()
res = {k: [] for k in ks}
for r in range(rounds):
    for k in ks:
        u = up(); t = time.time()
        ps = [subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, text=True, cwd=root, env=env) for _ in range(k)]
        for q in ps: q.stdin.write(f's {N}\nq\n'); q.stdin.close()
        for q in ps: q.wait()
        dt = time.time() - t; res[k].append(dt)
        print(f'round {r} k={k} wall {dt:6.2f}s aggregate {k*N/dt/1e6:5.2f} M/s per-proc {N/dt/1e6:4.2f}  load {u}', flush=True)
for k in ks:
    a = res[k]; m = statistics.median(a)
    print(f'k={k}: median wall {m:.2f}s agg {k*N/m/1e6:.2f} M/s per-proc {N/m/1e6:.2f}; min wall {min(a):.2f}s agg {k*N/min(a)/1e6:.2f}')
