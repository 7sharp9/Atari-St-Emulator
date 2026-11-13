"""Drive the party by input and log each input: drive.py <snap> <out.snap> <input ...>
input = k<hex> keypad key, c<x>:<y> left click at a screen point (probe_input.py), w<steps> wait.
Per input: party position, facing, floor word 15688(A6), and the hit counts of the move/lift handlers and the
plane-2 step writers $9332/$9336."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_input as P
from probe_input import srv, w16  # noqa
P.ADDRS.update({0x9332: 'st9332', 0x9336: 'st9336', 0xf884: 'f884', 0x969a: '969a'})
s = srv(sys.argv[1])
for inp in sys.argv[3:]:
    tot = dict.fromkeys(P.ADDRS, 0)
    if inp[0] == 'w':
        P.run(s, int(inp[1:]), tot)
    else:
        P.drive(s, inp, tot)
    print(inp, 'pos', w16(s, 26), w16(s, 28), 'face', w16(s, 30), 'fl', w16(s, 15688),
          {P.ADDRS[a]: n for a, n in tot.items() if n and a != 0x969a}, flush=True)
s('save', path=os.path.abspath(sys.argv[2])); s.close()
