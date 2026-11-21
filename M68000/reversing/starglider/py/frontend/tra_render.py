"""Decode Starglider .TRA screen files (TITLE.TRA, RESULT.TRA) and render them to PNG.

usage: tra_render.py [<file.TRA> <out.png> ...]      (no arguments: both files under WORK/files -> WORK/frontend)

Format (proved in frontend.md "Boot and loaded files"): a Pack-Ice 2.x 'ICE!' file (ice_depack.py) that depacks to
$7d90 bytes: a $90-byte header (16-byte nibble table at +0, 16 ST palette words at +$14, rest padding) followed by
the 320x200 image as 32000 bytes of CHUNKY 4-bit pixels (160 bytes per row, high nibble = left pixel). The game
reads the file with Fread to $70000, a resident trap #1 hook at $a690 depacks it in place, and $15656 converts the
body to ST planar words.

Gate (--check): the depacked file equals the game's own in-RAM depack, byte for byte, and the body decoded here
equals the planar screen the game displays, pixel for pixel (title: g_title.snap)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
d = HERE
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    p = os.path.dirname(d)
    if p == d:
        raise SystemExit('repo root not found')
    d = p
sys.path.insert(0, os.path.join(d, 'reversing', 'starglider', 'py'))
sys.path.insert(0, HERE)
import sgcommon
import ice_depack
from PIL import Image


def st_rgb(w):
    return tuple(((w >> s) & 7) * 36 for s in (8, 4, 0))


def decode(path):
    d = ice_depack.depack(open(path, 'rb').read())
    assert len(d) == 0x7D90
    pal = [int.from_bytes(d[0x14 + 2 * i:0x16 + 2 * i], 'big') for i in range(16)]
    body = d[0x90:]
    idx = [[(body[y * 160 + x // 2] >> (4 if x % 2 == 0 else 0)) & 15 for x in range(320)] for y in range(200)]
    return d, pal, idx


def render(path, out, scale=1):
    d, pal, idx = decode(path)
    im = Image.new('RGB', (320, 200))
    px = im.load()
    for y in range(200):
        for x in range(320):
            px[x, y] = st_rgb(pal[idx[y][x]])
    if scale != 1:
        im = im.resize((320 * scale, 200 * scale), Image.NEAREST)
    im.save(out)


def planar_indices(ram, base):
    rows = []
    for y in range(200):
        row = []
        for xb in range(20):
            o = base + y * 160 + xb * 8
            pl = [int.from_bytes(ram[o + 2 * i:o + 2 * i + 2], 'big') for i in range(4)]
            for b in range(16):
                row.append(sum(((pl[i] >> (15 - b)) & 1) << i for i in range(4)))
        rows.append(row)
    return rows


if __name__ == '__main__':
    files = os.path.join(sgcommon.WORK, 'files')
    out = sgcommon.work('frontend')
    os.makedirs(out, exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == '--check':
        import gfxview
        ref = sgcommon.load_ram(os.path.join(out, 'after_title_read.snap'))[0x70000:0x70000 + 0x7D90]
        d, pal, idx = decode(os.path.join(files, 'TITLE.TRA'))
        print('depack vs game RAM bytes equal: %d/%d' % (sum(a == b for a, b in zip(d, ref)), len(d)))
        snap = sgcommon.SNAP_TITLE
        ram = sgcommon.load_ram(snap)
        v = gfxview.load_video_regs(snap)
        scr = planar_indices(ram, v['base'])
        n = sum(1 for y in range(200) for x in range(320) if idx[y][x] == scr[y][x])
        print('title.tra chunky body vs displayed planar screen: %d/64000' % n)
        print('header palette == live palette:', pal == list(v['palette_words']))
        sys.exit(0)
    if not args:
        args = [os.path.join(files, 'TITLE.TRA'), os.path.join(out, 'title_tra.png'),
                os.path.join(files, 'RESULT.TRA'), os.path.join(out, 'result_tra.png')]
    for i in range(0, len(args), 2):
        render(args[i], args[i + 1])
        print(args[i + 1])
