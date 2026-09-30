import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
from hidden_keys import key
r = Repl('scratchpad/impossamole/agents/hop3/snaps/seg7_pillars.snap'); r.cmd('s 30000')
key(r, 0x39, hold=60000); r.cmd('s 3000000')
print('after 1st: 227ff', r.b(0x227ff), '22800', r.b(0x22800))
r.cmd('watch 227ff 2')
key(r, 0x39, hold=60000)
print('hits ed9a (bomb start) after 2nd press:', r.cmd('hits 1000000 ed9a'))
key(r, 0x39, hold=60000); r.cmd('s 1000000')
print('after 2nd/3rd: 227ff', r.b(0x227ff), '22800', r.b(0x22800), 'watch lines', [l for l in r.err if 'WATCH' in l][:6])
# what re-arms it: level install
r.close()
