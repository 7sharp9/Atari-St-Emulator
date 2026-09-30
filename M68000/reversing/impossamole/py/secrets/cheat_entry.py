"""Type a name into the high-score entry ($19dfc loop) with real joystick-1 packets and see what $bb7d becomes.
usage: cheat_entry.py NAME [--noend]   (NAME letters from the 32-cell grid; END cell is appended unless --noend or the name has 8 letters)
Start state: data/name_entry.snap (made by t_death.py: Amazon gameplay, score 10000 poked, health poked to 0, real death,
Game Over, 250-frame timeout, entry screen at $19dfc)."""
import sys, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
GRID = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ@.!?\xfe\xff'   # $1a083: 26 letters, @ . ! ?, $fe = DEL cell, $ff = END cell
UP, DOWN, LEFT, RIGHT, FIRE = 1, 2, 4, 8, 0x80
CELL = {c: i for i, c in enumerate(GRID)}

def path(a, b):
    """shortest sequence of (bits) from cell a to b; up/down = -/+8, left/right = -/+1, all mod 32 ($19e5a: and #$1f)."""
    prev = {a: None}; q = collections.deque([a])
    moves = [(UP, -8), (DOWN, 8), (LEFT, -1), (RIGHT, 1)]
    while q:
        c = q.popleft()
        if c == b: break
        for bits, d in moves:
            n = (c + d) & 31
            if n not in prev: prev[n] = (c, bits); q.append(n)
    seq = []; c = b
    while prev[c]: c, bits = prev[c]; seq.append(bits)
    return seq[::-1]

def cell(r): return r.b(0x19c1e)
def pos(r): return r.b(0x19c1f)

def move_to(r, target):
    for bits in path(cell(r), target):
        cur = cell(r)
        r.joy(bits)
        for _ in range(60):
            r.cmd('s 20000')
            if cell(r) != cur: break
        r.joy(0)
        r.cmd('s 20000')

def press_fire(r):
    p0 = pos(r)
    r.joy(FIRE)
    for _ in range(60):
        r.cmd('s 20000')
        if pos(r) != p0 or r.pc() >= 0x18300 and False: break
    r.joy(0); r.cmd('s 30000')

def fire_letter(r):
    """fire pulse; returns True once the name-entry accepted it (pos advanced) or the entry finished."""
    p0 = pos(r)
    r.joy(FIRE)
    for _ in range(40):
        r.cmd('s 20000')
        if pos(r) != p0: break
    r.joy(0); r.cmd('s 200000')     # release must span at least one $19dfc iteration (6 VBL ticks) so the next press is an edge

def run(name, end=True, snap='scratchpad/impossamole/agents/secrets/data/name_entry.snap', verbose=True):
    r = Repl(snap)
    r.cmd('s 30000')
    assert r.b(0xbb7d) == 0
    n = 0
    for ch in name:
        move_to(r, CELL[ch])
        if verbose: print(f'  cell {cell(r)} pos {pos(r)} buf {r.mem(0x1a07a, 8)!r}')
        n += 1
        if n == 8:
            r.joy(FIRE); print('  8th pick reached $19f3c:', r.until(0x19f3c, 800000)); r.joy(0)   # the 8th pick ends the entry at once ($19ece: pos 7 -> $19f3c)
            break
        fire_letter(r)
    if end and n < 8:
        move_to(r, CELL['\xff'])
        r.joy(FIRE); print('  END pick reached $19f3c:', r.until(0x19f3c, 800000)); r.joy(0)
    r.cmd('s 1500000')          # entry ends, $19fba inserts the name, $18348 compares, $183ae stores the code, fade, title
    buf = r.mem(0x1a07a, 8)
    return r, dict(name=name, buf=buf, bb7d=r.b(0xbb7d), rank2=r.mem(0x184ef + 16, 8), pc=hex(r.pc()))

if __name__ == '__main__':
    name = sys.argv[1]
    r, res = run(name, end='--noend' not in sys.argv)
    print(res)
    r.close()
