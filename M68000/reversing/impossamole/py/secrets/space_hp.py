import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
from hidden_keys import key
r = Repl('scratchpad/impossamole/agents/hop3/snaps/seg5_stone_hole.snap'); r.cmd('s 30000')
print('hp', r.b(0xbb74), r.b(0xbb75))
r.cmd('watch bb74 1')
key(r, 0x39, hold=60000)
r.cmd('s 1500000')
print('\n'.join(r.err[-20:]))
print('hp', r.b(0xbb74))
r.close()
