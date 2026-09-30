"""Scancodes the game reads outside the joystick: $01 (ESC) at $b1c2, $1d (Ctrl) at $1abe2/$1abf4, $39 (Space) at $ed66.  Live tests from the Amazon
gameplay snapshot.  Keyboard bytes are sent as raw IKBD bytes with the same two-call make/break discipline (kbd <make>, s n, kbd <break>)."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
SNAP = 'scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap'

def key(r, make, hold=30000):
    r.cmd(f'kbd {make:02x}', f's {hold}', f'kbd {make | 0x80:02x}')

def esc():
    r = Repl(SNAP); r.cmd('s 30000')
    print('ESC: hp/world/bb76 before', r.b(0xbb74), r.b(0xbb76), 'score', hex(r.l(0xbb6e)))
    key(r, 0x01)
    t = r.until(0xb088, 8000000)
    print('  $b088 (title path) reached:', t, ' steps', r.steps)
    if t:
        print('  title $17a9e reached:', r.until(0x17a9e, 30000000), ' score now', hex(r.l(0xbb6e)), 'bb79', hex(r.b(0xbb79)))
    r.close()

def pause():
    r = Repl(SNAP); r.cmd('s 30000')
    def st(): return (r.mem(0x1a574, 2).hex(), r.mem(0x1a2e9, 1).hex(), r.w(0x227b6), hex(r.pc()))
    r.joy(0x08)     # hold right
    r.cmd('s 200000'); a = r.w(0x227b6)
    key(r, 0x1d)
    r.cmd('s 1000000'); b = r.w(0x227b6); pcs = set()
    for _ in range(5):
        r.cmd('s 1000000'); pcs.add(hex(r.pc()))
    c = r.w(0x227b6)
    print('Ctrl pause: camera before', a, 'after 1M', b, 'after 6M', c, 'PCs while paused', sorted(pcs))
    key(r, 0x1d)
    r.cmd('s 1000000'); d = r.w(0x227b6)
    print('  after second Ctrl: camera', d, 'pc', hex(r.pc()))
    r.close()

def space():
    r = Repl(SNAP); r.cmd('s 30000')
    print('SPACE: hp', r.b(0xbb74), '$227ff', r.b(0x227ff), '$22800', r.b(0x22800), 'hero', r.mem(0x1a572, 8).hex())
    key(r, 0x39, hold=60000)
    print('  hits on $ed72/$ee2a/$f31c:', r.cmd('hits 100000 ed72 ee2a f31c ed9a'))
    for i in range(12):
        r.cmd('s 400000')
        print('  ', i, '$227ff', r.b(0x227ff), '$22800', r.b(0x22800), 'hp', r.b(0xbb74), 'hero', r.mem(0x1a572, 8).hex(), 'pc', hex(r.pc()))
    print('  Game Over reached within 3M more:', r.until(0x17fe8, 3000000), ' bb78', r.b(0xbb78))
    r.close()

if __name__ == '__main__':
    for f in sys.argv[1:]:
        globals()[f]()
