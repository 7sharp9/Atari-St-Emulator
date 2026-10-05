"""Final Fight sprite frames: a Python port of the object-list builder `$16910` (and its seven layout kinds) in the
program ROM (scratchpad/finalfight/ff_main.bin, sha256 8535dd51...), plus readers for the animation scripts
(`$3b10`/`$3b1c`/`$3b3c`, README "player.md").  Gate: gate_frames.py compares the port with the live object RAM.

Frame block (A1 = 36(A0), set from an animation script entry by `$3b1c`/`$3b3c`; ROM `$016910-$016e38`):
  +0 byte  layout kind * 4 (index into the long table at $16976: 0 $16a0e, 1 $16a5a, 2 $16ab0, 3 $16b42, 4 $16bea,
           5 $16d12, 6 $16d9c)
  +2 byte  grid id: row of the table at $64770 (8 bytes: word tile count n, word 0, long offset list)
  +4,+5    hurt box and attack box index (not used by the builder)
  +6 word  -> 48(A0), x displacement (negated when the record is mirrored)
  +8 word  y displacement
  +10 word attribute word D6: bits 0-4 palette, 5 flip x, 6 flip y, 8-15 block size (>= $100: one big sprite,
           code = word +12)
  +12 ...  n tile words (negative = empty cell), kinds 2, 3, 6 interleave a per-tile attribute word
Offset list: word pairs (dx, dy); pair 0 is the origin shift, pair i moves to tile i; kind 5 lists contain escape
records (1, dx, dy, attr, long next list).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ROM_PATH = os.environ.get("FF_MAIN", os.path.join(ROOT, "scratchpad", "finalfight", "ff_main.bin"))
rom = open(ROM_PATH, "rb").read()

GRID_TAB = 0x64770


def w(a):
    return int.from_bytes(rom[a:a + 2], "big")


def sw(a):
    v = w(a)
    return v - 0x10000 if v >= 0x8000 else v


def l(a):
    return int.from_bytes(rom[a:a + 4], "big")


def _conv(d4):
    """not.b D4 ; addq.w #1,D4 (object y: CPS y grows downwards)."""
    d4 &= 0xffff
    d4 = (d4 & 0xff00) | (~d4 & 0xff)
    return (d4 + 1) & 0xffff


def build(block, x, y, camx, camy, mirror=False, pal=0, xoff=0):
    """Entries (x, y, code, attr) the game would put in the object list for a record at world (x, y) with
    36(A0) = block, 46(A0) = mirror, 47(A0) = pal, 48(A0) = xoff, camera (camx, camy).  Mirrors `$16910`."""
    a1 = block
    gid = rom[a1 + 2]
    n = w(GRID_TAB + 8 * gid)
    a2 = l(GRID_TAB + 8 * gid + 4)
    kind = rom[a1] // 4
    d6 = w(a1 + 10)
    if pal:
        d6 = (d6 & 0xffe0) | (pal & 0x1f)
    cx40 = (camx - 0x40) & 0xffff          # -28028(A5)
    cx30 = (cx40 + 0x10) & 0xffff          # -28026(A5)
    out = []

    def nxt():
        nonlocal a2
        v = sw(a2)
        a2 += 2
        return v

    if d6 >= 0x100:                        # $16992: one block sprite
        if not mirror:
            d3 = (x + xoff - cx40) & 0xffff
        else:
            d3 = (x - xoff - cx40) & 0xffff
            d6 ^= 0x20
        d4 = _conv(y + sw(a1 + 8) - camy)
        if not (d6 & 0x20):
            d3 = (d3 + nxt()) & 0xffff
            d4 = (d4 + sw(a2)) & 0xffff
        else:
            d3 = (d3 - ((d6 >> 4) & 0xf0)) & 0xffff
            d3 = (d3 - 16) & 0xffff
            d3 = (d3 - nxt()) & 0xffff
            d4 = (d4 + sw(a2)) & 0xffff
        return [(d3, d4, w(a1 + 12), d6)]

    def y0():
        return (y + sw(a1 + 8) - camy) & 0xffff

    if kind in (1, 3) and not mirror:
        kind -= 1                          # mirror-aware twins fall through to the plain routine
    if kind == 5 and not mirror:
        pass                               # handled below by the plain branch of kind 5
    mir = mirror and kind in (1, 3, 4, 5)
    codes = a1 + 12
    pair = []
    if mir:
        d3 = (x - xoff - cx30) & 0xffff
        d3 = (d3 - nxt()) & 0xffff
        d4 = _conv(y0() - nxt())
        base_d6 = d6 ^ 0x20
    else:
        d3 = (x + xoff - cx40) & 0xffff
        d3 = (d3 + nxt()) & 0xffff
        d4 = _conv(y0() - nxt())
        base_d6 = d6
    attr_per_tile = kind in (2, 3, 6)
    clip = kind in (4, 6)
    ov = pal & 0xff                         # 47(A0) as a byte
    for _ in range(n):
        code = w(codes)
        codes += 2
        attr = None
        if attr_per_tile:
            attr = w(codes)
            codes += 2
        skip = code & 0x8000
        if not skip and clip and d3 >= 0x200:
            skip = True
        if not skip:
            if attr_per_tile:
                t = attr
                if ov:
                    t = (t & 0xffe0) | ov
                if mir:
                    t ^= 0x20
            else:
                t = base_d6
            out.append((d3, d4, code, t & 0xffff))
        # advance by the next pair; kind 5 escape records first
        while kind == 5 and w(a2) == 1:
            a2 += 2
            dx, dy = nxt(), nxt()
            nd6 = w(a2)
            a2 += 2
            a2 = l(a2)
            d3 = (d3 - dx) & 0xffff if mir else (d3 + dx) & 0xffff
            d4 = (d4 + dy) & 0xffff
            base_d6 = (nd6 ^ 0x20) if mir else nd6
        dx, dy = nxt(), nxt()
        d3 = (d3 - dx) & 0xffff if mir else (d3 + dx) & 0xffff
        d4 = (d4 + dy) & 0xffff
    return out


# ------------------------------------------------------------------ animation scripts
def script(a, maxn=200):
    """Animation script at absolute address a (`$3b1c`/`$3b3c`): entries are (word offset, word duration << 8 | flags).
    A positive timer word is a frame: the block is entry + offset.  A negative timer word is the loop marker: its
    offset points back to the entry the script restarts from (`$3b50-$3b5c`).  Returns (frames, loop target address or
    None); frames are (entry address, block address, duration byte, flag byte)."""
    frames = []
    e = a
    loop = None
    for _ in range(maxn):
        off = sw(e)
        tm = w(e + 2)
        if tm & 0x8000:
            loop = e + off
            break
        frames.append((e, e + off, (tm >> 8) & 0x7f, tm & 0xff))
        e += 4
    return frames, loop


def frame_ok(blk):
    """A plausible frame block: layout kind byte a multiple of 4 below 28, grid id in range, inside ROM."""
    if not (0 <= blk < len(rom) - 16):
        return False
    return rom[blk] % 4 == 0 and rom[blk] < 28 and rom[blk + 2] < 0x80 and w(GRID_TAB + 8 * rom[blk + 2]) in range(1, 80)
