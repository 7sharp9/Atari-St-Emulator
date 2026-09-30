import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from hidden_keys import *
r = Repl(SNAP); r.cmd('s 30000')
D = 'scratchpad/impossamole/agents/secrets/data/'
r.snap(D + 'space0.snap')
key(r, 0x39, hold=60000)
for i, n in enumerate([100000, 300000, 600000, 1500000, 4000000]):
    r.cmd(f's {n}'); r.snap(D + f'space{i+1}.snap')
    print(i+1, '227ff', r.b(0x227ff), '22800', r.b(0x22800), 'hero', r.mem(0x1a572, 12).hex(), 'hp', r.b(0xbb74), 'pc', hex(r.pc()))
r.close()
