"""dump.py SNAP : god records, side states, frame, flags of a snapshot."""
import sys
from aicfg import *
from popmem import ram, sw, w, l
def show(m):
    print('frame', w(m, 0x3c4c8), 'human', w(m, 0x3affe), 'cw', sw(m, 0x21d5e), 'flags', hex(w(m, 0x219b2)), 'seed', hex(w(m,0x3d52e)))
    for s in (0, 1):
        r = 0x21e0c + s * 0x2e; st = 0x3b226 + s * 16
        print(' side', s, 'cmd', m[r], m[r+1], m[r+2], 'ctrl', w(m, r+6), 'busy', w(m, r+8), 'rating', w(m, r+12),
              'opts', hex(w(m, r+14)), 'react', w(m, r+16), 'c', sw(m, r+18), 'cast/h', w(m, r+20), w(m, r+22),
              'swcap/qq', w(m, r+24), w(m, r+26), 'hold/tgt', w(m, r+28), hex(w(m, r+30)))
        print('   leader', w(m, st), 'magnet', hex(w(m, st+2)), 'mode', w(m, st+4), 'towns', w(m, st+6), 'pop', l(m, st+8), 'mana', sw(m, st+12)*65536+w(m,st+14))
if __name__ == '__main__':
    show(ram(sys.argv[1]))
