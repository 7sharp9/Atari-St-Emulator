"""pause_and_map.py: P pauses (waits in $011842-$011892 until fire or any key other than F2-F4), F1 shows the explored-rooms map and the
room counter 2118(A5) ("ROOMS ENTERED") is bumped by the room loader $00e854 at $00e8b8.
Start gameplay_empire.snap.  Prints: main-loop hits ($006ba2) and pause-loop hits ($011842) in the 1M steps after P, then again after
pressing 'X' ($2d); the counter before/after a callcap of the room loader to room slot 1 (callcap restores state, so the counter
delta shown is the loader's own write).
    uv run python reversing/cadaver/py/secrets/pause_and_map.py"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
r = Repl()
r.cmd('kbd 19', 's 60000', 'kbd 99')
h = r.hits(1000000, 0x6ba2, 0x11842); print('after P: main loop', h[0x6ba2], 'pause loop', h[0x11842])
r.key(0x2d, 60000, 10)
h = r.hits(1000000, 0x6ba2, 0x11842); print('after X: main loop', h[0x6ba2], 'pause loop', h[0x11842])
r.close()
r = Repl()
print('2118(A5) rooms entered =', r.w(A5 + 2118))
out = r.cmd('w 185e0 00012888', 'callcap e854 2000000 -')       # (A5)+1166 = 1 (TUNNEL), low word of the longword keeps $2888 (mechanics.md 67)
d = [l for l in out if l.startswith('mem $') and int(l.split()[1][1:], 16) in (A5 + 2118, A5 + 2119)]
print('callcap e854 room 1: rooms-entered byte writes:', d)
r.close()
