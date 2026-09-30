"""coast_diff.py [n] - verify the coasting (throttle released) deceleration rule of the human control `$d4fa` with callcap.

Static reading ($dc9e..$dd3e): when the car is moving and the pad is idle, every frame
    speed -= 1  if  row[u2][phase] == 0        (u2 = level of item 2, 'turbo acceleration')
    speed -= 1  if  row[u0][phase] != 0        (u0 = level of item 0, 'traction')
    speed = max(speed, 0)
with row[k][p] = word at -8476(A4) + 14*k + 2*p (6 rows x 7 words, e.g. row0 = 0000000, row5 = 1011101) and phase = -8478(A4) (0..6, the
frame counter df18 advances).  Test: from a live race state (car slot 1 = human, joystick channel 2 with the pad byte -4804 forced to 0),
for n random (u0, u2, speed, phase) poke the values, callcap `$d4fa` for car 1 and compare the speed word afterwards.
"""
import random
from aiutil import *

n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
fire = len(sys.argv) > 2 and sys.argv[2] == 'fire'   # fire: accelerate rule  speed<cap: +2, else speed=cap
rnd = random.Random(11)
r = Repl2(os.path.join(DATA, 'prerace_k.snap'))
r.cmd('s 600000')
out, regs = r.cmd('')
sp0 = regs['A7']
rows = [r.words(A4 - 8476 + 14 * k, 7) for k in range(6)]
print('decel rows', rows)
orig = r.mem(sp0, 4)
ok = tot = 0
for t in range(n):
    u0, u2 = rnd.randint(0, 5), rnd.randint(0, 5)
    speed = rnd.randint(0, 130)
    ph = rnd.randint(0, 6)
    pk = {A4 - 4074 + 8 + 0: u0, A4 - 4074 + 8 + 4: u2, A4 - 3730 + 2: speed, A4 - 8478: ph, A4 - 3810 + 2: 0, A4 - 3826 + 2: 0,
          A4 - 3866 + 2: 0, A4 - 3778 + 2: 0, A4 - 4804: 0x8000 if fire else 0}
    cap = rnd.randint(40, 140)
    pk[A4 - 3874 + 2] = cap
    setwords(r, pk)
    r.cmd('w %x %04x%02x%02x' % (sp0, 1, orig[2], orig[3]))
    out, _ = r.cmd('callcap d4fa 20000 - A4=%x A5=a304' % A4)
    r.cmd('w %x %s' % (sp0, orig.hex()))
    returned = any('returned' in l for l in out if l.startswith('--- callcap'))
    new = speed
    for l in out:
        m = re.match(r'mem \$([0-9a-f]+) \$([0-9a-f]+)->\$([0-9a-f]+)', l)
        # speed word of slot 1 = A4-3730+2, big-endian: high byte at +0, low byte at +1
    a = A4 - 3730 + 2
    bytes_ = {}
    for l in out:
        m = re.match(r'mem \$([0-9a-f]+) \$([0-9a-f]+)->\$([0-9a-f]+)', l)
        if m and int(m.group(1), 16) in (a, a + 1):
            bytes_[int(m.group(1), 16)] = int(m.group(3), 16)
    hi = bytes_.get(a, (speed >> 8) & 0xFF)
    lo = bytes_.get(a + 1, speed & 0xFF)
    new = (hi << 8) | lo
    exp = speed
    if fire:
        exp = speed + 2 if speed < cap else cap
    elif speed > 0:
        if rows[u2][ph] == 0:
            exp -= 1
        if rows[u0][ph] != 0:
            exp -= 1
        exp = max(exp, 0)
    tot += 1
    if returned and new == exp:
        ok += 1
    else:
        print('MISMATCH u0=%d u2=%d speed=%d cap=%d phase=%d got %d exp %d returned=%s' % (u0, u2, speed, cap, ph, new, exp, returned))
print('RESULT %d/%d' % (ok, tot))
r.close()
