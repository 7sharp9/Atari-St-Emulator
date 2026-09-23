"""s2_custom.py - from cg0.snap (GENESIS gameplay after START GAME) switch to a custom game and set
OPTIONS FOR EVIL all on, AGGRESSION HIGH, RATE FAST, all through menu clicks. Writes cg1.snap
(custom, options set) and prints the god records after each step."""
import struct, sys
from aicfg import *
from livelib import Sess
from popdrive import icon_point, move_lines, FRAME

class Drv:
    def __init__(s, snap, errfile=None):
        s.r = Sess(snap, errfile)
        s.px, s.py = s.sw(0x24748), s.sw(0x2474a)
    def sw(s, a): return struct.unpack('>h', s.r.mem(a, 2))[0]
    def w(s, a): return struct.unpack('>H', s.r.mem(a, 2))[0]
    def run(s, *lines):
        for L in lines: s.r.cmd(L)
    def click(s, x, y, button='l', settle=2, hold=2, after=4):
        for L in move_lines(s.px, s.py, x, y): s.r.cmd(L)
        s.px, s.py = x, y
        s.r.cmd('s %d' % (FRAME * settle))
        s.r.cmd('mouse down %s' % button)
        s.r.cmd('s %d' % (FRAME * hold))
        s.r.cmd('mouse up %s' % button)
        s.r.cmd('s %d' % (FRAME * after))
    def btn(s, a):
        """OK/CANCEL rect as drawn by $183ea: x0, y0, x1 (hit: x0<=x<=x1, y0<=y<=y0+16)."""
        return s.sw(a), s.sw(a + 2), s.sw(a + 4)
    def recs(s, tag):
        out = [tag, 'cw', s.sw(0x21d5e), 'onepl', s.w(0x219b0), 'human', s.w(0x3affe)]
        for side in (0, 1):
            b = s.r.mem(0x21e0c + side * 0x2e, 0x12)
            out.append('side%d ctrl %d rating %d opts %03x react %d' % ((side,) + struct.unpack('>H', b[6:8]) +
                       struct.unpack('>H', b[12:14]) + struct.unpack('>H', b[14:16]) + struct.unpack('>H', b[16:18])))
        print(*out)

def item(base, i, dx=4, dy=4):
    import popmem
    m = popmem.img(); a = base + i * 0x2e
    return popmem.sw(m, a) + 16 + dx, popmem.sw(m, a + 2) + 16 + dy

if __name__ == '__main__':
    d = Drv(P('cg0.snap'))
    d.recs('start')
    d.click(*icon_point('game_setup'), after=8)
    d.click(*item(0x22286, 10))                       # CUSTOM GAME
    x0, y0, x1 = d.btn(0x22a9a); print('OK rect', x0, y0, x1, 'CANCEL', d.btn(0x22b80))
    d.click((x0 + x1) // 2, y0 + 8, after=8)
    d.recs('after setup')
    d.click(*icon_point('options'), 'r', after=8)     # right click: options for the other side (left = own)
    print('title', d.r.mem(0x22006, 24))
    for i in range(4, 10): d.click(*item(0x22000, i))
    d.click(187, 151)                                 # AGGRESSION slider cell 9 (HIGH): x=(112..191)
    d.click(187, 170)                                 # RATE slider cell 9 (FAST)
    x0, y0, x1 = d.btn(0x22a9a); print('OK rect', x0, y0, x1)
    d.click((x0 + x1) // 2, y0 + 8, after=8)
    d.recs('after evil')
    d.r.cmd('snap ' + P('cg1.snap'))
    d.r.close()
