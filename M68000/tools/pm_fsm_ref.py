"""A from-disassembly reconstruction of PowerMonger's per-entity iterator
$14b62 (the entity FSM sim tick), integer-exact, no fudge.  Differential-tested
against the real 68000 via the `callcap 14b62` REPL primitive.

Covered handlers (each proven vs the real CPU on its own pass - see the pass
count / N-of-N in reversing/powermonger/ai.md and the tooling memo):

    $12  $14ff8  halt / cool-down                              93rd  675/675
    $68  $16048  formation follower  (upkeep only)             93rd
    $8a  $161b2  garrison            (upkeep only)             93rd
    $06  $14d32  walk until blocked                            94th  1335/1335
    $08  $14d7c  escort / orbit                                94th
    $0e  $14e70  patrol spline                                 94th
    $10  $14f08  advance / chase                               94th
    $32  $1533c  melee  (+ $56a6 / $5590 / $30fe leaves)       95th  413/413
    $7c  $157e6  settlement heartbeat  (+ $16848 / $163b8)     96th/97th 85/85, 99/99

plus the shared machinery they touch: the prologue ($14b72..$14bb0 - active
gate, anim-frame advance, D6/D7 load), $5c80 per-entity upkeep (morale creep;
the $5bd2 wear/removal path is asserted OFF), the epilogues $161c4 (clamp +
$1648e terrain veto + on-land $163ea relink) / $16202 (clamp + relink, no veto)
/ $1622c (straight to next record), $1648e terrain sample, $163ea/$16778 bucket
relink, and the movement leaves $164bc step-toward / $14262 heading / $12d56
rotate.

Regroup / group-teardown paths ($3c08 / $4bc8 / $2776 / $1b8c / $5cde / $550e /
$5c2c / $15302 / $1518a) are ASSERTED OFF - reconstruct() raises AssertionError
if a state ever reaches one, so a corpus mistake cannot pass silently.

Transcribed line-for-line + raw-byte-verified from the disassembly in
scratchpad/pm9{3,4,5,6}/disasm/ (base 0).  Records whose mode is not covered
MUST have owner byte (offset 5) == 0 in the state handed in - the diff harness
zeroes them.

USAGE: call init_tables(ram_image) once (any PowerMonger .ram - the three
lookup tables are constant program data) before the first reconstruct().

History: graduated to tools/ on the 98th pass from scratchpad/pm97/fsm_ref.py
(itself the pm93->94->95->96->97 line, copied forward each pass).  The only
change on graduation: the $13f8a / $14360 / $168ee lookup tables are now sliced
from a RAM image via init_tables() instead of loaded from committed .bin files.
"""
import struct
import struct

OBJ = 0x51b66
BUCKETS = 0x47970
TERRAIN = 0x438ee
SURVIV = 0x5ccc
MASTER_TICK_LO = 0x4bb40
TICK_RNG = 0x57fec
REC = 50
END = 0x57f66            # cmpa.l #$57f66,A1  -> loop terminator


def s8(v):  v &= 0xff;  return v - 0x100 if v >= 0x80 else v
def s16(v): v &= 0xffff; return v - 0x10000 if v >= 0x8000 else v
def u16(v): return v & 0xffff


class Mem:
    """Byte-addressable view over the 1 MB RAM image, with the exact
    read/write widths the 68k uses."""
    def __init__(self, ram):
        self.r = bytearray(ram)

    def bu(self, a): return self.r[a]
    def bs(self, a): return s8(self.r[a])
    def wu(self, a): return struct.unpack_from('>H', self.r, a)[0]
    def ws(self, a): return struct.unpack_from('>h', self.r, a)[0]
    def lu(self, a): return struct.unpack_from('>I', self.r, a)[0]

    def wb(self, a, v): self.r[a] = v & 0xff
    def ww(self, a, v): struct.pack_into('>H', self.r, a, v & 0xffff)
    def wl(self, a, v): struct.pack_into('>I', self.r, a, v & 0xffffffff)


# ---------------------------------------------------------------- $1648e
def terrain_sample(m, D6, D7):
    """$1648e: return the terrain byte at world (D6,D7). Caller tests == 0."""
    D5 = u16(D6) >> 6                       # move.w D6,D5 ; lsr.w #6,D5
    D0 = (D7 & 0xff00) | (D5 & 0xff)        # move.w D7,D0 ; move.b D5,D0
    D0 = (D0 & 0xffff) >> 2                 # lsr.w #2,D0
    A4 = (TERRAIN + s16(D0)) & 0xfffff      # adda.w D0,A4
    if m.bs(A4 + 8257) < 0:                 # tst.b 8257(A4) ; bpl $164b2
        lo = (D6 & 0xff) + (D7 & 0xff)      # move.b D6,D0 ; add.b D7,D0
        if lo > 0xff:                       # bcc $164b6  (carry -> take type plane)
            return m.bu(A4)                 # $164ac  move.b 0(A4),D0
        return m.bu((A4 - 8257) & 0xfffff)  # $164b6  move.b -8257(A4),D0
    else:
        if (D6 & 0xff) > (D7 & 0xff):       # cmp.b D7,D6 ; bhi $164ac
            return m.bu(A4)
        return m.bu((A4 - 8257) & 0xfffff)


# ---------------------------------------------------------------- $16778
def bucket_unlink(m, cell, rec_off):
    """$16778: remove object at byte-offset rec_off from cell chain `cell`
    (word index into $47970)."""
    A0 = BUCKETS + cell * 2
    head = m.wu(A0)
    if head == 0:
        m.wl(OBJ + rec_off, 0)
        return
    if head == rec_off:                     # unlink at head
        nxt = m.wu(OBJ + head + 0)
        m.ww(A0, nxt)
        if nxt != 0:
            m.ww(OBJ + nxt + 2, 0)
        m.wl(OBJ + rec_off, 0)
        return
    # walk
    prev = head
    while True:
        nxt = m.wu(OBJ + prev + 0)
        if nxt == 0:
            break
        if nxt == rec_off:
            follow = m.wu(OBJ + nxt + 0)
            m.ww(OBJ + prev + 0, follow)
            if follow != 0:
                m.ww(OBJ + follow + 2, prev)
            break
        prev = nxt
    m.wl(OBJ + rec_off, 0)


# ---------------------------------------------------------------- $163ea
def relink(m, A1, D6, D7):
    """$163ea: write the new position back and, if the screen cell changed,
    move the record between $47970 buckets."""
    rec_off = A1 - OBJ
    D4 = (m.wu(A1 + 10) & 0xff00) >> 2      # OLD cell (pre-writeback stored pos)
    D4 = (D4 + m.bu(A1 + 8)) & 0xffff       # add.b 8(A1),D4
    m.ww(A1 + 8, D6)                        # move.w D6,8(A1)
    m.ww(A1 + 10, D7)                       # move.w D7,10(A1)
    D7c = (D7 & 0xff00) >> 2                # NEW cell
    D7c = (D7c + m.bu(A1 + 8)) & 0xffff     # add.b 8(A1),D7  (8(A1) == D6 low now)
    if D4 == D7c:                           # cmp.w D7,D4 ; beq $1648c
        return
    # -- unlink from old bucket --
    D5 = m.wu(A1 + 2)                       # bucket_prev
    if D5 != 0:
        m.ww(OBJ + D5 + 0, m.wu(A1 + 0))    # prev.next = self.next
        nxt = m.wu(A1 + 0)
        if nxt != 0:
            m.ww(OBJ + nxt + 2, D5)         # next.prev = prev
    else:
        cell = (D4 * 2) & 0xffff            # add.w D4,D4
        nxt = m.wu(A1 + 0)
        m.ww(BUCKETS + cell, nxt)           # head = self.next
        if nxt != 0:
            m.ww(OBJ + nxt + 2, 0)          # next.prev = 0
    m.wl(A1 + 0, 0)                         # clr.l 0(A1)
    # -- link at head of new bucket --
    cell = (D7c * 2) & 0xffff               # add.w D7,D7
    old_head = m.wu(BUCKETS + cell)
    if old_head != 0:
        m.ww(A1 + 0, old_head)
        m.ww(OBJ + old_head + 2, rec_off)
    m.ww(BUCKETS + cell, rec_off)


# ---------------------------------------------------------------- $5c80
def upkeep(m, A1, assert_no_wear=True):
    """$5c80: morale creep toward the flags-indexed survivability cap.
    Asserts the wear/removal path stays off (anim_wear < $3c for the corpus)."""
    D0 = m.bu(A1 + 7) & 0x1f                # flags & 0x1f
    D0 = s8(m.bu(SURVIV + D0)) & 0xffff     # move.b 66(PC..) -> signed byte into D0.w
    D1 = s8(m.bu(A1 + 14)) - 0x3c           # anim_wear - $3c   (byte op, then bmi)
    D1 &= 0xff
    if D1 < 0x80:                           # bmi $5ca2  -> not taken means (wear-3c) >= 0
        if assert_no_wear:
            raise AssertionError("wear path: anim_wear >= 0x3c at rec %d" % ((A1 - OBJ) // REC))
        D1 = (D1 << 2) & 0xffff
        D0 = (D0 - D1) & 0xffff
        # (bpl $5ca2) ; else jsr $5bd2 - out of scope
    morale = m.bs(A1 + 45)                  # move.b 45(A1),D1 ; bmi
    if morale < 0:
        m.wb(A1 + 45, 0)                    # $5cc4 clr.b 45(A1)
        return
    D1w = morale & 0xffff                   # ext.w D1
    if s16(D0) > s16(D1w):                  # cmp.w D1,D0 ; ble $5cc0 (no change)
        add = m.wu(TICK_RNG) & 1
        m.wb(A1 + 45, (m.bu(A1 + 45) + add) & 0xff)


# ---------------------------------------------------------------- $161c4
def epilogue_161c4(m, A1, D6, D7):
    """clamp D6/D7, terrain-veto, on-land write back + relink."""
    if s16(D6) < 0:
        D6 = 0
    elif s16(D6) >= 0x4000:
        D6 = 0x3fff
    if s16(D7) < 0:
        D7 = (-s16(D7)) & 0xffff            # neg.w D7
        if D7 > 0x1f40:                     # cmp.w #$1f40,D7 ; bhi -> $7fff
            D7 = 0x7fff
        else:
            D7 = 0
    # (D7 >= 0: no upper clamp - matches $161d6 bpl $161ea)
    t = terrain_sample(m, D6, D7)
    if t != 0:                              # land
        m.wb(A1 + 7, m.bu(A1 + 7) & ~0x20)  # bclr #5,7(A1)
        relink(m, A1, D6, D7)               # $16228 bsr $163ea
    else:                                  # water: revert to mode 0, discard pos
        m.wb(A1 + 31, 0)


# ================================================================ 94th pass:
# the movement modes  $06 / $08 / $0e / $10  and their leaves
# $164bc step_toward, $14262 heading, $12d56 rotate, $16202 epilogue.
# Transcribed line-for-line from the disassembly in scratchpad/pm94/disasm/
# (raw-byte-verified).
# ================================================================
# The three lookup tables below are constant PowerMonger program data (in the
# code/data segment of the loaded binary), byte-identical across every snapshot.
# init_tables() slices them from a RAM image; verified equal across
# pm78_settle / pm73_fight / pm88_f1 / pm97_map0 on graduation.
TBL_HEADING = 0x14360      # 2048 B: 1024 shift ($14360) + 1024 dir ($14760)
TBL_TRIG    = 0x13f8a      # 640 B = 320 s16 words
TBL_SPLINE  = 0x168ee      # 256 B

_HTBL = SHIFT_TBL = DIR_TBL = _TRIG = SPLINE = None


def init_tables(ram):
    """Populate the module-level lookup tables from a PowerMonger RAM image
    (>= 0x100000 bytes, base 0).  Must be called before reconstruct()."""
    global _HTBL, SHIFT_TBL, DIR_TBL, _TRIG, SPLINE
    ram = bytes(ram)
    _HTBL = ram[TBL_HEADING:TBL_HEADING + 2048]
    SHIFT_TBL = _HTBL[:1024]                # $14360 : big>>5 -> shift amount
    DIR_TBL   = _HTBL[1024:2048]            # $14760 : (a<<5)+b -> heading
    _TRIG  = ram[TBL_TRIG:TBL_TRIG + 640]   # base $13f8a
    SPLINE = ram[TBL_SPLINE:TBL_SPLINE + 256]  # base $168ee
    assert len(_HTBL) == 2048 and len(_TRIG) == 640 and len(SPLINE) == 256, \
        "init_tables: RAM image too small"


def _trig(i):                               # s16 word[$13f8a + 2*i]
    return struct.unpack_from(">h", _TRIG, (i & 0xffff) * 2)[0]
def _sin(h): return _trig(h & 0xff)         # word[$13f8a + 2h]
def _cos(h): return _trig((h & 0xff) + 64)  # word[$1400a + 2h] = word[$13f8a + 2(h+64)]
def _spw(off):                              # s16 word[$168ee + off]
    return struct.unpack_from(">h", SPLINE, off & 0xffff)[0]


# ---------------------------------------------------------------- $14262
def heading(m, dx, dy):
    """$14262: (dx,dy) -> 0..255 heading byte. dx,dy passed as 16-bit words."""
    dx = s16(dx); dy = s16(dy)
    negx = dx < 0                           # tst.w D0 ; bmi
    negy = dy < 0                           # tst.w D1 ; bmi
    a = (-dx if negx else dx) & 0xffff      # neg.w D0  (per quadrant)
    b = (-dy if negy else dy) & 0xffff      # neg.w D1
    big = b if b > a else a                 # cmp.w D0,D1 ; bgt  -> Y drives when b>a
    sh = SHIFT_TBL[(big >> 5) & 0xffff]     # move.b 0(A0,idx.w),D3
    a = (a >> sh) & 0xffff                  # lsr.w D3,D0
    b = (b >> sh) & 0xffff                  # lsr.w D3,D1
    idx = ((a << 5) + b) & 0xffff           # move.w D0,D2 ; lsl.w #5,D2 ; add.w D1,D2
    d = DIR_TBL[idx]                         # move.b 0(A0,D2.w),D0   (A0 += 1024)
    if not negx and not negy:               # ++  : $14294..$1429e
        h = d
    elif not negx and negy:                 # +-  : neg.w D0 ; addi.w #$80
        h = 0x80 - d
    elif negx and not negy:                 # -+  : neg.w D0 ; andi.w #$ff
        h = -d
    else:                                   # --  : addi.w #$80
        h = d + 0x80
    return h & 0xff                          # movem restore ; andi.w #$ff,D0 ; rts


# ---------------------------------------------------------------- $12d56
def rotate(m, x, y, hd):
    """$12d56: rotate the vector (x,y) by heading hd. Returns (x',y') as 16-bit."""
    x = s16(x); y = s16(y)
    co = _cos(hd)                           # move.w 0(A0,D2.w),D6     (D2 = hd*2)
    si = _sin(hd)                           # move.w -128(A0,D2.w),D5
    px = ((x * co - y * si) * 2) & 0xffffffff   # muls,muls,sub.l,add.l D0,D0
    py = ((x * si + y * co) * 2) & 0xffffffff   # muls,muls,add.l,add.l D1,D1
    xp = (px >> 16) & 0xffff               # swap D0  -> take the high word
    yp = (py >> 16) & 0xffff               # swap D1
    return xp, yp


def _swap(v):    return ((v & 0xffff) << 16) | ((v >> 16) & 0xffff)
def _movew(dst, src):  return (dst & 0xffff0000) | (src & 0xffff)

def _divu(dividend, divisor16):
    """68000 DIVU.W.  Divide-by-zero traps through vector 5; PM's handler
    resumes with the operand unchanged, so model it as a no-op.  Overflow
    (quotient > $ffff) also leaves the operand unchanged (V set)."""
    d = divisor16 & 0xffff
    dv = dividend & 0xffffffff
    if d == 0:
        return dv                          # divu #0 -> trap -> (handler) -> unchanged
    q, r = dv // d, dv % d
    if q > 0xffff:
        return dv                          # overflow -> unchanged
    return ((r & 0xffff) << 16) | (q & 0xffff)


# ---------------------------------------------------------------- $164bc
def step_toward(m, tx, ty, cx, cy, A1):
    """$164bc: write step_x/step_y (12,13), heading (17), dwell (18); return
    (count, dwell, reached).  reached == (D2>>1 == 0) out of the swap-dance.

    Faithful register-level sim of the divu / swap-dance so the degenerate
    inputs (target == current -> `divu #0`, or a stationary speed-0 entity)
    reproduce the real 68000 exactly rather than being excluded."""
    speed = m.bu(A1 + 16)
    D0 = s16((tx - cx) & 0xffff)            # sub.w D6,D0
    D1 = s16((ty - cy) & 0xffff)            # sub.w D7,D1
    negx = D0 < 0                           # bmi $1652a
    negy = D1 < 0                           # bmi $164f6 / $16562 / $1652c
    a = (-D0 if negx else D0) & 0xffff      # neg.w D0  (per quadrant) -> |dx|
    b = (-D1 if negy else D1) & 0xffff      # neg.w D1                 -> |dy|
    D0 = a; D1 = b                          # ext.l D0 ; ext.l D1  (values are >= 0)
    D2 = speed & 0xff                       # moveq #0,D2 ; move.b 16(A1),D2
    if b > a:                               # cmp.w D0,D1 ; bgt -> major = Y
        D1 = _divu(D1, D2)                  # divu D2,D1
        D0 = _divu(D0, D1)                  # divu D1,D0
        D2 = _swap(D2); D2 = _movew(D2, D1); D2 = _swap(D2)   # swap;move.w D1,D2;swap
        D1 = _movew(D1, D2); D2 = _swap(D2)                   # move.w D2,D1 ; swap
    else:                                   # major = X
        D0 = _divu(D0, D2)                  # divu D2,D0
        D1 = _divu(D1, D0)                  # divu D0,D1
        D2 = _swap(D2); D2 = _movew(D2, D0); D2 = _swap(D2)   # swap;move.w D0,D2;swap
        D0 = _movew(D0, D2); D2 = _swap(D2)                   # move.w D2,D0 ; swap
    sx = (-D0 if negx else D0) & 0xffff     # neg.w D0 in the -x quadrants
    sy = (-D1 if negy else D1) & 0xffff     # neg.w D1 in the -y quadrants
    # ---- shared tail $16596 ----
    m.wb(A1 + 12, sx & 0xff)               # move.b D0,12(A1)
    m.wb(A1 + 13, sy & 0xff)               # move.b D1,13(A1)
    h = heading(m, sx, (-s16(sy)) & 0xffff)   # neg.w D1 ; jsr $14262
    m.wb(A1 + 17, h & 0xff)                # move.b D0,17(A1)
    count = D2 & 0xffff
    dwell = count >> 1                     # lsr.w #1,D2
    m.ww(A1 + 18, dwell)                   # move.w D2,18(A1)
    return count, dwell, (dwell == 0)


# ---------------------------------------------------------------- $16202
def _clamp(D6, D7):
    """the world-coord clamp shared by $161c4 and $16202."""
    d6 = s16(D6); d7 = s16(D7)
    if d6 < 0:            D6 = 0            # tst.w D6 ; bpl ; clr.w D6
    elif d6 >= 0x4000:    D6 = 0x3fff      # cmpi.w #$4000,D6 ; blt ; move.w #$3fff
    else:                D6 = d6 & 0xffff
    if d7 < 0:                             # tst.w D7 ; bpl (no upper clamp when >=0)
        n = (-d7) & 0xffff                 # neg.w D7
        D7 = 0x7fff if n > 0x1f40 else 0   # cmp.w #$1f40,D7 ; bhi -> $7fff else clr
    else:
        D7 = d7 & 0xffff
    return D6, D7


def epilogue_16202(m, A1, D6, D7):
    """$16202: clamp, then $163ea write-back + relink.  No terrain veto, no
    bclr #5 (that is what distinguishes it from $161c4)."""
    D6, D7 = _clamp(D6, D7)
    relink(m, A1, D6, D7)                  # $16228 bsr $163ea


# ---------------------------------------------------------------- $14d32  mode $06
def h_mode06(m, A1, D6, D7):
    D6 = (D6 + s8(m.bu(A1 + 12))) & 0xffff        # move.b 12(A1),D0 ; ext.w ; add.w D0,D6
    D7 = (D7 + s8(m.bu(A1 + 13))) & 0xffff
    t = terrain_sample(m, D6, D7)                 # bsr $1648e
    if t != 0:                                    # bne $14d6a  (land)
        _dwell_dance_8(m, A1)                     # $14d6a
        epilogue_16202(m, A1, D6, D7)
        return
    # water:
    if m.bu(A1 + 33) == 0x0a:                     # cmpi.b #$a,33(A1) ; beq $14d5a
        m.wb(A1 + 7, m.bu(A1 + 7) | 0x20)         # bset #5,7(A1)
        m.wb(A1 + 31, 0x02)                       # mode := $02
        _dwell_dance_8(m, A1)                     # bra $14d20 (== $14d6a body)
        epilogue_16202(m, A1, D6, D7)
    else:
        m.wb(A1 + 31, 0x00)                       # move.b #$0,31(A1)
        # bra $1622c : straight to next record, no write-back


def _dwell_dance_8(m, A1):
    """$14d6a / $14d20 : subq.w #1,18(A1) ; == 0 -> mode := $08."""
    dw = (m.wu(A1 + 18) - 1) & 0xffff             # subq.w #1,18(A1)
    m.ww(A1 + 18, dw)
    if dw == 0:                                   # bne $16202  (taken unless 0)
        m.wb(A1 + 31, 0x08)


# ---------------------------------------------------------------- $14d7c  mode $08
def h_mode08(m, A1, D6, D7):
    A4 = OBJ + s16(m.wu(A1 + 28))                 # lea $51b66 ; adda.w 28(A1),A4
    D0 = m.wu(A1 + 20); D1 = m.wu(A1 + 22)        # orbit offset vector
    D2 = m.bu(A4 + 17)                            # lead heading
    D0, D1 = rotate(m, D0, D1, D2)                # jsr $12d56
    D0 = (D0 + m.wu(A4 + 8)) & 0xffff             # add.w 8(A4),D0
    D1 = (D1 + m.wu(A4 + 10)) & 0xffff            # add.w 10(A4),D1
    spd = (m.bu(A4 + 16) + 4) & 0xff              # move.b 16(A4),D2 ; addi.b #$4
    m.wb(A1 + 16, spd)                            # move.b D2,16(A1)
    _c, _d, reached = step_toward(m, D0, D1, D6, D7, A1)   # bsr $164bc
    if reached:                                   # beq (fall through) -> reached block
        D0 = m.wu(A1 + 20); D1 = m.wu(A1 + 22)
        D2 = m.bu(A4 + 17)
        m.wb(A1 + 17, D2 & 0xff)                  # move.b D2,17(A1)
        D0, D1 = rotate(m, D0, D1, D2 & 0xff)     # jsr $12d56
        D0 = (D0 + m.wu(A4 + 8)) & 0xffff
        D1 = (D1 + m.wu(A4 + 10)) & 0xffff
        D6 = D0; D7 = D1                          # move.w D0,D6 ; move.w D1,D7
        m.ww(A1 + 12, m.wu(A4 + 12))              # move.w 12(A4),12(A1)  (copy step word)
        m.ww(A1 + 18, 0x000a)                     # move.w #$a,18(A1)
    # $14de6:
    t = terrain_sample(m, D6, D7)                 # bsr $1648e
    if t != 0:                                    # bne $14dec (land)
        m.wb(A1 + 31, 0x06)                       # move.b #$6,31(A1)
        m.wb(A1 + 7, m.bu(A1 + 7) & ~0x20)        # bclr #5,7(A1)
        h_mode06(m, A1, D6, D7)                   # bra $14d32  (run the mode $06 body)
        return
    # water : $14dfc
    if m.bu(A1 + 33) == 0x0a:                     # cmpi.b #$a,33(A1) ; bne $14e14
        m.wb(A1 + 31, 0x02)                       # move.b #$2,31(A1)
        m.wb(A1 + 7, m.bu(A1 + 7) | 0x20)         # bset #5,7(A1)
        h_mode02(m, A1, D6, D7)                   # bra $14cfa
    else:
        m.wb(A1 + 31, 0x00)                       # move.b #$0,31(A1)
        # bra $1622c


def h_mode02(m, A1, D6, D7):
    """$14cfa : mode $02 body (reached from $14e10 in mode $08)."""
    D6 = (D6 + s8(m.bu(A1 + 12))) & 0xffff
    D7 = (D7 + s8(m.bu(A1 + 13))) & 0xffff
    t = terrain_sample(m, D6, D7)                 # bsr $1648e ; beq $14d20
    if t == 0:
        _dwell_dance_8(m, A1)                     # $14d20
        epilogue_16202(m, A1, D6, D7)
    else:
        m.wb(A1 + 7, m.bu(A1 + 7) & ~0x20)        # bclr #5,7(A1)
        m.wb(A1 + 31, 0x06)                       # move.b #$6,31(A1)
        _dwell_dance_8(m, A1)                     # bra $14d6a
        epilogue_16202(m, A1, D6, D7)


# ---------------------------------------------------------------- $14e70  mode $0e
def h_mode0e(m, A1, D6, D7):
    D6 = (D6 + s8(m.bu(A1 + 12))) & 0xffff        # integrate one tick
    D7 = (D7 + s8(m.bu(A1 + 13))) & 0xffff
    dw = (m.wu(A1 + 18) - 1) & 0xffff             # subq.w #1,18(A1)
    m.ww(A1 + 18, dw)
    if dw != 0:                                   # bne $16202
        epilogue_16202(m, A1, D6, D7)
        return
    # ---- segment boundary: advance the spline cursor ($14e88) ----
    D2 = m.wu(A1 + 40)                            # path_cursor (byte offset)
    D6 = (_spw(D2) + m.ws(A1 + 36)) & 0xffff      # movem.w ->D6,D7 ; add origin
    D7 = (_spw(D2 + 2) + m.ws(A1 + 38)) & 0xffff
    D2 = (D2 + 4) & 0xffff                        # addq.w #4,D2
    while True:                                   # $14ea2
        D0 = _spw(D2); D1 = _spw(D2 + 2)          # movem.w 0(A0,D2),#$0003
        if s16(D0) >= 0x7d00:                     # cmpi.w #$7d00,D0 ; bge $14ee0
            if (D0 & 0xffff) == 0x7d01:           # cmpi.w #$7d01,D0 ; bne
                D2 = (D2 - (D1 & 0xffff)) & 0xffff  # sub.w D1,D2 ; bra $14ea2
                continue
            if s16(D0) < 0x7d02:                  # cmp.w #$7d02,D0 ; blt $14efe
                m.wb(A1 + 31, 0x92)               # move.b #$92,31(A1)
            else:
                m.wb(A1 + 31, (D0 - 0x7d02) & 0xff)  # subi.w #$7d02,D0 ; move.b D0,31(A1)
            epilogue_161c4(m, A1, D6, D7)         # bra $161c4
            return
        # ---- normal segment ($14eae) ----
        m.ww(A1 + 40, D2)                         # move.w D2,40(A1)
        nx = (D0 + m.ws(A1 + 36)) & 0xffff        # add.w 36(A1),D0
        ny = (D1 + m.ws(A1 + 38)) & 0xffff        # add.w 38(A1),D1
        sx = s16((nx - D6) & 0xffff) >> 3         # sub.w D6,D0 ; asr.w #3,D0
        sy = s16((ny - D7) & 0xffff) >> 3         # sub.w D7,D1 ; asr.w #3,D1
        m.wb(A1 + 12, sx & 0xff)                  # move.b D0,12(A1)
        m.wb(A1 + 13, sy & 0xff)                  # move.b D1,13(A1)
        m.wb(A1 + 17, heading(m, sx & 0xffff, (-sy) & 0xffff) & 0xff)  # neg.w D1 ; jsr $14262
        m.ww(A1 + 18, 0x0008)                     # move.w #$8,18(A1)
        epilogue_16202(m, A1, D6, D7)             # bra $16202
        return


# ---------------------------------------------------------------- $14f08  mode $10
def h_mode10(m, A1, D6, D7):
    if m.bu(A1 + 30) == 0x2e:                     # cmpi.b #$2e,30(A1)  (chase)
        A3 = OBJ + s16(m.wu(A1 + 48))             # link_target
        if m.bs(A3 + 5) <= 0 or m.bu(A3 + 30) == 0x3c:  # target gone / corpse
            m.wb(A1 + 31, 0x2c)                   # $14f48 : convert to a fixed cell
            m.wb(A1 + 30, 0x2c)
            epilogue_161c4(m, A1, D6, D7)
            return
        m.wl(A1 + 20, m.lu(A3 + 8))               # move.l 8(A3),20(A1)  (track live pos)
        D0 = m.wu(A1 + 20); D1 = m.wu(A1 + 22)
        _c, _d, reached = step_toward(m, D0, D1, D6, D7, A1)
        if reached:                              # beq $15302 -- ASSERT OFF
            raise AssertionError("mode $10 chase reached -> $15302 ($56a6 engage) "
                                 "- out of scope (rec %d)" % ((A1 - OBJ) // REC))
        m.ww(A1 + 18, 0x0003)                    # move.w #$3,D2 ; move.w D2,18(A1)
        D2probe = 3
    else:                                        # $14f58 : fixed target
        D0 = m.wu(A1 + 20); D1 = m.wu(A1 + 22)
        _c, D2probe, reached = step_toward(m, D0, D1, D6, D7, A1)
        if reached:                             # beq $14fdc
            m.wb(A1 + 31, m.bu(A1 + 30))         # move.b 30(A1),31(A1)
            D6 = m.wu(A1 + 20); D7 = m.wu(A1 + 22)
            if m.bu(A1 + 7) & 0x20:              # btst #5,7(A1) ; beq $161c4
                epilogue_16202(m, A1, D6, D7)
            else:
                epilogue_161c4(m, A1, D6, D7)
            return
    # ---- move body $14f66 ----
    if m.bu(A1 + 33) != 0x0a:                    # cmpi.b #$a,33(A1) ; beq $14fa2
        d3 = s8(m.bu(A1 + 12)); d4 = s8(m.bu(A1 + 13))  # probe ahead
        probe = (D2probe - 1) & 0xffff           # subi.w #$1,D2
        x, y = D6, D7
        blocked = False
        while True:                              # $14f82 ; dbeq D2
            x = (x + d3) & 0xffff; y = (y + d4) & 0xffff
            if terrain_sample(m, x, y) == 0:     # bsr $1648e ; Z set -> dbeq exits
                blocked = True                   # D2 unchanged, D2 >= 0
                break
            probe = (probe - 1) & 0xffff
            if s16(probe) == -1:                 # dbeq: Dn wrapped past 0
                break
        if s16(probe) >= 0:                      # tst.w D2 ; blt $14fa2  (not taken)
            m.wb(A1 + 31, 0x4a)                  # move.b #$4a,31(A1)
            return                              # bra $1622c
    # $14fa2 : group hand-off gate
    if m.bu(A1 + 7) & 0x10:                      # btst #4,7(A1)
        g = m.wu(A1 + 42)                        # move.w 42(A1),D0
        if g != 0 and m.wu(0x51538 + g) == 8:    # cmpi.w #$8,0(A3,D0.w)
            if s16(m.wu(A1 + 18)) <= 0x12:       # cmpi.w #$12,18(A1) ; bgt $14fca
                raise AssertionError("mode $10 group state-8 hand-off -> $1518a "
                                     "($4bc8) - out of scope (rec %d)"
                                     % ((A1 - OBJ) // REC))
            m.ww(A1 + 18, m.wu(A1 + 18) >> 1)    # lsr 18(A1)
    m.wb(A1 + 31, 0x12)                          # move.b #$12,31(A1)
    # $14fce falls into the $14ff8 body with the current D6/D7:
    D6 = (D6 + s8(m.bu(A1 + 12))) & 0xffff       # $14ff8
    D7 = (D7 + s8(m.bu(A1 + 13))) & 0xffff
    dwell = s16((m.wu(A1 + 18) - 1) & 0xffff)    # subq.w #1,18(A1)
    m.ww(A1 + 18, dwell & 0xffff)
    if not (dwell > 0):                          # bgt $161c4
        m.wb(A1 + 31, 0x10)                      # move.b #$10,31(A1)
    epilogue_161c4(m, A1, D6, D7)


# ================================================================ 95th pass:
# the COMBAT path  mode $32 $1533c (melee) + its leaves
#   $56a6  engage bookkeeping        (also called from $15302, mode $2e)
#   $5778  deep engage bookkeeping   ($4bc8 group hand-off = ASSERT OFF)
#   $5590  kill / rout roll          ($3c08 rout, $2776/$1b8c cleanup = ASSERT OFF)
#   $30fe  group.field60 - 2         (roll selector, transcribable)
# Transcribed line-for-line + raw-byte-verified from scratchpad/pm95/disasm/.
# $51538 = group-record array (state at +0, field60 at +60).
# ================================================================
GROUP = 0x51538
LEADER = 0x4e514
ROSTER = 0x4f916          # per-entity roster: word[+14] = leader-table byte offset


def _melee_lost(m, A1, D6, D7):
    """$153a2: self drops out of melee -> fixed cell, run the $161c4 epilogue."""
    m.wb(A1 + 31, 0x2c)                          # move.b #$2c,31(A1)
    m.wb(A1 + 30, 0x2c)                          # move.b #$2c,30(A1)
    epilogue_161c4(m, A1, D6, D7)                # bra $161c4


# ---------------------------------------------------------------- $30fe
def call_30fe(m, rec):
    """$30fe: D0 = word[group[42(rec)] + 60] - 2  (16-bit).  Called from $5590
    with A1 == the group-lead record."""
    A3 = GROUP + s16(m.wu(rec + 42))             # lea $51538 ; adda.w 42(A1),A3
    return (m.wu(A3 + 60) - 2) & 0xffff          # move.w 60(A3),D0 ; subi.w #$2,D0


# ---------------------------------------------------------------- $5778
def bookkeep_5778(m, A1self, A3):
    """$5778: engage-side group bookkeeping.  A1self = attacker, A3 = the record
    being enrolled.  The $4bc8 group hand-off (group state != $d) is ASSERTED OFF
    - no corpus/poked state reaches it."""
    D0 = m.wu(A3 + 42)                           # move.w 42(A3),D0 ; beq $57ea
    if D0 == 0:
        return
    A0 = GROUP + s16(D0)                         # lea $51538 ; adda.w D0,A0
    gstate = m.wu(A0 + 0)
    if gstate == 0x0006:                         # cmpi.w #$6,0(A0) ; bne $57b6
        D0b = m.wu(A3 + 46)                      # move.w 46(A3),D0 ; beq $57b6
        if D0b != 0:
            A2 = (OBJ + s16(D0b)) & 0xfffff
            if 0x4cff8 <= A2 < 0x4d250:          # cmpa.l #$4cff8 / #$4d250
                m.wb(A2 + 7, 0x11)               # move.b #$11,7(A2)
    if gstate != 0x000d:                         # cmpi.w #$d,0(A0) ; beq $57ca
        raise AssertionError("$5778 -> $4bc8 group hand-off (group state $%x != $d)"
                             " - OUT OF SCOPE (95th)" % gstate)
    # $57ca : group state == $d
    if (m.bu(A1self + 7) & 0x10) and m.wu(A1self + 42) != 0:
        m.ww(A3 + 204, 0x0004)                   # move.w #$4,204(A3)   (dead store)
        m.ww(A3 + 204, (A1self - OBJ) & 0xffff)  # move.w D0,204(A3)


# ---------------------------------------------------------------- $56a6
def engage_56a6(m, A1self, A3tgt):
    """$56a6: enroll A3tgt into melee against A1self.  Writes 31/30/48/46/38 of
    the target; may call $5778 twice."""
    if m.bu(A3tgt + 7) & 0x40:                   # btst #6,7(A3) ; beq $56f4
        d = m.wu(A3tgt + 28)                     # move.w 28(A3),D0 ; beq $56f4
        if d != 0:
            A2 = (OBJ + s16(d)) & 0xfffff        # lea $51b66 ; adda.w D0,A2
            dx = s16((m.wu(A2 + 8) - m.wu(A3tgt + 8)) & 0xffff)
            dx = -dx if dx < 0 else dx           # bpl / neg.w D0
            dy = s16((m.wu(A2 + 10) - m.wu(A3tgt + 10)) & 0xffff)
            dy = -dy if dy < 0 else dy           # bpl / neg.w D1
            far = dx if dx > dy else dy          # cmp.w D1,D0 ; bgt ; exg  -> D0 = max
            if not (far >= 0x0fff):              # cmp.w #$fff,D0 ; bge $5702
                bookkeep_5778(m, A1self, A2)     # movea.l A2,A3 ; jsr $5778
    if m.bu(A3tgt + 7) & 0x10:                   # btst #4,7(A3) ; beq $5702
        bookkeep_5778(m, A1self, A3tgt)          # jsr $5778
    # $5702
    m.wb(A3tgt + 31, 0x32)                       # move.b #$32,31(A3)
    m.wb(A3tgt + 30, 0x32)                       # move.b #$32,30(A3)
    m.ww(A3tgt + 48, (A1self - OBJ) & 0xffff)    # move.w D0,48(A3)
    f = m.bu(A1self + 7)
    if (f & 0x40) or ((f & 0x10) and m.wu(A1self + 42) != 0):
        D0 = m.wu(A1self + 28)                   # move.w 28(A1),D0 ; bne $573e
        if D0 == 0:
            D0 = (A1self - OBJ) & 0xffff
        m.ww(A3tgt + 46, D0 & 0xffff)            # move.w D0,46(A3)
        m.wb(A3tgt + 38, 0x04)                   # move.b #$4,38(A3)
    else:                                        # $574a
        A0 = (ROSTER + s16(m.wu(A1self + 34))) & 0xfffff
        D0 = m.wu(A0 + 14)                       # move.w 14(A0),D0
        A0 = (LEADER + s16(D0)) & 0xfffff        # lea $4e514 ; adda.w D0,A0
        m.ww(A3tgt + 46, (A0 - OBJ) & 0xffff)    # move.l A0,D0 ; subi.l #$51b66 ; move.w D0,46(A3)
        m.wb(A3tgt + 38, 0x02)                   # move.b #$2,38(A3)


# ---------------------------------------------------------------- $5590
def kill_rout_5590(m, A1self, A3tgt):
    """$5590: the kill/rout roll.  A1self = attacker, A3tgt = the loser.
    The ROUT branch ($3c08) and the group/leader cleanup calls $2776 / $1b8c are
    ASSERTED OFF (no corpus/poked state reaches them)."""
    m.wb(A3tgt + 45, 0)                          # move.b #$0,45(A3)
    D0 = 0                                       # move.w #$0,D0
    f = m.bu(A1self + 7)
    go_55b6 = False
    if f & 0x10:                                 # btst #4,7(A1) ; beq $55ae
        if m.wu(A1self + 42) != 0:               # tst.w 42(A1) ; beq $55d6
            go_55b6 = True
    elif f & 0x40:                               # $55ae btst #6,7(A1) ; beq $55d6
        go_55b6 = True
    if go_55b6:                                  # $55b6
        d = m.wu(A1self + 28)                    # move.w 28(A1),D0
        A4 = (OBJ + s16(d)) & 0xfffff if d != 0 else A1self
        D0 = d                                   # D0 still == 28(A1) here
        if m.bs(A4 + 5) > 0:                     # tst.b 5(A4) ; ble $55d6
            D0 = call_30fe(m, A4)                # exg A4,A1 ; jsr $30fe ; exg A4,A1
    # $55d6
    if (D0 & 0xffff) == 0x0000:                  # cmp.w #$0,D0 ; beq $55f2
        kill = True
    elif (D0 & 0xffff) == 0x0002:                # cmp.w #$2,D0 ; beq $560a
        kill = False
    else:
        r = (m.wu(TICK_RNG) + m.wu(A1self + 24)) & 0xffff   # move.w $57fec,D0 ; add.w 24(A1),D0
        kill = (r & 0x0002) != 0                 # btst #1,D0 ; beq $560a (rout) else fall to $55f2
    if not kill:                                 # $560a
        if not (m.bu(A3tgt + 7) & 0x20):         # btst #5,7(A3) ; bne $55f2
            raise AssertionError("$5590 ROUT branch -> $3c08 - OUT OF SCOPE (95th)")
        kill = True                              # bit5 set -> fall to $55f2 (kill after all)
    # $55f2 : KILL
    m.wb(A3tgt + 5, (-m.bu(A3tgt + 5)) & 0xff)   # neg.b 5(A3)
    m.wb(A3tgt + 32, 0)                          # move.b #$0,32(A3)
    m.wb(A3tgt + 6, 0x0c)                        # move.b #$c,6(A3)
    m.ww(A3tgt + 18, 0x00a0)                     # move.w #$a0,18(A3)
    # $5628 : common tail
    ff = m.bu(A3tgt + 7)
    if (ff & 0x80) or (ff & 0x10):               # btst #7 bne $5638 ; btst #4 beq $5658
        D0 = m.wu(A3tgt + 42)                    # $5638 move.w 42(A3),D0 ; beq $5658
        if D0 != 0:
            if m.bs(A3tgt + 5) > 0:              # tst.b 5(A3) ; bgt $56a0
                return
            raise AssertionError("$5590 tail -> $2776 group cleanup - OUT OF SCOPE (95th)")
    # $5658
    if ff & 0x40:                               # btst #6,7(A3) ; beq $567e
        if m.wu(A3tgt + 28) != 0:                # move.w 28(A3),D0 ; beq $56a0
            raise AssertionError("$5590 tail -> $1b8c - OUT OF SCOPE (95th)")
        return
    # $567e
    if m.bs(A3tgt + 5) > 0:                      # tst.b 5(A3) ; bgt $56a0
        return
    A0 = (ROSTER + s16(m.wu(A3tgt + 34))) & 0xfffff
    D0 = m.wu(A0 + 14)                           # move.w 14(A0),D0
    A0 = (LEADER + s16(D0)) & 0xfffff            # lea $4e514 ; adda.w D0,A0
    m.ww(A0 + 8, (m.wu(A0 + 8) - 1) & 0xffff)    # subi.w #$1,8(A0)


# ---------------------------------------------------------------- $1533c  mode $32
def h_mode32(m, A1, D6, D7):
    A3 = (OBJ + s16(m.wu(A1 + 48))) & 0xfffff    # lea $51b66 ; adda.w 48(A1),A3
    if m.bs(A3 + 5) <= 0:                        # tst.b 5(A3) ; ble $153a2
        return _melee_lost(m, A1, D6, D7)
    if m.bu(A3 + 30) == 0x3c:                    # cmpi.b #$3c,30(A3) ; beq $153a2
        return _melee_lost(m, A1, D6, D7)
    m.wb(A3 + 17, (m.bu(A1 + 17) + 0x80) & 0xff) # move.b 17(A1),D0 ; addi.b #$80 ; move.b D0,17(A3)
    if m.bu(A3 + 31) != 0x32:                    # cmpi.b #$32,31(A3) ; beq $1536e
        engage_56a6(m, A1, A3)                   # jsr $56a6
    D0 = m.bu(A1 + 44)                           # move.b 44(A1),D0
    if not (s8(D0) < 6):                         # cmp.b #$6,D0 ; blt $1537a
        D0 = 0                                   # moveq #0,D0
    D0 = (D0 & 0xff) >> 1                        # lsr.b #1,D0
    D0 = (D0 + 1) & 0xff                         # addi.b #$1,D0
    res = (m.bu(A3 + 45) - D0) & 0xff            # sub.b D0,45(A3)
    m.wb(A3 + 45, res)
    if s8(res) <= 0:                             # ble $1539c
        kill_rout_5590(m, A1, A3)                # jsr $5590
        return _melee_lost(m, A1, D6, D7)        # falls into $153a2
    # $15386 : mutual melee - target retaliates, no epilogue (bra $1622c)
    m.ww(A3 + 48, (A1 - OBJ) & 0xffff)           # move.l A1,D0 ; subi.l #$51b66 ; move.w D0,48(A3)
    m.wb(A3 + 31, 0x32)                          # move.b #$32,31(A3)


# ================================================================ 96th pass:
# the SETTLEMENT HEARTBEAT  mode $7c  $157e6  (dispatch entry $157ba)
#   $16848  side<->owner reconcile + $57ff4 note + tail $5c80
#   $163b8  settlement.leader.troops_reserve -= 1, floored at 0
#   $5cde   settlement herd-op assessment  -- ASSERTED OFF (large routine; every
#           test state is arranged so field*4 >= reserve, or (14(A1)&3)==3, so it
#           is not reached; reconstruct() raises if one ever would)
#   $550e   revolt  -- ASSERTED OFF (loyalty_pressure kept < $258 = 600)
#   $5c2c   owner reconcile inside $16848  -- ASSERTED OFF (marker.side kept == owner
#           on the bit-4 path)
# $157ba pre-check: word[$57fd0] == 0 -> $157e6 ; else $3c08 regroup (OUT OF SCOPE).
#   Mission 1 has $57fd0 = (seed&3)*2 != 0, so mode $7c never occurs naturally
#   there; the differential test pokes $57fd0 := 0 and synthesises $7c records.
# Transcribed line-for-line + raw-byte-verified from scratchpad/pm96/disasm/.
# ================================================================
SIDE_ASSESS = 0x580a6            # 5 x $20-byte per-side blocks; word0 = pulse period
SETTL       = 0x4f916            # 18-byte settlement records


def call_16848(m, A1):
    """$16848: reconcile the marker's side byte with its settlement's owner, then
    jsr $5c80.  The $5c2c owner-reconcile arm is ASSERTED OFF."""
    A3 = (SETTL + s16(m.wu(A1 + 34))) & 0xfffff
    D0 = m.bu(A3 + 5)                            # move.b 5(A3),D0   settlement.owner
    if D0 != m.bu(A1 + 5):                       # cmp.b 5(A1),D0 ; beq $16878
        if not (m.bu(A1 + 7) & 0x80):            # btst #7,7(A1) ; bne $16878
            if m.bu(A1 + 7) & 0x10:              # btst #4,7(A1) ; beq $16874
                raise AssertionError("$16848 -> $5c2c owner reconcile - OUT OF SCOPE (96th)")
            m.wb(A1 + 5, D0)                     # $16874 move.b D0,5(A1)  (adopt owner)
    # $16878
    D0 = m.wu(A1 + 24)                           # move.w 24(A1),D0 ; beq $1688a
    if D0 != 0 and D0 == m.wu(A1 + 0):           # cmp.w 0(A1),D0 ; bne $1688a
        m.ww(0x57ff4, D0)                        # move.w D0,$57ff4   (untracked global)
    upkeep(m, A1)                                # $1688a jsr $5c80


def call_163b8(m, A1):
    """$163b8: settlement.leader.troops_reserve -= 1, floored at 0."""
    A0 = (SETTL + s16(m.wu(A1 + 34))) & 0xfffff  # lea $4f916 ; adda.w 34(A1),A0
    D0 = m.wu(A0 + 14)                           # move.w 14(A0),D0   settlement.leader_off
    A0 = (LEADER + s16(D0)) & 0xfffff            # lea $4e514 ; adda.w D0,A0
    D0 = (m.wu(A0 + 6) - 1) & 0xffff             # move.w 6(A0),D0 ; subi.w #$1,D0
    if s16(D0) < 0:                              # bge $163e0
        D0 = 0                                   # move.w #$0,D0
    m.ww(A0 + 6, D0)                             # move.w D0,6(A0)


def _revolt_check(m, A0L):
    """$158ae: cmpi.w #$258,14(A0) ; blt $158d6.  $550e is ASSERTED OFF."""
    if s16(m.wu(A0L + 14)) >= 0x258:
        raise AssertionError("mode $7c -> $550e revolt (loyalty_pressure >= 600)"
                             " - OUT OF SCOPE (96th)")


def h_mode7c(m, A1, D6, D7):
    """$157e6: the per-settlement heartbeat body."""
    dwell = s16((m.wu(A1 + 18) - 1) & 0xffff)    # subi.w #$1,18(A1)
    m.ww(A1 + 18, dwell & 0xffff)
    if dwell > 0:                                # bgt $1622c  (next record, NO epilogue)
        return
    call_16848(m, A1)                            # jsr $16848
    upkeep(m, A1)                                # jsr $5c80  (a second time)
    D5 = dwell & 0xffff                          # move.w 18(A1),D5  (== post-decrement value)
    side = m.bs(A1 + 5) & 0xffff                 # move.b 5(A1),D0 ; ext.w D0
    idx = (side * 0x20) & 0xffff                 # mulu #$20,D0
    m.ww(A1 + 18, m.wu(SIDE_ASSESS + idx))       # move.w 0(A3,D0.w),18(A1)  dwell reload
    call_163b8(m, A1)                            # jsr $163b8
    A0 = (SETTL + s16(m.wu(A1 + 34))) & 0xfffff  # lea $4f916 ; adda.w 34(A1),A0
    if not (m.bu(A1 + 7) & 0x10):                # btst #4,7(A1) ; bne $158d6
        if m.bu(A0 + 7) == 0x0a:                 # cmpi.b #$a,7(A0) ; bne $15866  (under construction)
            m.wb(A0 + 16, (m.bu(A0 + 16) + 1) & 0xff)   # addi.b #$1,16(A0)
            if m.bu(A0 + 16) >= 0x78:            # cmpi.b #$78,16(A0) ; blt $15866
                rem = m.wu(A0 + 12) % 10         # move.w 12(A0),D0 ; divu #$a,D0 ; swap D0
                m.wb(A0 + 7, rem & 0xff)         # move.b D0,7(A0)   nation_kind := dest_cell % 10
                if rem == 7:                     # cmp.w #$7,D0 ; bne $15862
                    m.wb(A0 + 6, 0x10)           # move.b #$10,6(A0)  (capital)
                m.wb(A0 + 16, 0)                 # clr.b 16(A0)
        # $15866
        A0L = (LEADER + s16(m.wu(A0 + 14))) & 0xfffff   # move.w 14(A0),D0 ; lea $4e514 ; adda.w D0,A0
        f4 = (m.wu(A0L + 8) << 2) & 0xffff       # move.w 8(A0),D0 ; lsl.w #2,D0
        if f4 != 0:                              # beq $158d6
            if s16(f4) >= s16(m.wu(A0L + 6)):    # cmp.w 6(A0),D0 ; bge $158a2
                if D5 == 0xff9c:                 # $158a2 cmp.w #$ff9c,D5 ; bne $158d6
                    m.ww(A0L + 14, (m.wu(A0L + 14) + 2) & 0xffff)   # addi.w #$2,14(A0)
                    _revolt_check(m, A0L)        # fall into $158ae
            else:                               # $15880 : field*4 < reserve
                if D5 == 0xff9c:                 # cmp.w #$ff9c,D5 ; bne $1588c
                    m.ww(A0L + 14, (m.wu(A0L + 14) - 1) & 0xffff)   # subi.w #$1,14(A0)
                if (m.bu(A1 + 14) & 3) != 3:     # move.b 14(A1),D1 ; andi.w #$3,D1 ; cmp.w #$3,D1 ; beq $158ae
                    raise AssertionError("mode $7c -> $5cde herd-op assessment"
                                         " - OUT OF SCOPE (96th) (rec %d)"
                                         % ((A1 - OBJ) // REC))
                _revolt_check(m, A0L)            # $158ae
    epilogue_161c4(m, A1, D6, D7)                # $158d6 bra $161c4


# ---------------------------------------------------------------- prologue + dispatch
def reconstruct(m):
    if _TRIG is None:
        raise RuntimeError("pm_fsm_ref.init_tables(ram) must be called before reconstruct()")
    A1 = OBJ + REC                          # skip slot 0
    tick_lo = m.wu(MASTER_TICK_LO)
    while A1 != END:
        owner = m.bs(A1 + 5)
        if owner == 0:
            A1 += REC
            continue
        if owner < 0:
            raise AssertionError("dying record (owner<0) at rec %d - out of scope"
                                 % ((A1 - OBJ) // REC))
        # anim-frame advance
        d0 = (tick_lo + m.wu(A1 + 24)) & 0x3ff
        if d0 == m.wu(A1 + 34):
            if not (m.bu(A1 + 7) & 0x10):   # btst #4,7(A1)
                m.wb(A1 + 14, (m.bu(A1 + 14) + 1) & 0xff)
        D6 = m.ws(A1 + 8)
        D7 = m.ws(A1 + 10)
        mode = m.bu(A1 + 31)

        if mode == 0x12:                    # ---- $14ff8 halt / cool-down ----
            D6 = (D6 + m.bs(A1 + 12)) & 0xffff
            D7 = (D7 + m.bs(A1 + 13)) & 0xffff
            dwell = s16(m.wu(A1 + 18) - 1)
            m.ww(A1 + 18, dwell)
            if not (dwell > 0):            # bgt $161c4  (falls through on <= 0)
                m.wb(A1 + 31, 0x10)
            epilogue_161c4(m, A1, D6, D7)

        elif mode == 0x68:                 # ---- $16048 formation follower ----
            upkeep(m, A1)
            m.ww(A1 + 12, 0)               # clr.w 12(A1)  (step_x, step_y)
            m.wb(A1 + 17, 0)               # clr.b 17(A1)  (heading)
            # bra $1622c - no writeback, no relink

        elif mode == 0x8a:                 # ---- $161b2 garrison ----
            upkeep(m, A1)
            # bra $1622c

        elif mode == 0x06:                 # ---- $14d32 walk until blocked ----
            h_mode06(m, A1, D6, D7)

        elif mode == 0x08:                 # ---- $14d7c escort / orbit ----
            h_mode08(m, A1, D6, D7)

        elif mode == 0x0e:                 # ---- $14e70 patrol spline ----
            h_mode0e(m, A1, D6, D7)

        elif mode == 0x10:                 # ---- $14f08 advance / chase ----
            h_mode10(m, A1, D6, D7)

        elif mode == 0x32:                 # ---- $1533c melee ----
            h_mode32(m, A1, D6, D7)

        elif mode == 0x7c:                 # ---- $157e6 settlement heartbeat ----
            h_mode7c(m, A1, D6, D7)

        else:
            raise AssertionError("rec %d live in unsupported mode $%02x"
                                 % ((A1 - OBJ) // REC, mode))
        A1 += REC


# ---------------------------------------------------------------- diff helpers
REGIONS = [
    (OBJ + REC, END, "obj"),
    (BUCKETS, BUCKETS + 0x4000, "bucket"),
    (0x4e514, 0x4e514 + 32 * 40, "leader"),
    (0x4f916, 0x4f916 + 0x100, "settlement"),   # 96th: mode $7c construction path
]

def in_tracked_region(a):
    return any(lo <= a < hi for lo, hi, _ in REGIONS)


def apply_callcap_delta(base_ram, mem_list):
    out = bytearray(base_ram)
    for a, b0, b1 in mem_list:
        out[a] = b1
    return out
