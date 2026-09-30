"""spells_callcap.py: call each overlay spell-effect routine (table 2, header word +4; dispatched from $00f0d4 cast and
$00fa72/$00fb60 projectile-hit) with a hand-built register set on real CAVERN objects and print the state change.
Start snapshot scratchpad/cadaver/gameplay_empire.snap (CAVERN, level 0 overlay).  callcap restores state after each call, so
the pokes below are re-applied before every test.  Conventions read off the overlay bodies and $00f02e/$00fa34 (inferred, see
report): A2 = scroll instance (spell id +0, power +1), A1 = attacker/target object start (+4 = object id), A4 = victim template
(type-6 record: +8 sprite-slot offset, +12 instance offset, +22 class), A3 = victim instance data (A4 + 12(A4)), D1 = 12(A1).
22(A4) is the class byte and, for the barrel (instance offset 16), it is instance byte 6.
Real objects used: FULL BARREL template $06f0b8 (instance $06f0c8, live_rec $058a1a), BOAT template $07061e (instance $070634).
Routines that begin with a full-screen effect (svc 6/7/10: VBL waits that never return under callcap, interrupts are masked)
are entered just after it where noted.  Output: per spell the REPL delta ('returned'/'THREW'), changed bytes filtered to (A5)+N
(N<4000), the scratch/objects area, and the ring-304 queue writes."""
import sys, struct, re
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay')
from ov import *
BASE = 0x4c65e
ov = open('scratchpad/cadaver/secrets_out/overlay/overlay_level0.bin', 'rb').read()[4:]
W = lambda o: struct.unpack_from('>H', ov, o)[0]; S = lambda o: struct.unpack_from('>h', ov, o)[0]
t2 = W(4)
entry = lambda i: BASE + t2 + S(t2 + 2 * i)
BAR_T, BAR_I, BAR_LIVE = 0x6f0b8, 0x6f0c8, 0x58a1a
BOAT_T, BOAT_I = 0x7061e, 0x70634
SC = 0xf0000          # scroll instance
AT = 0xf0100          # attacker / A1 record
def scene(spell, cls, inst_bytes=None, power=10, atk_id=60):
    wl(r, SC, (spell << 24) | (power << 16)); wl(r, SC + 4, 0)
    wl(r, AT, 0); wl(r, AT + 4, atk_id << 16); wl(r, AT + 8, 0); wl(r, AT + 12, 0x03000000)   # AT+12 (D1=12) +1 = damage byte: set below
    wb(r, AT + 13, 3)
    if inst_bytes is not None:
        for i, b in enumerate(inst_bytes): wb(r, BAR_I + i, b)
    wb(r, BAR_T + 22, cls)      # 22(A4) == instance+6 for this object (instance offset 16): written AFTER the instance bytes
def run(label, addr, regs, watch_extra=()):
    out = r.cmd('callcap %x 60000 - %s' % (addr, ' '.join('%s=%x' % kv for kv in regs.items())))
    head = [l for l in out if l.startswith('---')][0]
    status = 'returned' if 'returned' in head else ('THREW (' + re.sub(r'.*THREW after \d+ steps: ', '', head).split(',')[0] + ')')
    d = []
    for l in out:
        if l.startswith('mem '):
            a = int(l.split()[1][1:], 16); v = l.split()[2].replace('$', '')
            off = a - A5
            if 0 <= off < 4000: d.append('A5+%d:%s' % (off, v))
            elif a >= 0x19000 and a < 0x100000 and not (0x15000 <= a < 0x17000): d.append('$%06x:%s' % (a, v))
    print('%-22s %-26s %s' % (label, status, ' '.join(d[:40])))
r = Repl()
base = dict(A1=AT, A2=SC, A3=BAR_I, A4=BAR_T, D1=12)
# 0 MAGIC MISSILE: victim must be a class-3 creature: live_rec +22 = 3 ; HP byte instance+0 = 10, damage 3 -> 7
wb(r, BAR_LIVE + 22, 3)
scene(0, 3, [10, 0, 0, 0, 0, 0, 0])
run('0 MAGIC MISSILE', entry(0), base)
scene(0, 3, [2, 0, 0, 0, 0, 0, 0])
run('0 MAGIC MISSILE (HP<dmg)', entry(0), base)
# 1 MASSACRE: entered after its svc 6 effect ($04cde6); creature list 396(A5): count 2, ids 60, 168
wl(r, a5(396), 0x0002003c); wl(r, a5(400), 0x00a80000)
scene(1, 3, [10, 0, 0, 0, 0, 0, 0], power=5)
run('1 MASSACRE (body)', BASE + 0x788, base)
# 5 MIND BLAST: body after svc 6 ($04ce5a): HP byte of each creature - power; list as above
scene(5, 3, [10, 0, 0, 0, 0, 0, 0], power=4)
run('5 MIND BLAST (body)', 0x4ce5a, base)
# 7 UNLOCK CHEST: class 8, instance +4 bit0/bit6 clear -> clr 2(A3), bclr #1,4(A3), then svc 14 (touch)
scene(7, 8, [0, 0, 0x12, 0x34, 0x02, 0, 0])
run('7 UNLOCK CHEST', entry(7), dict(base, A4=BAR_T, A3=BAR_I))
scene(7, 8, [0, 0, 0x12, 0x34, 0x41, 0, 0])   # bit 0 set = "trapped/locked hard" -> refuse
run('7 UNLOCK CHEST (refused)', entry(7), dict(base))
# 8 UNLOCK DOOR / 16 LOCK DOOR: A4 = door-like record: bit 5 of 7(A4) clear; 2(A4) lock id, bit 6 of 7(A4)
for i in range(0, 12): wb(r, 0xf0200 + i, 0)
wl(r, 0xf0202, 0x12340000); wb(r, 0xf0207, 0x40)
run('8 UNLOCK DOOR', entry(8), dict(base, A4=0xf0200))
wb(r, 0xf0207, 0x20)
run('8 UNLOCK DOOR (bit5 set)', entry(8), dict(base, A4=0xf0200))
wb(r, 0xf0207, 0x00)
run('16 LOCK DOOR', entry(16), dict(base, A4=0xf0200))
# 10 BLESS WEAPON: class 4, 2(A3) == 0 -> add power to instance+1
scene(10, 4, [0, 5, 0, 0, 0, 0, 0])
run('10 BLESS WEAPON', entry(10), base)
scene(10, 4, [0, 5, 1, 0, 0, 0, 0])
run('10 BLESS WEAPON (2(A3)!=0)', entry(10), base)
# 13 BLESS MAGIC (class 1) / 14 BLESS POTION (class 2): 1(A3) += power capped $ff
scene(13, 1, [0, 100, 0, 0, 0, 0, 0]); run('13 BLESS MAGIC', entry(13), base)
scene(13, 1, [0, 250, 0, 0, 0, 0, 0]); run('13 BLESS MAGIC (cap)', entry(13), base)
scene(14, 2, [0, 100, 0, 0, 0, 0, 0]); run('14 BLESS POTION', entry(14), base)
scene(14, 1, [0, 100, 0, 0, 0, 0, 0]); run('14 BLESS POTION (wrong cls)', entry(14), base)
# 15 DISPELL TRAP: chest class 8, 5(A3) != 0 -> clear
scene(15, 8, [0, 0, 0, 0, 0, 7, 0]); run('15 DISPELL TRAP', entry(15), base)
# 19 PURIFY POTION: class 2, bit 2 of 3(A3) (dirty) cleared
scene(19, 2, [0, 0, 0, 0x05, 0, 0, 0]); run('19 PURIFY POTION', entry(19), base)
# 20 READ MAGIC: class 1, bit0 of 3(A3) cleared (+ bits 1,7)
scene(20, 1, [0, 0, 0, 0x83, 0, 0, 0]); run('20 READ MAGIC', entry(20), base)
scene(21, 2, [0, 0, 0, 0x03, 0, 0, 0]); run('21 LEARN POTION', entry(21), base)
# 28: class 1 and -power >= (A3) (signed): gate only, no state change either way (rts / fail message)
scene(28, 1, [0xf0, 0, 0, 0, 0, 0, 0], power=10); run('28 gate passes', entry(28), base)
scene(28, 1, [5, 0, 0, 0, 0, 0, 0], power=10); run('28 gate fails', entry(28), base)
# 9 DESTROY: svc 15 on the id at 4(A1) (=60 FULL BARREL) then grey flash (VBL wait: THREW is expected, the effect is before it)
scene(9, 2, [0, 0, 0, 0, 0, 0, 0], atk_id=60); run('9 DESTROY', entry(9), base)
# timer spells: start a timer (svc 12) with duration 1(A2)=10, plus flag, then a flash
scene(2, 1, [0] * 7); run('2 FREEZE', entry(2), base)
scene(11, 1, [0] * 7); run('11 SLOW CREATURE', entry(11), base)
scene(18, 1, [0] * 7); run('18 CONFUSION', entry(18), base)
scene(22, 1, [0] * 7); run('22 TURN MONSTER', entry(22), base)
for i in (3, 17, 23, 24, 27, 29, 30): scene(i, 1, [0] * 7); run('%d (flash only)' % i, entry(i), base)
# 4 MAP, 6,12,25,26 (rts)
run('4 MAP', entry(4), base)
for i in (6, 12, 25, 26): run('%d (bare rts)' % i, entry(i), base)
r.close()
