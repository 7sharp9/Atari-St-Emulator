"""gate_b892.py: differential gate for $b892 (per-pool live-record counts into $5878c..$58795, five words).
Model: pools (base, end, stride, test) read from the snapshot RAM; the real routine is run with callcap.
usage: cd M68000 && uv run python reversing/powermonger/py/link/gate_b892.py [snap ...]   (default: 24 snapshots)"""
import os, re, subprocess, sys, glob
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
LO, HI = 0x4ccd6, 0x57f66
HEX = re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')


def sb(v): return v - 256 if v > 127 else v


def model(r):
    g = lambda a: r[a - LO]
    w = lambda a: (g(a) << 8) | g(a + 1)
    c = []
    c.append(sum(1 for a in range(0x4e514, 0x4f914, 32) if g(a) != 0))
    c.append(sum(1 for a in range(0x4f916, 0x51536, 18) if g(a + 5) != 0))
    c.append(sum(1 for a in range(0x51b66, 0x57f66, 50) if sb(g(a + 5)) > 0))
    c.append(sum(1 for a in range(0x4ccd6, 0x4cff6, 20) if g(a + 5) != 0 and g(a + 7) in (0x11, 0x12)))
    c.append(sum(1 for a in range(0x4d252, 0x4e512, 12) if w(a + 10) != 0))
    return c


def run(snap):
    cmds = f'm {LO:x} {HI - LO}\nm 5878c 10\ncallcap b892 100000\nq\n'
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'], input=cmds, text=True,
                       capture_output=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'))
    toks = []
    for ln in p.stdout.splitlines():
        if HEX.match(ln.strip()):
            toks.append([int(x, 16) for x in ln.split()])
    r, pre = bytes(toks[0]), bytearray(toks[1])
    for m in re.finditer(r'^mem \$([0-9a-f]+) \$([0-9a-f]{2})->\$([0-9a-f]{2})', p.stdout, re.M):
        a = int(m.group(1), 16)
        if 0x5878c <= a < 0x5878c + 10:
            pre[a - 0x5878c] = int(m.group(3), 16)
    return r, [(pre[2 * i] << 8) | pre[2 * i + 1] for i in range(5)]


def main():
    snaps = sys.argv[1:] or (sorted(glob.glob(os.path.join(ROOT, 'scratchpad/pm121/cap/*.snap')))[:14]
                             + sorted(glob.glob(os.path.join(ROOT, 'scratchpad/pm121/corpus_1623c/*.snap')))[:6]
                             + [os.path.join(ROOT, f'scratchpad/pm123/win/{n}.snap') for n in ('m1_win', 'm1_ready', 'm1_s0', 'l1_built')]
                             + [os.path.join(ROOT, 'scratchpad/pm142/rand1.snap')])
    ok = 0
    for s in snaps:
        r, got = run(s)
        exp = model(r)
        ok += got == exp
        print(os.path.relpath(s, ROOT), 'real', got, 'model', exp, 'OK' if got == exp else 'DIFF')
    print(f'{ok}/{len(snaps)} match')


if __name__ == '__main__':
    main()
