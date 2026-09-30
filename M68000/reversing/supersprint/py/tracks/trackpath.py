"""Racing-line interpreter: replays the drone waypoint state machine ($ec52/$f2dc/$f3c2, see ../notes) on the
per-track blocks in SUPER.DAT, without the emulator.

Record = (x, y, len, hd) in world units (1 px = 8 units).  A normal record (hd <= 15) is a straight segment:
start (x,y), end = start + len * (dx[hd], dy[hd]) with the 16-direction tables INIT.DAT -4118/-4150(A4).
After a segment the AI advances wp = (wp + 2) mod n and looks at hd of the new record:
    hd == 0x100        fork: odd-numbered car wp += 2, even-numbered car wp += 3   ($ed26)
    hd & 0x200         gate jump: wp += gate[hd & 3]  (gate value 2 or 3 = open/closed phase, $aada..$aba8)
    hd & 0x400         skip: wp += hd & 0xff  (lane merge)                          ($edc6)
"""
import struct
from tkcommon import *
import trackdata as TD
import initmap

_d = None
def dirs():
    global _d
    if _d is None:
        i = {off: b for off, ln, pos, b in initmap.split_init()[0]}
        _d = (struct.unpack('>16h', i[-4118]), struct.unpack('>16h', i[-4150]))
    return _d

def segment(rec):
    x, y, l, h = rec; dx, dy = dirs(); h &= 15
    return (x, y), (x + l * dx[h], y + l * dy[h])

def next_wp(recs, wp, car, gate=(2, 2, 2, 2)):
    """the waypoint index that follows wp (after the control-record handling above)"""
    n = len(recs); wp = (wp + 2) % n; hd = recs[wp][3]
    if hd == 0x100: wp += 2 if (car & 1) else 3
    elif hd & 0x200: wp += gate[hd & 3]
    elif hd & 0x400: wp += hd & 0xff
    return wp % n

def successors(track, car):
    """wp -> set of possible next wps over every gate phase (value 2 or 3 for each of the 4 gate slots)"""
    import itertools
    recs = TD.waypoints(track); out_ = {}
    for wp in range(len(recs)):
        out_[wp] = {next_wp(recs, wp, car, g) for g in itertools.product((2, 3), repeat=4)}
    return out_

def walk(track, car, gate=(2, 2, 2, 2), maxsteps=400):
    """One lap of waypoint indices for `car` (0-3; parity selects the fork lane). Returns list of wp indices visited
    starting at 0 until the index wraps back to 0 (or an index repeats)."""
    recs = TD.waypoints(track); n = len(recs)
    wp = 0; seq = []; seen = set()
    for _ in range(maxsteps):
        if wp in seen: break
        seen.add(wp); seq.append(wp)
        wp = (wp + 2) % n
        hd = recs[wp][3]
        if hd == 0x100: wp += 2 if (car & 1) else 3
        elif hd & 0x200: wp += gate[hd & 3]
        elif hd & 0x400: wp += hd & 0xff
        wp %= n
        if wp == 0: break
    return seq

def lane_segments(track, car, gate=(2, 2, 2, 2)):
    recs = TD.waypoints(track)
    return [(i,) + segment(recs[i]) for i in walk(track, car, gate)]

def closure_error(track, car, gate=(2, 2, 2, 2)):
    """max distance (world units) between the end of each segment and the start of the next one in the lane walk,
    including the wrap from the last segment back to segment 0: a closed loop gives 0."""
    segs = lane_segments(track, car, gate)
    errs = []
    for a, b in zip(segs, segs[1:] + segs[:1]):
        (ex, ey) = a[2]; (sx, sy) = b[1]
        errs.append(max(abs(ex - sx), abs(ey - sy)))
    return errs

if __name__ == '__main__':
    for t in range(8):
        for car in (0, 1):
            e = closure_error(t, car)
            print('track %d car %d: %2d segments, length %5d units, max join gap %d units, gaps>0: %s' %
                  (t, car, len(e), sum(abs(s[2][0]-s[1][0]) + abs(s[2][1]-s[1][1]) for s in lane_segments(t, car)),
                   max(e), [i for i, v in enumerate(e) if v]))
