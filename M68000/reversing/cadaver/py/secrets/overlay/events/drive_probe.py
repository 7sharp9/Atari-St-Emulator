"""a3: drive_probe.py <snap> <push site hex> <label> [long4] -- natural run (no input, no poke) to a producer push site; prints the decoded entry and the gate the consumer runs for it.
Used for events 4, 10, 11, 13 (snapshots from the natural chain, scratchpad/cadaver/s88/parent/full_A)."""
from probe import *
snap = absp(sys.argv[1]); site = int(sys.argv[2], 16); label = sys.argv[3]
h = HH.H(snap)
e = bp_push(h, site, int(os.environ.get("CAP", "3000000")), long4=(len(sys.argv) > 4))
if not e: print(label, 'no hit'); sys.exit(1)
print('%s: site $%06x entry op=$%04x (event %d) ptr=%s word=$%04x (%d)  1166(A5)=%d  D0..D2 %x %x %x A1=%06x A2=%06x A3=%06x A4=%06x A6=%06x D5=%x D6=%x D7=%x' % (label, site, e['op'], e['op'] & 0xff, e['ptrname'], e['word'], e['word'], e['room1166'],
      e['regs']['D0'], e['regs']['D1'], e['regs']['D2'], e['regs']['A1'], e['regs']['A2'], e['regs']['A3'], e['regs']['A4'], e['regs']['A6'], e['regs']['D5'], e['regs']['D6'], e['regs']['D7']))
for g in follow_consumer(h, e, e['op'] & 0xff): print('   consumer gate:', g)
h.close()
