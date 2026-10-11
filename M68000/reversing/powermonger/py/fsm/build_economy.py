#!/usr/bin/env python3
"""Figure: the economy as flows into and out of one lord record ($4e514, 32 bytes).

usage: build_economy.py     writes out/economy.svg and out/economy.png
Every flow, amount and evidence label is from economy.md sections 1, 2a-2c, 3a, 6 and ai.md (see economy.facts.md).
"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from svgkit import Svg, EVID  # noqa: E402

root = here
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
out = os.path.join(os.environ.get('PM_WORK') or os.path.join(root, 'scratchpad/pm_fig'), 'out')

W, H = 900, 1026
s = Svg(W, H, 'PowerMonger economy: what moves a lord\'s food, men, goods and loyalty',
        'Flows into and out of one lord record $4e514 (32 bytes); every flow is a write by a named routine')

# columns
LX, LW = 16, 248           # producers (civilian jobs)
CX, CW = 336, 228          # the lord record
RX, RW = 636, 248          # the army (group record + men)
TOP = 70

# ------------------------------------------------------------------ the lord record
regions = [  # name, y0, y1
    ('+6  food (store)', 96, 300),
    ('+8  troops_field (men at home)', 312, 456),
    ('+24..31  goods[8]', 468, 708),
    ('+14  loyalty_pressure', 720, 840),
]
s.box(CX, 70, CW, 784, 'plain', rx=8)
s.text(CX + CW / 2, 88, 'lord record $4e514', size=13, weight='bold', anchor='middle')
for name, y0, y1 in regions:
    s.box(CX + 10, y0, CW - 20, y1 - y0, 'code', rx=5, sw=1)
    s.text(CX + CW / 2, y0 + 18, name, size=12, weight='bold', anchor='middle', mono=False)
s.lines(CX + 22, 520, ['Pike, Sword, Bow, Plough,', 'Boat, Pot, Catapult, Cannon', '(0..255 each; the lord',
                       'panel prints them)'], size=10.5, color='#424242', lh=14)
s.lines(CX + 22, 132, ['filled by catches and', 'returning farmers;', 'emptied by armies,',
                       'gatherers and winter upkeep'], size=10.5, color='#424242', lh=14)
s.lines(CX + 22, 348, ['no growth term: men', 'are conserved (econ. 6)'], size=10.5, color='#424242', lh=14)
s.lines(CX + 22, 756, ['>= 600: $550e revolt,', 'lord and his buildings', 'change side, reset 300'],
        size=10.5, color='#424242', lh=14)

# ------------------------------------------------------------------ side frames
s.frame(LX, 70, LW, 784, 'Civilian jobs (entity modes)')
s.frame(RX, 70, RW, 784, 'The army: group $51538 + men')
s.lines(RX + 12, 108, ['group food 36(group)  ("Food:")', 'carried stock 84 + 12i (8 items)',
                       'men: byte 44 weapon, 33 tool'], size=10.5, color='#424242', lh=14, mono=False)


def flow(side, y, lines, ev, direction, amt=None):
    """side 'L' or 'R'; direction 'in' (into the lord) / 'out' / 'both'. A box in the side column and an arrow."""
    n = len(lines)
    h = 14 * n + 10
    if side == 'L':
        bx, bw = LX + 10, LW - 20
        x_box, x_lord = bx + bw, CX
    else:
        bx, bw = RX + 10, RW - 20
        x_box, x_lord = bx, CX + CW
    s.box(bx, y, bw, h, ev, rx=4, sw=1.1)
    for i, t in enumerate(lines):
        s.text(bx + 7, y + 16 + 14 * i, t, size=10.5, weight='bold' if i == 0 else 'normal')
    ym = y + h / 2
    col = EVID[ev][1]
    if direction in ('in', 'both'):
        s.line(x_box, ym - (3 if direction == 'both' else 0), x_lord, ym - (3 if direction == 'both' else 0), color=col)
    if direction in ('out', 'both'):
        s.line(x_lord, ym + (3 if direction == 'both' else 0), x_box, ym + (3 if direction == 'both' else 0), color=col)
    if amt:
        mx = (x_box + x_lord) / 2
        s.text(mx, ym - 7, amt, size=10.5, anchor='middle', weight='bold', color='#212121')
    return y + h


# ---- food, left
flow('L', 100, ['fisher delivers: mode $60', '$15ddc, one catch per trip'], 'proven', 'in', '+4')
flow('L', 148, ['farmer home: mode $16', '+2 more with a Plough (byte 33 = 8):', '0 of 5164 returns doubled'], 'proven', 'in', '+2')
flow('L', 210, ['gatherer delivery, no group:', 'mode $42 -> $600a (food <= 2:', 'sent home, delivery lost)'], 'proven', 'out', '-2')
flow('L', 268, ['winter park: mode $7c pulse', '$163b8, each parked man'], 'proven', 'out', '-1')
# ---- food, right
flow('R', 150, ['order $06 take food: mode $1a', 'food >> shift into 36(group)', 'live: town 22 -> 11'], 'proven', 'out', 'slice')
flow('R', 206, ['order $12 drop food: $3bc0', '36(group) >> shift to the town', 'live: town 22 -> 147'], 'live', 'in', 'slice')
flow('R', 262, ['trade $63f4 (order $1c, mode $78):', 'food spent goes to the lord'], 'proven', 'in', '+spent')
# ---- men
flow('R', 318, ['a recruit joins: mode $2a', '$1b2a; order $08 summons $34f2'], 'proven', 'out', '-1')
flow('R', 362, ['leaves a group: $1b8c -> $1c04;', '$37c2 re-parent $382a: -1'], 'proven', 'both', '+1 / -1')
flow('R', 406, ['transfer men, order $04: $1c96', 'live: 6 pairs for 6 men'], 'live', 'both', '-1 / +1')
flow('L', 318, ['revolt: $25d6 $2644, old lord', 'of a captain with no group'], 'proven', 'out', '-1')
flow('L', 362, ['player pigeon lands: $42be', 'a dead man revived, 6 of 6'], 'live', 'in', '+1')
flow('L', 406, ['kill: $5590 tail $567e', 'an ungrouped man dies'], 'proven', 'out', '-1')
# ---- goods, left
flow('L', 470, ['gatherers: $5cde work order', '-> $3e fell / $40 build / $6a pots', '-> $42 deliver -> $600a -> $60dc',
                'throttled: ~8100 ticks between'], 'proven', 'in', '+1')
flow('L', 548, ['merchants: $159de takes, $159a4', 'banks, nearly always at the home', 'lord (k5_s4, 100M: 10 taken, 8 banked);',
                '1 of 10 moved a Plough to another', 'lord (stale A0 at $15b54)'], 'live', 'both', '-1 / +1')
# ---- goods, right
flow('R', 470, ['order $10 take equipment:', 'mode $6e -> $61f8, goods >> shift', '-> $6352 / $638c equip or upgrade'],
     'proven', 'out', '>> shift')
flow('R', 534, ['trade $63f4: carried stock sold', 'at 2 x price, credit buys back', 'in the posture\'s order ($650a)'],
     'proven', 'both', 'sell / buy')
flow('R', 598, ['exchange $160f8 (modes $8e, $90):', 'weapon back, best bow/sword/pike', 'taken, farmer takes a Plough;',
                'lord >= 8: return misdirected'], 'proven', 'both', 'swap')
flow('R', 670, ['drop equipment, order $18:', '$39d4 D7=2, carried >> shift'], 'code', 'in', '>> shift')
# ---- loyalty
flow('R', 724, ['order $06 take food:', '+16 >> shift'], 'proven', 'in', '+')
flow('R', 766, ['order $12 drop food, trade:', '-8 own side (trade +8 other)'], 'live', 'in', '-')
flow('L', 724, ['winter park, mode $7c, first', 'pulse after a park only:', 'hungry (troops_field x 4 >= food) +2,',
                'fed -1'], 'proven', 'in', '+2 / -1')
flow('L', 798, ['revolt $550e at >= 600: 10 of the', '27 natural calls (17: conquest $539a)'], 'proven', 'out', '')

# ------------------------------------------------------------------ notes
s.lines(16, 880, [
    ('Reading the figure', {'weight': 'bold'}),
    'shift = posture - 2 ($30fe): aggressive takes all, neutral half, passive a quarter. Men and goods are separate ledgers:',
    'goods never become men. Food and goods meet only in the trade. The winter park (mode $7c) needs the season word',
    '$57fd0 == 0: farmers ($16), merchants ($4e) and fishers ($5e) park there, so upkeep and loyalty move only in winter',
    '(a man idling in $7e pulses too, never on that first-pulse edge). Mission 1 builds both enemy lords at 608; the first winter pulse resets them to 300.',
    'Gates: gate_fsm15.py (job modes, 18452/18452 bytes), gate_orders.py ($600a, $60dc, $61f8, $6352, $638c, $63f4),',
    'gate_equip.py ($160f8, 385/385 over 201 states), diff_revolt.py (1778/1778 over 49 states), heartbeat block (99/99).',
], size=11.5, lh=16)
s.legend(16, 1006, ['proven', 'live', 'code'])
s.save(os.path.join(out, 'economy.svg'))
