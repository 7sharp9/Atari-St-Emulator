"""Time the basher's mask erases with `watch`: which game ticks write the terrain bitmap, and how many words.
Run from M68000/:  uv run python reversing/lemmings/py/maskwatch.py <out dir> [--ticks 40]
Builds on skilldrive.py's drive script (basher, wall poked at groups 46..48 rows 56..74), watches group 46 rows 62..76
and steps one game tick (36,000 steps) at a time, dumping lemming 0's record (+10 is the tick) before each.
Prints the write bursts (step offset, word count, rows) and the tick samples; the burst at offset k*36000 is the
handler run that takes the tick from sample k to k+1 ($81d0 increments before it erases).
"""
import os, re, struct, subprocess, sys
out = sys.argv[1]; ticks = int(sys.argv[sys.argv.index('--ticks') + 1]) if '--ticks' in sys.argv else 40
os.makedirs(out, exist_ok=True)
subprocess.run([sys.executable, '-c', 'pass'])
subprocess.run(['uv', 'run', 'python', 'reversing/lemmings/py/skilldrive.py', '5', '26c28', out + '/base', '--samples', '1',
                '--wall', '46,48,56,74', '--x0', '704'], check=True, capture_output=True)
L = open(out + '/base/drive.txt').read().splitlines()
i = next(k for k, l in enumerate(L) if l == 'mouse down l')
cmds = L[:i + 4] + ['watch %x %d' % (0x41806 + 62 * 0x330 + 46 * 8, 15 * 0x330)]
for _ in range(ticks): cmds += ['m 23484 44', 's 36000']
cmds.append('q')
open(out + '/watch.txt', 'w').write('\n'.join(cmds) + '\n')
r = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', 'scratchpad/lemmings/sel.snap', 'repl', '--disk-a',
                    'scratchpad/lemmings/lemmings.st'], input='\n'.join(cmds) + '\n', capture_output=True, text=True,
                   env=dict(os.environ, ATARI_NOTRACE='1'))
open(out + '/watch.out', 'w').write(r.stdout); open(out + '/watch.err', 'w').write(r.stderr)
w = [(int(m[1]), int(m[2], 16)) for m in (re.match(r'WATCH: step=(\d+) pc=\$\w+ Write\w+ \$(\w+)', l) for l in r.stderr.splitlines()) if m]
recs = []
for l in r.stdout.splitlines():
    t = l.split()
    if len(t) >= 44 and all(len(s) == 2 for s in t[:44]):
        b = bytes(int(s, 16) for s in t[:44])
        if b[14:18] == b'\0\0\0\x40': recs.append(struct.unpack('>H', b[10:12])[0])
s0, bursts, cur = w[0][0], [], []
for x in w:
    if cur and x[0] - cur[-1][0] > 200: bursts.append(cur); cur = []
    cur.append(x)
bursts.append(cur)
print('ticks sampled (+10) after the click:', recs)
for b in bursts:
    print('burst at +%d (tick interval %d): %d words, rows %s' % (b[0][0] - s0, round((b[0][0] - s0) / 36000), len(b),
          sorted({(a - 0x41806) // 0x330 for _, a in b})[:1] + sorted({(a - 0x41806) // 0x330 for _, a in b})[-1:]))
