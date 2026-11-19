#!/usr/bin/env python3
"""Interleaved A/B (or A/B/C...) timing of built emulator DLLs, the measurement DEVELOPING.md "Performance" asks for.

usage: bench_builds.py <rounds> <outdir> <name>=<M68000.dll> <name>=<M68000.dll> ... [--game <snap>] [--game-steps N]

Each build is a whole `dotnet build -c Debug M68000.fsproj -o <dir>` directory; the first one named is the base.
Per round, in an order that reverses every round: a 30M-step diskless boot to a snapshot (hashed, so a build that
changes behaviour shows up) and, with --game, <N> steps resumed from a game snapshot (default 20M). Prints every
run with the load average before it, then per build the median, the minimum and its ratio to the base in each round.
A gap under about 5% that does not repeat in every round is noise.
"""
import subprocess, time, os, sys, json, hashlib, statistics

def root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isfile(os.path.join(d, 'tools', 'rdis.py')):
        nd = os.path.dirname(d)
        if nd == d: sys.exit('no repo root')
        d = nd
    return d

def main():
    a = sys.argv[1:]
    game = None; gsteps = 20000000
    if '--game' in a: i = a.index('--game'); game = os.path.abspath(a[i + 1]); del a[i:i + 2]
    if '--game-steps' in a: i = a.index('--game-steps'); gsteps = int(a[i + 1]); del a[i:i + 2]
    if len(a) < 4: sys.exit(__doc__)
    rounds = int(a[0]); out = os.path.abspath(a[1]); os.makedirs(out, exist_ok=True)
    builds = [(x.split('=', 1)[0], os.path.abspath(x.split('=', 1)[1])) for x in a[2:]]
    M = root(); env = dict(os.environ, ATARI_NOTRACE='1'); res = []
    def run(name, dll, w, r):
        snap = os.path.join(out, 'boot_%s.snap' % name)
        if w == 'boot':
            if os.path.exists(snap): os.remove(snap)
            cmd = ['dotnet', 'exec', dll, '30000000', 'snapshot', snap]
        else:
            cmd = ['dotnet', 'exec', dll, str(gsteps), 'resume', game]
        la = os.getloadavg()[0]; t = time.time()
        p = subprocess.run(cmd, cwd=M, env=env, capture_output=True)
        dt = time.time() - t
        h = hashlib.sha256(open(snap, 'rb').read()).hexdigest()[:12] if w == 'boot' and os.path.exists(snap) else ''
        res.append(dict(b=name, w=w, r=r, dt=dt, rc=p.returncode, la=la, h=h))
        print('%d %s %s %.2fs rc=%d load=%.1f %s' % (r, w, name, dt, p.returncode, la, h), flush=True)
    for r in range(rounds):
        order = builds if r % 2 == 0 else builds[::-1]
        for w in (['boot', 'game'] if game else ['boot']):
            for name, dll in order: run(name, dll, w, r)
    json.dump(res, open(os.path.join(out, 'bench.json'), 'w'))
    for w in sorted({x['w'] for x in res}):
        base = {x['r']: x['dt'] for x in res if x['w'] == w and x['b'] == builds[0][0]}
        for name, _ in builds:
            d = [x['dt'] for x in res if x['w'] == w and x['b'] == name]
            q = [x['dt'] / base[x['r']] for x in res if x['w'] == w and x['b'] == name]
            print('%s %s median %.2f min %.2f ratio per round: %s' % (w, name, statistics.median(d), min(d), ' '.join('%.3f' % v for v in q)))
        print('%s snapshot hashes %s, exit codes %s' % (w, sorted({x['h'] for x in res if x['w'] == w}), sorted({x['rc'] for x in res})))

if __name__ == '__main__':
    main()
