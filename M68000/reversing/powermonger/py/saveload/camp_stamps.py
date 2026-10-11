"""camp_stamps.py <ram> [steps-per-tick]  the commander's camp-wait inputs for every AI group, and the predicted
first camp decision `$65b4`.

`$6522` walks the five entries of `$58016` (stride 6); an entry with byte 4 == 4 (AI) uses side = byte 0 and, for
group k = 5..0, A1 = $51538 + side*$13c + 2k. It goes on to the clock compare only when word 28(A1) > 0,
word 4(A1) == 0 and the state 76(A1) == 6 (state 9 jumps to $65b4 directly); then `move.w 256(A1),D0 /
addi.w #20 / cmp.w $2df72,D0 / bgt` skips while stamp + 20 > clock (signed), and `$6762` must return Z.
The prediction is the first tick at which clock >= min(stamp + 20) over the eligible groups (it ignores $6762).
Default steps per tick 167,504 (rand1 after a load, clock 441 -> 1038 in 100M steps)."""
import struct, sys
ram = open(sys.argv[1], 'rb').read()
spt = float(sys.argv[2]) if len(sys.argv) > 2 else 167504.0
w = lambda a: struct.unpack('>h', ram[a:a + 2])[0]
clock = w(0x2df72)
print(f"clock $2df72 = {clock & 0xffff} (signed {clock})")
best = None
for e in range(5):
    a = 0x58016 + 6 * e; side, st = ram[a], ram[a + 4]
    if st != 4: continue
    for k in range(5, -1, -1):
        A1 = 0x51538 + side * 0x13c + 2 * k
        own, busy, state, stamp = w(A1 + 28), w(A1 + 4), w(A1 + 76), w(A1 + 256)
        if own <= 0: continue
        elig = busy == 0 and state in (6, 9)
        note = 'eligible' if elig else ('busy 4(A1)=%d' % busy if busy else 'state %d' % state)
        print(f"  side {side} group {k}: state {state} stamp {stamp} stamp+20 {stamp + 20}  {note}")
        if elig:
            due = clock if state == 9 else max(clock, stamp + 20)
            best = due if best is None else min(best, due)
if best is None: print("no eligible camped AI group")
else:
    t = best - clock
    print(f"first $65b4 due at clock {best}: {t} ticks = {t * spt:,.0f} steps from this state")
