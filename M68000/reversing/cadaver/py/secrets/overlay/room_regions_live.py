"""room_regions_live.py [walk|bounds|obj]: CAVERN's region events (15 for the hero, 17 for any other object) driven live on gameplay_empire.snap.

CAVERN (room 0) has three regions, the six-byte records `30 30 4e 4e 00 01`, `00 40 14 4e 00 01`, `0e 28 15 3f 00 01`.  Read from the contact test
`$009160`-`$0092e6`: a record is (x_lo, y_lo, x_hi, y_hi, z_lo, z_hi), the test is an inclusive overlap of the mover's box [trail, lead] (the hero's bbox at
`$038338` is x lead, y lead, x trail, y trail) with the region box, and D7 = the region number is the gate byte of the event.

  walk    natural joystick input only: Down, Right, Down, Right from the start (the hero stalls against objects between the holds); each step that
          has the hero's x lead in 48..78 and y lead in 48..78 queues event 15 (`$0092b4`) and the block's `45 ffff` takes 1 health: pushes == health lost.
  bounds  three labelled pokes of the hero's bbox, each followed by one held step: the push comes on the first step the lead reaches the low bound, with the
          region number in D7 (region 2 on y lead 64, region 3 on x lead 14, region 1 on y lead 48).
  obj     a labelled poke of object 14 (template 417) into region 1: event 17 is queued once (`$0092da`), the block's verb 41 (PLACE) runs once, the object
          leaves the room (its rectangle becomes 255,255,255,255), health is unchanged; the control run (no poke) reads 0 on all of them."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'action'))
from drv import *
what = sys.argv[1] if len(sys.argv) > 1 else 'walk'
NAV = {'U': UP, 'D': DOWN, 'L': LEFT, 'R': RIGHT}
def reg(r, n):
    regs = ' '.join(r.cmd('r')); return int(re.search(n + r':([0-9a-f]{8})', regs).group(1), 16)

if what == 'walk':
    r = Repl(START)
    for ch in 'DRD': walk(r, NAV[ch], max_steps=3000000)
    print('before the last hold', pos(r), 'health', r.w(A5 + 1174))
    joy(r, RIGHT)
    tot = {0x9274: 0, 0x92b4: 0, 0x92da: 0}; h0 = r.w(A5 + 1174)
    for i in range(30):
        for k, v in r.hits(5000, *tot).items(): tot[k] += v
    joy(r, 0)
    print('pos', pos(r), 'event-15 pushes', tot[0x92b4], 'event-17 pushes', tot[0x92da], 'health', h0, '->', r.w(A5 + 1174))
    r.close()
elif what == 'bounds':
    def trial(rect, bits):
        r = Repl(START)
        r.cmd('w 38338 %02x%02x%02x%02x' % rect); r.cmd('s 2000')
        joy(r, bits)
        out = r.cmd('bp 92b4 400000')
        hit = any('breakpoint' in l and 'hit' in l for l in out)
        res = (rect, 'D7=%d' % reg(r, 'D7') if hit else 'no push', 'bbox at the push', pos(r))
        joy(r, 0); r.close(); return res
    print('region 2, Down :', trial((10, 62, 4, 56), DOWN))
    print('region 3, Right:', trial((13, 63, 7, 57), RIGHT))
    print('region 1, Down :', trial((60, 46, 54, 40), DOWN))
elif what == 'obj':
    def run(poke):
        r = Repl(START); tbl = r.l(A5 + 56)
        if poke: r.cmd('w %x 4632452c' % (tbl + 0x46 * 14))      # rect (70,50,69,44): straddles region 1's y_lo = 48
        hp0 = r.w(A5 + 1174)
        h = r.hits(400000, 0x92da, 0x9274, 0x10aaa)
        e = r.mem(tbl + 0x46 * 14, 4)
        res = ('event-17 pushes %d, contacts %d, verb 41 runs %d' % (h[0x92da], h[0x9274], h[0x10aaa]), 'object 14 rect', tuple(e), 'health', hp0, '->', r.w(A5 + 1174))
        r.close(); return res
    print('control:', run(False)); print('poke   :', run(True))
