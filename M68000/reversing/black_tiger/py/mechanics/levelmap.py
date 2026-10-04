"""Black Tiger level file ("0".."7") decoder: a Python model of the level scanner at $00cd58.

File layout (all big-endian words), loaded at $201c8 (so the tile words start at A5 = $201cc):
  +0 width in tiles (128 for level 1), +2 height in tiles (50), then width*height words, row-major.
  word = (marker << 10) | tile id (10 bits).  The scanner strips the marker in place (word &= $3ff).
  marker 0         : nothing
  marker 1..$27    : breakable container / pickup: an entry of the 10-byte table at $1fb60
  marker $28..$3c  : actor spawn: record in the 16-byte table starting $1f030, actor type = marker-$27
  marker $3d,$3e,$3f: three map anchor points ($1effa/c, $1eff6/8, $1eff2/4)
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b

ACTOR_BASE = 0x1f030
ITEM_BASE = 0x1fb60
TYPE_DATA_171F4 = 0x171f4        # byte table indexed by actor type -> record byte +8


def load(n):
    d = open(os.path.join(b.FILES, str(n)), "rb").read()
    w, h = struct.unpack_from(">HH", d, 0)
    words = struct.unpack_from(">%dH" % (w * h), d, 4)
    return w, h, list(words), len(d)


def scan(w, h, words, post):
    """Faithful model of $cd58 operating on `post` (a bytearray RAM image, modified in place).
    Returns decoded (items, actors, anchors, final actor pointer)."""
    items, actors, anchors = [], [], {}
    a2 = ACTOR_BASE
    a0 = ITEM_BASE
    for a in range(ITEM_BASE, ITEM_BASE + 164 * 10, 10):
        post[a] = post[a + 1] = 0
    for row in range(h):
        for col in range(w):
            wd = words[row * w + col]
            m = wd >> 10
            x16, y16 = col * 16, row * 16
            if m == 0:
                continue
            if m < 0x28:
                items.append((m, x16 + 8, y16 + 16))
                post[a0:a0 + 8] = struct.pack(">HHH", m, x16 + 8, y16 + 16) + b"\0\0"
                post[a0 + 6] = post[a0 + 7] = 0
                a0 += 10
            elif m in (0x3f, 0x3e, 0x3d):
                base = {0x3f: 0x1eff2, 0x3e: 0x1eff6, 0x3d: 0x1effa}[m]
                anchors["%x" % m] = (x16, y16 + 16)
                post[base:base + 4] = struct.pack(">HH", x16, y16 + 16)
            else:
                t = m - 0x27
                post[a2] = t
                post[a2 + 4:a2 + 8] = struct.pack(">HH", x16 + 8, y16 + 16)
                post[a2 + 8] = post[TYPE_DATA_171F4 + t]
                post[a2 + 12] = post[a2 + 13] = 0
                post[a2 + 1] = 6
                actors.append(dict(type=t, x=x16 + 8, y=y16 + 16, b8=post[a2 + 8]))
                copies = 2 if t == 0xf else (1 if t == 0xd else 0)
                for c in range(copies):
                    post[a2 + 16:a2 + 32] = post[a2:a2 + 16]
                    a2 += 16
                    actors.append(dict(type=t, x=x16 + 8, y=y16 + 16, b8=post[a2 + 8]))
                a2 += 16
    for i in range(w * h):
        post[0x201cc + 2 * i] &= 0x03
    post[0x1ee96:0x1ee9a] = struct.pack(">I", a2)
    return items, actors, anchors, a2
