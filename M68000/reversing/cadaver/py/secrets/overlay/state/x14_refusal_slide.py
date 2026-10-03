"""x14_refusal_slide.py [snapshot] [id] [pass]: the two mover_free_run mismatches (obj 912, s88/parent/full_A/e1/route/31_w150000.snap, passes 5 and 6): `watch` on the record's x,y,z while the mover pass $f71a runs,
printing every writer (pc) and the mover block before and after.  Shows that the block follows the refusal branch ($fc2a: counters cleared, class 3 sets bits 3 and 4) and that the one-unit x change is written
by another routine, not by the refused step.  usage: x14_refusal_slide.py [snap] [id] [pass]"""
import sys, re
from lab import *
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/s88/parent/full_A/e1/route/31_w150000.snap'
oid = int(sys.argv[2]) if len(sys.argv) > 2 else 912
want = int(sys.argv[3]) if len(sys.argv) > 3 else 5
r = start(snap)
def to(a): r.cmd('u %x 400000' % a)
r.cmd('s 1'); to(0xf71a)
for k in range(want): r.cmd('s 1'); to(0xf71a)
rec = rec_of(r, oid); h = r.mem(rec, 16); mb = rec + h[13]
sp = None
for l in r.cmd('r'):
    for tok in l.split():
        if tok.startswith('A7:'): sp = int(tok[3:], 16)
ret = r.l(sp)
print('before: pos %s mover %s' % (r.mem(rec, 3).hex(' '), r.mem(mb, 14).hex(' ')))
r.err.clear(); r.cmd('watch %x 3' % rec); r.cmd('s 1'); to(ret) if False else None
to(ret); r.cmd('unwatch')
for l in r.err:
    m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) Write(\w+) \$([0-9a-f]+) <- \$([0-9a-f]+)', l)
    if m: print('  write pc $%06x -> rec+%d <- $%s' % (int(m.group(2), 16), int(m.group(4), 16) - rec, m.group(5)))
print('after:  pos %s mover %s' % (r.mem(rec, 3).hex(' '), r.mem(mb, 14).hex(' ')))
r.close()
