"""validity.py: gate the code-read model of $1394c (armed-order target test) against live callcap.
For each order and one sample cell per (kind, owner, byte7 bits, chain length) class of the cell-record grid $47970,
callcap $1394c with D7=(x<<16|y) and compare D3 (8 valid / $10 invalid) with a transcription of the routine.
Run from M68000: uv run python reversing/powermonger/py/input/validity.py [snap]"""
import os, subprocess, sys, re
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
SNAP = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm142/rand1.snap'
env = dict(os.environ, ATARI_NOTRACE='1')
def repl(lines):
    r = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl'], input='\n'.join(lines + ['q']) + '\n',
                       capture_output=True, text=True, cwd=ROOT, env=env)
    return r.stdout.splitlines()
def hexl(s): return bytes(int(t, 16) for t in s.split())
out = repl(['m 57ffe 2', 'm 47970 16384', 'm 49b66 98304'])
body = [l for l in out if re.fullmatch(r'([0-9a-f]{2} ?)+', l.strip())]
side = hexl(body[0])[1]; grid = hexl(body[1]); rec = hexl(body[2])
out = repl(['m %x 32' % (0x580a6 + side * 0x20)])
mask = hexl([l for l in out if re.fullmatch(r'([0-9a-f]{2} ?)+', l.strip())][0])[6]
def sg(o): return o - 0x10000 if o >= 0x8000 else o   # adda.w sign-extends the word offset
def R(off): return rec[off + 0x8000:off + 0x8000 + 12]
def chain(off):
    c = []
    off = sg(off)
    while off and len(c) < 20 and 0 <= off + 0x8000 and off + 0x8000 + 12 <= len(rec):
        r = R(off); c.append((r[6], r[5], r[7])); off = sg((r[0] << 8) | r[1])
    return c
def pred(order, off):
    if order in (2, 0x1a): return True
    if off == 0: return False  # off here is the raw grid word
    for kind, owner, b7 in chain(off):
        ally = bool(mask >> (owner & 7) & 1)
        if order == 0x1c:
            if kind in (2, 0x10): return True
        elif order == 6:
            if kind == 0x2c: return True
            if kind in (2, 0x10) and ally: return True
        elif order == 0x10:
            if kind in (0xa, 0x2c): return True
            if kind == 0x18 and b7 == 0x10: return True
            if kind in (2, 0x10) and ally: return True
        elif order == 0xc:
            if owner != side and kind in (2, 0x10, 0, 0xe, 8, 4): return True
        elif order == 8:
            if owner == side:
                if kind in (2, 0x10): return True
                if kind in (0, 0xe) and not (b7 & 0x40) and not (b7 & 0x10): return True
        elif order == 0x1e:
            if kind in (2, 0x10) and not ally: return True
        else:
            if kind in (2, 0x10):
                if order in (0xe, 8): 
                    if owner == side: return True
                elif owner != side: return True
    return False
seen = {}
for y in range(128):
    for x in range(64):
        off = (grid[(y * 64 + x) * 2] << 8) | grid[(y * 64 + x) * 2 + 1]
        if off:
            key = tuple((k, o, b7 & 0x50) for k, o, b7 in chain(off))
            seen.setdefault(key, []).append((x, y, off))
cells = [v[0] for v in seen.values()][:60]
cells.append((0, 0, 0))
orders = [2, 6, 8, 0xc, 0xe, 0x10, 0x1a, 0x1c, 0x1e, 0x20]
cmds = []; plan = []
for o in orders:
    cmds.append('w 57fd4 %04x0000' % o)
    for (x, y, off) in cells:
        cmds.append('callcap 1394c 20000 - D7=%04x%04x' % (x, y)); plan.append((o, x, y, off))
lines = repl(cmds)
d3 = []
for l in lines:
    if l.startswith('--- callcap'): d3.append(None)
    m = re.match(r'regdelta .*?D3 \$[0-9a-f]+->\$([0-9a-f]+)', l)
    if m and d3: d3[-1] = int(m.group(1), 16)
ok = bad = 0; byorder = {}
for (o, x, y, off), v in zip(plan, d3):
    p = pred(o, off); got = (v == 8)
    byorder.setdefault(o, [0, 0, 0])
    if p == got: ok += 1; byorder[o][0] += 1
    else: bad += 1; byorder[o][1] += 1; print('MISMATCH order %02x cell (%d,%d) off %04x chain %s pred %s got D3=%s' % (o, x, y, off, chain(off), p, v))
    byorder[o][2] += got
print('side', side, 'allymask %02x' % mask, 'classes', len(cells), 'callcaps', len(plan), 'match', ok, 'mismatch', bad)
for o, (a, b, c) in byorder.items(): print('order %02x: match %d mismatch %d valid-targets %d' % (o, a, b, c))
