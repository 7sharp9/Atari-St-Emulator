"""Montage of what each object-map type draws: reversing/virus/objects.png.

    uv run python objects_montage.py <shapes_dir> <flags_dir> <out.png>

<shapes_dir> holds object_shapes.py's *_D.png crops for flags $00 (types 1..9, 11, and 10, 12 by --cells), <flags_dir>
those for flags $10 and $20 (--n 1); one row per type: plain | damaged ($10) | infected ($20). Writes only <out.png>.
"""
import glob, sys
from PIL import Image, ImageDraw

def first(d, t, fl):
    import os
    f = sorted(glob.glob(f'{d}/t{t}_f{fl}_*_D.png'), key=lambda p: -os.path.getsize(p))     # the crop with the most object pixels
    return Image.open(f[0]) if f else None

def main():
    sd, fd, out = sys.argv[1:4]
    names = {1: 'palm', 2: 'bush', 3: 'pine', 4: 'palm (type 4)', 5: 'tall palm', 6: 'fir', 7: 'long house', 8: 'cottage',
             9: 'archway', 10: 'pad marker', 11: 'tower', 12: 'bonus craft'}
    rows = [(t, [first(sd, t, '00'), first(fd, t, '10'), first(fd, t, '20')]) for t in range(1, 13)]
    CW, CH = 330, 150
    W = Image.new('RGB', (CW * 3 + 40, (CH + 14) * len(rows)), (40, 40, 40)); d = ImageDraw.Draw(W)
    for r, (t, ims) in enumerate(rows):
        d.text((2, r * (CH + 14)), f'type {t} ({names[t]}): plain | damaged ($10) | infected ($20)', fill=(255, 255, 255))
        for c, im in enumerate(ims):
            if im is None: continue
            im = im.copy(); im.thumbnail((CW - 10, CH - 4)); W.paste(im, (c * CW + 20, r * (CH + 14) + 12))
    W.save(out)
    print('wrote', out)
main()
