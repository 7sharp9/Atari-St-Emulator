"""Python port of Super Sprint's track-background builder ($15884 and its callees) working from SUPER.DAT/INIT.DAT.

    $152d2(map, buf)   tile-map compositor            -> tiles()
    $157ee/$15642      per-track scenery sprites      -> scenery()     (list from INIT.DAT -628/-166/-158(A4))
    $1bc92/$1bd9a      extra coloured polylines       -> polylines()   (INIT.DAT -8152/-8186/-8298(A4), tracks 5-7 1-based)

The buffer is ST low-res 4-plane interleaved, 160 bytes/row, 32000 bytes.
"""
import struct
from tkcommon import *
import trackdata as TD
import initmap
from trackdata import w16

def rol32(v, n): n &= 31; return ((v << n) | (v >> (32 - n))) & 0xffffffff if n else v & 0xffffffff
def not32(v): return ~v & 0xffffffff


class Gfx:
    def __init__(s):
        d = TD.sup(); s.d = d
        n0, n1, n2, n3 = TD.tile_header()[1:5]
        s.sets = [TD.F['set0'], TD.F['set1'], TD.F['set2'], TD.F['set3']]
        s.recsz = [10, 18, 26, 32]
        s.counts = [n0, n1, n2, n3]
        init = {off: b for off, ln, pos, b in initmap.split_init()[0]}
        s.init = init

    # ---- $152d2 ---------------------------------------------------------------------------------
    def tile(s, w, buf, dst_off):
        """composite one 8x8 tile word; returns list of 8 rows x 4 plane bytes"""
        d = s.d
        if not (w & 0x8000):                              # plain copy from an earlier screen position (byte offset w)
            return [[buf[w + 160 * r + 2 * p] for p in range(4)] for r in range(8)]
        idx = w & 0x7ff; st = (w >> 11) & 3
        rec = s.sets[st] + idx * s.recsz[st]
        if st == 3:
            work = [[d[rec + 8 * p + r] for p in range(4)] for r in range(8)]
        else:
            lut = w16(d, rec + s.recsz[st] - 2)
            planes = st + 1
            wk = [[0] * 8 for _ in range(4)]             # work[plane][row]
            for half in range(2):                        # two passes: rows 0-3 then 4-7 (longs)
                ld = lambda pl: struct.unpack('>I', d[rec + 8 * pl + 4 * half: rec + 8 * pl + 4 * half + 4])[0]
                D0 = D1 = D2 = 0xffffffff
                D0 = not32(ld(0))
                if planes >= 2: D1 = not32(ld(1))
                if planes >= 3: D2 = not32(ld(2))
                # (for planes==1, D1=D2=-1; planes==2, D2=-1) exactly as $15390..$153ac
                cnt = 0
                for c in range(15, -1, -1):
                    if (lut >> c) & 1:
                        m = D0 & D1 & D2
                        for pl in range(4):
                            if (c >> pl) & 1:
                                for r in range(4):       # 32-bit mask = 4 rows x 8 px
                                    wk[pl][4 * half + r] |= (m >> (24 - 8 * r)) & 0xff
                        cnt += 1                          # swap D4; addq #1; counter toggles D0/D1/D2
                        D0 = not32(D0)
                        if not (cnt & 1):
                            D1 = not32(D1)
                            if not (cnt & 3): D2 = not32(D2)
            work = [[wk[p][r] for p in range(4)] for r in range(8)]
        fl = w >> 13
        if fl & 1: work = work[::-1]                      # vertical flip (btst #0 of word bit 13)
        if fl & 2:                                        # horizontal mirror of every byte (word bit 14)
            work = [[int('{:08b}'.format(b)[::-1], 2) for b in row] for row in work]
        return work

    def tiles(s, mapidx, buf=None):
        if buf is None: buf = bytearray(32000)
        tm = TD.tilemap(mapidx)
        for row in range(25):
            for col in range(40):
                w = tm[row * 40 + col]
                t = s.tile(w, buf, 0)
                base = row * 8 * 160 + (col >> 1) * 8 + (col & 1)
                for r in range(8):
                    for p in range(4):
                        buf[base + r * 160 + 2 * p] = t[r][p]
        return buf

    # ---- $157ee / $15642 scenery sprites ---------------------------------------------------------
    def scenery_list(s, track):
        i = s.init
        start = i[-166][track]; cnt = i[-158][track]
        lst = i[-628]
        out_ = []
        for k in range(cnt):
            o = (start + k) * 6
            # records at -628(A4)+6*idx: x (-628), y (-626), kind (-624)
            out_.append(struct.unpack('>3H', lst[o:o+6]))
        return out_

    def sprite(s, buf, x, y, kind):
        d = s.d; sp = TD.F['sprites']
        A0 = sp + 0x70e0 + kind * 128
        gx = (x & 0xfff0) >> 1
        sh = ((~x) & 15) + 1
        base = y * 160 + gx
        def put(o, v):
            if 0 <= o < 32000 - 1: buf[o] = v >> 8; buf[o+1] = v & 0xff
        def get(o): return (buf[o] << 8) | buf[o+1]
        for row in range(16):
            ro = base + row * 160
            if ro < 0 or ro + 16 > 32000: continue
            w = [w16(d, A0 + row * 8 + 2 * p) for p in range(4)]
            L = [rol32(v, sh) for v in w]
            opq = L[0] | L[1] | L[2] | L[3]
            g0 = [(L[k] >> 16) & 0xffff for k in range(4)]; g1 = [L[k] & 0xffff for k in range(4)]
            m0 = (~(opq >> 16)) & 0xffff; m1 = (~opq) & 0xffff
            # output word order in the destination is [D0', D2', D1', D3'] = planes (w0, w2, w1, w3)
            for grp, g, m in ((0, g0, m0), (1, g1, m1)):
                o = ro + 8 * grp
                if gx + 8 * grp >= 160: continue
                order = (0, 2, 1, 3)
                for slot, k in enumerate(order):
                    oo = o + 2 * slot
                    put(oo, (get(oo) & m) | g[k])
        # shadow (kind-dependent) : $156de.. second stage; 1bpp 16-row mask at +$72e0 + kind*32
        A0 = sp + 0x72e0 + kind * 32
        D0 = x
        hi_minus = False
        if kind != 3:
            D0 -= 8
            if D0 < 0: hi_minus = True; D0 = 8
        sx = D0; sh2 = ((~sx) & 15) + 1
        gx2 = (sx & 0xfff0) >> 1
        tbl = struct.unpack('>8H', b''.join([bytes([0, 11, 0, 7, 0, 15, 0, 9, 0, 16, 0, 10, 0, 16, 0, 10])]))
        dy, hh = tbl[2 * kind], tbl[2 * kind + 1]
        y2 = y + dy
        end = min(y2 + hh, 200)
        nrows = end - y2
        for row in range(nrows):
            mk = w16(d, A0 + 2 * row)
            D6 = rol32(mk, sh2)
            g0m = (D6 >> 16) & 0xffff; g1m = D6 & 0xffff
            ro = y2 * 160 + row * 160 + gx2
            for grp, mm in ((0, g0m), (1, g1m)):
                o = ro + 8 * grp
                if hi_minus:                                # $015764 bne $1579a: group-0 block skipped WITHOUT advancing A1,
                    if grp == 0: continue                   # so group 1's mask piece lands on group 0's address
                    o = ro
                if o < 0 or o + 8 > 32000 or gx2 + 8 * grp >= 160: continue
                p0, p1, p2, p3 = [get(o + 2 * k) for k in range(4)]
                D5 = ((~p1) & p0 & p2 & p3 & mm) & 0xffff
                D5 = (~D5) & 0xffff; p3 &= D5
                nm = (~mm) & 0xffff
                D5 = ((~p3) | p0 | p1 | p2 | nm) & 0xffff
                p3 &= D5; D5 = (~D5) & 0xffff
                p0 |= D5; p1 |= D5
                for k, v in enumerate((p0, p1, p2, p3)): put(o + 2 * k, v)

    def scenery(s, track, buf):
        for x, y, kind in s.scenery_list(track): s.sprite(buf, x, y, kind)
        return buf


# ---- $1bd9a coloured Bresenham line (4 planes, 160 B/row) and $1bc92 polyline lists ------------------
def plot4(buf, x, y, col):
    if not (0 <= x < 320 and 0 <= y < 200): return
    o = y * 160 + (x & 0xfff0) // 2
    bit = 0x8000 >> (x & 15)
    for p in range(4):
        v = (buf[o + 2 * p] << 8) | buf[o + 2 * p + 1]
        v = (v & ~bit) | (bit if (col >> p) & 1 else 0)
        buf[o + 2 * p] = v >> 8; buf[o + 2 * p + 1] = v & 0xff

def line_col(buf, x0, y0, x1, y1, col):
    dx, dy = abs(x0 - x1), abs(y0 - y1)
    if dy >= dx:                                        # y-major ($1bdc0)
        if y0 > y1: x0, y0, x1, y1 = x1, y1, x0, y0
        right = (x0 - x1) < 0
        err = dy >> 1; x = x0
        for y in range(y0, y1 + 1):
            plot4(buf, x, y, col)
            err += dx
            if err >= dy:
                err -= dy; x += 1 if right else -1
    else:                                               # x-major ($1bebc)
        if x0 > x1: x0, y0, x1, y1 = x1, y1, x0, y0
        down = (y0 - y1) < 0
        err = dx >> 1; y = y0
        for x in range(x0, x1 + 1):
            plot4(buf, x, y, col)
            err += dy
            if err >= dx:
                err -= dx; y += 1 if down else -1

def polylines(g, track, buf):
    t1 = track + 1
    if t1 <= 4 or t1 == 8: return buf
    lst = g.init[{5: -8152, 6: -8186}.get(t1, -8298)]
    i = 0; n = lst[0]
    while n != 0xff:
        i += 1
        for k in range(n):
            line_col(buf, lst[i], lst[i+1], lst[i+2], lst[i+3], 3); i += 2
        i += 2; n = lst[i]
    return buf

def build_bg(g, track):
    buf = g.tiles(track)
    g.scenery(track, buf)
    polylines(g, track, buf)
    return buf
