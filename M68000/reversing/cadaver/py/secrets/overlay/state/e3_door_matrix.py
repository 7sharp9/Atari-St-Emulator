"""e3_door_matrix.py: PROVES the door crossing branches of $00716e (door word +2: 0 / $ffff / item id; +7 bits 1, 2, 6) live.
Start: scratchpad/cadaver/secrets_out/action/cavern_door3b_stand.snap (CAVERN, hero holds item 73 in the rucksack, standing at door $3b (+2 = $0049, +7 = $02); joystick right crosses to room 8).
For each case the door record is poked, the key optionally removed (type-8 entry zeroed, count 2438(A5) = 0), joystick right held for 150,000 steps; `hits` on the branch sites.
Sites: 717c word==0 -> 71ca crossing; 731e $ffff; 7326 event 8 queued (+7 bit 6); 734a key not carried; 719a key carried; 71a2 key consumed (c3d4); 71b0/71b8 clear word."""
import sys
from live import *
from st import St
SNAP = SN('DOOR3B', 'scratchpad/cadaver/secrets_out/action/cavern_door3b_stand.snap')
s = St(SNAP); door = s.res(4, 0x3b); idx8, dat8, _ = s.rows[8]
SITES = {'717c': 0x717c, 'word0->71ca': 0x71ca, '731e ($ffff)': 0x731e, '7326 evt8': 0x7326, '734a nokey': 0x734a, '719a key': 0x719a, '71a2 consume': 0x71a2, '71b0 bit2?': 0x71b0, '71b8 clear': 0x71b8}
def run(label, word, b7, key=True):
    r = start(SNAP)
    wb(r, door + 2, word >> 8); wb(r, door + 3, word & 0xff); wb(r, door + 7, b7)
    if not key:
        for i in range(4): wb(r, dat8 + i, 0)
        wb(r, A5 + 2438, 0); r.cmd('w %x 00000000' % (idx8))
    r.cmd('kbd ff 08', 's 300')
    h = r.hits(150000, *SITES.values())
    room = r.w(A5 + 1166); n = r.mem(A5 + 2438, 1)[0]; w = r.w(door + 2)
    hs = ', '.join('%s=%d' % (k, h[v]) for k, v in SITES.items() if h[v])
    print('%-46s -> room %2d  ruck count %d  door word $%04x   hits: %s' % (label, room, n, w, hs))
    r.close()
    return room, n, w, h
run('A word $0049, +7=$02, key carried', 0x49, 0x02)
run('B word $0049, +7=$04, key carried', 0x49, 0x04)
run('C word $0049, +7=$00, key carried', 0x49, 0x00)
run('D word $0049, +7=$02, key NOT carried', 0x49, 0x02, key=False)
run('E word $0000', 0x0000, 0x02)
run('F word $ffff, +7=$00', 0xffff, 0x00)
run('G word $ffff, +7=$40', 0xffff, 0x40)
