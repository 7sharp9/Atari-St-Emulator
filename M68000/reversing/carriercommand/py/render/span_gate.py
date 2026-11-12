"""span_gate.py - prove the span filler $4678 (+ colour setup $494c) against a pixel-level python model.
Pass 1: callcap $494c for each colour code -> patch bytes + A0/A5. Pass 2: poke the patches, callcap $4678
with (D1=xl, D2=xr, D7 parity) on a randomised screen row, apply the memory diff, compare to the model.
Run from anywhere: uv run python -I span_gate.py"""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import random, struct, sys
from rig import *
random.seed(7)
codes = [0, 3, 5, 9, 15, 16, 17, 40, 55, 63]
tbl = RAM[0x1544:0x1544 + 2 * 256]
# pass 1
out = repl([f'callcap 494c 20000 D0={c:x}' for c in codes])
cc = parse_callcaps(out)
assert len(cc) == len(codes), (len(cc), out[-500:])
setup = {}
for c, r in zip(codes, cc):
    setup[c] = r
    r['A0']=r['regs'].get('A0',(0,0))[1]; r['A5']=r['regs'].get('A5',(0,0))[1]
    print('code', c, 'pair', tbl[2*c], tbl[2*c+1], 'A0=%08x A5=%08x' % (r['A0'], r['A5']),
          'patched', sorted(hex(a) for a in r['mem'])[:12])
ROW = 0x78000 + 160 * 30
pre = bytearray(RAM)
cmds = []
for i in range(0, 160, 4):
    v = random.getrandbits(32); struct.pack_into('>I', pre, ROW + i, v); cmds.append(f'w {ROW+i:x} {v:08x}')
spans = [(0, 0), (5, 5), (3, 20), (16, 31), (0, 255), (250, 300), (-5, 10), (10, -3), (255, 255), (100, 240), (1, 33), (17, 47), (200, 215)]
tests = []
for c in codes:
    for (xl, xr) in spans:
        for par in (0, 1):
            for pe in ((0x7fff, 0x8001), (10, 20), (200, 100)):
                tests.append((c, xl, xr, par, pe))
UNION = sorted({a & ~3 for r in setup.values() for a in r['mem'] if not (0x9ee <= a <= 0x9f1)})
def patch_cmds(c):
    r = setup[c]['mem']; out = []
    for g in UNION:
        b = bytearray(RAM[g:g+4])      # snapshot bytes, overridden by this colour's $494c diff
        for k in range(4):
            if g+k in r: b[k] = r[g+k][1]
        out.append(f'w {g:x} {bytes(b).hex()}')
    return out
cmds2 = list(cmds)
idx = []
for (c, xl, xr, par, pe) in tests:
    cmds2 += patch_cmds(c)
    cmds2.append(f'w 9ee {pe[0] & 0xffff:04x}{pe[1] & 0xffff:04x}')
    cmds2.append('# test')
    cmds2.append(f'callcap 4678 20000 D1={xl & 0xffff:x} D2={xr & 0xffff:x} D7={par<<16:x} A6={ROW:x} A0={setup[c]["A0"]:x} A5={setup[c]["A5"]:x}')
cmds2 = [x for x in cmds2 if not x.startswith('#')]
out = repl(cmds2)
res = parse_callcaps(out)
res = [r for r in res if r['addr'] == 0x4678]
assert len(res) == len(tests), (len(res), len(tests))
def pix(buf, x):
    base = ROW + (x >> 4) * 8; b = 15 - (x & 15); v = 0
    for p in range(4): v |= ((struct.unpack_from('>H', buf, base + 2*p)[0] >> b) & 1) << p
    return v
def model(c, xl, xr, par, pe):
    buf = bytearray(pre)
    xr0, xl0 = xr, xl
    if xr >= 0:
        xr = max(xr, pe[1] if pe[1] < 0x8000 else pe[1] - 0x10000); xl = min(xl, pe[0] if pe[0] < 0x8000 else pe[0] - 0x10000)
    c1, c2 = tbl[2*c], tbl[2*c+1]
    if xr < 0: return buf
    xl = max(xl, 0)
    if xl >= 256: return buf
    xr = min(xr, 255)
    if xr - xl < 0: return buf
    for x in range(xl + 32, xr + 32 + 1):
        if c1 == c2: v = c1
        elif (par + 1) & 1 == 1: v = c2 if x % 2 == 0 else c1  # D7 hi word is incremented before the bit0 test ($46a0)
        else: v = c1 if x % 2 == 0 else c2
        base = ROW + (x >> 4) * 8; b = 15 - (x & 15)
        for p in range(4):
            w = struct.unpack_from('>H', buf, base + 2*p)[0]
            w = (w & ~(1 << b)) | (((v >> p) & 1) << b)
            struct.pack_into('>H', buf, base + 2*p, w)
    return buf
ok = 0; bad = []; trkbad = []
for t, r in zip(tests, res):
    emu = apply(pre, {a: v for a, v in r['mem'].items() if ROW <= a < ROW + 160})
    mod = model(*t)
    # tracker check: $9ee <- xr', $9f0 <- xl' (unclamped)
    pe = t[4]; xr, xl = t[2], t[1]
    s16 = lambda v: v - 0x10000 if v >= 0x8000 else v
    if xr >= 0:
        e_r = max(xr, s16(pe[1])); e_l = min(xl, s16(pe[0]))
        g9ee = (r['mem'].get(0x9ee, (0, pe[0] >> 8))[1] << 8) | r['mem'].get(0x9ef, (0, pe[0] & 255))[1]
        g9f0 = (r['mem'].get(0x9f0, (0, pe[1] >> 8))[1] << 8) | r['mem'].get(0x9f1, (0, pe[1] & 255))[1]
        trk_ok = (s16(g9ee) == e_r and s16(g9f0) == e_l)
    else: trk_ok = True
    if emu[ROW:ROW+160] == mod[ROW:ROW+160]: ok += 1
    if not trk_ok: trkbad.append(t)
    if emu[ROW:ROW+160] != mod[ROW:ROW+160]: bad.append(t)
print('span model match', ok, '/', len(tests), ' tracker ($9ee/$9f0) mismatches', len(trkbad)); print('first mismatches', bad[:12])
# show the output bytes for one example
t = (3, 3, 20, 1, (0x7fff, 0x8001)); i = tests.index(t); emu = apply(pre, {a: v for a, v in res[i]['mem'].items() if ROW <= a < ROW+160})
print('example solid colour 3, xl=3 xr=20 (screen x 35..52): row words 2..4 before', pre[ROW+16:ROW+40].hex(' ', 2), 'after', emu[ROW+16:ROW+40].hex(' ', 2))
t = (16, 3, 20, 1, (0x7fff, 0x8001)); i = tests.index(t); emu = apply(pre, {a: v for a, v in res[i]['mem'].items() if ROW <= a < ROW+160})
print('example dither code 16 (c1,c2)=(%d,%d) par1, same span: after' % (tbl[32], tbl[33]), emu[ROW+16:ROW+40].hex(' ', 2))
if len(sys.argv) > 1:
    t = eval(sys.argv[1]); i = tests.index(t)
    emu = apply(pre, {a: v for a, v in res[i]['mem'].items() if ROW <= a < ROW + 160}); mod = model(*t)
    print(t); print('pre ', pre[ROW:ROW+48].hex(' ', 2)); print('emu ', emu[ROW:ROW+48].hex(' ', 2)); print('mod ', mod[ROW:ROW+48].hex(' ', 2))
    print({hex(a): v for a, v in res[i]['mem'].items()})
from collections import Counter
print('mismatches by (code,parity):', sorted(Counter((t[0], t[3]) for t in bad).items()))
