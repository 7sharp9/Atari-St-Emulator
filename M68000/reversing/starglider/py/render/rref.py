"""Python reference model of the Starglider 3D pipeline, written from the 68000 bodies (listing sg.asm) and gated against `callcap`.

Every routine takes a Mem (read-only RAM image + a write log) and the entry register values and returns the exit registers; the
writes go to mem.w (dict addr -> byte).  A6 = $5bf00 (globals).  All 16-bit arithmetic wraps exactly as the 68000's .w operations do;
`divs` leaves its destination unchanged on a quotient overflow (the game relies on that), `muls` is 16x16 -> 32.
"""
A6 = 0x5BF00


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def divs(dividend, divisor):
    """68000 DIVS.W: dividend s32, divisor s16 -> (overflow, quotient s16, remainder s16)"""
    dividend = s32(dividend)
    divisor = s16(divisor)
    q = abs(dividend) // abs(divisor)
    if (dividend < 0) != (divisor < 0):
        q = -q
    r = dividend - q * divisor
    if q > 32767 or q < -32768:
        return True, 0, 0
    return False, q, r


class Mem:
    def __init__(self, ram):
        self.ram = ram
        self.w = {}

    def b(self, a):
        a &= 0xFFFFFF
        return self.w.get(a, self.ram[a])

    def u16(self, a):
        return (self.b(a) << 8) | self.b(a + 1)

    def s16(self, a):
        return s16(self.u16(a))

    def u32(self, a):
        return (self.u16(a) << 16) | self.u16(a + 2)

    def wb(self, a, v):
        self.w[a & 0xFFFFFF] = v & 0xFF

    def ww(self, a, v):
        self.wb(a, v >> 8)
        self.wb(a + 1, v)

    def g(self, o):          # signed word at o(A6)
        return self.s16(A6 + o)

    def sg(self, o, v):      # set word at o(A6)
        self.ww(A6 + o, v)

    def changes(self):
        return {a: v for a, v in self.w.items() if self.ram[a] != v}


def mulq(a, b):
    """muls a,b ; asl.l #2 ; swap -> high word of (a*b<<2) as a signed word (Q14 product)"""
    return s16(((s16(a) * s16(b) << 2) & 0xFFFFFFFF) >> 16)


# ---- rotation matrices -------------------------------------------------------------------------------------------------

def trig(m, idx, step_bits):
    """sin/cos words for an angle: tables 108(A6)/112(A6); 12-bit angle (a & $fff)*2 bytes, or 9-bit angle (a & $1ff)*16 bytes"""
    S, C = m.u32(A6 + 108), m.u32(A6 + 112)
    return m.s16(S + idx), m.s16(C + idx)


def angle_index12(a):
    return ((a & 0xFFF) * 2) & 0xFFFF


def angle_index9(a):
    return (((a & 0x1FF)) << 4) & 0xFFFF


def build_matrix(m, base, s1, c1, s2, c2, s3, c3):
    """the 3x3 Q14 matrix written by $eca0 (base 342) and $ede4 (base 360), words base+0,2,..16 column-major"""
    D3, D4, D5 = s1, c1, s3
    D6 = mulq(D5, D3)
    D7 = mulq(c2, c3)
    D2 = mulq(s2, D6)
    m.sg(base + 0, s16(D7 + D2))
    D1 = mulq(mulq(D3, s2), c3)
    D2 = mulq(D5, c2)
    m.sg(base + 2, s16(D1 - D2))
    m.sg(base + 4, mulq(s2, D4))
    m.sg(base + 6, mulq(D4, D5))
    m.sg(base + 8, mulq(D4, c3))
    m.sg(base + 10, s16(-D3))
    D1 = mulq(D6, c2)
    D2 = mulq(s2, c3)
    m.sg(base + 12, s16(D1 - D2))
    D1 = mulq(D5, s2)
    D2 = mulq(D7, D3)
    m.sg(base + 14, s16(D1 + D2))
    m.sg(base + 16, mulq(D4, c2))


def ede4(m):
    """$ede4: view matrix 360..376(A6) from the sin/cos words 458..468(A6)"""
    build_matrix(m, 360, m.g(458), m.g(460), m.g(462), m.g(464), m.g(466), m.g(468))


def eca0(m):
    """$eca0: object matrix 342..358(A6) from the angle words 378/380/382(A6), recomputed only when they differ from the cache 384/386/388"""
    if (m.g(378), m.g(380), m.g(382)) == (m.g(384), m.g(386), m.g(388)):
        return
    m.sg(384, m.g(378)); m.sg(386, m.g(380)); m.sg(388, m.g(382))
    s1, c1 = trig(m, angle_index12(m.g(378)), 0)
    s2, c2 = trig(m, angle_index12(m.g(380)), 0)
    s3, c3 = trig(m, angle_index9(m.g(382)), 0)
    m.sg(458, s1); m.sg(460, c1); m.sg(462, s2); m.sg(464, c2); m.sg(466, s3); m.sg(468, c3)
    build_matrix(m, 342, s1, c1, s2, c2, s3, c3)


def matvec(m, base, D1, D2, D3):
    """$ec1e (base 360) / first half of $eb8a (base 342): (D1,D2,D3) * matrix; also leaves x,y in 398/400(A6)"""
    out = []
    for r in range(3):
        a = mulq(m.g(base + 2 * r), D1)
        b = mulq(m.g(base + 6 + 2 * r), D2)
        c = mulq(m.g(base + 12 + 2 * r), D3)
        out.append(s16(s16(a + b) + c))
    return out


def ec1e(m, D1, D2, D3):
    x, y, z = matvec(m, 360, D1, D2, D3)
    m.sg(398, x); m.sg(400, y)
    return x, y, z


def eb8a(m, D1, D2, D3):
    """$eb8a: model -> view-space point: object matrix, >>4, + object offset 404/406/408(A6)"""
    x, y, z = matvec(m, 342, D1, D2, D3)
    m.sg(398, x); m.sg(400, y)
    x, y, z = x >> 4, y >> 4, z >> 4
    return s16(x + m.g(404)), s16(y + m.g(406)), s16(z + m.g(408))


def eeac(m, D1, D4, D5, A0, A1, A2):
    """$eeac: transformed-vertex cache.  A2 flag bytes (index D1), A1 model vertices, A0 cache rows (8 bytes per vertex, offset D4)"""
    idx = s16(D1)
    fl = m.b(A2 + idx)
    if 0 < fl < 0x80:                      # tst.b ; ble: only a positive flag is a cache hit
        return m.s16(A0 + D4), m.s16(A0 + D4 + 2), m.s16(A0 + D4 + 4)
    m.wb(A2 + idx, 1)
    x, y, z = m.s16(A1 + D4), m.s16(A1 + D4 + 2), m.s16(A1 + D4 + 4)
    m.sg(84, D4); m.sg(88, D5)
    a, b, c = matvec(m, 342, x, y, z)
    m.sg(398, a); m.sg(400, b)
    a, b, c = s16(a >> 4), s16(b >> 4), s16(c >> 4)
    a, b, c = s16(a + m.g(404)), s16(b + m.g(406)), s16(c + m.g(408))
    m.ww(A0 + D4, a); m.ww(A0 + D4 + 2, b); m.ww(A0 + D4 + 4, c)
    return a, b, c


# ---- clipping and projection ----------------------------------------------------------------------------------------------

def clip_near(m, D1, D2, D3, D4, D5, D6):
    """$14f00: clip the segment against the near plane z = 2 only (the x/y frustum outcode code at $14f06/$14f34 is skipped by a
    `bra` and never reached).  Returns (D0, D1..D6) with D0 = 0 accept, -1 reject; writes the outcode bytes 698/699(A6)."""
    D1, D2, D3, D4, D5, D6 = (s16(v) for v in (D1, D2, D3, D4, D5, D6))
    while True:
        c1 = 0x10 if D3 < 2 else 0
        c2 = 0x10 if D6 < 2 else 0
        m.wb(A6 + 698, c1); m.wb(A6 + 699, c2)
        if (c1 | c2) == 0:
            return 0, D1, D2, D3, D4, D5, D6
        if c1 & c2:
            return -1, D1, D2, D3, D4, D5, D6
        if c1 & 0x10:
            D0 = s32(((2 - D3) & 0xFFFF) << 16)
            D7 = s16(D6 - D3)
            ov, q, r = divs(D0, D7)
            if not ov:
                D0 = ((r & 0xFFFF) << 16) | (q & 0xFFFF)
            t = s16(D0)
            D7 = s16(D4 - D1)
            P = (D7 * t << 1) & 0xFFFFFFFF
            D1 = s16(D1 + s16(P >> 16))
            D7 = s16(D5 - D2)
            P = (D7 * t << 1) & 0xFFFFFFFF
            D2 = s16(D2 + s16(P >> 16))
            D3 = 2
        else:
            D1, D4 = D4, D1
            D2, D5 = D5, D2
            D3, D6 = D6, D3


def clip2d(m, D4, D5, D6, D7):
    """$14cfc: Cohen-Sutherland against the window 326(xmin) 328(xmax) 330(ymin) 332(ymax)(A6).  Returns (D0, D4, D5, D6, D7);
    the endpoints come back swapped when the second point was the one clipped."""
    xmin, xmax, ymin, ymax = m.g(326), m.g(328), m.g(330), m.g(332)
    D4, D5, D6, D7 = (s16(v) for v in (D4, D5, D6, D7))

    def code(x, y):
        c = 0
        if x > xmax: c |= 8
        if y > ymax: c |= 4
        if x < xmin: c |= 2
        if y < ymin: c |= 1
        return c

    def interp(a, b, c, d, e):
        """D2 = (a - b) * (c - d) / (e - b) with muls and divs.w; on overflow D2 keeps the 32-bit product (low word used)"""
        D2 = s16(a - b)
        D3 = s16(c - d)
        P = D2 * D3
        D3b = s16(e - b)
        ov, q, r = divs(P, D3b)
        return s16(P) if ov else q

    guard = 0
    while True:
        guard += 1
        if guard > 3000:
            raise RuntimeError('clip2d loop')
        D0 = code(D4, D5)
        D1 = code(D6, D7)
        if (D0 | D1) == 0:
            return 0, D4, D5, D6, D7
        if D0 & D1:
            return -1, D4, D5, D6, D7
        if D4 == D6:
            D5 = ymin if D5 < ymin else (ymax if D5 > ymax else D5)
            D7 = ymin if D7 < ymin else (ymax if D7 > ymax else D7)
            continue
        if D5 == D7:
            D4 = xmin if D4 < xmin else (xmax if D4 > xmax else D4)
            D6 = xmin if D6 < xmin else (xmax if D6 > xmax else D6)
            continue
        if D0 == 0:
            if D1 == 0:
                continue
            D4, D6 = D6, D4
            D5, D7 = D7, D5
            D0, D1 = D1, D0
        # clip point 1 (D4,D5) by its first set bit in the order bit0, bit1, bit2, bit3
        if D0 & 1:
            D4 = s16(D4 + interp(ymin, D5, D6, D4, D7)); D5 = ymin
        elif D0 & 2:
            D5 = s16(D5 + interp(xmin, D4, D7, D5, D6)); D4 = xmin
        elif D0 & 4:
            D4 = s16(D4 + interp(ymax, D5, D6, D4, D7)); D5 = ymax
        elif D0 & 8:
            D5 = s16(D5 + interp(xmax, D4, D7, D5, D6)); D4 = xmax


# ---- the line drawer ($13cb4, low resolution, colour 520(A6)) ---------------------------------------------------------------

def draw_line(m, D4, D5, D6, D7, colour=None, screen=None, quirk10=True):
    """$13cb4: Bresenham with OR into the bit planes selected by the colour (plane k <- bit k of 520(A6)); 160-byte rows, 8-byte word groups
    (interleaved planes).  x ascending (swap), y step +-160.  The colour-10 shallow-slope slot jumps into the steep loop (quirk10)."""
    D4, D5, D6, D7 = (v & 0xFFFF for v in (D4, D5, D6, D7))
    col = (m.g(520) & 0xF) if colour is None else colour
    base = m.u32(A6 + 0) if screen is None else screen
    if D6 < D4:
        D4, D6 = D6, D4
        D5, D7 = D7, D5
    D2 = (D6 - D4) & 0xFFFF
    D3 = (D7 - D5) & 0xFFFF
    stride = 160
    if D5 > D7:
        stride = -160
        D3 = (-D3) & 0xFFFF
    t = (D5 << 5) & 0xFFFF
    t2 = (t << 2) & 0xFFFF
    A0 = base + s16(t) + s16(t2)          # y*160 = y*32 + y*128 (word-wise, sign-extended by adda.w)
    A0 += ((D4 >> 1) & 0xF8)
    offs = [2 * k for k in range(4) if (col >> k) & 1]
    shallow = D2 > D3
    if col == 10 and shallow and quirk10:
        shallow = False
    pix = []

    def put(a, mask):
        for o in offs:
            pix.append((a + o, mask))

    def ror():
        nonlocal D0
        carry = D0 & 1
        D0 = (D0 >> 1) | (carry << 15)
        return carry

    A0v = A0
    D0 = 1 << ((~D4) & 0xF)
    if not shallow:
        e = D3
        for _ in range(D3 + 1):
            put(A0v, D0)
            before = e
            e = (e - D2) & 0xFFFF
            if before <= D2:                 # borrow or zero: bls
                e = (e + D3) & 0xFFFF
                if ror():
                    A0v += 8
            A0v += stride
    else:
        e = D2
        for _ in range(D2 + 1):
            put(A0v, D0)
            before = e
            e = (e - D3) & 0xFFFF
            if before <= D3:
                e = (e + D2) & 0xFFFF
                A0v += stride
            if ror():
                A0v += 8
    for a, mask in pix:
        a &= 0xFFFFFF
        cur = m.u16(a)
        m.ww(a, cur | mask)
    return pix


def f8f2(m, D1, D2, D3, D4, D5, D6):
    """$f8f2: one edge: near clip, perspective divide, window clip, line draw.  D1..D3 and D4..D6 are the two endpoints in view space."""
    D0, D1, D2, D3, D4, D5, D6 = clip_near(m, D1, D2, D3, D4, D5, D6)
    if D0 != 0:
        return None
    sh = m.g(530)
    r = {}
    X1, Y1, X2, Y2 = (s32(v << sh) for v in (D1, D2, D4, D5))
    for name, val, z in (('x1', X1, D3), ('y1', Y1, D3), ('x2', X2, D6), ('y2', Y2, D6)):
        ov, q, rem = divs(val, z)
        r[name] = s16(val) if ov else q
    D4 = s16(r['x1'] + m.g(508)); D5 = s16(r['y1'] + m.g(510))
    D6 = s16(r['x2'] + m.g(508)); D7 = s16(r['y2'] + m.g(510))
    D0, D4, D5, D6, D7 = clip2d(m, D4, D5, D6, D7)
    if D0 != 0:
        return None
    return draw_line(m, D4, D5, D6, D7)


# ---- one object: $f6a8 ---------------------------------------------------------------------------------------------------------

def mul32(a, b):
    return s32(s16(a) * s16(b))


def f6a8(m, D0, D5=0):
    """$f6a8: draw the model of object type D0 with the angles in 378/380/382(A6) and the view-space centre in 404/406/408(A6).
    Faces are culled by the sign of (e1 x e2) . P2 on the cached view-space vertices ($eeac), the surviving faces flag their vertices (1800(A6))
    and edges (1930(A6)); flagged vertices are transformed ($eb8a) into the cache 760(A6) and each flagged edge goes through $f8f2 in the colour
    of the LAST face visited (520(A6))."""
    D0 &= 0xFFFF
    mi = m.u16(0x15802 + 2 * D0)
    hdr = 0x15ada + ((mi << 4) & 0xFFFF)
    nv, ne, nf = m.u16(hdr), m.u16(hdr + 2), m.u16(hdr + 4)
    m.sg(474, nv); m.sg(476, ne); m.sg(478, nf)
    base = m.u32(A6 + 120)
    verts, edges, faces = base + m.u16(hdr + 6), base + m.u16(hdr + 8), base + m.u16(hdr + 10)
    for off, v in ((16, verts), (20, edges), (24, faces), (28, base + m.u16(hdr + 12))):
        m.ww(A6 + off, v >> 16); m.ww(A6 + off + 2, v)
    m.sg(480, m.u16(hdr + 14))
    eca0(m)
    FE, FV, CACHE = A6 + 1930, A6 + 1800, A6 + 760
    for i in range(ne): m.wb(FE + i, 0)
    for i in range(nv): m.wb(FV + i, 0)
    if nf:
        A4 = faces
        for _ in range(nf):
            m.sg(520, m.s16(A4)); m.sg(546, m.s16(A4 + 2)); m.sg(548, m.s16(A4 + 4)); m.sg(554, m.s16(A4 + 6))
            m.sg(550, m.s16(A4 + 14)); m.sg(552, m.s16(A4 + 16))
            A4 += 18
            nvx, nex = m.g(550), m.g(552)
            draw = m.b(A6 + 701) != 0 or m.g(554) < 0
            if not draw:
                pts = []
                for k in range(3):
                    idx = m.u16(A4 + 2 * k)
                    x, y, z = eeac(m, idx, (idx << 3) & 0xFFFF, D5, CACHE, verts, FV)
                    pts.append((s16(x >> 2), s16(y >> 2), s16(z >> 2)))
                    if k == 0:
                        D5 = (D5 & 0xFFFF0000) | (pts[0][0] & 0xFFFF)      # move.w D1,D5 after the first vertex
                P0, P1, P2 = pts
                e1 = tuple(s16(P1[i] - P0[i]) for i in range(3))
                m.sg(492, e1[0]); m.sg(494, e1[1]); m.sg(496, e1[2])
                m.sg(132, P2[0]); m.sg(136, P2[1]); m.sg(140, P2[2])
                D1, D2, D3 = (s16(P2[i] - P0[i]) for i in range(3))
                n0 = s32(mul32(D3, e1[1]) - mul32(D2, e1[2]))
                n1 = s32(mul32(D1, e1[2]) - mul32(D3, e1[0]))
                n2 = s32(mul32(D2, e1[0]) - mul32(D1, e1[1]))
                for o, v in ((32, n0), (36, n1), (40, n2)):
                    m.ww(A6 + o, (v >> 16) & 0xFFFF); m.ww(A6 + o + 2, v & 0xFFFF)
                dot = s32(s32(n0 * P2[0]) + s32(n1 * P2[1]))
                dot = s32(dot + s32(n2 * P2[2]))
                D5 = dot & 0xFFFFFFFF                                 # the running dot product is left in D5
                draw = dot < 0
            if draw:
                for k in range(nvx):
                    m.wb(FV + m.u16(A4 + 2 * k), 0xFF)
                for k in range(nex):
                    m.wb(FE + m.u16(A4 + 2 * (nvx + k)), 0xFF)
                A4 += 2 * (nvx + nex)
            else:
                A4 += 2 * (nvx + nex)
    A3 = CACHE
    for i in range(nv):
        if m.b(FV + i) & 0x80:
            x, y, z = eb8a(m, m.s16(verts + 8 * i), m.s16(verts + 8 * i + 2), m.s16(verts + 8 * i + 4))
            m.wb(FV + i, 1)
            m.ww(A3 + 8 * i, x); m.ww(A3 + 8 * i + 2, y); m.ww(A3 + 8 * i + 4, z)
    if ne:
        for i in range(ne):
            if m.b(FE + i) != 0:
                a = CACHE + m.u16(edges + 4 * i)
                b = CACHE + m.u16(edges + 4 * i + 2)
                f8f2(m, m.s16(a), m.s16(a + 2), m.s16(a + 4), m.s16(b), m.s16(b + 2), m.s16(b + 4))


# ---- point sprite / dust ($142f4 -> vector 52(A6) = $142fa in low resolution) -------------------------------------------------

def plot_dot(m, D1, D2, D3):
    """$142fa: one star/dust/spark pixel at (D1,D2) in the planes named by the byte offsets 522..528(A6); the size grows with the
    nearness D3: < $700 two wide, < $1000 two tall (and the 8-byte-away neighbour word when the pair straddles a word boundary)."""
    D1 &= 0xFFFF; D2 &= 0xFFFF; D3 &= 0xFFFF
    t = (D2 << 5) & 0xFFFF
    A0 = m.u32(A6) + s16(t) + s16((t << 2) & 0xFFFF) + ((D1 >> 1) & 0xF8)
    offs = [m.g(522), m.g(524), m.g(526), m.g(528)]
    D1 = (~D1) & 0xF
    D2 = 1 << D1
    if D3 < 0x700:
        D1 -= 1
        if D1 >= 0:
            D2 |= 1 << D1
    def orw(a, v):
        m.ww(a, m.u16(a) | v)
    for o in offs: orw(A0 + o, D2)
    if D3 < 0x1000:
        for o in offs: orw(A0 + o + 160, D2)
        if D1 < 0:
            for o in offs: orw(A0 + o + 8, 0x8000)
            for o in offs: orw(A0 + o + 168, 0x8000)


# ---- random numbers and the ground-dust field ----------------------------------------------------------------------------------

def rng1(m):
    """$f21e: 32-bit shift/xor generator in 100(A6) plus the word at $c3ce and the long at 92(A6); returns the high word."""
    D0 = m.u32(A6 + 100)
    c = D0 >> 31
    D0 = (D0 << 1) & 0xFFFFFFFF
    if c or D0 == 0:                       # bhi not taken: carry set or result zero
        D0 ^= 0x1D872B41
    D0 = (D0 & 0xFFFF0000) | ((D0 + m.u16(0xC3CE)) & 0xFFFF)
    D0 = (D0 + m.u32(A6 + 92)) & 0xFFFFFFFF
    m.ww(A6 + 100, D0 >> 16); m.ww(A6 + 102, D0)
    return ((D0 >> 16) | (D0 << 16)) & 0xFFFFFFFF      # swap


def rng2(m, D0):
    """$f23e: byte lagged-add generator on 92..97(A6); D0.w is an input (the caller's leftover) that is added to the word at 92(A6);
    returns D0.w = (538, 539)(A6), the two new bytes."""
    D0 &= 0xFFFF
    D0 = (D0 + m.u16(0xC3CE)) & 0xFFFF
    w = m.u16(A6 + 92) + D0
    X = w >> 16
    m.ww(A6 + 92, w)
    def addx(a, b):
        nonlocal X
        t = a + b + X
        X = t >> 8
        return t & 0xFF
    out = []
    for _ in range(2):
        d = m.b(A6 + 92)
        d = addx(d, m.b(A6 + 96))
        d = addx(d, m.b(A6 + 97))
        m.wb(A6 + 92, d)
        m.wb(A6 + 97, m.b(A6 + 96)); m.wb(A6 + 96, m.b(A6 + 95)); m.wb(A6 + 95, m.b(A6 + 94)); m.wb(A6 + 94, m.b(A6 + 93)); m.wb(A6 + 93, m.b(A6 + 92))
        m.wb(A6 + 538 + len(out), d)
        out.append(d)
    return (out[0] << 8) | out[1]


def dust(m, D0):
    """$f336: 40 ground points (x, z words at 2060(A6), y = 0) re-based on the camera, rotated by the view matrix, kept when z > 2 and
    |x|,|y| <= 2z, projected (x << 530(A6)) / z + (508, 510) and plotted by $142f4 when strictly inside the window; the others are respawned
    at a random place in front of the camera ($f3d4: two $f23e draws, rotated by the yaw 316(A6), or by 626(A6) about 618/622 in the second view)."""
    A0 = 0x13B02
    for k in range(4):
        m.sg(522 + 2 * k, m.s16(A0 + 2 * k))
    A4 = A6 + 2060
    D0 &= 0xFFFF
    for _ in range(0x28):
        D1 = m.s16(A4); D3 = m.s16(A4 + 2); A4 += 4
        D2 = 0
        D1 = s16(D1 - m.g(302)); D2 = s16(D2 - m.g(304)); D3 = s16(D3 - m.g(306))
        D1, D2, D3 = ec1e(m, D1, D2, D3)
        respawn = True
        if D3 > 2:
            m.sg(140, D3)
            D3b = s16(D3 * 2); D4 = s16(-D3b)
            if not (D1 < D4 or D1 > D3b or D2 < D4 or D2 > D3b):
                respawn = False
                D3 = m.g(140)
                D0 = m.g(530)
                X, Y = s32(D1 << D0), s32(D2 << D0)
                ov, q, r = divs(X, D3); D1 = s16(X) if ov else q
                ov, q, r = divs(Y, D3); D2 = s16(Y) if ov else q
                D1 = s16(D1 + m.g(508)); D2 = s16(D2 + m.g(510))
                if D1 > m.g(326) and D1 < m.g(328) and D2 > m.g(330) and D2 < m.g(332):
                    plot_dot(m, D1, D2, m.g(140))
        if respawn:
            ang, px, pz = (316, 302, 306) if m.b(A6 + 712) == 0 else (626, 618, 622)
            S, C = m.u32(A6 + 108), m.u32(A6 + 112)
            i = angle_index12(m.g(ang))
            m.sg(462, m.s16(S + i)); m.sg(464, m.s16(C + i))
            D0 = rng2(m, D0) & 0x1FFF
            D3 = D0
            D0 = rng2(m, D0)
            D0 = s16((D0 & 0x1FFF) - 0x1000)
            D1 = D0
            D4 = s16(mulq(D1, m.g(464)) + mulq(D3, m.g(462)))
            D5 = s16(mulq(D3, m.g(464)) - mulq(D1, m.g(462)))
            D4 = s16(D4 + m.g(px)); D5 = s16(D5 + m.g(pz))
            m.ww(A4 - 4, D4); m.ww(A4 - 2, D5)


# ---- bearing to an object ($12f1c) --------------------------------------------------------------------------------------------

def bearing(m, A0):
    """$12f1c: 12-bit bearing (4096 = turn) of the object record at A0 (world x at 4(A0), z at 8(A0)) from the camera 302/306(A6), by an
    arctangent table lookup (512 words at $1e0f4 for |dz| >= |dx|, at $1e4f6 otherwise).  Returns D1 (low word); division by dx = 0 traps."""
    D0 = s16(m.s16(A0 + 4) - m.g(302))
    D1 = s16(m.s16(A0 + 8) - m.g(306))
    D5 = 0xC00
    if D0 < 0:
        D5 = s16(D5 - 0x800)
    D2 = s16(-D0) if D0 < 0 else D0
    D3 = s16(-D1) if D1 < 0 else D1
    if D3 >= D2:
        A1 = 0x1E0F4
        ov, q, r = divs(D1, D0)
        D1 = s16(D1) if ov else q
        if D1 >= 0xFF: D1 = 0x400; look = False
        elif D1 >= -255: look = True
        else: D1 = s16(0xFC00); look = False
    else:
        A1 = 0x1E4F6
        X = s32(D1 << 8)
        ov, q, r = divs(X, D0)
        D1 = s16(X) if ov else q
        if D1 >= 0xFF: D1 = 0x200; look = False
        elif D1 >= -255: look = True
        else: D1 = s16(0xFE00); look = False
    if look:
        D1 = ((D1 + 0xFF) & 0x1FF) * 2
        D1 = m.s16(A1 + D1)
    D5 = s16(D5 - D1)
    return s16(-D5)


def f938(m, D0):
    """$f938: draw object type D0 as debris (records flagged by `st 36(A0)` at $12612..$12950): all vertices are transformed ($eb8a) with no culling,
    then every face's edges are drawn pushed along the face normal (cross product of two face edges, scaled by the age 610(A6)) and dropped by the
    table at $fb34[610]; a face whose pushed height 36(A6) is not above 406(A6) is skipped."""
    D0 &= 0xFFFF
    mi = m.u16(0x15802 + 2 * D0)
    hdr = 0x15ada + ((mi << 4) & 0xFFFF)
    nv, ne, nf = m.u16(hdr), m.u16(hdr + 2), m.u16(hdr + 4)
    m.sg(474, nv); m.sg(476, ne); m.sg(478, nf)
    base = m.u32(A6 + 120)
    verts, edges, faces = base + m.u16(hdr + 6), base + m.u16(hdr + 8), base + m.u16(hdr + 10)
    for off, v in ((16, verts), (20, edges), (24, faces), (28, base + m.u16(hdr + 12))):
        m.ww(A6 + off, v >> 16); m.ww(A6 + off + 2, v)
    m.sg(480, m.u16(hdr + 14))
    eca0(m)
    if nv == 0:
        return
    CACHE = A6 + 760
    for i in range(nv):
        x, y, z = eb8a(m, m.s16(verts + 8 * i), m.s16(verts + 8 * i + 2), m.s16(verts + 8 * i + 4))
        m.ww(CACHE + 8 * i, x); m.ww(CACHE + 8 * i + 2, y); m.ww(CACHE + 8 * i + 4, z)
    if nf == 0:
        return
    A4 = faces
    age = m.g(610)
    for _ in range(nf):
        m.sg(520, m.s16(A4)); m.sg(546, m.s16(A4 + 2)); m.sg(548, m.s16(A4 + 4)); m.sg(554, m.s16(A4 + 6))
        m.sg(550, m.s16(A4 + 14)); m.sg(552, m.s16(A4 + 16))
        A4 += 18
        nvx, nex = m.g(550), m.g(552)
        def P(k):
            o = CACHE + ((m.u16(A4 + 2 * k) << 3) & 0xFFFF)
            return m.s16(o), m.s16(o + 2), m.s16(o + 4)
        p0 = P(0); p1 = P(1); p2 = P(2)
        e1 = tuple(s16(p1[i] - p0[i]) for i in range(3))
        m.sg(492, e1[0]); m.sg(494, e1[1]); m.sg(496, e1[2])
        D1, D2, D3 = (s16(p2[i] - p0[i]) for i in range(3))
        n0 = s16(s32(mul32(D3, e1[1]) - mul32(D2, e1[2])) >> 5) if False else (s32(mul32(D3, e1[1]) - mul32(D2, e1[2])) >> 5)
        v0 = s32(n0 * age)
        m.sg(32, v0)
        n1 = s32(mul32(D1, e1[2]) - mul32(D3, e1[0])) >> 6
        v1 = s32(n1 * age)
        w = s16(s16(v1) + m.s16(0xFB34 + ((age * 2) & 0xFFFF)))
        m.sg(36, w)
        if s16(w - m.g(406)) >= 0:
            A4 += 2 * (nvx + nex)
            continue
        n2 = s32(mul32(D2, e1[0]) - mul32(D1, e1[1])) >> 5
        m.sg(40, s32(n2 * age))
        A4 += 2 * nvx
        for _ in range(nex):
            e = edges + ((m.u16(A4) << 2) & 0xFFFF)
            A4 += 2
            a = CACHE + m.u16(e); b = CACHE + m.u16(e + 2)
            f8f2(m, s16(m.s16(a) + m.g(32)), s16(m.s16(a + 2) + m.g(36)), s16(m.s16(a + 4) + m.g(40)),
                 s16(m.s16(b) + m.g(32)), s16(m.s16(b + 2) + m.g(36)), s16(m.s16(b + 4) + m.g(40)))
