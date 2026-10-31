"""session_end.py <arm> - a real session end after a human race win, and the SSPRINT.HSC save it makes.

Start: data/bot_bot_end.snap (bot_ab.py bot 2400: the bot-driven human won race 1 on Track 1, race 2 is running). The stick is
released (`kbd fe 00`), so the human idles, a drone wins race 2 and the human is eliminated: all three drone flags
-3914..-3910(A4) set, the session loop $13a5e ends. One variable per arm:

  nat   nothing poked: the human keeps the score it earned
  hi    slot 1's score digits (-4846+6 and the shown copy -4870+6) poked to 050000 at the start, above table row 30 (028730)

Stops at each entry of the entry screen $172f0 (thunk 0x22e -> $18024 -> $172f0 runs after every race) and prints the flags and
scores there, then counts the entry-screen helpers, the save $1000e and the session tail $13b2c to the end of the budget.
The game's own write goes to the emulator's in-memory disk (DEVELOPING.md, "Disk A"); the final snapshot's DSKA journal is
applied to a copy of the image and SSPRINT.HSC is extracted and compared with the shipped file record by record.
"""
from lt import *
import subprocess, shutil
arm = sys.argv[1]
budget = int(sys.argv[2]) if len(sys.argv) > 2 else 120_000_000
OUT = os.path.join(LT, 'session_end'); os.makedirs(OUT, exist_ok=True)
r = Repl2(os.path.join(DATA, 'bot_bot_end.snap'))
r.cmd('kbd fe 00')
def score(c): return r.mem(A4 - 4846 + 6 * c, 6)
def digits(b): return ''.join(' ' if x & 0x80 else str(x) for x in b)
if arm == 'hi':
    for base in (-4846, -4870):
        a = A4 + base + 6                                   # 6 bytes at an address 2 mod 4: rewrite 8 aligned bytes
        lo = a & ~3; old = r.mem(lo, 12); new = bytearray(old)
        new[a - lo:a - lo + 6] = bytes([0x80, 5, 0, 0, 0, 0])
        r.cmd('w %x %s' % (lo, new[0:4].hex())); r.cmd('w %x %s' % (lo + 4, new[4:8].hex())); r.cmd('w %x %s' % (lo + 8, new[8:12].hex()))
print(arm, 'start scores', [digits(score(c)) for c in range(4)], 'flags', r.a4w(-3914, 4))
tbl0 = r.mem(A4 - 7956, 186)
H = [0x172f0, 0x17cb4, 0x17c02, 0x17a76, 0x17eb8, 0x17dba, 0x15ffe, 0x17d00, 0x13b2c, 0x1000e, 0xbe40]
used, n = 0, 0
while used < budget:
    out, regs = r.cmd('u 172f0 %d' % (budget - used))
    m = [l for l in out if 'reached' in l]
    if not any('reached PC' in l for l in out):
        print('  $172f0 not reached:', m[:1]); break
    used += int(re.search(r'after (\d+)', m[0]).group(1))
    n += 1
    print('  entry %d at +%d: flags %s scores %s laps %s' % (n, used, r.a4w(-3914, 4), [digits(score(c)) for c in range(4)], r.a4w(-3906, 4)))
    out, _ = r.cmd('hits 40000000 ' + ' '.join('%x' % h for h in H))
    used += 40_000_000
    print('  hits after entry %d:' % n, ' '.join('%s=%s' % (l.split()[0][3:], l.split()[1]) for l in out if l.startswith('  $')))
    print('  scores now', [digits(score(c)) for c in range(4)])
    tbl = r.mem(A4 - 7956, 186)
    print('  table rows changed:', [i for i in range(31) if tbl[6 * i:6 * i + 6] != tbl0[6 * i:6 * i + 6]])
    if n >= 2: break
snap = os.path.join(OUT, '%s_end.snap' % arm)
out, _ = r.cmd('snap %s' % snap); print(' ', [l for l in out if 'disk-A' in l or 'saved' in l])
ini = r.mem(A4 - 8050, 93); laprec = r.a4w(-8066, 8)
r.close()
# apply the DSKA journal to a copy of the disk and extract the high-score file
b = open(snap, 'rb').read()
k = b.rfind(b'DSKA')
img = bytearray(open(sscfg.DISK, 'rb').read())
nsec = 0
if k >= 0 and b[k + 4] == 1:
    cnt = struct.unpack('<i', b[k + 13:k + 17])[0]; p = k + 17
    for _ in range(cnt):
        off = struct.unpack('<i', b[p:p + 4])[0]; img[off:off + 512] = b[p + 4:p + 516]; p += 516
    nsec = cnt
print('written disk-A sectors in the snapshot:', nsec)
st = os.path.join(OUT, '%s_disk.st' % arm); open(st, 'wb').write(img)
ex = os.path.join(OUT, '%s_files' % arm); shutil.rmtree(ex, ignore_errors=True)
subprocess.run([sys.executable, os.path.join(sscfg.R, 'tools', 'extract_disk.py'), st, ex], check=True, capture_output=True)
new = open(os.path.join(ex, 'SSPRINT.HSC'), 'rb').read(); old = open(os.path.join(sscfg.FILES, 'SSPRINT.HSC'), 'rb').read()
print('SSPRINT.HSC: shipped %d bytes, saved %d bytes, differing bytes %d' % (len(old), len(new), sum(x != y for x, y in zip(old, new))))
for nm, f in (('shipped', old), ('saved', new)):
    rows = [digits(f[6 * i:6 * i + 6]) for i in range(31)]
    inits = [f[186 + 3 * i:189 + 3 * i] for i in range(31)]
    print('  %s rows 1-4:' % nm, rows[1:5], 'initials', [''.join(chr(c - 0x0b + 64) if 0x0c <= c <= 0x25 else '_' for c in x) for x in inits[1:5]],
          'lap records', list(struct.unpack('>8h', f[279:295])))
print('RAM lap records -8066(A4):', laprec)
