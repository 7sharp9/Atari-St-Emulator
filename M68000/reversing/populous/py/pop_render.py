"""pop_render.py - re-implementation of Populous' (Atari ST) per-frame compositor, driven only by RAM.

  python pop_render.py <snap> <out.png> [--truth] [--pointer]

Reads the game's RAM out of an emulator snapshot and rebuilds the frame the way $b510 does:

  $149ea  copy the backdrop buffer [$3afd8] (QAZ.PIC + minimap) to the draw screen [$3c4d2]
  $da52   mana marker (sprite $45) on the power rail
  $14364  8x8 terrain window at (cx=[$37e7a], cy=[$249ae]) + earth side walls; walkers -> draw list
  $b704   draw list $3b00c (8-byte records x,y,sprite,entity) : 16x16 ($16916) or 32x32 ($169e8)
  $b7a8   minimap view marker (sprite $54)
  dots    minimap walker dots ($166b2) - plotted inside the AI pass ($e926/$ec26/$ec9e); rebuilt
          here from the entity table: colour rule of $b7e2, frame-parity rule of $e8d0/$ec50
  $d482   shield / status bars ($16834) - only the no-selection path is implemented
  (VBL)   $16de2 mouse pointer onto the DISPLAYED screen (only with --pointer)

The backdrop is taken from RAM ([$3afd8]) because it accumulates EOR highlights ($16b26) from UI
history; `backdrop_from_files()` rebuilds it from QAZ.PIC + $c27a minimap for the diff report.

  python pop_render.py <pre.snap> <out.png> --post <post.snap> --truth [--files]
--files   build the backdrop from QAZ.PIC + minimap + start-of-game EOR highlights instead of
          reading [$3afd8], so no screen memory is consulted at all
pre.snap  taken at $14364 entry (map/entity state the terrain pass reads)
post.snap taken at the following $16ed8 entry (before the flip): the AI pass has run, the draw screen
          [$3c4d2] holds the finished frame.  --truth compares against that buffer, prints the
          pixel-match %, and writes <out>_diff.png (magenta = mismatching pixel).
"""
import sys, os, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from snapram import ram as snap_ram
import pop_assets as A

class Mem:
    def __init__(self, r): self.r = r
    def b(self, a): return self.r[a]
    def sb(self, a): v = self.r[a]; return v - 256 if v & 0x80 else v
    def w(self, a): return struct.unpack_from('>H', self.r, a)[0]
    def sw(self, a): return struct.unpack_from('>h', self.r, a)[0]
    def l(self, a): return struct.unpack_from('>I', self.r, a)[0]

# RAM addresses (runtime)
BLKMAP, HGTMAP, OVLMAP, ENTMAP = 0x36e78, 0x33be4, 0x3c522, 0x37fd4
ENT, ENTSZ = 0x3b278, 0x16
SIDES = 0x3b226            # 2 x 16 bytes: +0 leader entity, +8 long, +12 long mana
P_BLOCKS, P_SPR16, P_SPR32 = 0x3c51e, 0x3d534, 0x37e7c
P_LOG, P_PHYS, P_BACK = 0x3c4d2, 0x3c4ce, 0x3afd8
ORG = 0x2287a              # byte offset of view cell (0,0) in the screen ($2858 = x 176, y 64)

class Screen:
    def __init__(self, pix): self.p = pix              # 200 rows x 320 palette indices
    def blit(self, img, x, y, clip_top_block=False):
        for j, row in enumerate(img):
            yy = y + j
            if yy < 0 or yy >= 200: continue
            pr = self.p[yy]
            for i, c in enumerate(row):
                xx = x + i
                if c >= 0 and 0 <= xx < 320: pr[xx] = c
    def plot(self, x, y, c):                            # $16772 (clips to 320x200)
        if 0 <= x < 320 and 0 <= y < 200: self.p[y][x] = c & 15
    def vbar(self, xcol, ybot, total, filled, colour):  # $16834 / $168aa
        filled = max(0, min(filled, total))
        x = xcol * 8 + 2                                 # byte mask $3c = pixels 2..5 of the byte
        for k in range(total):
            c = colour if k < filled else 2
            y = ybot - k
            for i in range(4):
                if 0 <= y < 200: self.p[y][x + i] = c

class Frame:
    def __init__(self, snap):
        self.m = Mem(snap_ram(snap))
        m = self.m
        self.blocks = A.land_blocks(ram_sheet=m.r[m.l(P_BLOCKS): m.l(P_BLOCKS) + 33600])
        self.spr = A.sprites16(m.r[m.l(P_SPR16): m.l(P_SPR16) + 23520])
        self.big = A.sprites32(m.r[m.l(P_SPR32): m.l(P_SPR32) + 8320])
        self.pal = [m.w(0x22880 + 2 * i) for i in range(16)]   # Setcolor source table (see $af12)
        self.cx, self.cy = m.sw(0x37e7a), m.sw(0x249ae)
        self.shim = m.sw(0x3b222)                              # toggled every frame at $b6a4
        self.side = m.sw(0x3affe)                              # player side
        self.ctr = m.sw(0x3c4c8)
        self.org = m.l(ORG)
        self.list = []

    # ---------------------------------------------------------------- $142d6
    def block(self, scr, col, row, hpix, blk):
        off = self.org + 8 * col - 8 * row + 160 * (8 * col + 8 * row) - 160 * hpix
        if off < 0: return                                     # bge $142fe : whole block skipped
        y, x = off // 160, (off % 160) // 8 * 16
        scr.blit(self.blocks[blk], x, y)

    def spr_at(self, scr, off, n):                            # $14540: 16x16 masked, word aligned
        scr.blit(self.spr[n], (off % 160) // 8 * 16, off // 160)

    # ---------------------------------------------------------------- $14364
    def terrain(self, scr):
        m, cx, cy = self.m, self.cx, self.cy
        for r in range(8):
            for c in range(8):
                cell = (cy + r) * 64 + cx + c
                b = m.b(BLKMAP + cell)
                if b == 0 and self.shim == 0: b = 0x10           # water shimmer frame
                h = m.sb(HGTMAP + cell) * 8
                self.block(scr, c, r, h, b)
                h += 8
                o = m.b(OVLMAP + cell)
                if o: self.block(scr, c, r, h, o)
                e = m.b(ENTMAP + cell)
                if e and self.org == 0x2858: self.walker(c, r, h, e, cell)
                if m.w(0x3d526) and m.w(0x3d526) == cell: self.block(scr, c, r, h, 0x2e)
                if m.w(0x3c4ca) and m.w(0x3c4ca) == cell: self.block(scr, c, r, h, 0x2d)
        # earth side walls: right face under column 7 (sprite 77), front face under row 7 (sprite 76)
        base = self.org + 0x2840
        for r in range(8):
            h = m.b(HGTMAP + (cy + r) * 64 + cx + 7)
            for k in range(h): self.spr_at(scr, base - 0x500 * k, 77)
            base += 0x4f8
        base -= 0x500
        for c in range(7, -1, -1):
            h = m.b(HGTMAP + (cy + 7) * 64 + cx + c)
            for k in range(h): self.spr_at(scr, base - 0x500 * k, 76)
            base -= 0x508

    # ---------------------------------------------------------------- $1457e / $148ee
    def walker(self, col, row, d2, e, cell):
        m = self.m
        d0, d1 = col * 8, row * 8
        d5 = d0 + d1 - d2
        d0 <<= 1; d1 <<= 1
        d4 = d0 - d1
        a2 = ENT + (e - 1) * ENTSZ
        t = m.b(a2); sd = m.b(a2 + 1)
        w12 = m.sw(a2 + 12); l14 = m.l(a2 + 14); w14 = m.w(a2 + 14)
        def push(x, y, s): self.push(x, y, s, e, a2)
        if t == 2 or (t != 1 and t & 0x10):
            pass                                                   # moving: fall through to $146de
        elif t == 1:
            s = 0x40 + self.shim + (2 if sd else 0); return push(d4 + 0xc0, d5 + 0x40, s)
        elif t & 0x60:
            s = w12 + (0x18 if l14 else 0) + (2 if sd else 0); return push(d4 + 0xc0, d5 + 0x40, s)
        elif t & 0x08:
            return push(d4 + 0xc0, d5 + 0x40, w12)
        elif t & 0x80:
            return push(d4 + 0xb8, d5 + 0x40, (self.ctr & 3) + 0x69)
        else:
            s = w12 + (0x20 if l14 else 0) + (4 if sd else 0); return push(d4 + 0xc0, d5 + 0x40, s)
        # $146de: walker between two cells; slope term from the height map
        w10 = m.sw(a2 + 10)
        dh = (m.b(HGTMAP + cell) - m.b(HGTMAP + cell + w10)) & 0xff
        dh = dh - 256 if dh & 0x80 else dh
        d5 += dh * w12
        if m.b(BLKMAP + cell) != 0x0f: d5 += 4
        big = w12 > 4
        tab = {-65: (0, -2, 0, lambda: d0 == 0 or d1 == 0), -64: (2, -1, 2, lambda: d1 == 0),
               -63: (4, 0, 4, lambda: d0 == 0x70 or d1 == 0), 1: (2, 1, 6, lambda: d0 == 0x70),
               65: (0, 2, 8, lambda: d0 == 0x70 or d1 == 0x70), 64: (-2, 1, 10, lambda: d1 == 0x70),
               63: (-4, 0, 12, lambda: d0 == 0 or d1 == 0x70), -1: (-2, -1, 14, lambda: d0 == 0)}
        if w10 in tab:
            dx, dy, s, edge = tab[w10]
            if big and edge(): return                              # leaving the window: not drawn
        else:
            dx, dy, s = 0, 0, 8
        if e >= 0xd1:
            s = m.sw(a2 + 6)
        elif t & 0x10:
            s = (self.ctr & 3) + 0x5d + (0x10 if l14 else 0) + (4 if sd else 0)
        else:
            s += (0x20 if w14 else 0) + (0x10 if sd else 0) + self.shim
        push(d4 + dx * w12 + 0xb8, d5 + dy * w12 + 0x40, s)

    def push(self, x, y, s, e, a2):
        m = self.m
        self.list.append((x, y, s, e))
        if e == m.sw(0x3c4c6): self.list.append((x + 8, y, 0x44, e))   # selected walker
        sd = m.sb(a2 + 1)
        lead = SIDES + (0x10 if sd else 0)
        if m.w(lead) and m.w(lead) == e: self.list.append((x + 8, y, 0x4a + sd, e))  # leader

    def draw_list(self, scr, lst):
        for x, y, s, e in lst:
            if e >= 0xd1:
                if y - 16 >= 0: scr.blit(self.big[s], x - 8, y - 16)
            elif y >= 0: scr.blit(self.spr[s], x, y)

    # ---------------------------------------------------------------- $da52 mana marker
    def mana_marker(self, scr):
        m = self.m
        mana = struct.unpack_from('>i', m.r, SIDES + 16 * self.side + 12)[0]
        th = lambda i: struct.unpack_from('>i', m.r, 0x21984 + 4 * i)[0]
        d7 = 0
        while mana > th(d7): d7 += 1
        if d7 > 9: return scr.blit(self.spr[0x45], 0x137, 0x57)
        span = th(d7) - th(d7 - 1); part = (mana - th(d7 - 1)) * 8
        d6 = int(part / span) if span else 0                           # ldiv (truncating)
        scr.blit(self.spr[0x45], 0xa0 + (d7 - 1) * 16 + 2 * d6, 8 + (d7 - 1) * 8 + d6)

    # ---------------------------------------------------------------- minimap ($166b2)
    @staticmethod
    def mm_xy(cell): return 64 + (cell & 63) - (cell >> 6), ((cell & 63) + (cell >> 6)) >> 1

    def dots(self, scr, m=None):
        m = m or self.m
        for i in range(m.sw(0x3c4e2)):
            a = ENT + i * ENTSZ
            if m.sw(a + 4) == 0: continue
            sd = m.b(a + 1)
            if sd != self.side and m.w(0x219b0) == 0: continue
            # the AI pass ($e8d0 / $ec50) plots settled walkers (bit0) on frames with [$3b222]=0 and
            # moving walkers (bit1) on frames with [$3b222]!=0, so the two dot kinds alternate
            shim = m.sw(0x3b222)
            if m.b(a) & 1 and shim == 0:
                scr.plot(*self.mm_xy(m.w(a + 8)), m.w(0x21e0c + sd * 0x2e + 32))
            if m.b(a) & 2 and shim != 0:
                scr.plot(*self.mm_xy(m.w(a + 8)), 8 + (7 if sd == 0 else 0))

    def view_marker(self, scr):                                          # $b766
        a, b = self.cx + 3, self.cy + 3
        scr.blit(self.spr[0x54], 0x40 + a - b - 3, int((a + b) / 2) - 3)

    def panel(self, scr, m=None):                                        # $d918.. (both sides)
        m = m or self.m
        for sd, col, colour in ((0, 0x20, 15), (1, 0x27, 8)):
            v = m.l(SIDES + 16 * sd + 8)
            n = (v * 31) // 50000 + 1 if v else 0
            scr.vbar(col, 0x1f, 0x20, n, colour)

    # ---------------------------------------------------------------- $d482 selected-walker shield
    def icon(self, scr, gx, y, n):                                       # $167e8: opaque 16x16 icon
        global _TEXT
        if _TEXT is None: _TEXT = open(os.path.join(A.POP, 'pop_ad58.img'), 'rb').read()
        scr.blit(A.icons(_TEXT, addr=0x150e2 + 128 * n, count=1)[0], gx * 16, y)

    def shield(self, scr, m):
        """$d482 with [$3c4c6] != 0.  Returns False when the selection is dead ($d4c0: the side bars
           are then skipped for this frame as well)."""
        a5 = ENT + (m.sw(0x3c4c6) - 1) * ENTSZ
        if m.sw(a5 + 4) <= 0: return False
        t, sd = m.b(a5), m.b(a5 + 1)
        shim, ctr = m.sw(0x3b222), m.sw(0x3c4c8)
        self.icon(scr, 0x11, 4, sd)                                      # ankh / skull
        d7 = 1
        while not (m.sw(0x3b25e + 2 * d7) == m.b(a5 + 3) or d7 >= 0xb): d7 += 1
        if d7 < 0xb: self.icon(scr, 0x12, 4, d7 + 1)                    # rank weapon
        if t & 8:                                                        # fighting: strength share
            opp = ENT + m.w(a5 + 6) * ENTSZ
            good, evil = (a5, opp) if sd == 0 else (opp, a5)
            scr.blit(self.spr[m.sw(a5 + 12)], 0x110, 0x16)
            tot = m.sw(good + 4) + m.sw(evil + 4)
            scr.vbar(0x24, 0x25, 0x10, int(m.sw(good + 4) * 16 / tot) if tot else 0, 15)
            scr.vbar(0x25, 0x25, 0x10, int(m.sw(evil + 4) * 16 / tot) if tot else 0, 8)
            return True
        if t == 1:                                                       # settled: capacity/strength
            scr.blit(self.spr[0x40 + shim + 2 * sd], 0x10c, 0x16)
            cap = capacity(m, sd, m.w(a5 + 8)) or 1
            scr.vbar(0x24, 0x25, 0x10, 16 if cap == 0xbea else (cap * 16) // 0x131, 10)
            v = (m.w(a5 + 4) * 16 & 0xffff) // cap
            scr.vbar(0x25, 0x25, 0x10, max(0, min(16, v)), 12)
            return True
        if t & 0x60:
            s = (0x7d if m.l(a5 + 14) else 0x65) + 2 * sd + shim
        elif t & 0x10:
            s = (0x6d if m.l(a5 + 14) else 0x5d) + 4 * sd + (ctr & 3)
        else:
            k = 0
            while k < 9 and m.sw(0x21ee8 + 2 * k) != m.sw(a5 + 10): k += 1
            if k > 7: k = 4
            s = 2 * k + shim + (0x20 if m.l(a5 + 14) else 0) + 16 * sd
        scr.blit(self.spr[s], 0x110, 0x16)
        w4 = m.sw(a5 + 4)
        if w4 > 0x1000:
            scr.vbar(0x24, 0x25, 0x10, int(w4 / 0x400), 10)
            scr.vbar(0x25, 0x25, 0x10, w4 % 0x400, 9)
        else:
            scr.vbar(0x24, 0x25, 0x10, int(w4 / 0x100), 9)
            scr.vbar(0x25, 0x25, 0x10, int((w4 % 0x100) / 16), 9)
        return True

    def pointer(self, scr, m=None):                                      # VBL $16de2
        m = m or self.m
        n = m.sw(0x22ac8 + 2 * m.sw(0x2165c))
        scr.blit(self.spr[n], m.sw(0x24748), m.sw(0x2474a))

    def render(self, backdrop=None, with_pointer=False, post=None):
        """self = state at $14364 entry; post = Mem at $16ed8 entry (AI has run: dots, panel)"""
        m = self.m
        pm = post or m
        if backdrop is None:
            bb = m.l(P_BACK); backdrop = A.screen(m.r, bb)
        scr = Screen([row[:] for row in backdrop])
        self.mana_marker(scr)
        self.terrain(scr)
        self.draw_list(scr, self.list)
        self.view_marker(scr)
        self.dots(scr, pm)
        if pm.sw(0x3c4c6) == 0 or self.shield(scr, pm): self.panel(scr, pm)
        if with_pointer: self.pointer(scr, pm)
        return scr

    def ram_list(self, m=None):
        m = m or self.m
        return [tuple(m.sw(0x3b00c + 8 * i + 2 * k) for k in range(4)) for i in range(m.sw(0x37eb2))]

def _probe(m, cell, off):
    """$18198: 0 = usable land, 1 = off the 64x64 map, 2 = block $2f, 3 = water (block 0)"""
    if off == 0: return 0
    d4 = cell + off
    if d4 < 0 or d4 >= 0x1000: return 1
    d3 = off & 0x3f
    if d3 > 3: d3 -= 0x40
    d3 += cell & 0x3f
    if d3 < 0 or d3 > 0x3f: return 1
    b = m.b(BLKMAP + d4)
    return 3 if b == 0 else 2 if b == 0x2f else 0

def capacity(m, side, cell):
    """$18206(side, cell): settlement size score over the 17 offsets at $22b4e ($bea = castle)"""
    d6 = side + 0x1f; d4 = 0
    for d5 in range(17):
        off = m.sw(0x22b4e + 2 * d5)
        r = _probe(m, cell, off)
        if r:
            if r == 2: d4 -= 15
            continue
        c = cell + off; b = m.b(BLKMAP + c)
        if b == d6 or b == 0x0f:
            d4 = (d4 or 0x32) + 0xf
        elif d5 == 0:
            return 0
        d1 = m.sb(OVLMAP + c)
        if d5 < 9 and m.b(OVLMAP + cell) == 0x2a and 0x29 <= d1 <= 0x2c:
            continue
        if d5 and 0x20 < d1 <= 0x2c:
            return 0
    if d4 < 0x23: d4 = 0
    if d4 == 0x131: d4 = 0xbea
    return d4

def backdrop_from_files(fr, eor_initial=True):
    """QAZ.PIC + the $c27a minimap (colour = $21ea0[block], $19 -> $21ebf) + the four mode
       highlights $b510 EORs in at game start (later clicks toggle others via $16b26)"""
    m = fr.m
    scr = Screen(A.screen(A.packed(A.readf('QAZ.PIC'))))
    for y in range(64):
        for x in range(64):
            c = m.b(0x21ea0 + m.b(BLKMAP + y * 64 + x))
            if c == 0x19: c = m.b(0x21ebf)
            scr.plot(64 + x - y, (x + y) >> 1, c)
    if eor_initial:
        for d0, d1, off in ((0, 3, 0x5f90), (0, 4, 0x5f90), (6, 1, 0x4b00), (4, 3, 0x4b00)):  # $b54a..$b59c
            eor_diamond(scr.p, d0, d1, off)
    return scr.p

_TEXT = None
def eor_diamond(pix, d0, d1, off):
    """$16b26: EOR the 32x16 diamond outline at $16b8e into bit-plane 0 only (UI-mode highlight).
       address = screen + d0*$508 + d1*$4f8 + off  (one step of d0/d1 = one iso cell of the panel)"""
    global _TEXT
    if _TEXT is None: _TEXT = open(os.path.join(A.POP, 'pop_ad58.img'), 'rb').read()
    a = (d0 * 0x508 + d1 * 0x4f8 + off) & 0xffff
    y0, x0 = a // 160, (a % 160) // 8 * 16
    for j in range(16):
        wl, wr = struct.unpack_from('>HH', _TEXT, 0x16b8e - 0xad58 + 4 * j)
        for i in range(32):
            bit = ((wl << 16 | wr) >> (31 - i)) & 1
            if bit and 0 <= x0 + i < 320: pix[y0 + j][x0 + i] ^= 1

def to_png(pix, pal, path, scale=2):
    from PIL import Image
    cols = [A.st_rgb(c & 0x777) for c in pal]
    im = Image.new('RGB', (320, 200)); px = im.load()
    for y in range(200):
        for x in range(320): px[x, y] = cols[pix[y][x]]
    im.resize((320 * scale, 200 * scale), Image.NEAREST).save(path)

def compare(a, b, pal, path=None, region=None):
    x0, y0, x1, y1 = region or (0, 0, 320, 200)
    tot = (x1 - x0) * (y1 - y0); same = 0
    for y in range(y0, y1):
        for x in range(x0, x1): same += a[y][x] == b[y][x]
    if path:
        from PIL import Image
        cols = [A.st_rgb(c & 0x777) for c in pal]
        im = Image.new('RGB', (320, 200)); px = im.load()
        for y in range(200):
            for x in range(320):
                c = cols[a[y][x]]
                px[x, y] = tuple(v // 3 for v in c) if a[y][x] == b[y][x] else (255, 0, 255)
        im.resize((640, 400), Image.NEAREST).save(path)
    return same, tot

def main():
    snap, out = sys.argv[1], sys.argv[2]
    fr = Frame(snap)
    post = Mem(snap_ram(sys.argv[sys.argv.index('--post') + 1])) if '--post' in sys.argv else None
    bd = backdrop_from_files(fr) if '--files' in sys.argv else None     # no screen buffer read at all
    scr = fr.render(backdrop=bd, with_pointer='--pointer' in sys.argv, post=post)
    to_png(scr.p, fr.pal, out)
    rl = fr.ram_list(post)
    print('draw list: mine %d entries, RAM %d entries, identical=%s' % (len(fr.list), len(rl), fr.list == rl))
    if fr.list != rl: print('  mine', fr.list, '\n  ram ', rl)
    if '--truth' in sys.argv:
        tm = post or fr.m
        truth = A.screen(tm.r, tm.l(P_LOG))
        same, tot = compare(scr.p, truth, fr.pal, out.replace('.png', '_diff.png'))
        print('whole screen : %d/%d = %.3f%%' % (same, tot, 100.0 * same / tot))
        s2, t2 = compare(scr.p, truth, fr.pal, region=(96, 96, 320, 200))
        print('play-field box (96..319, 96..199): %d/%d = %.3f%%' % (s2, t2, 100.0 * s2 / t2))
        bd = backdrop_from_files(fr); ramb = A.screen(fr.m.r, fr.m.l(P_BACK))
        s3, t3 = compare(bd, ramb, fr.pal, out.replace('.png', '_backdrop_diff.png'))
        print('backdrop from QAZ.PIC+minimap vs RAM [$3afd8]: %d/%d = %.3f%%' % (s3, t3, 100.0 * s3 / t3))

if __name__ == '__main__':
    main()
