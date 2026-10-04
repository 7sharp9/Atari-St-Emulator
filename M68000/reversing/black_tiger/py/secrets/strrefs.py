"""For each NUL-terminated string in the COMMAND.PRG data area $17200..$17d00 list literal references
(4-byte big-endian value at any byte alignment, in the text segment $c470..$1f274, plus 2-byte for <$8000)."""
from btsec import *
import struct
mem = bytes(ram(os.path.join(WORK, "play_start.snap")))
def refs(t):
    p = struct.pack(">L", t); out = []; i = 0xc470
    while True:
        i = mem.find(p, i, 0x1f274)
        if i < 0: break
        out.append(i); i += 1
    return out
a = 0x17200
seen = []
while a < 0x17d00:
    if 32 <= mem[a] < 127 or mem[a] in (13, 10, 35):
        e = a
        while mem[e] and (32 <= mem[e] < 127 or mem[e] in (13,10,9)) : e += 1
        if mem[e] == 0 and e - a >= 4:
            s = mem[a:e].decode("latin1")
            r = refs(a)
            print("%05x %-3d refs=%s  %r" % (a, e - a, " ".join("%05x" % x for x in r[:5]) or "NONE", s[:60]))
            a = e + 1; continue
    a += 1
