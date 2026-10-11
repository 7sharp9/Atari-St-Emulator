#!/usr/bin/env python3
"""Figure: one simulation tick ($13000) and the entity iterator $14b62, with the pools that share the tick.

usage: build_tick.py      writes out/tick.svg and out/tick.png
Every label is from strategy.md "Where it runs" / "Measured cadence" and ai.md "The simulation tick", "The iterator",
"The object record", the shepherds/animals/pigeons and arrows blocks; see tick.facts.md for the line-by-line sources.
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from svgkit import Svg  # noqa: E402

root = here
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
out = os.path.join(os.environ.get('PM_WORK') or os.path.join(root, 'scratchpad/pm_fig'), 'out')

W, H = 900, 925
s = Svg(W, H, 'PowerMonger: one simulation tick and the entity iterator',
        'The tick body $13000 runs every call; only the present-rate block sits behind the $57ff0/$57fee divider')

# ------------------------------------------------------------------ left: the tick body
LX, LW = 16, 380
s.frame(LX, 62, LW, 678, 'The tick: $13000, in call order')
rows = [
    ('$13026', 'paused ($57ff2 != 0): skip to $13058', 'code'),
    ('$1302e', 'sim clock $2df70 += 1; master tick $4bb3e += 1', 'code'),
    ('$1303a', 'no game running ($14e4e == 0): skip to $13058', 'code'),
    ('$127e6', 'sound events', 'code'),
    ('$6522', 'commander AI (strategy.md)', 'live'),
    ('$d322', 'per-side troop totals -> $57fba', 'live'),
    ('$3e06', 'side pools: animals, pigeons, arrows, forest', 'live'),
    (None, 'present-rate divider $57ff0 / $57fee (1 at normal speed)', None),
    ('$1870', 'VBL sync, then $12ce0 buffer flush', 'code'),
    ('$178ae', 'HUD bars, then $f898 terrain raster', 'code'),
    (None, 'every tick again', None),
    ('$1abaa', 'seasons and weather; $57fec += 1', 'code'),
    ('$17878', 'compass, then $165b2 water animation', 'code'),
    ('$14b62', 'ENTITY ITERATOR (right)', 'proven'),
    ('$6a3a', 'order executor: $58016 -> group state, lead mode', 'live'),
    ('$7a56', 'info panels; $130d4 auto-rotate', 'code'),
    ('$d23a', 'force ratio $57fba -> $57fce (0..4)', 'code'),
    ('$7202', 'text panels, minimap, captain boxes', 'code'),
]
y = 90
for addr, lab, ev in rows:
    if addr is None:
        s.text(LX + 14, y + 13, lab, size=11, color='#6a1b9a', italic=True)
        y += 22
        continue
    s.box(LX + 12, y, LW - 24, 26, ev, rx=4, sw=2 if addr == '$14b62' else 1.2)
    s.text(LX + 20, y + 17, addr, size=12, mono=True, weight='bold')
    s.text(LX + 86, y + 17, lab, size=12)
    y += 32
# $3e06 detail
y += 2
s.lines(LX + 14, y + 6, [
    ('$3e06 also runs, per tick:', {'weight': 'bold'}),
    'animals $4044 (40 slots), pigeons $416e (48),',
    'arrows $596a (49), forest animator $4342,',
    'the armies eat (food decay)',
], size=11)
# ------------------------------------------------------------------ right: the iterator
RX, RW = 410, 474
s.frame(RX, 62, RW, 420, 'The iterator $14b62: one pass per tick')
bx = RX + 14
s.box(bx, 90, RW - 28, 44, 'proven', rx=4)
s.lines(bx + 8, 107, ['object records $51b66: 512 slots x 50 bytes ($32);',
                      'slot 0 never walked: A1 = $51b98 .. $57f66 (records 1..511)'], size=12)
s.line(RX + RW / 2, 134, RX + RW / 2, 152)
s.box(bx, 152, RW - 28, 26, 'proven', rx=4)
s.text(bx + 8, 170, 'byte 5 (owner): $14b72  tst.b 5(A1)', size=12)
# three branches
cw = (RW - 28 - 16) / 3
labels = [('== 0: free slot', ['skip to $1622c']),
          ('< 0: dying', ['$1623c: count 18 down', 'from $a0, then $0a loose', 'equipment or $20 freed']),
          ('> 0: live', ['anim frame: byte 14 += 1', 'when ($4bb40 + w24) & $3ff', '== w34, flag bit 4 clear'])]
for i, (h, body) in enumerate(labels):
    x = bx + i * (cw + 8)
    s.line(RX + RW / 2, 178, x + cw / 2, 196)
    s.box(x, 196, cw, 74, 'proven', rx=4)
    s.text(x + 6, 212, h, size=12, weight='bold')
    s.lines(x + 6, 229, body, size=10.5, lh=14)
lx = bx + 2 * (cw + 8)
s.line(lx + cw / 2, 270, lx + cw / 2, 288)
s.box(bx, 288, RW - 28, 44, 'proven', rx=4)
s.lines(bx + 8, 305, ['D6, D7 := x, y (bytes 8, 10); D0 := mode, byte 31',
                      'jmp $14bb4 + word[$14bb4 + mode]: 75 entries, $00..$94'], size=12)
s.line(RX + RW / 2, 332, RX + RW / 2, 350)
s.box(bx, 350, RW - 28, 26, 'proven', rx=4)
s.text(bx + 8, 368, 'one tick of the mode handler ($14c48..$1620e, ai.md)', size=12)
s.line(RX + RW / 2, 376, RX + RW / 2, 394)
s.box(bx, 394, RW - 28, 58, 'proven', rx=4)
s.lines(bx + 8, 410, ['epilogue: $161c4 clamp + terrain veto (water: mode $00) + relink;',
                      '$16202 clamp + relink; $16228 relink; $1622c no write-back.',
                      '$1622c: lea 50(A1),A1; cmpa.l #$57f66,A1; bne $14b72'], size=11, lh=14.5)
# loop arrow back to the top
s.path('M %d 452 L %d 466 L %d 466 L %d 112 L %d 112' % (RX + RW / 2, RX + RW / 2, RX + RW - 4, RX + RW - 4, RX + RW - 14))
s.text(RX + RW - 10, 476, 'next record', size=10, anchor='end', color='#424242')

# ------------------------------------------------------------------ right bottom: the pools
s.frame(RX, 490, RW, 250, 'What shares the tick: the pools')
hdr = ['pool', 'address, layout', 'updated by']
cols = [RX + 12, RX + 134, RX + 330]
yy = 530
for c, t in zip(cols, hdr):
    s.text(c, yy, t, size=11, weight='bold')
pools = [
    ('men, boats, houses', '$51b66, 511 x 50 B', '$14b62', 'proven'),
    ('animals (sheep)', '$4ccd6, 40 x 20 B', '$3e06 ($4044)', 'proven'),
    ('carrier pigeons', '$4c112, 48 x 26 B', '$3e06 ($416e)', 'proven'),
    ('arrows', '$4be00, 49 x 16 B', '$596a', 'proven'),
    ('trees', '$4d252, stride 12', '$4342', 'proven'),
    ('forest markers', '$4c5f4, stride 22', '$4342', 'proven'),
    ('cell buckets', '$47970, one chain/cell', 'every mover', 'proven'),
]
yy += 8
for name, addr, upd, ev in pools:
    s.box(RX + 8, yy, RW - 16, 21, ev, rx=3, sw=1)
    s.text(cols[0], yy + 15, name, size=11)
    s.text(cols[1], yy + 15, addr, size=11, mono=True)
    s.text(cols[2], yy + 15, upd, size=11, mono=True)
    yy += 24
s.text(RX + 12, yy + 14, 'The bucket chains link all pools by offsets from $51b66 (negative below it).', size=10.5,
       color='#424242')

# ------------------------------------------------------------------ bottom notes
s.lines(16, 768, [
    ('Reading the figure', {'weight': 'bold'}),
    'Cadence (3M-instruction trace, mission 1): 13 ticks per 250 VBLs, about 2.6 Hz; one tick body costs about 19 VBLs of',
    'instructions (compute-bound). $6522, $d322, $3e06 and $6a3a 13 hits each, $14b62 14. About 200k to 230k steps per tick.',
    'A man, boat, building or marker is one 50-byte record and runs its mode handler once per tick inside $14b62. Animals,',
    'pigeons, arrows and trees are separate pools moved by $3e06 near the top of the same tick; they are not entity records.',
    'Mission 1, settled view: about 50 of the 511 slots are in use and about 26 reach a handler each tick.',
    'Proven: $14b62 prologue and epilogues (675/675, 1335/1335 tracked bytes), $1623c 275/275, animals and pigeons',
    '45094/45094, arrows 4210/4210, $4342 8 of 9 branches. Live: the trace counts above. Code read: the call order listing.',
], size=11.5, lh=16)
s.legend(16, 908, ['proven', 'live', 'code'])
s.save(os.path.join(out, 'tick.svg'))
