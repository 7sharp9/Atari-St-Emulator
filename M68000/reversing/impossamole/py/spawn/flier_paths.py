"""Flight paths of the Amazon fliers (types 116-125), reconstructed from the handlers.

    uv run python flier_paths.py [snap]        # default pass103/room188.snap; prints each type's path

Two mechanisms, both driven from the per-frame object pass `$0b4de` (x -= or += 16(A0) by bit 0 of 20(A0), y -= or +=
18(A0) by bit 0 of 21(A0); dir bit 0 = left/up, 1 = right/down) and the handler:

  118-125, handler `$0142be`: 82(A0) counts frames; when it equals the descriptor word at +34 (the low half of the
     entry pointer at +32: `$1e` = 30 frames, `$14` = 20 frames) both direction bytes flip (`eori.w #$101,20(A0)`) and the
     animation pointer is reloaded from entry 20(A0). Speeds are the descriptor words +14/+16 (16/18(A0)), the start
     vertical direction is byte +4 (21(A0): 0 up first, 1 down first), the start horizontal direction is byte +3
     (0 = left) so the object goes back and forth along the vector (vx, vy) for P frames each way.
  116, 117, handler `$015b3c`: `bsr $013308`, the script mover. Entry +32 points at two byte scripts, a speed script
     (indexed by 82(A0)) and a direction script (indexed by 84(A0)), both advancing one entry per frame. Direction code
     bits 0-1 = vertical (1 up, 2 down), bits 2-3 = horizontal (4 left, 8 right); the speed byte is applied to every axis
     the code moves (table `$013508`). `$fe` restarts a script; `$fc` in the direction script (type 117) replays the script
     backwards with the direction bits mirrored (`80(A0)` = 1), i.e. the object retraces its path.
"""
import os, struct, sys
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, os.path.join(ROOT, 'reversing/impossamole/py'))
from tiles import ram_from_snap
W = lambda ram, a: struct.unpack_from('>H', ram, a)[0]
L = lambda ram, a: struct.unpack_from('>I', ram, a)[0]

# $013508: 4 bytes per direction code: x flag, y flag, x direction, y direction (flag 0 = stop, 1 = move, $ff = unchanged)
DIRTAB = {0: (0, 0, 0, 0), 1: (0, 1, 0, 0), 2: (0, 1, 0, 1), 3: (0, -1, 0, 0), 4: (1, 0, 0, 0), 5: (1, 1, 0, 0), 6: (1, 1, 0, 1),
          7: (1, -1, 0, 0), 8: (1, 0, 1, 0), 9: (1, 1, 1, 0), 10: (1, 1, 1, 1), 11: (1, -1, 1, 0), 12: (-1, 0, 0, 0),
          13: (-1, 1, 0, 0), 14: (-1, 1, 0, 1)}


def describe(ram, typ):
    d = L(ram, 0x10474 + 4 * typ)
    return dict(desc=d, startx=ram[d + 3], starty=ram[d + 4], vx=W(ram, d + 14), vy=W(ram, d + 16), handler=L(ram, d + 20),
                entry2=L(ram, d + 32), period=W(ram, d + 34), hp=ram[d + 6], dmg=ram[d + 7])


def pingpong(vx, vy, startx, starty, period, frames):
    """Per-frame (dx, dy) of a $0142be flier: flip both direction bits every `period` frames. Returns positions relative
    to the spawn point after each frame (x += vx if dir 1)."""
    dx, dy = startx, starty
    n = 0
    x = y = 0
    out = []
    for f in range(frames):
        # handler first (it counts and flips), then the object pass moves by the current direction
        n += 1
        if n == period:
            n = 0
            dx ^= 1
            dy ^= 1
        x += vx if dx else -vx
        y += vy if dy else -vy
        out.append((x, y))
    return out


class Script:
    """Transcription of `$013308` for one object: state 79, 80, 82, 84 and the resulting 16/18/20/21."""

    def __init__(self, ram, speed_ptr, dir_ptr, x20=0, y21=0):
        self.ram, self.sp, self.dp = ram, speed_ptr, dir_ptr
        self.b79 = self.b80 = 0
        self.i82 = self.i84 = 0
        self.v16 = self.v18 = 0
        self.d20, self.d21 = x20, y21

    def step(self):
        ram = self.ram
        sb = lambda v: v - 256 if v > 127 else v
        while True:                                   # speed script
            b = ram[self.sp + self.i82]
            if b < 0x80:
                break
            if b == 0xfd:
                self.v16 = self.v18 = 0
                return True
            if b == 0xf9:
                self.v16 = 0
                return True
            if b == 0xf8:
                self.v18 = 0
                return True
            if b == 0xfe:
                self.i82 = 0
            else:                                     # $ff and any other negative: step back (others also set 79)
                if b != 0xff:
                    self.b79 = 1
                self.i82 -= 1
        speed = b
        if self.b79 == 0:
            self.i82 += 1
        else:
            self.i82 -= 1
            if self.i82 < 0:
                self.b79 = 0
                self.i82 = 0
        d7 = 0
        while True:                                   # direction script
            c = ram[self.dp + self.i84]
            if c < 0x80:
                break
            if c == 0xfe:
                self.i84 = 0
            elif c == 0xff:
                self.i84 -= 1
            else:
                self.b80 = (256 - c) - 3
                self.i84 -= 1
        if self.b80 == 0 and ram[self.dp + self.i84 + 1] >= 0x80 and ram[self.dp + self.i84 + 1] != 0xff:
            d7 = 1
        if self.b80:
            d2 = c & 3
            if d2 != 3 and self.b80 != 2:
                c ^= 3
                if c & 3 == 3:
                    c &= 0xc
            d2 = c & 0xc
            if d2 != 0xc and self.b80 != 3:
                c ^= 0xc
                if c & 0xc == 0xc:
                    c &= 3
        if self.b80 == 0:
            self.i84 += 1
        else:
            self.i84 -= 1
            if self.i84 < 0:
                self.b80 = 0
                self.i84 = 0
                d7 = 1
        xa, ya, xd, yd = DIRTAB[c & 0xf]
        if xa >= 0:
            self.v16 = 0
            if xa:
                self.v16 = speed
                self.d20 = xd
        if ya >= 0:
            self.v18 = 0
            if ya:
                self.v18 = speed
                self.d21 = yd
        return bool(d7)


def script_path(ram, typ, frames):
    d = describe(ram, typ)
    sp, dp = L(ram, d['entry2']), L(ram, d['entry2'] + 4)
    s = Script(ram, sp, dp, d['startx'], d['starty'])
    x = y = 0
    out = []
    for f in range(frames):
        s.step()
        x += s.v16 if s.d20 else -s.v16
        y += s.v18 if s.d21 else -s.v18
        out.append((x, y, s.v16, s.v18, s.d20, s.d21, s.i82, s.i84))
    return out, sp, dp


def rle(ram, ptr):
    out, prev, n = [], None, 0
    a = ptr
    while True:
        b = ram[a]
        if b == prev:
            n += 1
        else:
            if prev is not None:
                out.append((prev, n))
            prev, n = b, 1
        a += 1
        if b >= 0xf0 and b != 0xff:       # $fe restart, $fc/$fb/$fa play the script backwards (mirrored) for the rest
            out.append((b, 1))
            break
    return out


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'scratchpad/impossamole/pass103/room188.snap')
    ram = ram_from_snap(Path(snap))
    print('type handler    start(x,y) speed(vx,vy) period  extent per half-period (px)')
    for t in range(118, 126):
        d = describe(ram, t)
        p = d['period']
        print(f"{t:4} ${d['handler']:06x}  {('L','R')[d['startx']]},{('up','down')[d['starty']]:4}  ({d['vx']},{d['vy']})  {p:3}  {d['vx']*p}x{d['vy']*p}")
    for t in (116, 117):
        path, sp, dp = script_path(ram, t, 400)
        print(f'type {t}: speed script ${sp:05x}', rle(ram, sp))
        print(f'         direction script ${dp:05x}', rle(ram, dp))
        n = next((i for i in range(1, 400) if (path[i][6], path[i][7]) == (path[0][6], path[0][7]) and i > 5), None)
        xs = [p[0] for p in path]; ys = [p[1] for p in path]
        print(f'         first loop closes after {n} frames; x range {min(xs)}..{max(xs)}, y range {min(ys)}..{max(ys)};'
              f' net displacement after one loop {path[n-1][:2] if n else None}')


if __name__ == '__main__':
    main()
