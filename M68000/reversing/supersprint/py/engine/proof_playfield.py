"""Proof: rebuild the Track-1 static background (tile map + trees + tree shadows) in Python and compare with the live
background stash (-86(A4)) of the race snapshot.  Reports byte/pixel match counts overall and outside the HUD/bonus areas."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from tiles import *
from sprites import *
from PIL import Image

snap = sscfg.SNAP_RACE
r = Ram(snap)
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
pack = TilePack(dat[52566:52566 + 80000])
b5 = bytes(dat[132566:132566 + 30000])            # -1722(A4) block
img = open(os.path.join(sscfg.WORK, 'ss.img'), 'rb').read()
SH = [struct.unpack_from('>2H', img, 0x157da - 0xa304 + 4 * t) for t in range(4)]


def build(track):
    scr = render_map(pack, track)
    base = r.b[A4 - 166 + track] * 3; cnt = r.b[A4 - 158 + track]
    for i in range(cnt):
        o = A4 - 628 + 2 * (base + 3 * i)
        x, y, t = r.sw(o), r.sw(o + 2), r.sw(o + 4)
        rows = [struct.unpack_from('>4H', b5, 0x70e0 + t * 128 + rr * 8) for rr in range(16)]
        tree_sprite(scr, x, y, rows)
        sh = struct.unpack_from('>16H', b5, 0x72e0 + t * 32)
        tree_shadow(scr, x, y, t, sh, SH[t])
    return scr


if __name__ == '__main__':
    stash = bytes(r.b[r.g(-86):r.g(-86) + 32000])
    scr = bytes(build(0))
    regs = load_video_regs(snap)
    pal = [st_rgb(w) for w in regs['palette_words']]
    a = decode_st_screen(scr, pal); b = decode_st_screen(stash, pal)
    pa, pb = a.load(), b.load()
    tot = sum(1 for y in range(200) for x in range(320) if pa[x, y] == pb[x, y])
    print('all pixels equal: %d / 64000' % tot)
    # exclude the HUD band (rows 0..29) and the wrench bonus (drawn live); count rows 30..199
    body = sum(1 for y in range(30, 200) for x in range(320) if pa[x, y] == pb[x, y])
    print('rows 30..199 pixels equal: %d / %d' % (body, 170 * 320))
    bad = [(x, y) for y in range(30, 200) for x in range(320) if pa[x, y] != pb[x, y]]
    print('mismatching pixels in rows 30..199:', len(bad), bad[:40])
    a.save(os.path.join(PNG, 'track1_rebuilt.png'))
    xs = [p[0] for p in bad]; ys = [p[1] for p in bad]
    print('mismatch bbox rows 30..199: x %d..%d y %d..%d' % (min(xs), max(xs), min(ys), max(ys)))
    hud = [(x, y) for y in range(30) for x in range(320) if pa[x, y] != pb[x, y]]
    print('mismatching pixels rows 0..29 (HUD digits/panels drawn over the tile crowd):', len(hud))
    left = [p for p in bad if p[0] < 60]
    print('mismatches with x<60:', len(left), left[:60])
    other = [p for p in bad if p[0] >= 60]
    xs = [p[0] for p in other]; ys = [p[1] for p in other]
    print('mismatches x>=60: %d bbox x %d..%d y %d..%d' % (len(other), min(xs), max(xs), min(ys), max(ys)))
