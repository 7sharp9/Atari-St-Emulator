"""render_unused.py: annotated sheets of the assets that contain the candidate blocks.
  b9_prize_frames_by_animation.png : the 16 B9 frames (48x32), each labelled with its prize animation (frame = 3*anim + img, $1b4e4) and
                                     the SUPER.DAT file-offset range, in the winner's-circle palette band 3 (-5716+96(A4)).
  heli_sheets_8_frames.png         : the 8 small (32x36) and 8 large (64x26) helicopter frames, labelled with the crash side that selects them
                                     (census_heli.py: flags bit0 = top/bottom or left/right half, bit1 = large sheet).
  steering_wheel_stored_frames.png : the 5 stored wheel frames (copied by $19164 at SELECT TRACK entry; the other 11 are derived)."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
sys.path.insert(0, os.path.join(sscfg.R, 'reversing', 'supersprint', 'py', 'engine'))
from common import Ram, palette_at
from PIL import Image, ImageDraw
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
R = Ram(sscfg.SNAP_RACE)
def PAL(off): return palette_at(R, A4 + off)
RACE_PAL = palette_at(R, A4 - 6078)
def bits4(w, perm=False):
    p = [w[0], w[2], w[1], w[3]] if perm else list(w)
    return [sum(((p[i] >> (15 - b)) & 1) << i for i in range(4)) for b in range(16)]
def draw(img, ox, oy, rows, pal, S):
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            col = (255, 0, 255) if c is None else pal[c]
            for dy in range(S):
                for dx in range(S): img.putpixel((ox + x * S + dx, oy + y * S + dy), col)

def sheet(frames, labels, cols, cw, ch, pal, S, name, hl=None):
    LH = 24; gap = 4
    rows = (len(frames) + cols - 1) // cols
    img = Image.new('RGB', (cols * (cw * S + gap) + gap, rows * (ch * S + LH + gap) + gap), (30, 30, 30))
    d = ImageDraw.Draw(img)
    for i, f in enumerate(frames):
        ox = gap + (i % cols) * (cw * S + gap); oy = gap + (i // cols) * (ch * S + LH + gap)
        draw(img, ox, oy, f, pal, S)
        d.text((ox, oy + ch * S + 2), labels[i], fill=(255, 255, 255))
    img.save(os.path.join(PNG, name)); print(name, img.size)

def b9():
    B9 = 171086; fr = []; lab = []
    for k in range(16):
        rows = []
        for r in range(32):
            row = []
            for g in range(3): row += bits4(struct.unpack_from('>4H', dat, B9 + k * 768 + r * 24 + g * 8))
            rows.append(row)
        fr.append(rows)
        a = k // 3 if k < 9 else 3
        lab.append('f%d anim%d\n%x-%x' % (k, a, B9 + k * 768, B9 + (k + 1) * 768))
    sheet(fr, lab, 4, 48, 32, PAL(-5716 + 96), 3, 'b9_prize_frames_by_animation.png')

def heli():
    B5 = 132566; fr = []; lab = []
    def big(off, fsize, rows, groups, nf):
        out = []
        for f in range(nf):
            fm = []
            for r in range(rows):
                o = B5 + off + f * fsize + r * (20 * (groups // 2)); row = []
                for hg in range(groups // 2):
                    L = struct.unpack_from('>10H', dat, o + hg * 20)
                    for g in range(2):
                        w = L[g * 4:g * 4 + 4]; m = L[8 + g]; px = bits4(w)
                        row += [None if (m >> (15 - b)) & 1 else px[b] for b in range(16)]
                fm.append(row)
            out.append(fm)
        return out
    small = big(0x24c0, 720, 36, 2, 8); large = big(0x3b40, 1040, 26, 4, 8)
    sl = ['small %d\n%s' % (i, 'top-half crash' if i < 4 else 'bottom-half crash') for i in range(8)]
    ll = ['large %d\n%s' % (i, 'left-edge crash' if i < 4 else 'right-edge crash') for i in range(8)]
    sheet(small, sl, 8, 32, 36, RACE_PAL, 2, 'heli_small_8_frames.png')
    sheet(large, ll, 4, 64, 26, RACE_PAL, 2, 'heli_large_8_frames.png')

def wheel():
    import wheel as W
    b2 = dat[0x3140:0x3140 + 7190]; fr = []; lab = []
    for i in range(5):
        fb = b2[0x96 + i * 1408:0x96 + (i + 1) * 1408]; rows = []
        for r in range(44):
            row = []
            for g in range(4): row += bits4(struct.unpack_from('>4H', fb, r * 32 + g * 8))
            rows.append(row)
        fr.append(rows); lab.append('stored %d\n%x-%x' % (i, 0x3140 + 0x96 + i * 1408, 0x3140 + 0x96 + (i + 1) * 1408))
    sheet(fr, lab, 5, 64, 44, RACE_PAL, 2, 'steering_wheel_stored_frames.png')

if __name__ == '__main__':
    b9(); heli(); wheel()
