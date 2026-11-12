#!/usr/bin/env python3
"""Infographic: Automation Packer V2.3r's backwards in-place depack (packer.md), drawn from a per-token log
of the depacker transcribed in py/autopack_depack.py.

usage: gen_depack.py [outdir]   (default WORK/infographics; writes depack.svg and prints the figures it draws)

The depacker here is autopack_depack.depack with a per-token log added, run on one shared memory image laid
out as the stub lays it out (stream at tbase+$31a, output at tbase+$400), so a write over an unread stream
byte would corrupt the result. Checks before drawing: the output equals autopack_depack.py's and the sha256
in packer.md, and matches the emulator's RAM in c80.snap (the depacked image sits at $296 + file offset
there); lowering the destination by the closest live gap must still depack correctly and one byte more must
not (the margin is exact). Facts and sources: depack.facts.md beside this script."""
import pathlib as _pl, sys as _sys
_here = _pl.Path(__file__).resolve().parent
_sys.path.insert(0, str(_here.parent))
from ccpaths import *
import hashlib, math, struct, subprocess
import autopack_depack as AD
from autopack_depack import LIT_BITS, LIT_BASE, LEN_BITS, LEN_BASE, OFF_BITS, OFF_BASE

OUT = _pl.Path(_sys.argv[1]) if len(_sys.argv) > 1 else WORK / 'infographics'
OUT.mkdir(parents=True, exist_ok=True)
PRG = WORK / 'files' / 'PACT2.PRG'
SHA = '0d3938982b8a909de79b52d26824ba05b42980cbcdcd94ce790b912bcfe20448'   # packer.md "Ratios"
TBASE = 0xa304                                                            # auto-boot run, packer.md


def inplace(path, dest_ofs=AD.DEST_OFS):
    """Depack in one memory image (offsets from tbase), destination at dest_ofs. Returns (output, token log,
    (min gap, at), (min gap while a stream byte is unread, (at, unread)), text length, size, payload length,
    final A1, tail). Gap = write offset of the byte just written - offset of the lowest consumed stream byte, as
    autopack_depack.min_gap. Token log: (kind, n, write offset, read offset after the token[, match offset])."""
    d = open(path, 'rb').read()
    tl, dl = struct.unpack('>II', d[2:10])
    p = d[0x1c + tl: 0x1c + tl + dl]
    size = struct.unpack('>I', p[4:8])[0]
    plen = struct.unpack('>I', p[8:12])[0]
    lo = min(tl, dest_ofs)
    mem = bytearray(max(tl + len(p), dest_ofs + size) - lo + 1)
    S = tl - lo; D = dest_ofs - lo                     # stream and destination base inside mem
    mem[S:S + len(p)] = p
    pos = 8 + plen - 4 - 2                             # same start as autopack_depack.depack
    if mem[S + pos] & 0x80: pos -= 1
    stop = 12
    a1 = size
    log = []; gmin = [None, None]; glive = [None, None]   # live: a stream byte is still unread
    tail = []                                          # (file offset written, gap, stream bytes unread), last 48
    st = {'pos': pos}
    def rdbyte():
        st['pos'] -= 1; return mem[S + st['pos']]
    d0 = rdbyte()
    def getbit():
        nonlocal d0
        c = (d0 >> 7) & 1; d0 = (d0 << 1) & 0xff
        if d0 == 0:
            nb = rdbyte(); c2 = nb >> 7; d0 = ((nb << 1) | c) & 0xff
            return c2
        return c
    def bits(n):
        v = 0
        for _ in range(n): v = (v << 1) | getbit()
        return v
    def write(v):
        nonlocal a1
        a1 -= 1; mem[D + a1] = v
        g = (dest_ofs + a1) - (tl + st['pos'])        # as autopack_depack.min_gap
        if gmin[0] is None or g < gmin[0]: gmin[0] = g; gmin[1] = a1
        if st['pos'] > stop and (glive[0] is None or g < glive[0]): glive[0] = g; glive[1] = (a1, st['pos'] - stop)
        if a1 < 48: tail.append((a1, g, st['pos'] - stop))
    log.append(('start', 0, dest_ofs + size, tl + len(p)))   # before any read: stream end, output end
    while True:
        if getbit():
            if not getbit(): n = 0
            else:
                d3 = 3
                while True:
                    v = bits(LIT_BITS[d3])
                    if d3 and v == (1 << LIT_BITS[d3]) - 1: d3 -= 1; continue
                    break
                n = v + LIT_BASE[d3]
            for _ in range(n + 1): write(rdbyte())
            log.append(('lit', n + 1, dest_ofs + a1, tl + st['pos']))
        if st['pos'] <= stop: break
        k = 3
        while k >= 0 and getbit(): k -= 1
        k += 1
        ln = bits(LEN_BITS[k]) + LEN_BASE[k]
        if ln == 2:
            off = bits(9) + 64 if getbit() else bits(6)
        else:
            t = 1
            while t >= 0 and getbit(): t -= 1
            t += 1
            off = bits(OFF_BITS[t]) + OFF_BASE[t]
        a2 = a1 + off + ln
        for _ in range(ln):
            a2 -= 1; write(mem[D + a2])
        log.append(('match', ln, dest_ofs + a1, tl + st['pos'], off))
    return bytes(mem[D:D + size]), log, gmin, glive, tl, size, len(p), a1, tail



# ---- data and checks -----------------------------------------------------------------------------
out, log, (gmin, gmin_at), (glive, (glive_at, glive_unread)), TL, SIZE, PLEN, a1end, tail = inplace(PRG)
(ref, _, _), _ = AD.unpack_prg(PRG)
assert out == ref, 'in-place depack differs from autopack_depack.py'
assert hashlib.sha256(out).hexdigest() == SHA, 'sha256 differs from packer.md'
assert a1end == 0
final = AD.DEST_OFS - (TL + 12)
ag = AD.min_gap(str(PRG))
assert ag[2] == gmin and ag[3] == final, ag
# independent of the Python: the emulator's RAM at the language menu holds the depacked image at $296 + offset
RAMSH = 0x296
r80 = ram(WORK / 'c80.snap')
ram_same = sum(1 for i in range(0x1c, SIZE) if r80[RAMSH + i] == out[i])
ram_same_hi = sum(1 for i in range(0x101c, SIZE) if r80[RAMSH + i] == out[i])
# control: lowering the destination by the closest live gap still works, one byte more corrupts
def corrupt(path, ref, shift):
    o2 = inplace(path, AD.DEST_OFS - shift)[0]
    return sum(1 for x, y in zip(o2, ref) if x != y)
bad_live0, bad_live1 = corrupt(PRG, ref, glive), corrupt(PRG, ref, glive + 1)
assert bad_live0 == 0 and bad_live1 > 0, (bad_live0, bad_live1)

gaps = [(t[2] - AD.DEST_OFS, t[2] - t[3]) for t in log]           # (bytes still to write, gap) after each token
g0 = gaps[0][1]
second = min(g for left, g in gaps if left > 4096)                 # closest approach before the last 4 KB
second_at = [left for left, g in gaps if left > 4096 and g == second][0]
toks = log[1:]
nlit = sum(1 for t in toks if t[0] == 'lit'); nmatch = sum(1 for t in toks if t[0] == 'match')
litbytes = sum(t[1] for t in toks if t[0] == 'lit'); matchbytes = sum(t[1] for t in toks if t[0] == 'match')
assert litbytes + matchbytes == SIZE
maxoff = max(t[4] for t in toks if t[0] == 'match'); maxlen = max(t[1] for t in toks if t[0] == 'match')
maxrun = max(t[1] for t in toks if t[0] == 'lit')
# does each token shrink the gap? gap change across each token (a literal run's change includes its own bits)
dg = [(log[i][0], (log[i][2] - log[i][3]) - (log[i-1][2] - log[i-1][3])) for i in range(1, len(log))]
lit_widen = sum(1 for k, d in dg if k == 'lit' and d >= 0); match_shrink = sum(1 for k, d in dg if k == 'match' and d < 0)
# literal-count range from the tier tables (count = v + base + 1; all ones escapes, except in the last tier)
tiers = [(LIT_BASE[d] + 1, (1 << LIT_BITS[d]) - (2 if d else 1) + LIT_BASE[d] + 1) for d in (3, 2, 1, 0)]
LITMAX = tiers[-1][1]

others = []
for nm in ('PACT1.PRG', 'PACT2.PRG', 'PACT3.PRG', 'PACT4.PRG', 'STRAID.PRG', 'FRODON.STA'):
    f = WORK / 'files' / nm
    o1, _, (g, _), (gl, gla), tl, n, _, _, _ = inplace(f)
    (r1, _, _), _ = AD.unpack_prg(f)
    assert o1 == r1
    others.append((nm, n, g, AD.DEST_OFS - (tl + 12), gl, gla, corrupt(f, r1, gl), corrupt(f, r1, gl + 1)))

def clen(cmd):
    return len(subprocess.run(cmd, input=out, capture_output=True, check=True).stdout)
ratios = [('lz4 -9', clen(['lz4', '-9', '-c'])), ('Automation 2.3r', PLEN),
          ('gzip -9', clen(['gzip', '-9', '-c'])), ('zstd -19', clen(['zstd', '-19', '-c', '-q'])),
          ('xz -9e', clen(['xz', '-9e', '-c']))]

print(f'PACT2: text ${TL:x}, payload {PLEN} (stream {PLEN-12}), unpacked {SIZE}, sha256 ok, == autopack_depack.py')
print(f'c80.snap at ${RAMSH:x}+offset: {ram_same} of {SIZE-0x1c} bytes equal; past the first 4 KB {ram_same_hi} of {SIZE-0x101c}')
print(f'pointers before any read: write {log[0][2]}, read {log[0][3]}, gap {g0}')
print(f'min gap {gmin} at file offset {gmin_at} (final {final}); while stream unread: {glive} writing offset '
      f'{glive_at} with {glive_unread} stream bytes unread; closest before the last 4096 bytes: {second} ({second_at} to write)')
print(f'control: destination {glive} lower corrupts {bad_live0} bytes; {glive+1} lower corrupts {bad_live1}')
print(f'tokens: {nlit} literal runs ({litbytes} bytes, longest {maxrun}), {nmatch} matches ({matchbytes} bytes, '
      f'longest {maxlen}, farthest {maxoff}); literal runs that widen or keep the gap {lit_widen}/{nlit}, '
      f'matches that shrink it {match_shrink}/{nmatch}')
print('literal count tiers (lo, hi):', tiers)
print('tail (offset, gap, unread):', tail[::-1][:12])
for nm, n, g, fg, gl, gla, b0, b1 in others:
    print(f'  {nm}: unpacked {n} min gap {g} final {fg}; live min {gl} at (offset, unread) {gla}; '
          f'lowered {gl}: {b0} bad bytes, {gl+1}: {b1}')
for nm, b in ratios: print(f'  {nm}: {b} ({100*b/SIZE:.1f}%)')

# ---- svg -----------------------------------------------------------------------------------------
W, H = 900, 1192
s = []
a = s.append
INK, MUTE, ACC, BAD, GRID, OK = '#1f2328', '#656d76', '#0969da', '#cf222e', '#d0d7de', '#1a7f37'
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">')
a('<title id="t">Backwards in-place depack, 218 bytes apart at the end</title>')
a('<desc id="d">Carrier Command (1988) as packed by Automation Packer V2.3r: the stub depacks the LSD! stream '
  'backwards into a buffer that overlaps it, and the write pointer closes on the read pointer to 218 bytes at the '
  'last byte. Source: reversing/carriercommand/packer.md; pointers logged per token by '
  'py/infographics/gen_depack.py from the depacker in py/autopack_depack.py, checked against the emulator RAM in '
  'c80.snap. Facts: depack.facts.md.</desc>')
a('<style>text{font-family:Helvetica,Arial,sans-serif;fill:%s;font-size:12px}.t{font-size:20px;font-weight:bold}'
  '.h{font-size:14px;font-weight:bold}.m{fill:%s}.c{font-family:Menlo,monospace;font-size:11.5px}'
  '.s{font-size:11px;fill:%s}</style>' % (INK, MUTE, MUTE))
a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
a('<text x="24" y="38" class="t">Backwards in-place depack, 218 bytes apart at the end</text>')
a(f'<text x="24" y="60" class="m">Carrier Command (Realtime Games, 1988), packed by Automation Packer V2.3r: {PLEN:,} bytes '
  f'become {SIZE:,} in the same memory, with no second buffer.</text>')

def panel(x, y, w, h, title):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{GRID}"/>')
    a(f'<text x="{x+14}" y="{y+24}" class="h">{title}</text>')

def kfmt(v): return f'{v/1000:.0f}K' if v else '0'

# A: memory layout at start and end ---------------------------------------------------------------
panel(24, 80, 852, 190, 'A. One block of memory, before and after (offsets from tbase)')
mx0, mw = 110, 740
TOP = AD.DEST_OFS + SIZE
def MX(o): return mx0 + mw * o / TOP
rp0, wp0 = log[0][3], log[0][2]
def bar(y, label, segs, ptrs):
    a(f'<text x="{mx0-10}" y="{y+15}" text-anchor="end" class="h" style="font-size:12px">{label}</text>')
    for o1, o2, col, op, txt in segs:
        a(f'<rect x="{MX(o1):.1f}" y="{y}" width="{max(MX(o2)-MX(o1),1.5):.1f}" height="22" fill="{col}" fill-opacity="{op}"/>')
        if txt: a(f'<text x="{(MX(o1)+MX(o2))/2:.1f}" y="{y+15}" text-anchor="middle" class="s" style="fill:{INK}">{txt}</text>')
    a(f'<rect x="{mx0}" y="{y}" width="{mw}" height="22" fill="none" stroke="{MUTE}" stroke-width="0.8"/>')
    for o, col, txt, anc in ptrs:
        a(f'<path d="M{MX(o):.1f},{y-2} l-5,-8 h10 z" fill="{col}"/>')
        if txt: a(f'<text x="{MX(o)+(8 if anc=="start" else -8):.1f}" y="{y-4}" text-anchor="{anc}" class="s" style="fill:{col}">{txt}</text>')
y1 = 132
bar(y1, 'start', [(0, TL + 12, MUTE, 0.5, ''), (TL + 12, rp0, ACC, 0.35, f'packed stream, {PLEN-12:,} bytes'),
                  (rp0, TOP, '#ffffff', 0, 'free memory above the stream')],
    [(rp0, ACC, f'read pointer {rp0:,}', 'start'), (wp0, BAD, f'write pointer {wp0:,}', 'end')])
y2 = 194
bar(y2, 'end', [(0, TL + 12, MUTE, 0.5, ''), (TL + 12, AD.DEST_OFS, ACC, 0.15, ''),
                (AD.DEST_OFS, TOP, BAD, 0.22, f'unpacked PRG, {SIZE:,} bytes')],
    [(TL + 12, ACC, '', 'start'), (AD.DEST_OFS, BAD, f'read stops at {TL+12}, write ends at {AD.DEST_OFS} ($400)', 'start')])
a(f'<text x="{mx0}" y="{y2+40}" class="s">Grey: the {TL}-byte stub and the 12-byte LSD! header. The stream starts at {TL+12}, the '
  f'output at $400 = 1024: they finish {AD.DEST_OFS} - {TL+12} = {final} bytes apart.</text>')
a(f'<text x="{mx0}" y="{y2+56}" class="s">A mover copied into screen memory then slides the image down $400 onto tbase '
  f'(packer.md, from the stub\'s code at $a43c).</text>')

# B: the two pointers -------------------------------------------------------------------------------
panel(24, 284, 420, 336, 'B. Both pointers, token by token')
bx, by, bw, bh = 96, 324, 324, 210
def BX(written): return bx + bw * written / SIZE
def BY(o): return by + bh * (TOP - o) / TOP
for v in range(0, TOP + 1, 50000):
    a(f'<line x1="{bx}" y1="{BY(v):.1f}" x2="{bx+bw}" y2="{BY(v):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
    a(f'<text x="{bx-8}" y="{BY(v)+4:.1f}" text-anchor="end" class="s">{kfmt(v)}</text>')
for v in range(0, SIZE + 1, 100000):
    a(f'<text x="{BX(v):.1f}" y="{by+bh+16}" text-anchor="middle" class="s">{kfmt(v)}</text>')
a(f'<text x="{bx+bw/2}" y="{by+bh+32}" text-anchor="middle" class="s">bytes written</text>')
a(f'<text x="42" y="{by+bh/2}" class="s" transform="rotate(-90 42 {by+bh/2})" text-anchor="middle">offset from tbase</text>')
stp = max(1, len(log) // 900)
pts = [(SIZE - (t[2] - AD.DEST_OFS), t[2], t[3]) for t in log[::stp]] + [(SIZE, AD.DEST_OFS, TL + 12)]
poly = ' '.join(f'{BX(w):.1f},{BY(wo):.1f}' for w, wo, ro in pts) + ' ' + \
       ' '.join(f'{BX(w):.1f},{BY(ro):.1f}' for w, wo, ro in reversed(pts))
a(f'<polygon points="{poly}" fill="{OK}" fill-opacity="0.12"/>')
a('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>' % (' '.join(f'{BX(w):.1f},{BY(wo):.1f}' for w, wo, ro in pts), BAD))
a('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>' % (' '.join(f'{BX(w):.1f},{BY(ro):.1f}' for w, wo, ro in pts), ACC))
a(f'<text x="{BX(150000)+8:.1f}" y="{BY(TOP-150000)-6:.1f}" class="s" style="fill:{BAD}">write</text>')
a(f'<text x="{BX(200000):.1f}" y="{BY(rp0-60000)+18:.1f}" class="s" style="fill:{ACC}">read</text>')
a(f'<text x="{BX(60000):.1f}" y="{BY(200000):.1f}" class="s" style="fill:{OK}">gap</text>')
a(f'<text x="38" y="592" class="s">The write pointer falls one byte per byte written, the read</text>')
a(f'<text x="38" y="607" class="s">pointer {PLEN-12:,} in all. Matches close the gap, literals widen it.</text>')

# C: the gap, log scale -----------------------------------------------------------------------------
panel(456, 284, 420, 336, 'C. The gap shrinks to its minimum at the end')
cx0, cy0, cw, ch = 530, 324, 324, 210
glo, ghi = 100, 300000
def CX(left): return cx0 + cw * (1 - left / SIZE)
def CY(g): return cy0 + ch * (math.log10(ghi) - math.log10(g)) / (math.log10(ghi) - math.log10(glo))
for v in (100, 1000, 10000, 100000):
    a(f'<line x1="{cx0}" y1="{CY(v):.1f}" x2="{cx0+cw}" y2="{CY(v):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
    a(f'<text x="{cx0-8}" y="{CY(v)+4:.1f}" text-anchor="end" class="s">{v:,}</text>')
for v in range(0, SIZE + 1, 100000):
    a(f'<text x="{cx0+cw*v/SIZE:.1f}" y="{cy0+ch+16}" text-anchor="middle" class="s">{kfmt(v)}</text>')
a(f'<text x="{cx0+cw/2}" y="{cy0+ch+32}" text-anchor="middle" class="s">bytes written</text>')
a(f'<text x="474" y="{cy0+ch/2}" class="s" transform="rotate(-90 474 {cy0+ch/2})" text-anchor="middle">gap, bytes (log)</text>')
gp = ' '.join(f'{CX(left):.1f},{CY(max(g, glo)):.1f}' for left, g in gaps[::stp] + [gaps[-1]])
a(f'<polyline points="{gp}" fill="none" stroke="{OK}" stroke-width="2"/>')
a(f'<line x1="{cx0}" y1="{CY(final):.1f}" x2="{cx0+cw}" y2="{CY(final):.1f}" stroke="{BAD}" stroke-dasharray="4 3"/>')
a(f'<circle cx="{CX(0):.1f}" cy="{CY(gmin):.1f}" r="4" fill="{BAD}"/>')
a(f'<text x="{cx0+cw-8}" y="{CY(final)+16:.1f}" text-anchor="end" class="s" style="fill:{BAD}">{gmin} at the last byte</text>')
a(f'<text x="{cx0+8}" y="{CY(g0)+48:.1f}" class="s">{g0:,} before the first read</text>')
a(f'<text x="470" y="592" class="s">gap = {final} + (bytes still to write) - (stream still unread).</text>')
a(f'<text x="470" y="607" class="s">Before the last 4 KB it never drops below {second:,}.</text>')

# D: the last 48 bytes -------------------------------------------------------------------------------
panel(24, 634, 852, 196, 'D. The last 48 bytes written: what the margin really is')
dx0, dy0, dw, dh = 96, 670, 470, 110
glo2, ghi2 = 214, 6 * math.ceil(max(g for _, g, _ in tail) / 6)
def DX(off): return dx0 + dw * (47 - off) / 47
def DY(g): return dy0 + dh * (ghi2 - g) / (ghi2 - glo2)
for v in range(216, ghi2 + 1, 6):
    a(f'<line x1="{dx0}" y1="{DY(v):.1f}" x2="{dx0+dw}" y2="{DY(v):.1f}" stroke="{GRID}" stroke-width="0.6"/>')
    a(f'<text x="{dx0-8}" y="{DY(v)+4:.1f}" text-anchor="end" class="s">{v}</text>')
for v in (47, 40, 30, 20, 10, 0):
    a(f'<text x="{DX(v):.1f}" y="{dy0+dh+16}" text-anchor="middle" class="s">{v}</text>')
a(f'<text x="{dx0+dw/2}" y="{dy0+dh+32}" text-anchor="middle" class="s">file offset being written (the depack ends at offset 0)</text>')
a(f'<text x="42" y="{dy0+dh/2}" class="s" transform="rotate(-90 42 {dy0+dh/2})" text-anchor="middle">gap</text>')
tl_ = sorted(tail, reverse=True)
a('<polyline points="%s" fill="none" stroke="%s" stroke-width="1"/>' % (' '.join(f'{DX(o):.1f},{DY(g):.1f}' for o, g, u in tl_), GRID))
for o, g, u in tl_:
    a(f'<circle cx="{DX(o):.1f}" cy="{DY(g):.1f}" r="3" fill="{ACC if u else BAD}"/>')
a(f'<text x="{DX(glive_at)-4:.1f}" y="{DY(glive)-44:.1f}" text-anchor="middle" class="s" style="fill:{ACC}">{glive}, with {glive_unread} stream bytes unread</text>')
a(f'<line x1="{DX(glive_at):.1f}" y1="{DY(glive)-40:.1f}" x2="{DX(glive_at):.1f}" y2="{DY(glive)-5:.1f}" stroke="{ACC}"/>')
a(f'<text x="{DX(0)-2:.1f}" y="{DY(gmin)-10:.1f}" text-anchor="end" class="s" style="fill:{BAD}">{gmin}</text>')
tx = 600
a(f'<circle cx="{tx+4}" cy="{dy0+2}" r="3" fill="{ACC}"/><text x="{tx+12}" y="{dy0+6}" class="s">stream bytes still to read</text>')
a(f'<circle cx="{tx+4}" cy="{dy0+18}" r="3" fill="{BAD}"/><text x="{tx+12}" y="{dy0+22}" class="s">all read: nothing left to overwrite</text>')
a(f'<text x="{tx}" y="{dy0+46}" class="s">The 218 comes after the last read, so the</text>')
a(f'<text x="{tx}" y="{dy0+60}" class="s">binding approach is {glive}. Rerun with the</text>')
a(f'<text x="{tx}" y="{dy0+74}" class="s">destination {glive} bytes lower: correct.</text>')
a(f'<text x="{tx}" y="{dy0+88}" class="s">{glive+1} lower: {bad_live1} bytes come out wrong.</text>')
o_l = {nm.split('.')[0]: gl for nm, n, g, fg, gl, gla, b0, b1 in others}
same218 = [k for k, v in o_l.items() if v == 218]
a(f'<text x="{tx}" y="{dy0+108}" class="s">Other packed files on the disk:</text>')
a(f'<text x="{tx}" y="{dy0+122}" class="s">{", ".join(same218)} at 218,</text>')
o3 = [f'{k} {v}' for k, v in o_l.items() if v not in (218,) and k != 'PACT2']
a(f'<text x="{tx}" y="{dy0+136}" class="s">{", ".join(o3)}; all six end at 218.</text>')

# E: the token format ---------------------------------------------------------------------------------
panel(24, 844, 852, 236, 'E. One token: bits read backwards, MSB first, from the same bytes as the literals')
def box(x, y, w, txt, col, sub=None):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="3" fill="{col}" fill-opacity="0.15" stroke="{col}"/>')
    a(f'<text x="{x+w/2}" y="{y+17}" text-anchor="middle" class="c">{txt}</text>')
    if sub: a(f'<text x="{x+w/2}" y="{y+42}" text-anchor="middle" class="s">{sub}</text>')
ty = 882
box(40, ty, 60, 'flag', MUTE, '1 = literals')
box(110, ty, 140, 'literal count', ACC, f'1 .. {LITMAX:,}')
box(260, ty, 140, 'literal bytes', ACC, 'stream to output')
box(410, ty, 130, 'match length', BAD, '2 .. 1,033')
box(550, ty, 110, 'offset', BAD, '0 .. 4,383')
box(670, ty, 190, 'copy length bytes', BAD, 'from write + offset + length')
a(f'<text x="40" y="{ty+64}" class="s">Flag 0 skips to the match. Between the literals and the match the loop stops once the read pointer is down '
  f'to header + 12. The source is above the write</text>')
a(f'<text x="40" y="{ty+78}" class="s">pointer, in bytes already written, copied one byte at a time, so a match can overlap itself and repeat a run.</text>')
lt = ',  '.join(f'{b} bits ({lo}..{hi:,})' for (lo, hi), b in zip(tiers, (2, 2, 3, 10)))
rows = [
    ('literal count', f'0 = 1;  1 then {lt}; all ones escapes'),
    ('match length', '0 = 2,  10 = 3,  110 = 4 + 1 bit,  1110 = 6 + 2 bits,  1111 = 10 + 10 bits'),
    ('offset, length 2', '0 then 6 bits (0..63),  1 then 9 bits + 64 (64..575)'),
    ('offset, longer', '10 then 5 bits (0..31),  0 then 8 bits + 32,  11 then 12 bits + 288 (..4,383)'),
]
yy = ty + 104
for k, v in rows:
    a(f'<text x="40" y="{yy}" class="h" style="font-size:12px">{k}</text><text x="160" y="{yy}" class="c">{v}</text>')
    yy += 20
a(f'<text x="40" y="{yy+6}" class="s">In this file {nlit:,} literal runs carry {litbytes:,} bytes and {nmatch:,} matches carry {matchbytes:,} '
  f'(longest {maxlen:,}, farthest {maxoff:,}). Fixed codes, no Huffman.</text>')

# F: ratios -------------------------------------------------------------------------------------------
panel(24, 1094, 852, 84, f'F. The same {SIZE:,}-byte program through other compressors (run here, stdin)')
for i, (nm, b) in enumerate(ratios):
    col = BAD if nm.startswith('Automation') else ACC
    xi = 40 + i * 168
    yb = 1136
    a(f'<text x="{xi}" y="{yb}" class="h" style="font-size:12px;fill:{col}">{nm}</text>')
    a(f'<text x="{xi}" y="{yb+16}" class="s">{b:,} bytes, {100*b/SIZE:.1f}%</text>')
    a(f'<rect x="{xi}" y="{yb+24}" width="{300*b/SIZE:.1f}" height="7" fill="{col}" fill-opacity="0.6"/>')
a('</svg>')
(OUT / 'depack.svg').write_text('\n'.join(s))
print('wrote', OUT / 'depack.svg')
