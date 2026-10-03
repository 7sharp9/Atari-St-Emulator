"""a3: ev1_icon_drive.py -- event 1 at the READ-icon handler ($00a0ce, push $00a114) through the real panel: sv_held_lever.snap (action/drv.py: pickaxe 168 in the rucksack, hero facing the TUNNEL lever 144); the held item's
type-8 record is overwritten with scroll 132 (READ LANGUAGE) -- LABEL: poked item -- Space opens the item panel, icon $10 is picked with the joystick and confirmed with fire (drv.pick_icon_id).  bp at $a114 decodes the entry:
expect [1][front object = lever 144][word 132]; the lever has no event-1 block, so the consumer matches nothing."""
import sys, os
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/action')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drv                       # chdirs to ROOT; we never call drv.ensure() (it would write under secrets_out/action)
from drv import Repl, Tally, ruck_panel, icons, pick_icon_id, type8, A5
import probe
from probe import *
snap = ROOT + '/scratchpad/cadaver/secrets_out/action/sv_held_lever.snap'
h = HH.H(snap); r = h.r
t = Tally(r)
t8 = type8(r); print('rucksack before', t8['recs'][:2], 'sel', r.a5(1262, 2).hex())
dat = int(t8['data'], 16)
r.cmd('w %x %08x' % (dat, (132 << 16) | (t8['recs'][0][1])))        # [id.w][word.w] of record 0
print('rucksack after poke', type8(r)['recs'][:2])
ruck_panel(r, t, 'space')
ic = icons(r); print('icons offered for 132:', [hex(i) for i in ic])
if 0x10 not in ic: print('icon $10 not offered'); sys.exit(1)
# pick icon $10 and stop at the producer: run the fire confirm manually so bp can catch $a114
path = []
from drv import cur_icon, pulse, RIGHT, DOWN, FIRE
for _ in range(12):
    cur, box = cur_icon(r)
    if cur == 0x10: break
    pulse(r, t, RIGHT if len(path) % 3 != 2 else DOWN); path.append('R' if len(path) % 3 != 2 else 'D')
print('cursor icon', hex(cur_icon(r)[0]), 'path', path)
r.cmd('kbd ff 80', 's 300')
e = bp_push(h, 0xa114, 400000)
if not e: print('no hit at $a114'); sys.exit(1)
print('entry op=$%04x ptr=%s word=%d  2128(A5)=%d' % (e['op'], e['ptrname'], e['word'], r.w(A5 + 2128)))
r.cmd('kbd ff 00', 's 30000')
h.close()
