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
s = Svg(W, H, 'PowerMonger: everything the game does in one simulation step (a tick), in order',
        'The drawing calls sit behind a divider that sets how often the screen is redrawn; at normal speed it is 1, so everything runs every tick')

# ------------------------------------------------------------------ lead (README "Design digest", ai.md "What the loop
# actually is", strategy.md "Where it runs"; see tick.facts.md "Lead and captions")
FW = W - 32
y0 = s.para(16, 74, FW, 'PowerMonger (Bullfrog / Electronic Arts, 1990, here the Atari ST version) is a war game on a '
            'height-mapped land of settlements: the player gives orders to captains, the computer lords give orders '
            'through the same path, and every man carries them out on his own. This figure comes from reverse-engineering '
            'the game\'s 68000 machine code (the ST\'s CPU) and running it in an emulator. The game advances in ticks. '
            'Each tick runs one routine ($13000) that moves the whole world one step: the commander AI decides, every '
            'man, boat and building takes one step of its own small state machine, and the screen is redrawn.',
            size=12.5, lh=17)
y0 = s.para(16, y0 + 4, FW, 'The figure shows one tick. Left: the calls $13000 makes, in order. Right: the loop '
            '$14b62 that walks every object record once and jumps to the handler for its current mode. Lower right: '
            'the other data pools the same tick moves. The point to take away is that there is no separate AI per '
            'unit type (observed in every record traced, not proven absent): a record holds a mode number (one byte '
            'saying what that man or boat is doing), the loop runs that mode\'s handler, and the handler\'s choice of the '
            'next mode is the behaviour.',
            size=12.5, lh=17)
y0 = s.key(16, y0 + 4, FW)
DY = y0 + 6 - 62
s.begin(0, DY)

# ------------------------------------------------------------------ left: the tick body
LX, LW = 16, 380
s.frame(LX, 62, LW, 678, 'One tick, in call order (routine $13000)')
rows = [
    ('$13026', 'if paused ($57ff2 != 0), skip to $13058', 'code'),
    ('$1302e', 'game clock +1 ($2df70), master tick +1 ($4bb3e)', 'code'),
    ('$1303a', 'if no game is running ($14e4e == 0), skip to $13058', 'code'),
    ('$127e6', 'sound events', 'code'),
    ('$6522', 'commander AI: the computer lords decide orders', 'live'),
    ('$d322', 'per-side troop totals (stored at $57fba)', 'live'),
    ('$3e06', 'the smaller pools: animals, pigeons, arrows, forest', 'live'),
    (None, 'screen-update divider ($57ff0 / $57fee, 1 at normal speed)', None),
    ('$1870', 'wait for the screen refresh (VBL), flush buffer $12ce0', 'code'),
    ('$178ae', 'status bars, then terrain drawing ($f898)', 'code'),
    (None, 'every tick again', None),
    ('$1abaa', 'seasons and weather; $57fec += 1', 'code'),
    ('$17878', 'compass, then water animation ($165b2)', 'code'),
    ('$14b62', 'ENTITY LOOP: steps every man, boat, house (right)', 'proven'),
    ('$6a3a', 'order executor: order slots $58016 -> group state', 'live'),
    ('$7a56', 'info panels; camera auto-rotate ($130d4)', 'code'),
    ('$d23a', 'force ratio from the troop totals (0..4, $57fce)', 'code'),
    ('$7202', 'text panels, minimap, captain boxes', 'code'),
]
y = 90
for addr, lab, ev in rows:
    if addr is None:
        s.text(LX + 14, y + 13, lab, size=11, color='#6a1b9a', italic=True)
        y += 22
        continue
    s.box(LX + 12, y, LW - 24, 26, ev, rx=4, sw=2 if addr == '$14b62' else 1.2)
    s.text(LX + 20, y + 17, addr, size=10.5, mono=True, color='#57606a')
    s.text(LX + 72, y + 17, lab, size=11.5)
    y += 32
# $3e06 detail
y += 2
s.lines(LX + 14, y + 6, [
    ('The smaller-pools call ($3e06) also runs, per tick:', {'weight': 'bold'}),
    'animals $4044 (40 slots), pigeons $416e (48),',
    'arrows $596a (49), forest animator $4342,',
    'the armies eat (food decay)',
], size=11)
# ------------------------------------------------------------------ right: the iterator
RX, RW = 410, 474
s.frame(RX, 62, RW, 420, 'The entity loop ($14b62): one pass over every record per tick')
bx = RX + 14
s.box(bx, 90, RW - 28, 44, 'proven', rx=4)
s.lines(bx + 8, 107, ['object records: 512 slots of 50 bytes ($32) from $51b66;',
                      'slot 0 is never walked: records 1..511 ($51b98 .. $57f66)'], size=12)
s.line(RX + RW / 2, 134, RX + RW / 2, 152)
s.box(bx, 152, RW - 28, 26, 'proven', rx=4)
s.text(bx + 8, 170, 'read byte 5 of the record, the owner ($14b72)', size=12)
# three branches
cw = (RW - 28 - 16) / 3
labels = [('byte 5 = 0: free slot', ['skip to the next', 'record ($1622c)']),
          ('below 0: dying', ['$1623c: count 18 down', 'from $a0, then $0a loose', 'equipment or $20 freed']),
          ('above 0: live', ['anim frame: byte 14 += 1', 'when ($4bb40 + w24) & $3ff', '== w34, flag bit 4 clear'])]
for i, (h, body) in enumerate(labels):
    x = bx + i * (cw + 8)
    s.line(RX + RW / 2, 178, x + cw / 2, 196)
    s.box(x, 196, cw, 74, 'proven', rx=4)
    s.text(x + 6, 212, h, size=12, weight='bold')
    s.lines(x + 6, 229, body, size=10.5, lh=14)
lx = bx + 2 * (cw + 8)
s.line(lx + cw / 2, 270, lx + cw / 2, 288)
s.box(bx, 288, RW - 28, 44, 'proven', rx=4)
s.lines(bx + 8, 305, ['read the position x, y (bytes 8, 10) and the mode (byte 31);',
                      'jump through a table of 75 handlers ($14bb4, entries $00..$94)'], size=12)
s.line(RX + RW / 2, 332, RX + RW / 2, 350)
s.box(bx, 350, RW - 28, 26, 'proven', rx=4)
s.text(bx + 8, 368, 'run one tick of that mode\'s handler (code $14c48..$1620e)', size=12)
s.line(RX + RW / 2, 376, RX + RW / 2, 394)
s.box(bx, 394, RW - 28, 58, 'proven', rx=4)
s.lines(bx + 8, 410, ['epilogue ($161c4): clamp the position, veto a step onto water (mode $00), relink',
                      '(relink = refile the record in its map-cell bucket); $16202 clamp + relink;',
                      '$16228 relink only; $1622c no write-back; then next record (+50 bytes, to $57f66)'], size=11, lh=14.5)
# loop arrow back to the top
s.path('M %d 452 L %d 466 L %d 466 L %d 112 L %d 112' % (RX + RW / 2, RX + RW / 2, RX + RW - 4, RX + RW - 4, RX + RW - 14))
s.text(RX + RW - 10, 476, 'next record', size=10, anchor='end', color='#424242')

# ------------------------------------------------------------------ right bottom: the pools
s.frame(RX, 490, RW, 250, 'What else moves each tick: the other data pools')
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
    ('map-cell buckets', '$47970, one chain/cell', 'every mover', 'proven'),
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
s.end()
y = 770 + DY
s.text(16, y, 'How to read each panel', size=13, weight='bold')
y += 20
cw3 = (FW - 2 * 20) / 3
cap = [
    ('The tick (left)', 'Each row is one call made by $13000, top to bottom in the order it runs: the routine\'s '
     'address, what it does, and a fill for the evidence (key above). The two purple italic lines are not '
     'calls; they mark where the drawing block behind the divider starts and ends.',
     'Takeaway: the game\'s decisions (commander AI $6522, entity loop $14b62, order executor $6a3a) run on every tick. '
     'Only the four drawing calls $1870, $12ce0, $178ae and $f898 sit behind the divider, which is a drawing rate, not '
     'a simulation rate: slowing the drawing does not slow the world, and at normal speed the divider is 1 anyway.'),
    ('The entity loop (right)', 'A flowchart for one record; the arrow on the right goes back for the next record until '
     'the end of the array. Byte 5 is the owner: 0 is a free slot, negative a dying man, positive a live one. A live '
     'record\'s mode (byte 31) indexes a table of 75 handler offsets at $14bb4.',
     'Takeaway: one jump table replaces any per-type logic. The handler moves the record one tick and usually writes a '
     'new mode; the epilogue clamps the position, vetoes a step onto water by setting mode $00, and relinks the record '
     'into its map-cell bucket.'),
    ('The pools (lower right)', 'One row per data pool: what it holds, its base address and record size, and the '
     'routine that moves it each tick. "511 x 50 B" means 511 records of 50 bytes.',
     'Takeaway: only men, boats, buildings and markers are object records. Animals, pigeons, arrows and trees are '
     'smaller pools moved near the top of the tick. The cell buckets let a man find neighbours by walking one chain '
     'instead of scanning all 511 records.'),
]
yb = y
for i, (h, how, take) in enumerate(cap):
    x = 16 + i * (cw3 + 20)
    yy = s.para(x, y, cw3, how, size=11, lh=14.5, lead=h)
    yy = s.para(x, yy + 4, cw3, take, size=11, lh=14.5, color='#1b5e20')
    yb = max(yb, yy)
y = yb + 14
s.text(16, y, 'Numbers and how we know them', size=13, weight='bold')
y += 18
for t in [
    'Cadence, from a 3-million-instruction trace of mission 1: 13 ticks per 250 VBLs (screen refreshes: the ST\'s '
    'screen interrupt, one per displayed frame), about 2.6 ticks a second; one tick takes as long as about 19 screen '
    'refreshes, so the game is limited by computation, not by the display. $6522, $d322, $3e06 and $6a3a ran 13 times each in that trace, '
    '$14b62 14 times. One tick is about 200k to 230k emulated instructions ("steps").',
    'A man, boat, building or marker is one 50-byte record and runs its mode handler once per tick inside $14b62. '
    'Animals, pigeons, arrows and trees are separate pools moved by $3e06 near the top of the same tick; they are not '
    'entity records. Mission 1, settled view: about 50 of the 511 slots are in use and about 26 reach a handler each tick.',
    'Proven means checked against the game\'s own code: a Python rewrite of the routine was run beside the game\'s own '
    '68000 code, called in isolation from many saved game states (the emulator\'s callcap command), and every changed '
    'byte matched; "675/675" is matching bytes out of bytes compared. Proven here: the $14b62 prologue and epilogues '
    '(675/675 and 1335/1335 tracked bytes), the dying path $1623c 275/275, animals and pigeons 45094/45094, arrows '
    '4210/4210, the forest animator $4342 8 of 9 branches. Observed: the trace counts above. Inferred: the call-order '
    'listing, read from the disassembly.',
]:
    y = s.para(16, y, FW, t, size=11.5, lh=15.5) + 5
s.legend(16, y + 14, ['proven', 'live', 'code'])
y = s.para(16, y + 30, FW, 'Sources: strategy.md "Where it runs", "Where the calls sit" and "Measured cadence"; ai.md "The simulation tick" '
           'and "The iterator"; generator py/fsm/build_tick.py; line-by-line sources in tick.facts.md.', size=9.5, lh=12.5,
           color='#57606a')
s.h = int(y + 8)
s.save(os.path.join(out, 'tick.svg'))
