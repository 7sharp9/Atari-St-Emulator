"""ramdiff.py <a.ram> <b.ram> [lo hi] [--gap N]  list the byte ranges where two 1 MB RAM dumps differ.
Ranges closer than --gap (default 16) bytes are merged; each line gives lo..hi (exclusive), the length,
the count of differing bytes inside, and the region label for PowerMonger's save block."""
import sys
args = [a for a in sys.argv[1:] if not a.startswith('--')]
gap = int(sys.argv[sys.argv.index('--gap') + 1]) if '--gap' in sys.argv else 16
if '--gap' in sys.argv: args.remove(str(gap))
a, b = open(args[0], 'rb').read(), open(args[1], 'rb').read()
lo, hi = (int(args[2], 16), int(args[3], 16)) if len(args) >= 4 else (0, min(len(a), len(b)))
SAVE_LO, SAVE_HI = 0x3f768, 0x58368
diff = [i for i in range(lo, hi) if a[i] != b[i]]
runs = []
for i in diff:
    if runs and i - runs[-1][1] <= gap: runs[-1][1] = i; runs[-1][2] += 1
    else: runs.append([i, i, 1])
inside = sum(1 for i in diff if SAVE_LO <= i < SAVE_HI)
print(f"{len(diff)} bytes differ in ${lo:06x}..${hi:06x} ({inside} inside the save block $3f768..$58368), {len(runs)} ranges")
for s, e, n in runs:
    tag = 'save' if SAVE_LO <= s < SAVE_HI else ''
    print(f"  ${s:06x}..${e+1:06x}  len {e+1-s:6d}  diff {n:6d}  {tag}")
