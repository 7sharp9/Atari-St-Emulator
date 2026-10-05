"""Parse lua/dumpframes.lua's ctl_log.txt and rebuild, for a frame, the sequence of tilemap-control states MAME rendered it with.

deco16ic_device::control_w calls screen().update_partial(vpos - ydelta) before changing a register, so a write that lands in the
visible part of a frame splits that frame: the rows already scanned keep the old registers, the rest use the new.  The screen is
256 lines per frame (scan period 67.349 us, frame 17241.379 us), the frame update (and our frame_done callback) happens at the start of
line 248; line y (0..247) starts 538.793 + 67.349 * y us later (measured with screen:time_until_pos); partial updates restart at the
end of the 529 us vblank.  htotal is 256 = visible width, so hpos is never in hblank and ydelta is always 1: rows y_abs < vpos are
rendered with the old state.  Rows are y_abs = 8..247 (image row = y_abs - 8)."""
import re

SCAN = 67.349137931034e-6
LINE0 = 538.79310344827e-6          # time from vblank start (line 248) to the start of line 0
VBLANK = 529e-6
VIS0, VIS1 = 8, 247


class CtlLog:
    def __init__(self, path):
        self.events = []            # (t, chip, word, data, mask)
        self.vbl = {}               # frame -> time of its frame_done (vblank start)
        self.prot = []              # (t, data)
        for line in open(path):
            p = line.split()
            if len(p) < 4:
                continue
            if p[3] == "vbl":
                self.vbl[int(p[0])] = float(p[1])
            elif p[3] == "spr":
                pass
            elif p[3] == "prot":
                self.prot.append((float(p[1]), int(p[4], 16)))
            else:
                idx = int(p[3])
                self.events.append((float(p[1]), idx >> 3, idx & 7, int(p[4], 16), int(p[5], 16)))
        self.events.sort(key=lambda e: e[0])

    @staticmethod
    def apply(state, ev):
        _, chip, w, data, mask = ev
        old = state[chip][w]
        state[chip][w] = (old & ~mask & 0xffff) | (data & mask)

    def state_before(self, t, upto=None):
        s = [[0] * 8, [0] * 8]
        for ev in self.events:
            if ev[0] >= t:
                break
            self.apply(s, ev)
        return s

    def segments(self, f):
        """[(y_abs_start, y_abs_end_exclusive, ctl_state)] covering 8..248 for the render of frame f (dumped at its frame_done)."""
        t1 = self.vbl[f]
        t0 = self.vbl.get(f - 1, t1 - 17241.379310345e-6)
        s = self.state_before(t0 + VBLANK)
        segs = []
        cur = VIS0
        for ev in self.events:
            if ev[0] <= t0 + VBLANK or ev[0] >= t1:
                continue
            dt = ev[0] - t0
            vpos = int((dt - LINE0) // SCAN)
            y_end = min(max(vpos, VIS0), VIS1 + 1)           # rows y_abs < vpos are scanned with the old state
            if y_end > cur:
                segs.append((cur, y_end, [list(s[0]), list(s[1])]))
                cur = y_end
            self.apply(s, ev)
        segs.append((cur, VIS1 + 1, [list(s[0]), list(s[1])]))
        return segs
