"""pop_assets.py - Populous (Atari ST) graphics asset decoders.

Every decoder returns images as lists of rows of palette indices, with -1 for a
transparent pixel (mask bit = 1).  All formats are 4-bitplane ST words, big-endian.

  LANDn        0x72-byte header, then [u32 packed_len][u32 unpacked_len][LZ stream] -> 33600 bytes
               = 70 terrain blocks, 32x24, masked.  Each 20-byte row in the FILE is word-interleaved
               (mL,mR,p0L,p0R,p1L,p1R,p2L,p2R,p3L,p3R); $1499a reorders it in RAM to
               (mL,p0L,p1L,p2L,p3L, mR,p0R,p1R,p2R,p3R), which is what the blitter $142d6 reads.
  SPRITES0.DAT 23520 = 147 sprites 16x16, row = (m,p0,p1,p2,p3) words, 160 bytes/sprite.
  SPR_320.DAT   8320 = 13 sprites 32x32, row = (mL,p0L..p3L, mR,p0R..p3R), 640 bytes/sprite.
  FONT.DAT      4400 = 110 glyphs 8x8 (chars $20..$8d), row = (m,p0,p1,p2,p3) BYTES, 40 bytes/glyph.
  QAZ.PIC      32000 = raw 320x200 screen (the in-game backdrop).
  MOUTHS.PIC    5040 = 6 frames 48x35, opaque, row = 12 words ordered plane-major
               (p0g0,p0g1,p0g2, p1g0,...), 840 bytes/frame (drawn by $1db1e).
  LORD.PIC, LOAD.PIC  128-byte NEOchrome-style header (+4 = 16 palette words) then packed 32000.
  $150e2 (in TEXT)  opaque 16x16 icons, 128 bytes each (4 plane words per row), drawn by $167e8.
"""
import struct, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from popcfg import WORK as POP
from popdepack import depack

FILES = os.path.join(POP, 'files')
GAMEPAL = [0x000,0x222,0x333,0x444,0x555,0x666,0x310,0x420,0x500,0x530,0x550,0x250,0x140,0x131,0x124,0x136]

def st_rgb(w):
    return tuple(((w >> s) & 7) * 255 // 7 for s in (8, 4, 0))

def packed(data, off=0):
    plen, ulen = struct.unpack_from('>II', data, off)
    out = depack(data[off + 8: off + plen])
    return out[:ulen]

def readf(name):
    return open(os.path.join(FILES, name), 'rb').read()

def _pix(planes, b):
    return sum(((planes[k] >> (15 - b)) & 1) << k for k in range(4))

def masked_groups(buf, off, rows, groups):
    """rows of `groups` x (mask word, 4 plane words); returns index rows, -1 = transparent"""
    img = []
    for y in range(rows):
        row = []
        for g in range(groups):
            o = off + (y * groups + g) * 10
            m = struct.unpack_from('>H', buf, o)[0]
            pl = struct.unpack_from('>4H', buf, o + 2)
            for b in range(16):
                row.append(-1 if (m >> (15 - b)) & 1 else _pix(pl, b))
        img.append(row)
    return img

def land_raw(n):
    d = readf('LAND%d' % n)
    return d[:0x72], packed(d, 0x72)

def land_reorder(raw):
    """what $1499a does to the depacked block sheet"""
    out = bytearray(raw)
    for r in range(len(raw) // 20):
        w = struct.unpack_from('>10H', raw, r * 20)
        struct.pack_into('>10H', out, r * 20, *(w[0::2] + w[1::2]))
    return bytes(out)

def land_blocks(n=None, ram_sheet=None):
    sheet = ram_sheet if ram_sheet is not None else land_reorder(land_raw(n)[1])
    return [masked_groups(sheet, i * 480, 24, 2) for i in range(len(sheet) // 480)]

def sprites16(buf=None):
    buf = buf if buf is not None else packed(readf('SPRITES0.DAT'))
    return [masked_groups(buf, i * 160, 16, 1) for i in range(len(buf) // 160)]

def sprites32(buf=None):
    buf = buf if buf is not None else packed(readf('SPR_320.DAT'))
    return [masked_groups(buf, i * 640, 32, 2) for i in range(len(buf) // 640)]

def font(buf=None):
    buf = buf if buf is not None else packed(readf('FONT.DAT'))
    out = []
    for c in range(len(buf) // 40):
        g = []
        for y in range(8):
            m, p0, p1, p2, p3 = buf[c * 40 + y * 5: c * 40 + y * 5 + 5]
            g.append([-1 if (m >> (7 - b)) & 1 else
                      sum((((p >> (7 - b)) & 1) << k) for k, p in enumerate((p0, p1, p2, p3)))
                      for b in range(8)])
        out.append(g)
    return out

def screen(buf, off=0):
    img = []
    for y in range(200):
        row = []
        for g in range(20):
            pl = struct.unpack_from('>4H', buf, off + y * 160 + g * 8)
            row += [_pix(pl, b) for b in range(16)]
        img.append(row)
    return img

def neo_pic(name):
    d = readf(name)
    pal = list(struct.unpack_from('>16H', d, 4))
    return pal, packed(d, 128)[:32000]

def mouths(buf=None):
    buf = buf if buf is not None else packed(readf('MOUTHS.PIC'))
    frames = []
    for f in range(len(buf) // 840):
        img = []
        for y in range(35):
            w = struct.unpack_from('>12H', buf, f * 840 + y * 24)
            row = []
            for g in range(3):
                pl = (w[g], w[3 + g], w[6 + g], w[9 + g])
                row += [_pix(pl, b) for b in range(16)]
            img.append(row)
        frames.append(img)
    return frames

def icons(img_bytes, text_base=0xad58, addr=0x150e2, count=30):
    out = []
    for i in range(count):
        o = addr - text_base + i * 128
        img = []
        for y in range(16):
            pl = struct.unpack_from('>4H', img_bytes, o + y * 8)
            img.append([_pix(pl, b) for b in range(16)])
        out.append(img)
    return out

# ---------------------------------------------------------------- contact sheets
def sheet(images, cols, pal, scale=2, pad=2, bg=(255, 0, 255), label=True):
    from PIL import Image, ImageDraw
    h = max(len(i) for i in images); w = max(len(i[0]) for i in images)
    lh = 8 if label else 0
    rows = (len(images) + cols - 1) // cols
    cw, ch = w * scale + pad, h * scale + pad + lh
    im = Image.new('RGB', (cols * cw + pad, rows * ch + pad), (40, 40, 40))
    px = im.load(); dr = ImageDraw.Draw(im)
    cols_rgb = [st_rgb(c & 0x777) for c in pal]
    for n, img in enumerate(images):
        ox = pad + (n % cols) * cw; oy = pad + (n // cols) * ch + lh
        if label:
            dr.text((ox, oy - lh - 1), '%d' % n, fill=(255, 255, 255))
        for y, row in enumerate(img):
            for x, c in enumerate(row):
                col = bg if c < 0 else cols_rgb[c]
                for sy in range(scale):
                    for sx in range(scale):
                        px[ox + x * scale + sx, oy + y * scale + sy] = col
    return im

def main():
    out = HERE
    for n in range(4):
        blk = land_blocks(n)
        sheet(blk, 10, GAMEPAL).save(os.path.join(out, 'land%d_blocks.png' % n))
    sheet(sprites16(), 16, GAMEPAL).save(os.path.join(out, 'sprites0.png'))
    sheet(sprites32(), 7, GAMEPAL).save(os.path.join(out, 'spr_320.png'))
    sheet(font(), 16, GAMEPAL, scale=3).save(os.path.join(out, 'font.png'))
    sheet(mouths(), 6, neo_pic('LORD.PIC')[0], scale=2).save(os.path.join(out, 'mouths_lordpal.png'))
    img = open(os.path.join(POP, 'pop_ad58.img'), 'rb').read()
    sheet(icons(img, count=24), 8, GAMEPAL, scale=3).save(os.path.join(out, 'icons_150e2.png'))
    sheet([screen(packed(readf('QAZ.PIC')))], 1, GAMEPAL, scale=2, pad=0, label=False).save(os.path.join(out, 'qaz.png'))
    for nm in ('LORD.PIC', 'LOAD.PIC'):
        pal, scr = neo_pic(nm)
        sheet([screen(scr)], 1, pal, scale=2, pad=0, label=False).save(os.path.join(out, nm.lower().replace('.', '_') + '.png'))
    # DEMOBACK.NEO: same packed stream, no header; palette unknown here -> game palette
    sheet([screen(packed(readf('DEMOBACK.NEO')))], 1, GAMEPAL, scale=2, pad=0, label=False).save(os.path.join(out, 'demoback_gamepal.png'))

if __name__ == '__main__':
    main()
