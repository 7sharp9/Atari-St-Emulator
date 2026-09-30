"""Render every decoded asset class to PNG sheets (agents/engine/png/).  Formats are taken from the blitters (see tiles.py, cars.py,
sprites.py, b5_regions.py, text.py); proofs are in the proof_*.py scripts.  usage: render_assets.py"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from PIL import Image
import rle
from tiles import TilePack, render_map
from cars import frame_pixels
import text as TX

dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
s1 = open(os.path.join(sscfg.FILES, 'SUPER1.DAT'), 'rb').read()
R = Ram(sscfg.SNAP_RACE)
RACE_PAL = [st_rgb(w) for w in load_video_regs(sscfg.SNAP_RACE)['palette_words']]
def PAL(off): return palette_at(R, A4 + off)
B = {  # SUPER.DAT sections: name -> (file offset, length)
    'B0': (0, 3488), 'B1': (3488, 9120), 'B2': (12608, 7190), 'B3': (19798, 32768), 'B4': (52566, 80000), 'B5': (132566, 30000),
    'B6': (162566, 3000), 'B7': (165566, 3520), 'B8': (169086, 2000), 'B9': (171086, 12300), 'B10': (183386, 480), 'B11': (183866, 7100),
    'B12': (190966, 8000), 'FONT': (198966, 336), 'BIGFONT': (199302, 1248), 'INSTR': (200550, 2100), 'SCRIPTS': (202650, 10000)}
def blk(n): o, l = B[n]; return dat[o:o + l]
MAG = (255, 0, 255)


def save(img, name):
    p = os.path.join(PNG, name); img.save(p); print('wrote', p, img.size)


def put_pix(img, ox, oy, pix, pal, S=1):
    for y, row in enumerate(pix):
        for x, c in enumerate(row):
            col = MAG if c is None else pal[c]
            if S == 1: img.putpixel((ox + x, oy + y), col)
            else:
                for dy in range(S):
                    for dx in range(S): img.putpixel((ox + x * S + dx, oy + y * S + dy), col)


def bits4(words, permuted=False):
    p = [words[0], words[2], words[1], words[3]] if permuted else list(words)
    return [sum(((p[i] >> (15 - b)) & 1) << i for i in range(4)) for b in range(16)]


def sheet(frames, cols, cw, ch, pal, S=3, gap=1, name=None):
    rows = (len(frames) + cols - 1) // cols
    img = Image.new('RGB', (cols * (cw * S + gap) + gap, rows * (ch * S + gap) + gap), (40, 40, 40))
    for i, f in enumerate(frames):
        put_pix(img, gap + (i % cols) * (cw * S + gap), gap + (i // cols) * (ch * S + gap), f, pal, S)
    if name: save(img, name)
    return img


def main():
    # 1 screens
    out, used = rle.unrle_plane_major(rle.to_words(s1))
    save(decode_st_screen(struct.pack('>%dH' % len(out), *out), PAL(-5556)), '00_splash_SUPER1DAT_pal1d590.png')
    out, used = rle.unrle_plane_major(rle.to_words(blk('B12')))
    save(decode_st_screen(struct.pack('>%dH' % len(out), *out), PAL(-5460)), '01_credits_reset_picture_B12_pal1d5f0.png')
    pack = TilePack(blk('B4'))
    save(decode_st_screen(bytes(render_map(pack, 8)), PAL(-5428)), '02_title_map08_pal1d610.png')
    # winner's circle with its 4 palette bands (band height = count * 2 scanlines, INFERRED from the Timer-B setup at $fa36)
    wc = decode_st_screen(bytes(render_map(pack, 9)), PAL(-5716))
    counts = [R.sw(A4 - 6098 + 2 * i) for i in range(3)]
    edges = [0] + [min(200, c * 2) for c in counts]
    edges = [sum(edges[:i + 1]) for i in range(len(edges))]
    for k in range(4):
        pk = PAL(-5716 + 32 * k); lo = edges[k]; hi = edges[k + 1] if k < 3 else 200
        src = decode_st_screen(bytes(render_map(pack, 9)), pk)
        wc.paste(src.crop((0, lo, 320, hi)), (0, lo))
    save(wc, '03_winners_circle_map09_banded.png')
    sheet_img = Image.new('RGB', (4 * 322, 2 * 202), (40, 40, 40))
    for m in range(8):
        im = decode_st_screen(bytes(render_map(pack, m)), PAL(-6078))
        sheet_img.paste(im, ((m % 4) * 322 + 1, (m // 4) * 202 + 1))
    save(sheet_img, '04_tracks_1_to_8_maps_pal1d386.png')
    save(decode_st_screen(bytes(render_map(pack, 10)), PAL(-6078)), '05_select_icons_map10.png')
    # 2 tile banks
    for b in range(4):
        n = pack.counts[b]
        cols = 32
        rows = (n + cols - 1) // cols
        img = Image.new('RGB', (cols * 9 + 1, rows * 9 + 1), (40, 40, 40))
        for i in range(n):
            planes = pack.tile_planes(b, i)
            for y in range(8):
                for x in range(8):
                    c = sum(((planes[p][y] >> (7 - x)) & 1) << p for p in range(4))
                    img.putpixel((1 + (i % cols) * 9 + x, 1 + (i // cols) * 9 + y), RACE_PAL[c])
        save(img.resize((img.width * 2, img.height * 2), Image.NEAREST), '06_tile_bank%d_%d_tiles.png' % (b, n))
    # 3 cars
    cars = [frame_pixels(blk('B3'), f) for f in range(128)]
    save(sheet(cars, 16, 16, 12, RACE_PAL, S=3), '07_cars_128_frames.png')
    # 4 B5 sprites
    b5 = blk('B5')
    def w4(off, rows): return [struct.unpack_from('>4H', b5, off + r * 8) for r in range(rows)]
    def masked(words_rows, permuted, rule):
        out = []
        for w in words_rows:
            px = bits4(w, permuted); row = []
            for b in range(16):
                sh = 15 - b; l = [(w[i] >> sh) & 1 for i in range(4)]
                tr = (l[0] | l[1] | l[2] | l[3]) == 0 if rule == 'any' else (l[0] == 0 and l[1] == 0 and l[2] == 0 and l[3] == 1)
                row.append(None if tr else px[b])
            out.append(row)
        return out
    tornado = [masked(w4(f * 128, 16), True, 'any') for f in range(3)]
    spin = [masked(w4(0x5bc0 + f * 112, 14), True, 'any') for f in range(26)]
    trees = [masked(w4(0x70e0 + t * 128, 16), True, 'any') for t in range(4)]
    save(sheet(tornado + trees, 7, 16, 16, RACE_PAL, S=4), '08a_tornado3_trees4.png')
    save(sheet(spin, 13, 16, 14, RACE_PAL, S=4), '08b_car_explosion_26_frames_16x14.png')
    shadows = [[[(1 if (struct.unpack_from('>H', b5, 0x72e0 + t * 32 + r * 2)[0] >> (15 - x)) & 1 else None) for x in range(16)] for r in range(16)] for t in range(4)]
    save(sheet(shadows, 4, 16, 16, [MAG, (0, 0, 0)] + RACE_PAL[2:], S=4), '08c_tree_shadow_masks.png')
    expl = []
    for f in range(44):
        fr = []
        for r in range(8):
            pl = b5[0x1240 + f * 32 + r * 4:0x1240 + f * 32 + r * 4 + 4]
            fr.append([None if sum(((pl[i] >> (7 - b)) & 1) << i for i in range(4)) == 8 else sum(((pl[i] >> (7 - b)) & 1) << i for i in range(4)) for b in range(8)])
        expl.append(fr)
    save(sheet(expl, 22, 8, 8, RACE_PAL, S=4), '08d_smoke_puff_44_frames_8x8.png')
    small = [masked(w4(0x1bc0 + f * 64, 8), True, 'c8') for f in range(36)]
    save(sheet(small, 18, 16, 8, RACE_PAL, S=4), '08e_track_dressing_36_16x8.png')
    tiles16 = []
    for f in range(22):
        fr = []
        for r in range(8):
            w = struct.unpack_from('>4H', b5, 0xcc0 + f * 64 + r * 8)   # 2 longs/row = [p0 p1][p2 p3]
            fr.append(bits4(w, False))
        tiles16.append(fr)
    save(sheet(tiles16, 11, 16, 8, RACE_PAL, S=4), '08f_score_labels_oil_wrench_cone_22_16x8.png')
    objs = []
    for k in range(5):
        fr = []
        for r in range(16):
            o = 0x180 + k * 576 + r * 36
            row = []
            for g in range(3):
                w = struct.unpack_from('>4H', b5, o + g * 8)
                row += bits4(w, False)
            fr.append(row)
        objs.append(fr)
    save(sheet(objs, 5, 48, 16, RACE_PAL, S=2), '08g_barriers_5_48x16.png')
    o1740 = []
    for f in range(12):
        fr = []
        for r in range(8):
            w = struct.unpack_from('>6H', b5, 0x1740 + f * 96 + r * 12)
            px = bits4(w[:4], False)
            fr.append([None if (w[0] | w[1] | w[2] | w[3]) >> (15 - b) & 1 == 0 else px[b] for b in range(16)])
        o1740.append(fr)
    save(sheet(o1740, 12, 16, 8, RACE_PAL, S=4), '08h_posts_12_16x8.png')
    def big(nf, fsize, rows, groups, off):
        fl = []
        for f in range(nf):
            fr = []
            for r in range(rows):
                o = off + f * fsize + r * (20 * (groups // 2))
                row = []
                for hg in range(groups // 2):
                    L = struct.unpack_from('>10H', b5, o + hg * 20)
                    for g in range(2):
                        w = L[g * 4:g * 4 + 4]
                        m = L[8 + g]
                        px = bits4(w, False)
                        row += [None if (m >> (15 - b)) & 1 else px[b] for b in range(16)]
                fr.append(row)
            fl.append(fr)
        return fl
    save(sheet(big(8, 720, 36, 2, 0x24c0), 4, 32, 36, RACE_PAL, S=3), '08i_helicopter_small_8_32x36.png')
    save(sheet(big(8, 1040, 26, 4, 0x3b40), 2, 64, 26, RACE_PAL, S=2), '08j_helicopter_large_8_64x26.png')

    # B5 $6720: 6 frames of 112x6 (7 groups/row; direct plane order; transparent = plane3-only pixels) and $6f00: 10 icons 16x6 ($144ca/$1453a)
    def c8rows(off, rows, groups):
        fr = []
        for r in range(rows):
            row = []
            for g in range(groups):
                w = struct.unpack_from('>4H', b5, off + r * groups * 8 + g * 8)
                px = bits4(w, False)
                for b in range(16):
                    l = [(w[i] >> (15 - b)) & 1 for i in range(4)]
                    row.append(None if (l[0] == 0 and l[1] == 0 and l[2] == 0 and l[3] == 1) else px[b])
            fr.append(row)
        return fr
    save(sheet([c8rows(0x6720 + f * 336, 6, 7) for f in range(6)], 2, 112, 6, RACE_PAL, S=4), '08k_hud_gauge_6_112x6.png')
    save(sheet([c8rows(0x6F00 + f * 48, 6, 1) for f in range(10)], 10, 16, 6, RACE_PAL, S=4), '08l_hud_icons_10_16x6.png')
    # 5 fonts
    font = blk('FONT')
    gl = []
    for g in range(42):
        gl.append([[(1 if (font[g * 8 + r] >> (7 - x)) & 1 else 0) for x in range(8)] for r in range(6)])
    save(sheet(gl, 21, 8, 6, [(0, 0, 80), (255, 255, 255)] + RACE_PAL[2:], S=5), '09a_font_42_glyphs.png')
    bf = blk('BIGFONT')
    bg = []
    for g in range(26):
        fr = []
        for r in range(12):
            m, ink = struct.unpack_from('>2H', bf, g * 48 + r * 4)
            fr.append([1 if (ink >> (15 - x)) & 1 else 0 for x in range(16)])
        bg.append(fr)
    save(sheet(bg, 13, 16, 12, [(0, 0, 80), (255, 255, 255)] + RACE_PAL[2:], S=3), '09b_bigfont_26_glyphs_ink.png')
    # 6 B9 prize pictures (16 x 48x32, screen-format, contiguous 24 B rows) with the winner palette band 3
    b9 = blk('B9')
    pz = []
    for k in range(16):
        fr = []
        for r in range(32):
            row = []
            for g in range(3):
                w = struct.unpack_from('>4H', b9, k * 768 + r * 24 + g * 8)
                row += bits4(w, False)
            fr.append(row)
        pz.append(fr)
    save(sheet(pz, 4, 48, 32, PAL(-5716 + 96), S=3), '10a_winner_circle_pictures_B9_16_48x32.png')
    b10 = blk('B10')
    t10 = []
    for k in range(6):
        fr = []
        for r in range(8):
            w = struct.unpack_from('>5H', b10, k * 80 + r * 10)
            ink = [w[i] >> 8 for i in range(4)]; keep = w[4] >> 8
            fr.append([None if (keep >> (7 - x)) & 1 and not any((ink[i] >> (7 - x)) & 1 for i in range(4)) else sum(((ink[i] >> (7 - x)) & 1) << i for i in range(4)) for x in range(8)])
        t10.append(fr)
    save(sheet(t10, 6, 8, 8, PAL(-5716 + 96), S=6), '10b_B10_6_tiles_8x8.png')
    # B0: hi-score cars picture 9 groups x 44 rows screen format (first 3168 B)
    b0 = blk('B0')
    img = Image.new('RGB', (144 * 3, 44 * 3), (40, 40, 40))
    pix = []
    for r in range(44):
        row = []
        for g in range(9):
            w = struct.unpack_from('>4H', b0, r * 72 + g * 8)
            row += bits4(w, False)
        pix.append(row)
    put_pix(img, 0, 0, pix, PAL(-5492), 3)
    save(img, '10c_B0_hiscore_cars_144x44_pal1d5d0.png')

    # B1: RLE full screen (the three PREPARE-screen car portraits), palette -5854 band 0
    out, used = rle.unrle_plane_major(rle.to_words(blk('B1') + b'\0\0'))
    save(decode_st_screen(struct.pack('>%dH' % len(out), *out), PAL(-5854)), '00b_ready_screen_cars_B1_RLE_pal1d470.png')
    # B7: HUD digit sets (10 digits each): sets 0..3 = 16x11, rows (ink word, keep word) pre-shifted variants; sets 4/5 = 32x11 (ink long, keep long)
    b7 = blk('B7')
    sets = []
    for off, sz in ((0, 44), (440, 44), (880, 44), (1320, 44)):
        fl = []
        for k in range(10):
            fr = []
            for r in range(11):
                a, m = struct.unpack_from('>2H', b7, off + k * 44 + r * 4)
                fr.append([1 if (a >> (15 - x)) & 1 else (2 if not (m >> (15 - x)) & 1 else 0) for x in range(16)])
            fl.append(fr)
        sets.append(fl)
    for off in (1760, 2640):
        fl = []
        for k in range(10):
            fr = []
            for r in range(11):
                ink, m = struct.unpack_from('>2I', b7, off + k * 88 + r * 8)
                fr.append([1 if (ink >> (31 - x)) & 1 else (2 if not (m >> (31 - x)) & 1 else 0) for x in range(32)])
            fl.append(fr)
        sets.append(fl)
    pal3 = [(0, 0, 0), (255, 255, 255), (90, 90, 160)]
    w = 10 * (32 * 3 + 1) + 1
    big = Image.new('RGB', (w, 6 * (11 * 3 + 1) + 1), (40, 40, 40))
    for si, fl in enumerate(sets):
        for k, fr in enumerate(fl):
            put_pix(big, 1 + k * (32 * 3 + 1), 1 + si * (11 * 3 + 1), fr, pal3, 3)
    save(big, '10e_B7_HUD_digit_sets_6x10.png')

    # B8: winner's-circle effect sprites (direct plane order, colour 0 transparent)
    b8 = blk('B8'); pw = PAL(-5716 + 96)
    def m16(w, n=16):
        px = bits4(w, False)
        return [None if ((w[0] | w[1] | w[2] | w[3]) >> (15 - b)) & 1 == 0 else px[b] for b in range(16)]
    save(sheet([[m16(struct.unpack_from('>4H', b8, f * 64 + r * 8)) for r in range(8)] for f in range(4)], 4, 16, 8, pw, S=6), '10d_B8_a_4frames_16x8.png')
    save(sheet([[m16(struct.unpack_from('>4H', b8, 0x100 + f * 16 + r * 8)) for r in range(2)] for f in range(3)], 3, 16, 2, pw, S=6), '10d_B8_b_3frames_16x2.png')
    f3 = []
    for f in range((2000 - 0x130) // 0xF0):
        fr = []
        for r in range(15):
            L = struct.unpack_from('>4I', b8, 0x130 + f * 0xF0 + r * 16)
            row = []
            for b in range(32):
                v = [(L[i] >> (31 - b)) & 1 for i in range(4)]
                row.append(None if sum(v) == 0 else sum(v[i] << i for i in range(4)))
            fr.append(row)
        f3.append(fr)
    save(sheet(f3, 7, 32, 15, pw, S=4), '10d_B8_c_7frames_32x15.png')

    # B2: steering wheel, 5 stored + 11 derived frames (64x44, screen-format rows of 4 groups)
    import wheel
    wf = []
    for fb in wheel.all_frames(blk('B2')):
        fr = []
        for r in range(44):
            row = []
            for g in range(4):
                row += bits4(struct.unpack_from('>4H', fb, r * 32 + g * 8), False)
            fr.append(row)
        wf.append(fr)
    save(sheet(wf, 8, 64, 44, RACE_PAL, S=2), '10f_steering_wheel_16_frames_64x44_B2.png')


if __name__ == '__main__':
    main()
