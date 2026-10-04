"""bt_common.py - shared helpers for the Black Tiger graphics decoders.

Paths come from __file__ (M68000_ROOT overrides the repo root); inputs from $BT_WORK
(default M68000/scratchpad/black_tiger), outputs under $BT_WORK/agents/graphics/.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_root():
    """M68000/ = the first ancestor that holds tools/gfxview.py (override: $M68000_ROOT)"""
    d = HERE
    while True:
        if os.path.exists(os.path.join(d, "tools", "gfxview.py")):
            return d
        p = os.path.dirname(d)
        if p == d:
            raise SystemExit("cannot find M68000 root from %s; set M68000_ROOT" % HERE)
        d = p


ROOT = os.environ.get("M68000_ROOT") or _find_root()
WORK = os.environ.get("BT_WORK") or os.path.join(ROOT, "scratchpad", "black_tiger")
OUT = os.path.join(WORK, "agents", "graphics")
PNG = os.path.join(OUT, "png")
FILES = os.path.join(WORK, "files")
sys.path.insert(0, os.path.join(ROOT, "tools"))

from gfxview import load_ram, load_video_regs  # noqa: E402
from PIL import Image  # noqa: E402

os.makedirs(PNG, exist_ok=True)


def snap_path(name):
    """name relative to $BT_WORK unless absolute"""
    if os.path.isabs(name):
        return name
    for base in (os.getcwd(), WORK, OUT):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return os.path.join(WORK, name)


def load_snap(name):
    ram, _ = load_ram(snap_path(name))
    return ram


def read_file(name):
    with open(os.path.join(FILES, name), "rb") as f:
        return f.read()


def st_colour(word):
    """Same 3-bit-per-gun conversion as tools/snap_render.py (gun*36), so images
    from this module compare exactly with snap_render output."""
    r, g, b = (word >> 8) & 7, (word >> 4) & 7, word & 7
    return (r * 36, g * 36, b * 36)


def palette_rgb(words):
    return [st_colour(w) for w in words]


def pal_from_bytes(data, off=0):
    return [struct.unpack_from(">H", data, off + 2 * i)[0] for i in range(16)]


def w16(b, o):
    return (b[o] << 8) | b[o + 1]


def l32(b, o):
    return int.from_bytes(b[o:o + 4], "big")


def decode_st16(buf, off, rows):
    """One 16 px wide block, `rows` rows of 8 bytes (4 interleaved plane words):
    returns list of rows of 16 colour indices (ST standard)."""
    out = []
    for y in range(rows):
        p = [w16(buf, off + y * 8 + 2 * i) for i in range(4)]
        row = []
        for bit in range(15, -1, -1):
            row.append(((p[0] >> bit) & 1) | (((p[1] >> bit) & 1) << 1)
                       | (((p[2] >> bit) & 1) << 2) | (((p[3] >> bit) & 1) << 3))
        out.append(row)
    return out


def decode_lin32(buf, off, rows):
    """One 32 px wide block, `rows` rows of 16 bytes = 4 longs (plane0..plane3)."""
    out = []
    for y in range(rows):
        p = [l32(buf, off + y * 16 + 4 * i) for i in range(4)]
        row = []
        for bit in range(31, -1, -1):
            row.append(((p[0] >> bit) & 1) | (((p[1] >> bit) & 1) << 1)
                       | (((p[2] >> bit) & 1) << 2) | (((p[3] >> bit) & 1) << 3))
        out.append(row)
    return out


def indexed_image(rows, palette=None, transparent0=False):
    """rows: list of lists of indices. returns RGBA image."""
    h = len(rows)
    w = len(rows[0]) if h else 0
    img = Image.new("RGBA", (w, h))
    px = img.load()
    pal = palette_rgb(palette) if palette else [(i * 17, i * 17, i * 17) for i in range(16)]
    for y in range(h):
        for x in range(w):
            i = rows[y][x]
            if transparent0 and i == 0:
                px[x, y] = (0, 0, 0, 0)
            else:
                r, g, b = pal[i]
                px[x, y] = (r, g, b, 255)
    return img


def screen_indices(ram, base=None):
    """The live 320x200 screen as 200 rows of 320 colour indices."""
    if base is None:
        # caller usually passes the video regs; default to the shifter base
        raise ValueError
    rows = []
    for y in range(200):
        row = []
        for g in range(20):
            o = base + y * 160 + g * 8
            p = [w16(ram, o + 2 * i) for i in range(4)]
            for bit in range(15, -1, -1):
                row.append(((p[0] >> bit) & 1) | (((p[1] >> bit) & 1) << 1)
                           | (((p[2] >> bit) & 1) << 2) | (((p[3] >> bit) & 1) << 3))
        rows.append(row)
    return rows


def snap_screen(name):
    """(indices rows, palette words, base) of a snapshot's live screen."""
    p = snap_path(name)
    ram, _ = load_ram(p)
    regs = load_video_regs(p)
    return screen_indices(ram, regs["base"]), regs["palette_words"], regs["base"], ram
