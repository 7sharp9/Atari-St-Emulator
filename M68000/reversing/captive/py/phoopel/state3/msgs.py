"""The end-screen message for each value of 14800(A6), read from RAM as $134b8/$136d6 index it (ai.md "Finishing a
base"): $136dc-$136e8 take the word at $1378a + 2*(14800+2) as an offset from $1378a to the text; $134e6-$13500 take
the byte at $134b0 + (14800+2) and store it as the 9th character of the string at $134f6-$ee4a (a digit, later
- '1' indexes the word table at $1372a). Prints each candidate value -2..8 with its byte, text offset and text.
msgs.py [snap]   default phoopel/state3/pre3.snap."""
import os, sys, struct
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'reversing', 'captive', 'py', 'ai'))
from cap import *  # noqa: E402

s = srv(sys.argv[1] if len(sys.argv) > 1 else os.path.join(W, 'phoopel', 'state3', 'pre3.snap'))
mem = s.read(0x13000, 0x1000)
rd = lambda a, n: mem[a - 0x13000:a - 0x13000 + n]


def text(a, n=160):
    b = rd(a, n)
    out = ''
    for c in b:
        if c == 0:
            break
        out += chr(c) if 32 <= c < 127 else f'<{c:02x}>'
    return out


print('byte table $134b0..$134b7:', rd(0x134b0, 8).hex())
print('word table $1378a..:', [hex(struct.unpack('>h', rd(0x1378a + 2 * i, 2))[0]) for i in range(10)])
for v in range(-2, 7):
    off = struct.unpack('>h', rd(0x1378a + 2 * (v + 2), 2))[0]
    print(f'14800={v:2d}: digit byte {rd(0x134b0 + v + 2, 1).hex()}  text @${0x1378a + off:x}: {text(0x1378a + off)!r}')
s.close()
