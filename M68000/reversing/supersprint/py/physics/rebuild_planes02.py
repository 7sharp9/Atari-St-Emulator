"""rebuild_planes02.py - reproduce collision planes 0 and 2 of the 3-plane bitmap at [-94(A4)] from the track art.
plane 0 ($154d2): bit = 1 unless the art pixel's colour index is 3, 4 or 7 (screen at [-90(A4)], 4 interleaved bitplanes).
plane 2 ($15182): starts all 1; for each region record (track list at -1154(A4)) every art pixel inside the rectangle whose colour is in the
    record's 16-bit colour-set has its bit cleared.  Record (after the 2-byte/track header): x(16px units? see decode), y, w/mask byte, h, colourset(le16).
usage: rebuild_planes02.py [snap]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *
from rebuild_walls import ram_plane
import numpy as np


def art_colours(r):
    base = r.gl(-90)
    raw = np.frombuffer(r.bytes(base, 32000), dtype=np.uint8).reshape(200, 20, 8)
    col = np.zeros((200, 320), dtype=np.uint8)
    for g in range(20):
        w = [(raw[:, g, 2 * k].astype(np.uint16) << 8) | raw[:, g, 2 * k + 1] for k in range(4)]
        for b in range(16):
            col[:, g * 16 + b] = sum(((w[k] >> (15 - b)) & 1) << k for k in range(4))
    return col


def plane0(col):
    return ~np.isin(col, (3, 4, 7))


def plane2(r, col, track=0):
    p = np.ones((200, 320), dtype=bool)
    tb = A4 - 1154
    cnt = r.u8(tb + 2 * track)
    off = r.u8(tb + 2 * track + 1)
    a = tb + off * 6 + 16
    regs = []
    for i in range(cnt + 1):
        x8, y, wb, hb = r.u8(a), r.u8(a + 1), r.u8(a + 2), r.u8(a + 3)
        cs = r.u8(a + 4) | (r.u8(a + 5) << 8)      # little-endian word, per $151fe..$15204 (byte 1 high, byte 0 low)
        cs = (r.u8(a + 5) << 8) | r.u8(a + 4)
        a += 6
        regs.append((x8, y, wb, hb, cs))
    return p, regs, tb, cnt, off


if __name__ == '__main__':
    snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
    r = Ram(snap)
    col = art_colours(r)
    p0 = plane0(col)
    ref0 = ram_plane(r, 0)
    print('plane 0 from art colours {3,4,7}: %d/64000 pixels equal' % (64000 - int((p0 != ref0).sum())))
    p2, regs, tb, cnt, off = plane2(r, col)
    print('plane 2 region list (track 0): header', cnt, off, 'records', regs[:6], '...')
    ref2 = ram_plane(r, 2)
    print('plane 2 pixels cleared in RAM: %d of 64000' % int((~ref2).sum()))
