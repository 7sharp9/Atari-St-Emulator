"""live_checks_e.py [a|b|c ...]: emulator checks for lint rule (e) findings.  Run from anywhere under the M68000 root.
  a  level 0, room 27 tick block `16 #127 / 48 [36 CREATE #127]`: object 127's +3 bit 0 is never set, so the IF-NOT part
     runs on every room-27 tick.  From the natural lineage snapshot s89/full_A/e1/route/03_D.snap (room 27): count room-tick
     pushes ($0090aa) and CREATE ($0108ce) as is, then with 127's bit 0 poked to 1 (LABEL: synthetic poke), same budget.
  b  level 1, room 82 event-20 block (gate 00): the only arming verb of level 1 is obj 736's `42 0a 05` (word 10).  Hero put in
     room 82 by an injected TELEPORT `37 52 06 04 02` (the coordinates of levers 710/711's own teleport); then 2462(A5)/2461(A5)
     poked as verb 42 would write them: arm 00 (gate value), arm 0a (what the game writes), control ff.  Count the countdown push
     $0090d0, consumer matches $00fe24 and SHOW $0100b0 (the block's only verb).
  c  level 0, VAR 17 (o70's "THE BODY IS COLD" test `40 11 02 02`): timer handler 7 adds 1.  From gameplay_empire.snap: VAR 17
     poked to 1 (what o70's event-7 block sets), then the real verb `49 07 01` run through the consumer (scratch script over an
     event-5 block) vs. an empty script; read 2299(A5).  Also `49 07 64` (o70's own arm, 100 ticks): the countdown after 4M steps.
LABEL: every poke and injection here is synthetic; the counted signals are the game's own code paths."""
import sys, os
from pathlib import Path
for p in [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
    if (p / 'tools' / 'rdis.py').exists(): ROOT = str(p); break
os.environ.setdefault('M68000_ROOT', ROOT)
sys.path.insert(0, ROOT + '/reversing/cadaver/py/secrets/overlay/verbs2')
import h as HH
from h import *          # H, real, wb, ww, A5
import repl as _repl
# the one-disk Empire image: repl.py's default is the Windows checkout's ../Cadaver/; on the Mac it is in Dropbox ($CADAVER_DISK overrides)
DISK = os.environ.get('CADAVER_DISK') or next((d for d in (
    os.path.join(ROOT, _repl.DISK), os.path.expanduser('~/Library/CloudStorage/Dropbox/Daves/ST games/Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st'))
    if os.path.exists(d)), _repl.DISK)
HH.Repl = lambda snap: _repl.Repl(snap, DISK)
OUT = ROOT + '/scratchpad/cadaver/lint/live_e'
HH.TMP = OUT
which = sys.argv[1:] or ['a', 'b', 'c']


def pick_owner(h):
    for oid in range(1000):
        a = h.obj(oid)
        if a is None: continue
        b = h.r.mem(a + 0x10, 2)
        if b[1] & 0x7f == 5 and b[0] >= 12 and oid not in (0, 2): return oid


if 'a' in which:
    snap = ROOT + '/scratchpad/cadaver/s89/full_A/e1/route/03_D.snap'
    for arm in ('as-is', 'bit0=1'):
        h = H(snap); r = h.r
        rec = h.obj(127)
        print('a/%s: room %d, record of 127 at %s, +3 = %02x' % (arm, r.w(A5 + 1166), '%06x' % rec if rec else None, r.b(rec + 3) if rec else -1))
        if arm == 'bit0=1': wb(r, rec + 3, r.b(rec + 3) | 1)
        hh = r.hits(9000000, 0x90aa, 0xfe24, 0x108ce)
        print('   9M steps: room-tick push $0090aa %d, consumer match $00fe24 %d, CREATE $0108ce %d; 127 +3 now %02x'
              % (hh.get(0x90aa, 0), hh.get(0xfe24, 0), hh.get(0x108ce, 0), r.b(rec + 3)))
        h.close()

if 'b' in which:
    for arm in (0x00, 0x0a, 0xff):
        h = H(ROOT + '/scratchpad/cadaver/level1_loaded.snap'); r = h.r
        h.owner = pick_owner(h)
        HH.real(h, [0x25, 0x52, 6, 4, 2, 0x17], steps=600000)
        room = r.w(A5 + 1166)
        hh0 = r.hits(600000, 0x100b0)        # settle: the entry block's own SHOW #653 happens here
        wb(r, A5 + 2462, arm); wb(r, A5 + 2461, 1)
        hh = r.hits(1500000, 0x90d0, 0xfe24, 0x100b0)
        print('b/arm %02x: owner %d, room %d (settle SHOW %d); 1.5M steps: countdown push $0090d0 %d, consumer match $00fe24 %d, SHOW $0100b0 %d; 2462 now %02x'
              % (arm, h.owner, room, hh0.get(0x100b0, 0), hh.get(0x90d0, 0), hh.get(0xfe24, 0), hh.get(0x100b0, 0), r.b(A5 + 2462)))
        h.close()

if 'c' in which:
    for arm, script in (('49 07 01', [49, 7, 1, 0x17]), ('control', [0x17])):
        h = H(); r = h.r; h.owner = pick_owner(h)
        wb(r, A5 + 2299, 1)
        HH.real(h, script, steps=1500000)
        print('c/%s: owner %d, VAR 17 (2299(A5)) after 1.5M steps = %d, timer 7 count 2315(A5) = %d' % (arm, h.owner, r.b(A5 + 2299), r.b(A5 + 2315)))
        h.close()
    h = H(); r = h.r; h.owner = pick_owner(h)
    wb(r, A5 + 2299, 1)
    HH.real(h, [49, 7, 100, 0x17], steps=1000)
    c0 = r.b(A5 + 2315); r.cmd('s 4000000'); c1 = r.b(A5 + 2315)
    print('c/49 07 64: timer 7 count %d -> %d over 4,000,000 steps; VAR 17 = %d' % (c0, c1, r.b(A5 + 2299)))
    h.close()
