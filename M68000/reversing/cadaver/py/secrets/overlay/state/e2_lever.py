"""e2_lever.py: the TUNNEL lever (object 144, template 35, anim script `00 00 | f9 00 | 00 01 | f9 00 | fd 00`) operated through the player's own action panel (natural input, as lever_operate.py),
with `watch` on its record's bytes: +3 (script state bits), +15 (anim stopped bit), the anim block and the type-4 flag record it clears (flag $33, word +2).  Every write is printed with the pc of the writer.
Start: scratchpad/cadaver/room2_tunnel_entry.snap.  The writers identify the mechanisms: operate producer -> GOANI body $0101d8 ($fe -> 0, step + 1, $b184 clears +15 bit 0), the anim interpreter ($b000/$b024/$b04a/$b064/$b06a),
the script verbs (verb 32 `bset #0,3(A0)` at $010778, verb 10 `clr.w 2(A0)` at $0104f2) and the halt op ($b0cc sets $fe, $b166 sets +15 bit 0).  Run twice (two operations) to show the second GOANI resuming at the next halt.
usage: e2_lever.py"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/action')
from drv import *
r = Repl(os.environ.get('SNAP_TUNNEL', 'scratchpad/cadaver/room2_tunnel_entry.snap')); t = Tally(r)
tbl = r.l(A5 + 56); rec = int.from_bytes(r.mem(tbl + 0x46 + 10, 4), 'big')
print('lever record $%x: %s' % (rec, r.mem(rec, 44).hex(' ')))
flagrec = None
# the door/flag it clears is flag $33: type-4 resource row 4
row4 = r.l(A5 + 96) + 0x12 * 4; fidx, fdat = r.l(row4), r.l(row4 + 4); fe = r.l(fidx + 4 * 0x33); flagrec = fdat + (fe & 0x1ffff)
p = walk(r, LEFT, max_steps=1500000)
def show(label):
    b = r.mem(rec, 44)
    print('%-24s +3=%02x +15=%02x anim %s flag33 word $%04x' % (label, b[3], b[15], b[0x22:0x2c].hex(' '), r.w(flagrec + 2)))
show('before')
open_panel(r, t); print('icons', icons(r))
r.err.clear(); r.cmd('watch %x 44' % rec)
def operate(n):
    r.err.clear()
    pick_icon_id(r, t, 7)
    for l in r.err:
        m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) Write(\w+) \$([0-9a-f]+) <- \$([0-9a-f]+)', l)
        if m: print('  op %d: pc $%06x write %s +%02x <- $%s' % (n, int(m.group(2), 16), m.group(3), int(m.group(4), 16) - rec, m.group(5)))
operate(1)
show('after 1st operate')
r.cmd('unwatch'); r.cmd('watch %x 44' % rec)
# trace the following passes (the anim keeps running): sample at pass entries
def passes(n):
    for _ in range(n):
        r.cmd('s 1'); r.cmd('u af10 400000')
r.err.clear(); passes(8); show('8 passes later')
for l in r.err:
    m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) Write(\w+) \$([0-9a-f]+) <- \$([0-9a-f]+)', l)
    if m: print('  later: pc $%06x write %s +%02x <- $%s' % (int(m.group(2), 16), m.group(3), int(m.group(4), 16) - rec, m.group(5)))
r.close()
