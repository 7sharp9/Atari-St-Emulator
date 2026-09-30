"""Gate animation frames: $142b2 blits 16 rows x 36 B per frame from SUPER.DAT sprite sheet +$180 + f*$240:
24 B of pixels (3 groups x 4 planes = 48x16 px) + 6 B occlusion mask + 6 B collision-fill mask per row. Render pixels and masks."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import trackdata as TD, trackrender as TR, struct
from PIL import ImageDraw
def frame(f):
    d = TD.sup(); o = TD.F['sprites'] + 0x180 + f * 0x240
    pix = []; occ = []; fil = []
    for r in range(16):
        row = d[o + 36 * r: o + 36 * r + 36]
        ws = struct.unpack('>12H', row[:24]); px = []
        for g in range(3):
            for x in range(16):
                px.append(sum(((ws[4 * g + p] >> (15 - x)) & 1) << p for p in range(4)))
        pix.append(px)
        occ.append(row[24:30]); fil.append(row[30:36])
    return pix, occ, fil
if __name__ == '__main__':
    g = TR.Gfx(); pal = struct.unpack('>16H', g.init[-6078]); S = 4; n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    sheet = Image.new('RGB', (n * (48 * S + 8), 16 * S * 2 + 28), (40, 40, 40)); dr = ImageDraw.Draw(sheet)
    for f in range(n):
        pix, occ, fil = frame(f)
        im = Image.new('RGB', (48, 16)); fm = Image.new('RGB', (48, 16))
        for y in range(16):
            for x in range(48):
                im.putpixel((x, y), st_rgb(pal[pix[y][x]]))
            bits = int.from_bytes(fil[y], 'big')
            for x in range(48):
                fm.putpixel((x, y), (255, 255, 255) if (bits >> (47 - x)) & 1 else (0, 0, 0))
        sheet.paste(im.resize((48 * S, 16 * S), Image.NEAREST), (f * (48 * S + 8), 12))
        sheet.paste(fm.resize((48 * S, 16 * S), Image.NEAREST), (f * (48 * S + 8), 16 * S + 24))
        dr.text((f * (48 * S + 8), 0), 'gate frame %d' % f, fill=(255, 255, 255)); dr.text((f * (48 * S + 8), 16 * S + 12), 'fill mask', fill=(255, 255, 255))
    sheet.save(out('png', 'gate_frames.png')); print('ok')
