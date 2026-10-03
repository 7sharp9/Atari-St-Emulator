"""a3: ev10_probe.py [snap] -- natural run (no input) of a snapshot where the region test $009160 fires: bp at the event-10 push $009286, decode the entry; shows pointer = the overlapping
object record, word = region number D7, and that 1166(A5) is the current room id (room record index of 164(A5)).  Default snapshot: s88 d1/gems/02_U.snap (event 10 fired 164 times in 2M steps in survey_all.out)."""
from probe import *
snap = absp(sys.argv[1]) if len(sys.argv) > 1 else ROOT + '/scratchpad/cadaver/s88/parent/full_A/d1/gems/02_U.snap'
h = HH.H(snap)
for k in range(4):
    e = bp_push(h, 0x9286, 2000000)
    if not e: print('no hit'); break
    cur = ptr_name(h, e['cur_room_rec'])
    print('event %d entry: ptr=%s word=%d  D7=%d  A1=%06x  1166(A5)=%d  current room record 164(A5) = %s' % (e['op'] & 0xff, e['ptr'] and e['ptrname'], e['word'], e['regs']['D7'], e['regs']['A1'], e['room1166'], cur))
h.close()
