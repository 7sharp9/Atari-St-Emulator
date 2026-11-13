"""Drive the group-hit path $f884 -> $f954 on one group by a direct call (LABELLED: a synthetic hit, not play).
kill_call.py <snap> <group_index> <dmg6_hex> <dmg7_hex> [byte5_hex: hit-area index, low nibble] [resume_steps]
Builds a scratch hit object at $7f000 (LABELLED POKE: bytes 6 and 7 = the damage factors $fc66 multiplies), calls
$f884 (the hit resolver; the cell is not the party's, so it goes to $f954) with A0 = the object (cell at +0, +5 = 0), interrupts masked, and reports: the group record before
and after, whether $fc46 (member removed, group survives) ran and A2 there, and the byte at A2-3 before/after."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import *

s = srv(sys.argv[1]); gi = int(sys.argv[2]); d6, d7 = int(sys.argv[3], 16), int(sys.argv[4], 16); b5 = int(sys.argv[5], 16) if len(sys.argv) > 5 else 0
for pk in filter(None, os.environ.get('POKES', '').split(',')):   # LABELLED POKES: env POKES=hexaddr:width:hexval,...
    pa, pw, pv = pk.split(':'); s('poke', addr=int(pa, 16), width=int(pw), value=int(pv, 16)); print('POKE', pk)
a = A6 + 4532
for _ in range(gi):
    a += struct.unpack('>h', s.read(a + 2, 2))[0]
sz = struct.unpack('>h', s.read(a + 2, 2))[0]
print('group', gi, hex(a), 'cell', tuple(s.read(a, 2)), 'size', sz, 'rec', s.read(a, sz).hex())
OBJ = 0x7f000
s('poke', addr=OBJ, width=4, value=int.from_bytes(s.read(a, 2), 'big') << 16)
s('poke', addr=OBJ + 4, width=4, value=(b5 << 16) | (d6 << 8) | d7)
s('bp_set', addrs=['$fc46', '$fbea', '$fac4'])
cell = int.from_bytes(s.read(a, 2), 'big')
saved = s('regs')
ret = 0x800
sp = s.reg('a7') - 64
s('poke', addr=sp, width=4, value=ret); s('set_reg', name='a7', value=sp); s('set_reg', name='sr', value=0x2700)
s('set_reg', name='a6', value=A6); s('set_reg', name='d0', value=cell); s('set_reg', name='a0', value=OBJ); s('set_reg', name='pc', value=0xf884)
for _ in range(40):
    r = s('run', max_steps=400000, until_pc=ret)
    pc = s.reg('pc')
    if r['reason'] == 'breakpoint':
        a2 = s.reg('a2')
        print(f'  stop ${pc:x}  A2=${a2:x}  byte at A2-3 (${a2 - 3:x}) = {s.read(a2 - 3, 1).hex()}  15022(A6) long = {s.read(A6 + 15022, 4).hex()}')
        if pc == 0xfc46:
            s('step', n=4)  # through cmpi/bhi/bclr
            print(f'  after $fc4e: byte at A2-3 = {s.read(a2 - 3, 1).hex()}  15022(A6) = {s.read(A6 + 15022, 4).hex()}  RNG2 1770(A6) = {s.read(A6 + 1770, 2).hex()}')
        continue
    print('end', r['reason'], hex(pc), 'D6', hex(s.reg('d6')))
    break
sz2 = struct.unpack('>h', s.read(a + 2, 2))[0]
print('after: rec', s.read(a, max(sz2, 8)).hex(), 'size', sz2)
if len(sys.argv) > 6:   # then resume play: every register put back, watch the record for <steps> steps
    s('bp_clear', addrs=['$fc46', '$fbea', '$fac4'])
    val = lambda k: int(str(saved[k]).lstrip('$'), 16)
    s('set_reg', name='sr', value=val('sr'))
    for k in ['usp', 'ssp'] + [f'd{i}' for i in range(8)] + [f'a{i}' for i in range(8)] + ['pc']:
        s('set_reg', name=k, value=val(k))
    wid = s('watch_add', lo='$%x' % (a + 4), hi='$%x' % (a + sz2 - 1), kind='w')['id']
    s('step', n=int(sys.argv[6]))
    for e in s('watch_events', id=wid)[0]['events']:
        off = int(e['addr'].lstrip('$'), 16) - a
        if e['width'] == 1 and (off == 5 or (off >= 9 and (off - 9) % 8 == 0)):
            print(f"  step {e['step']} pc {e['pc']} +{off} = {e['value']}")
    print('end rec', s.read(a, max(sz2, 8)).hex(), 'msg 14800 =', w16(s, 14800), 'mode', w16(s, 13564))
    if os.environ.get('OUT'):
        s('save', path=os.path.abspath(os.environ['OUT'])); s('render', path=os.path.abspath(os.environ['OUT']).replace('.snap', '.png'))
s.close()
