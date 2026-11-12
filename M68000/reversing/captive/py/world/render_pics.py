#!/usr/bin/env python3
"""Render Captive's fed*.pic sheets: 32,000 bytes = four separate 8,000-byte bitplanes (Amiga
layout, 40 bytes per row, 320x200), not ST interleaved words. The game's blitters read them that
way: $b36a reads planes at +0/+8000/+16000/+24000 and steps rows by $28 (40) bytes.

Usage (from M68000/):
  uv run python -I reversing/captive/py/world/render_pics.py <snap> <outdir> [file.pic ...]
The palette is the live shifter palette of <snap> (the surface view uses one palette for all sheets).
With no files named it renders every *.pic/*.pi in scratchpad/captive/fed. Also writes
view.png: the 160x112 view buffer at 15754(A6) (same plane layout, 20 bytes per row, 2,240 per plane),
and sheets_surface.png: the eight sheets loaded on the planet surface (fed7-E, fed2-A, fed3-B, fed5,
fed6-E, fed6-F, fed8, fed9), two per row, when all of them were rendered.
"""
import os
import struct
import sys
from PIL import Image


def repo_root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            raise SystemExit('repo root (tools/rdis.py) not found')
        d = p
    return d


R = repo_root()
sys.path.insert(0, os.path.join(R, 'tools'))
from gfxview import load_ram, load_video_regs, ste_colour  # noqa: E402


def planar(data, w, h, stride, plane, pal):
    im = Image.new('RGB', (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            b = y * stride + (x >> 3)
            bit = 7 - (x & 7)
            c = 0
            for p in range(4):
                c |= ((data[p * plane + b] >> bit) & 1) << p
            px[x, y] = pal[c]
    return im


def main():
    snap, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    pal = [ste_colour(w) for w in load_video_regs(snap)['palette_words']]
    files = sys.argv[3:]
    fed = os.path.join(R, 'scratchpad', 'captive', 'fed')
    if not files:
        files = sorted(f for f in os.listdir(fed) if f.endswith('.pic') or f.endswith('.pi'))
    for f in files:
        data = open(os.path.join(fed, f), 'rb').read()
        if len(data) != 32000:
            continue
        planar(data, 320, 200, 40, 8000, pal).save(os.path.join(out, f + '.png'))
    surf = ['fed7-E.pic', 'fed2-A.pic', 'fed3-B.pic', 'fed5.pic', 'fed6-E.pic', 'fed6-F.pic', 'fed8.pic',
            'fed9.pic']
    if all(f in files for f in surf):
        m = Image.new('RGB', (640, 800))
        for i, f in enumerate(surf):
            m.paste(Image.open(os.path.join(out, f + '.png')), ((i % 2) * 320, (i // 2) * 200))
        m.save(os.path.join(out, 'sheets_surface.png'))
    ram, _ = load_ram(snap)
    vb = struct.unpack('>I', ram[0x1b5ce + 15754:0x1b5ce + 15758])[0]
    planar(ram[vb:vb + 8960], 160, 112, 20, 2240, pal).resize((320, 224), Image.NEAREST).save(
        os.path.join(out, 'view.png'))
    print('palette', ['%03x' % w for w in load_video_regs(snap)['palette_words']], 'view buffer', hex(vb))


if __name__ == '__main__':
    main()
