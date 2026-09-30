"""Title screen: joystick UP/DOWN sets $bb7b (0/1) at $17ae0-$17b00; $17c6e draws glyph $5b+$bb7b at column $23 row 5.  Snapshots + renders both states."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
D = 'scratchpad/impossamole/agents/secrets/data/'
r = Repl(D + 'cold_SPACE.snap')
r.until(0x17ada, 40000000); r.cmd('s 300000')
print('bb7b at title', r.b(0xbb7b), 'bb7a', r.b(0xbb7a))
r.snap(D + 'title_bb7b_0.snap')
r.joy(0x02); r.cmd('s 400000'); r.joy(0); r.cmd('s 400000')
print('after DOWN bb7b', r.b(0xbb7b)); r.snap(D + 'title_bb7b_1.snap')
r.joy(0x01); r.cmd('s 400000'); r.joy(0); r.cmd('s 400000')
print('after UP bb7b', r.b(0xbb7b))
r.close()
