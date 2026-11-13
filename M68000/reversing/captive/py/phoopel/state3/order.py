"""Order check: from phoopel/state3/pre3.snap (PC $bfa4, the write of 13410 = 3), which per-frame entries run before the
end screen $134b8: hits on $bfaa (14800 = 3), $56ae (main loop's 14800 test), $56b4, $134b8, $5666 (main loop top),
$8772 (leave/exit frame test), $87c0 (13410 > 1 test) over 100,000 steps."""
import os, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'reversing', 'captive', 'py', 'ai'))
from cap import *  # noqa: E402
s = srv(os.path.join(W, 'phoopel', 'state3', 'pre3.snap'))
h = s('hits', steps=100_000, addrs=['$bfaa', '$56ae', '$56b4', '$134b8', '$5666', '$8772', '$87c0'])
print(' '.join(f"{a['addr']}:{a['count']}@{a['first']}..{a['last']}" for a in h['hits']))
s.close()
