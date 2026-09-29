"""Replay the recorded hop-3 route from its .repl files and compare snapshots byte for byte.

    uv run python reversing/impossamole/py/route/verify_route.py [--full-only | --segs-only]

1. Per segment: `resume <previous end snapshot> repl < segs/<seg>.repl`, writing verify/<seg>.snap, `cmp`ed against
   the live-driven snaps/<seg>.snap.
2. Whole route in ONE emulator process: the segments' .repl files concatenated (their closing `snap`/`q` lines removed,
   one `snap` at the end) run from room188.snap, `cmp`ed against the live final snapshot. The concatenation is written
   to route_full.repl (the single replayable file for the whole hop).
"""
import filecmp, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_driver import ROOT, DISK
import route_hop3 as R

D = os.path.join(ROOT, R.BASE)


def run_repl(start, lines):
    env = dict(os.environ, ATARI_NOTRACE='1')
    r = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', start, 'repl', '--disk-a', DISK],
                       cwd=ROOT, env=env, input='\n'.join(lines) + '\n', text=True, capture_output=True)
    return r.stdout


def body(path):
    return [l.rstrip('\n') for l in open(path) if not l.startswith(('snap ', 'q'))]


def main():
    names = [f.__name__ for f in R.SEGS]
    os.makedirs(os.path.join(D, 'verify'), exist_ok=True)
    ok = True
    if '--full-only' not in sys.argv:
        prev = R.START
        for n in names:
            out = os.path.join(D, 'verify', n + '.snap')
            t = time.time()
            run_repl(prev, body(os.path.join(D, 'segs', n + '.repl')) + [f'snap {out}', 'q'])
            same = filecmp.cmp(out, os.path.join(D, 'snaps', n + '.snap'), shallow=False)
            print(f'{n}: replay {time.time() - t:.0f}s, snapshot byte-identical to the live one: {same}', flush=True)
            ok &= same
            prev = f'{R.BASE}/snaps/{n}.snap'
    if '--segs-only' not in sys.argv:
        lines = []
        for n in names:
            lines += body(os.path.join(D, 'segs', n + '.repl'))
        full = os.path.join(D, 'verify', 'full.snap')
        with open(os.path.join(D, 'route_full.repl'), 'w') as f:
            f.write('\n'.join(lines) + f'\nsnap {os.path.join(D, "room299.snap")}\nq\n')
        t = time.time()
        run_repl(R.START, lines + [f'snap {full}', 'q'])
        same = filecmp.cmp(full, os.path.join(D, 'snaps', names[-1] + '.snap'), shallow=False)
        print(f'whole route from {R.START} in one process ({len(lines)} commands): {time.time() - t:.0f}s, final snapshot '
              f'byte-identical to the live segment-chained one: {same}', flush=True)
        ok &= same
    print('ALL IDENTICAL' if ok else 'MISMATCH')


if __name__ == '__main__':
    main()
