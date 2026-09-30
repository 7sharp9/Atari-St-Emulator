"""potions_callcap.py: overlay table 1 (header word +2) = potion effects, indexed by the potion id byte (A1)+0, dispatched at
$00a638 (`movea.l 2534(A5),A0 / adda.w 2(A0),A0 / move.b (A1),D0 / adda.w 0(A0,D0*2),A0 / jmp (A0)`).  Start snapshot
scratchpad/cadaver/gameplay_empire.snap.  For each potion id 0..17: scratch record at $0f0000 = [id][10][..], then
`callcap a638 30000 - A1=f0000` (callcap restores state after each call) and print the changed bytes.  Output format of the
REPL: 'mem $aaaaaa $old->$new' lines.  Potion names from (A5)+112 (cavern_objects.py): 0 STAMINA 1 SUPER FAST 2 GIANT JUMP
3 ALCOHOL 4 POISON 5 (blank) 6 SHOT SHIELD 7 WATER 8 FIRE SHIELD 9 CURE 10 SLOW 11 ICE SHIELD 12 MAGIC SHIELD 13 CURE POISON
14 TOTAL SHIELD 15 IMMORTAL 16 STRENGTH 17 SUICIDE."""
import sys
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
names = 'STAMINA,SUPER FAST,GIANT JUMP,ALCOHOL,POISON,(blank),SHOT SHIELD,WATER,FIRE SHIELD,CURE,SLOW,ICE SHIELD,MAGIC SHIELD,CURE POISON,TOTAL SHIELD,IMMORTAL,STRENGTH,SUICIDE'.split(',')
r = Repl()
print('(A5)+1174 (hit points) =', r.mem(a5(1174), 2).hex(), ' max (A5)+2516 =', r.mem(a5(2516), 2).hex())
for pid in range(18):
    wl(r, 0xf0000, (pid << 24) | (10 << 16))
    # preconditions the two conditional potions need (set live, callcap restores state afterwards only for what it touches
    # during the call, so undo them explicitly): CURE heals only when HP < max/2, CURE POISON only when 2434(A5) != 0
    if pid == 9: ww(r, a5(1174), 20)
    if pid == 13: wb(r, a5(2434), 5)
    out = r.cmd('callcap a638 30000 - A1=f0000')
    rel = lambda s: s
    deltas = []
    for l in out:
        if l.startswith('mem '):
            a = int(l.split()[1][1:], 16); off = a - A5
            if 0 <= off < 4000: deltas.append('A5+%d:%s' % (off, l.split()[2].replace('$', '')))
            elif off >= 0 and a < 0x19000: deltas.append('$%05x:%s' % (a, l.split()[2].replace('$', '')))
            # below A5 = the callee's own stack frame; $015xxx/$016xxx = sound sequencer state (svc 18): not listed
        elif l.startswith('---'):
            head = l
    if pid == 9: ww(r, a5(1174), 0x43)
    if pid == 13: wb(r, a5(2434), 0)
    print('potion %2d %-13s %s | %s' % (pid, names[pid], head.split(':')[1].split(',')[0].strip() if 'returned' in head else head, ' '.join(deltas)))
r.close()
