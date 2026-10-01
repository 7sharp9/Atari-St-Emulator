"""maps_ref.py: Python transcriptions of PowerMonger's land-map routines in $10000..$11700 and $ac20..$ae80 (140th pass, `maps`).

Every function works on a bytearray `r` holding the 1 MB RAM (index = address) and mutates it like the 68000 routine does.
Planes (all 64 columns x 128 rows, cell n = y*64 + x):
    ALT = $3f86c  altitude byte         ($438ee-16514)
    CA  = $418ad  colour byte, triangle A ($438ee-8257)
    CB  = $438ee  colour byte, triangle B
    FL  = $4592f  flag byte               ($438ee+8257)   bit7 diagonal, bit6 edge mark, bit5 skip-split, bit4 ambiguous, bit3/bit2 'B/A colour fixed', bit1 altitude pinned
    BK  = $47970  bucket word (2 bytes/cell, head of the entity chain in the cell)
Names are the developers' (powermonger_orig.sym), 8-char truncations.
"""
ALT, CA, CB, FL, BK = 0x3f86c, 0x418ad, 0x438ee, 0x4592f, 0x47970
SIN = 0x1400a  # word table read by $12d56


def s8(v):
    v &= 0xff
    return v - 256 if v & 0x80 else v


def s16(v):
    v &= 0xffff
    return v - 65536 if v & 0x8000 else v


def divs_trunc(a, b):
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


# ---------------------------------------------------------------- $10058: bake the two triangle colours + diagonal flag
def _render(d0):
    """the common tail of the render* helpers: addi, clamp 0..15"""
    d0 = s16(d0)
    if d0 < 0:
        return 0
    return 15 if d0 >= 16 else d0


def bake_10058(r):
    """$10058 (`_fill_bl...`, loop `feloop` $10062): for each cell n of the 8192 build colour A (-8257), colour B (0) and flags."""
    for n in range(0x2000):
        a = CB + n
        d4, d5, d6, d7 = r[ALT + n], r[ALT + n + 1], r[ALT + n + 64], r[ALT + n + 65]
        i = (8 if d4 == 0 else 0) + (4 if d5 == 0 else 0) + (2 if d6 == 0 else 0) + (1 if d7 == 0 else 0)
        S = (d4, d5, d6, d7)

        def fl(op, bit):
            if op == 'set':
                r[a + 8257] |= 1 << bit
            else:
                r[a + 8257] &= ~(1 << bit) & 0xff

        def findspli():  # $1021e
            if r[a - 8257] == 0x1d or r[a] == 0x1d or r[a + 8257] & 0x20:
                return
            d0 = s8(d4 - d7)
            d0 = d0 if d0 < 0 else s8(-d0)  # bmi: keep negative, else neg.b
            d2 = s8(d5 - d6)
            d2 = d2 if d2 < 0 else s8(-d2)
            if not d2 < d0:
                r[a + 8257] |= 0x80
            # cmpi #3,D0 bgt / cmpi #3,D2 bgt: D0,D2 are <= 0 here, never taken
            d0 = s8(d0 - d2)
            if d0 < 0:
                d0 = s8(-d0)
            if d0 > 4:
                return
            r[a + 8257] |= 0x10

        def coast(plane_off, render, trio, clr_bit):
            r[a + 8257] &= ~0x10 & 0xff
            if r[a + 8257] & (1 << clr_bit):
                return
            d0 = render()
            d2 = max(s8(x) for x in trio)
            if not d2 > 6:
                d0 += 0x26
            d0 += 0x0c
            r[a + plane_off] = d0 & 0xff

        def land(plane_off, render, clr_bit):
            if r[a + 8257] & (1 << clr_bit):
                return
            r[a + plane_off] = (render() + 0x1f) & 0xff

        def rnw():
            return _render(divs_trunc(s8(s8(s8(d5 - d4) + d6) - d4), 4) + 9)

        def rne():
            return _render(divs_trunc(s8(d7 - d4), 2) + 0x0a)

        def rsw():
            return _render(divs_trunc(s8(d7 - d4), 2) + 9)

        def rse():
            return _render(divs_trunc(s8(s8(s8(d7 - d6) + d7) - d5), 4) + 0x0a)

        # (plane offset, bit that blocks) : colour A = -8257 / bit2 ; colour B = 0 / bit3
        coastnw = lambda: coast(-8257, rnw, (d4, d5, d6), 2)
        landnw = lambda: land(-8257, rnw, 2)
        coastne = lambda: coast(0, rne, (d4, d5, d7), 3)
        landne = lambda: land(0, rne, 3)
        coastsw = lambda: coast(-8257, rsw, (d4, d6, d7), 2)
        landsw = lambda: land(-8257, rsw, 2)
        coastse = lambda: coast(0, rse, (d5, d6, d7), 3)
        landse = lambda: land(0, rse, 3)

        def split_pair():  # slow/elow/wlow/nlow share one body
            findspli()
            if r[a + 8257] & 0x80:
                coastnw(); coastse()
            else:
                coastsw(); coastne()

        if i == 0:
            findspli()
            if r[a + 8257] & 0x80:
                landnw(); landse()
            else:
                landne(); landsw()
        elif i == 1:
            fl('set', 7); landnw(); coastse()
        elif i == 2:
            fl('clr', 7); landne(); coastsw()
        elif i in (3, 5, 10, 12):
            split_pair()
        elif i == 4:
            fl('clr', 7); landsw(); coastne()
        elif i == 6:
            fl('set', 7); coastnw(); coastse()
        elif i == 7:
            fl('set', 7); coastnw(); r[a] = 0
        elif i == 8:
            fl('set', 7); landse(); coastnw()
        elif i == 9:
            fl('clr', 7); coastne(); coastsw()
        elif i == 11:
            fl('clr', 7); coastne(); r[a - 8257] = 0
        elif i == 13:
            fl('clr', 7); coastsw(); r[a] = 0
        elif i == 14:
            fl('set', 7); coastse(); r[a - 8257] = 0
        else:
            r[a - 8257] = 0; r[a] = 0


# ---------------------------------------------------------------- $10410: neighbour-average smoothing
def smooth_10410(r):
    """`_smooth_`: alt[n] = (((N+W+E+S)>>2) + alt[n]) >> 1 for n = 64..8255, unless flag bit 1 pins the cell."""
    for k in range(0x2000):
        n = 64 + k
        if r[FL + 64 + k] & 2:
            continue
        d0 = ((r[ALT + n - 64] + r[ALT + n - 1]) & 0xff)
        d2 = ((r[ALT + n + 1] + r[ALT + n + 64]) & 0xff)
        d0 = ((d0 + d2) & 0xffff) >> 2
        d0 = (d0 + r[ALT + n]) & 0xff
        r[ALT + n] = d0 >> 1


# ---------------------------------------------------------------- $10910: _do_road
def do_road_10910(r, d0, d1, d4, d5):
    """d0/d1 = start/end cell index (y*64+x), d4/d5 = their altitude (sign-extended words)."""
    a0 = CB + d0
    y1 = d0 >> 6; x1 = d0 & 63
    y2 = d1 >> 6; x2 = d1 & 63
    d6 = max(abs(x1 - x2), abs(y1 - y2))
    diff = s16(d5 - d4)
    dividend = diff << 16
    if d6 == 0:
        q = 0          # divide by zero: vector 5 is an rte, D5 unchanged = diff<<16, then ext.l of the low word (0)
    else:
        qq = divs_trunc(dividend, d6)
        q = qq if -32768 <= qq <= 32767 else 0   # overflow leaves D5 = diff<<16 -> ext.l -> 0
    step = q
    pos = (d4 & 0xffff) << 16   # swap/clr.w: altitude in the high word, 16.16
    x, y = x1, y1

    def setf(o, v):
        r[a0 + 8257 + o] |= v

    while True:
        r[a0 - 8257] = 0x1d
        r[a0] = 0x1d
        setf(0, 0x0e); setf(1, 2); setf(64, 2); setf(65, 2)
        alt = (pos >> 16) & 0xff
        for o in (-16514, -16513, -16450, -16449):
            r[a0 + o] = alt
        pos = (pos + step) & 0xffffffff
        if x2 == x:
            if y2 == y:
                return
            if y2 < y:
                y -= 1; a0 -= 64
            else:
                y += 1; a0 += 64
            continue
        if x2 > x:
            x += 1; a0 += 1
            if y2 == y:
                continue
            if y2 > y:
                y += 1; a0 += 64
                r[a0 - 1] = 0x1d; r[a0 + 8256] |= 0x28
                r[a0 - 8321] = 0x1d; r[a0 + 8193] |= 0x24
            else:
                y -= 1; a0 -= 64
                r[a0 - 1] = 0x1d; r[a0 + 8256] |= 0xa8
                r[a0 - 8193] = 0x1d; r[a0 + 8321] |= 0xa4
        else:
            x -= 1; a0 -= 1
            if y2 == y:
                continue
            if y2 > y:
                y += 1; a0 += 64
                r[a0 - 8256] = 0x1d; r[a0 + 8258] |= 0xa4
                r[a0 - 64] = 0x1d; r[a0 + 8193] |= 0xa8
            else:
                y -= 1; a0 -= 64
                r[a0 + 64] = 0x1d; r[a0 + 8321] |= 0x28
                r[a0 - 8256] = 0x1d; r[a0 + 8258] |= 0x24


# ---------------------------------------------------------------- $105d0: _fix_it (stamp a hand-made shape)
def fix_it_105d0(r, cell_ptr, shape):
    """cell_ptr = $438ee + y*64 + x; shape = address of (w, h, alt[w*h], colourA[w*h], colourB[w*h])."""
    w, h = r[shape], r[shape + 1]
    p = shape + 2
    pa = p + w * h
    pb = pa + w * h
    a0 = cell_ptr
    for _ in range(h):
        for _ in range(w):
            r[a0 - 16514] = r[p]; p += 1
            v = r[pa]; pa += 1
            if v:
                r[a0 - 8257] = 0 if v == 1 else v
                r[a0 + 8257] |= 4
            v = r[pb]; pb += 1
            if v:
                r[a0] = 0 if v == 1 else v
                r[a0 + 8257] |= 8
            r[a0 + 8257] |= 2
            a0 += 1
        a0 += 64 - w


# ---------------------------------------------------------------- $ae58: _flat_ci (flat disc)
def flat_ci_ae58(r, a2, radius):
    """a2 = $3f86c + cell, radius = site kind (cells). Sets the altitude of every cell the disc touches to the centre altitude (min 1)."""
    d4 = r[a2] or 1
    d3 = (radius << 8) & 0xffff

    def rot(d0, d1, ang):
        d6 = s16(r[SIN + 2 * ang] << 8 | r[SIN + 2 * ang + 1])
        d5 = s16(r[SIN + 2 * ang - 128] << 8 | r[SIN + 2 * ang - 127])
        x = (s16(d0) * d6 - s16(d1) * d5) * 2
        y = (s16(d1) * d6 + s16(d0) * d5) * 2
        return s16((x & 0xffffffff) >> 16), s16((y & 0xffffffff) >> 16)

    def plot(d0, d1):
        v = s16(d1 + 0x80) >> 2
        row = s16(v & 0xffc0)
        col = s16(d0 + 0x80) >> 8
        r[(a2 + row + col) & 0xfffff] = d4

    def quad(d0, d1):
        plot(d0, -d1)
        plot(-d0, -d1)
        plot(-d0, d1)
        plot(d0, d1)

    ang = 32
    while ang >= 0:
        d7 = d3
        while True:
            d0, d1 = rot(0, d7, ang)
            quad(d0, d1)
            quad(d1, d0)
            d7 = s16(d7 - 0x80)
            if d7 <= 0:
                break
        ang -= 4


# ---------------------------------------------------------------- $ac20: _dec_oth (decode the land script at $58152)
SHAPES = (0xad30, 0xad7a, 0xadc4, 0xae0e)  # $ad14 table: +$1c,+$66,+$b0,+$fa


def dec_oth_ac20(r):
    """Record (x, y, d0, type), 4 bytes, type 0 ends. type<$10: site (queue (d0,x,y,type) at $4b9f2 when d0 != 0) + flat disc;
    $10: group start cell (flatten 2x2 to >= 5); $11: road to the next record's cell; $12: stamp shape d0; >$12 ignored."""
    p = 0x58152
    q = 0x4b9f2
    while True:
        d1, d2, d0, d3 = r[p:p + 4]
        p += 4
        if d3 == 0:
            return
        if d3 < 0x10:
            if d0:
                for k, v in enumerate((d0, d1, d2, d3)):
                    r[q + 2 * k: q + 2 * k + 2] = v.to_bytes(2, 'big')
            flat_ci_ae58(r, ALT + d1 + d2 * 64, d3)
            q += 8
        elif d3 == 0x10:
            a4 = 0x51538 + d0 * 0x13c
            cell = d2 * 64 + d1
            r[a4 + 100: a4 + 102] = cell.to_bytes(2, 'big')
            a2 = ALT + cell
            v = r[a2]
            if v < 5:
                v = 5
                r[a2] = 5
            r[a2 + 64] = r[a2 + 65] = r[a2 + 1] = v
        elif d3 == 0x11:
            start = d2 * 64 + d1
            x2, y2, _, t = r[p:p + 4]
            p += 4
            if t == 0x11:
                p -= 4
            end = y2 * 64 + x2
            do_road_10910(r, start, end, s8(r[ALT + start]), s8(r[ALT + end]))
        elif d3 == 0x12:
            fix_it_105d0(r, CB + d1 + d2 * 64, SHAPES[d0 & 3] if d0 < 4 else None)


# ---------------------------------------------------------------- $10638: _town_gr (level the ground under a settlement)
def town_gr_10638(r, x, y, kind):
    k = kind * 2
    a1 = 0x3078 + (r[0x3078 + k] << 8 | r[0x3078 + k + 1])
    while r[a1] != 0x9d:
        a1 += 1
    a1 += 1
    w, h = r[a1], r[a1 + 1]
    x -= w
    y -= h
    cw, ch = 2 * w + 1, 2 * h + 1
    off = (y << 6) + x
    a2 = CB + off
    a1 = BK + 2 * off
    skip = 64 - cw
    for _ in range(ch):
        for _ in range(cw):
            if r[a1] or r[a1 + 1]:
                r[a2 - 8257] = 0x1d; r[a2] = 0x1d; r[a2 + 8257] |= 0x0c
            else:
                n = 1 if (r[a1 - 128] or r[a1 - 127]) else 0
                wv = 1 if (r[a1 - 2] or r[a1 - 1]) else 0
                e = 1 if (r[a1 + 2] or r[a1 + 3]) else 0
                s = 1 if (r[a1 + 128] or r[a1 + 129]) else 0
                i = 8 * n + 4 * wv + 2 * e + s
                if i == 3:
                    r[a2] = 0x1d; r[a2 + 8257] |= 0xa8
                elif i == 5:
                    r[a2 - 8257] = 0x1d; r[a2 + 8257] |= 0x24
                elif i == 10:
                    r[a2] = 0x1d; r[a2 + 8257] |= 0x28
                elif i == 12:
                    r[a2 - 8257] = 0x1d; r[a2 + 8257] |= 0xa4
                elif i in (7, 11, 13, 14, 15):
                    r[a2 - 8257] = 0x1d; r[a2] = 0x1d; r[a2 + 8257] |= 0x0c
            a1 += 2
            a2 += 1
        a2 += skip
        a1 += 2 * skip


# ---------------------------------------------------------------- $107d6 _draw_ma: the minimap, $e6ee pixel plotter
def plot_e6ee(r, base, x, y, c):
    """$e6ee: one pixel (x, y) of colour c in the 4-plane ST screen at `base` (what the movep.l pair does)."""
    c &= 0xf
    off = base + y * 160 + (x >> 4) * 8 + ((x >> 3) & 1)
    bit = 0x80 >> (x & 7)
    for p in range(4):
        a = off + 2 * p
        r[a] = (r[a] & ~bit & 0xff) | (bit if (c >> p) & 1 else 0)


def w16(r, a):
    return r[a] << 8 | r[a + 1]


def minimap_107d6(r, mode):
    """`_draw_ma` + `draw_con`: cell (x, y) of the 63 x 128 map is the pixel (x, y + 6) of the buffer at [$e0d4] (= $78000).
    mode `_show_ma` ($58098): 0 altitude contour, 1 terrain colour + object marks, 2 terrain colour, 3 terrain + lord-strength dots."""
    base = int.from_bytes(r[0xe0d4:0xe0d8], 'big')
    cont = bytes(r[0x107c6:0x107c6 + 16])
    cmap = bytes(r[0x108ce:0x108ce + 66])
    for row in range(128):
        y = 6 + row
        for x in range(63):
            n = row * 64 + x
            if mode == 0:
                plot_e6ee(r, base, x, y, cont[(r[ALT + n] + 7) >> 3])
                continue
            colour = None
            if mode != 2:
                d2 = w16(r, BK + 2 * n)
                while d2 and colour is None:
                    rec = 0x51b66 + s16(d2)   # (A4,D2.w): the offset is a sign-extended word (tree records sit below $51b66)
                    b6 = r[rec + 6]
                    if mode == 1:
                        if b6 in (4, 2, 0x10):
                            colour = {4: 8, 2: 9, 0x10: 10}[b6]
                    else:
                        if b6 in (2, 0x10):
                            lord = s16(w16(r, rec + 14))
                            d1 = s16(w16(r, 0x4e514 + lord + 6) - w16(r, 0x4e514 + lord + 8))
                            colour = 0 if d1 <= 0 else min((d1 >> 5) + 1, 5)
                    if colour is None:
                        d2 = w16(r, rec)
            if colour is None:
                colour = cmap[r[CA + n]]
            plot_e6ee(r, base, x, y, colour)


# ---------------------------------------------------------------- the conquest map: $11458 _draw_da / $11422 _draw_pa / $1153e dagger
MAPBMP = 0x3f364      # resource 10 (MAP): 320 x 608 4-plane bitmap, 160 bytes a row ($3f364 .. $57164), drawn straight into the 4th..
CONQ = 0x3f2a0        # 13 x 15 land states, byte > 0 = conquered (196 bytes)
DAGGER = 0x1153e      # 16 rows x (mask word, plane0..3 words), keep-mask first: word = (word & mask) | plane
BMSCROLL = 0x11420    # word: scroll offset in scanlines 0..$198


def draw_da_11458(r):
    """`_draw_da`: OR a 16 x 16 dagger onto the map bitmap at the top-left of every conquered land's 24 x 40 cell
    (first cell at byte $3fd65 = row 16, byte 1 of the row, i.e. x = 8; every land advances 15 or 9 bytes depending on parity,
    a land row 6400 bytes)."""
    a0 = 0x3fd65
    lands = 0
    for row in range(15):
        for col in range(13):
            conq = M_s8(r[CONQ + row * 13 + col]) > 0
            odd = a0 & 1
            if conq:
                lands += 1
                for k in range(16):
                    o = DAGGER + k * 10
                    mask = r[o] << 8 | r[o + 1]
                    for pl in range(4):
                        d = r[o + 2 + 2 * pl] << 8 | r[o + 3 + 2 * pl]
                        # the plane word of the 16 px group the dagger covers; an odd start splits it over two groups
                        if not odd:
                            ad = a0 + k * 160 + 2 * pl
                            v = (r[ad] << 8 | r[ad + 1]) & mask | d
                            r[ad], r[ad + 1] = v >> 8, v & 0xff
                        else:
                            ad = a0 + k * 160
                            for byte_off, mk, dd in ((2 * pl, mask >> 8, d >> 8), (7 + 2 * pl, mask & 0xff, d & 0xff)):
                                r[ad + byte_off] = (r[ad + byte_off] & mk) | dd
                a0 += 15 if odd else 9
            else:
                a0 += (6 + 9) if odd else 9
        a0 += 6241


def M_s8(v):
    return v - 256 if v & 0x80 else v


def blit_11422(r, dst, scroll):
    """`_draw_pa`: copy 32000 bytes of the map bitmap, starting `scroll` scanlines down, to the screen buffer at dst."""
    r[dst:dst + 32000] = r[MAPBMP + scroll * 160: MAPBMP + scroll * 160 + 32000]


def pick_1120e(mx, my, scroll, conq):
    """The pointer test at $11252..$112f6. Returns (land, box colour) or None. Box colour 10 on a conquered land, 8 on land 0 or a
    free land with a conquered 4-neighbour, no box otherwise; state < 0 never. conq = the 196 bytes of $3f2a0."""
    if not 8 <= mx <= 0x138:
        return None
    col, rx = divmod(mx - 8, 24)
    if rx >= 16:
        return None
    y = my + scroll - 8
    if y < 0:
        return None
    row, ry = divmod(y, 40)
    if ry >= 32:
        return None
    land = row * 13 + col
    st = M_s8(conq[land])
    if st < 0:
        return None
    if st != 0:
        return land, 10
    if land == 0:
        return land, 8
    if (row != 0 and conq[land - 13]) or (row != 14 and conq[land + 13]) or (col != 0 and conq[land - 1]) or (col != 12 and conq[land + 1]):
        return land, 8
    return None
