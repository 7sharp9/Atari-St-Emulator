"""The order senders and executors, transcribed from the listing (`disassemble.py --all`), imports
`tools/pm_fsm_ref.py` for everything already proven ($37c2, $1d70, $35f4, $30fe, $5cde, $39d4, $3c08, $16848, $16778).

Every function takes the register values the real routine reads at entry (the same names as the 68000 registers) and
returns the registers it hands back; memory effects land in `m` (a pm_fsm_ref.Mem).  Gated by gate_orders.py against
`callcap`.
"""
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_ref import OBJ, GROUP, SETTL, LEADERS, BUCKETS, SIDE_ASSESS, s8, s16, u16

CELLCTRL = P.CELLCTRL            # $3f86c
PRICE = 0x6502                   # 8 bytes: 5,10,20,4,6,2,100,200 (read from the image)
BUYROW = 0x650a                  # 3 rows of 8 bytes per posture (aggressive, neutral, passive): 0xff pads
TRACE = []                       # arm tags of the last call


def _price(m, i):
    return m.bu(PRICE + i)


def _cellidx(D0, D1):
    """lsl.w #6,D1 ; add.w D0,D1 ; add.w D1,D1  -> the doubled cell (word)."""
    d1 = (D1 << 6) & 0xffff
    d1 = (d1 + D0) & 0xffff
    return (d1 * 2) & 0xffff


def _bhead(m, d1):
    return m.wu(BUCKETS + s16(d1))


def _cell_a(m, A1):
    """$32c6-style cell: move.w 10(A1),D0 ; lsr.w #2 ; andi.w #$1fc0 ; add.b 8(A1),D0 (carry out of the byte lost)."""
    d0 = (m.wu(A1 + 10) >> 2) & 0x1fc0
    return (d0 & 0xff00) | ((d0 + m.bu(A1 + 8)) & 0xff)


def _xy_target(m, A1, x, y):
    """The 4-byte target stamp of the order senders: x byte, $80, y byte, $80 at 20..23."""
    m.wb(A1 + 20, x)
    m.wb(A1 + 21, 0x80)
    m.wb(A1 + 22, y)
    m.wb(A1 + 23, 0x80)


# $35f4 is pm_fsm_ref.call_35f4 (its bucket-chain walk sign-extends the record offsets).
call_35f4 = P.call_35f4


def call_39d4(m, A3, D0, D7, D5=0):
    """pm_fsm_ref.call_39d4 plus the caller's D5: for D7 == 1 the routine never clears D5 ($3a6a is in the goods half), so
    the `D5 == 0` early-out at $3abe tests the caller's stale D5 plus the shifted food.  For every other arm D5 starts at 0."""
    if D7 != 1 or D5 == 0:
        return P.call_39d4(m, A3, D0, D7)
    # D7 == 1 with a stale D5: the same walk as P.call_39d4 (bit 5, a drop, a settlement, a new drop) with D5 seeded
    A1 = (OBJ + s16(m.wu(A3 - 12))) & 0xfffff
    if m.bu(A1 + 7) & 0x20:
        return P.call_39d4(m, A3, D0, D7)
    D6 = (m.wu(A1 + 10) >> 2) & 0x1fc0
    D6 = (D6 & 0xff00) | ((D6 + m.bu(A1 + 8)) & 0xff)
    d1 = m.wu(BUCKETS + 2 * D6)
    A0, kind = None, None
    while d1 != 0:
        A0 = (OBJ + s16(d1)) & 0xfffff
        b6 = m.bu(A0 + 6)
        if b6 == 0x2c:
            kind = "drop"
            break
        if b6 in (0x02, 0x10):
            kind = "settl"
            break
        d1 = m.wu(A0 + 0)
    if kind == "settl":
        return P.call_39d4(m, A3, D0, D7)
    if kind is None:
        A0 = P.DROP_LO
        while P.s8(m.bu(A0 + 6)) > 0:
            A0 += 28
            if A0 == P.DROP_HI:
                return
        for d in range(0, 0x12, 2):
            m.ww(A0 + 10 + d, 0)
    D4 = P._lsr(m.wu(A3 + 36), D0)
    m.ww(A3 + 36, m.wu(A3 + 36) - D4)
    m.ww(A0 + 10, m.wu(A0 + 10) + D4)
    P._39d4_link(m, A0, u16(D5 + D4), D6)


# ---------------------------------------------------------------- $3248  get_men on a cell
def call_3248(m, D0, D1, D2, D5):
    """$3248: the first side-D5 man (byte6 0, not in a group) in the cell's bucket chain joins as the target: the lead's
    group goes to state 3 with the cell as its link, the lead walks to the man's position (mode $6c)."""
    d1 = _cellidx(D0, D1)
    d0 = _bhead(m, d1)
    if d0 == 0:
        TRACE.append("3248_empty")
        return
    while True:
        A1 = (OBJ + s16(d0)) & 0xfffff
        if m.bu(A1 + 5) == (D5 & 0xff) and m.bu(A1 + 6) == 0 and not (m.bu(A1 + 7) & 0x40):
            break
        d0 = m.wu(A1 + 0)
        if d0 == 0:
            TRACE.append("3248_none")
            return
    TRACE.append("3248_found")
    P.call_37c2(m, D2)
    A3 = (GROUP + s16(D2)) & 0xfffff
    m.ww(A3 + 24, _cell_a(m, A1))
    m.ww(A3 + 0, 3)
    A0 = (OBJ + s16(m.wu(A3 - 12))) & 0xfffff
    m.wl(A0 + 20, m.lu(A1 + 8))
    m.wb(A0 + 31, 0x10)
    m.wb(A0 + 30, 0x6c)


# ---------------------------------------------------------------- $3888 / $38ce / $390e  order senders (a cell)
def call_3888(m, D0, D1, D2):
    """$3888 go to: state 5, lead mode $1e towards the cell, then $1d70 re-routes the roster."""
    P.call_37c2(m, D2)
    A3 = (GROUP + s16(D2)) & 0xfffff
    A1 = (OBJ + s16(m.wu(A3 - 12))) & 0xfffff
    m.ww(A3 + 0, 5)
    _xy_target(m, A1, D0 & 0xff, D1 & 0xff)
    m.wb(A1 + 31, 0x10)
    m.wb(A1 + 30, 0x1e)
    P.call_1d70(m, A3)


def call_38ce(m, D0, D1, D2):
    """$38ce take food from a cell: state 2, lead mode $72 (pick up a pile)."""
    P.call_37c2(m, D2)
    A1g = (GROUP + s16(D2)) & 0xfffff
    A0 = (OBJ + s16(m.wu(A1g - 12))) & 0xfffff
    m.ww(A1g + 0, 2)
    _xy_target(m, A0, D0 & 0xff, D1 & 0xff)
    m.wb(A0 + 31, 0x10)
    m.wb(A0 + 30, 0x72)


def call_390e(m, D0, D1, D2):
    """$390e food supply line to a cell: state $c, lead mode $74, the cell index in 36(lead)."""
    P.call_37c2(m, D2)
    A3 = (GROUP + s16(D2)) & 0xfffff
    m.ww(A3 + 0, 0x0c)
    A1 = (OBJ + s16(m.wu(A3 - 12))) & 0xfffff
    _xy_target(m, A1, D0 & 0xff, D1 & 0xff)
    cell = (((D1 << 6) & 0xffff) + D0) & 0xffff
    m.ww(A1 + 36, cell)
    m.wb(A1 + 30, 0x74)
    m.wb(A1 + 31, 0x10)


# ---------------------------------------------------------------- $3bc8  the own lord holding the most of field D3
def call_3bc8(m, D2, D3):
    """$3bc8: scan the 160 leader records ($4e514, stride $20) for byte0 == D2.b and the largest signed word at D3(rec);
    A0 = the leader with the largest value (the first to reach it, strictly greater only); while the best value is 0,
    A0 follows every matching leader (so the LAST matching one when all are 0); A0 = 0 when none matches.
    Returns (A0, D0 word, D4 = $20)."""
    A1 = LEADERS
    A0 = 0
    D0 = 0
    while True:
        if m.bu(A1) == (D2 & 0xff):
            w = m.wu(A1 + s16(D3))
            if not (s16(D0) >= s16(w)):          # cmp.w 0(A1,D3.w),D0 ; bge
                D0 = w
                A0 = A1
            if D0 == 0:                           # tst.w D0 ; bne
                A0 = A1
        A1 += 0x20
        if A1 == 0x4f914:
            break
    return A0, D0, 0x20


# ---------------------------------------------------------------- $3956  the supply-line executor (mode $74 arrival)
def call_3956(m, A1, D5=0):
    """$3956: drop the group's food at the cell ($39d4 D7 = 1, shift = posture - 2), then send the lead to the own leader
    with the most food ($3bc8, field +6) with arrival mode $1a; none: $35f4 (disband the contact)."""
    A3 = (GROUP + s16(m.wu(A1 + 42))) & 0xfffff
    D0 = P.call_30fe(m, A1)
    call_39d4(m, A3, D0, 1, D5)
    A0, _, _ = call_3bc8(m, m.bu(A1 + 5), 6)
    if A0 == 0:
        TRACE.append("3956_none")
        call_35f4(m, A3)
        return
    TRACE.append("3956_lord")
    m.ww(A3 + 24, (A0 - OBJ) & 0xffff)
    d0 = m.wu(A0 + 4)
    m.wb(A1 + 20, d0 & 0x3f)
    m.wb(A1 + 21, 0x80)
    m.ww(A1 + 22, (((d0 & 0x1fc0) << 2) + 0x80) & 0xffff)
    m.wb(A1 + 30, 0x1a)
    m.wb(A1 + 31, 0x10)


# ---------------------------------------------------------------- $3da4  spy arrival (mode $7a)
def call_3da4(m, A1, A3):
    """$3da4: the lone captain A1 enters the settlement named by 24(A3): the settlement's leader gains one troops_field,
    the captain takes its owner's side, links itself at the head of the settlement's unit chain (10(A0)), mode $7e,
    flags bit 7 set / bit 4 clear; 24(A3) takes the captain's old settlement link."""
    D2 = m.wu(A3 + 24)
    A0 = (OBJ + s16(D2)) & 0xfffff
    A2 = (LEADERS + s16(m.wu(A0 + 14))) & 0xfffff
    m.ww(A2 + 8, m.wu(A2 + 8) + 1)
    m.ww(A3 + 24, m.wu(A1 + 34))
    m.wb(A1 + 31, 0x7e)
    m.wb(A1 + 7, (m.bu(A1 + 7) | 0x80) & ~0x10)
    m.wb(A1 + 5, m.bu(A0 + 5))
    m.ww(A1 + 34, (A0 - SETTL) & 0xffff)
    m.ww(A1 + 24, m.wu(A0 + 10))
    m.ww(A0 + 10, (A1 - OBJ) & 0xffff)


# ---------------------------------------------------------------- $4a7a  march and engage (the target picker)
def call_4a7a(m, D0, D1, D2):
    """$4a7a: scan the cell's chain: an enemy building (byte6 2/$10 of another side) ends the scan at once and targets its
    leader's cell (204(A3) := 2); otherwise the LAST enemy man (byte6 0 or $e, owner > 0 and not ours) wins (:= 6), else
    the last byte6 8/$14/$16 record (:= 8), else the last byte6 4 record (:= $c, its 10(rec) is the cell).  The
    lead goes to the target (state 8, link = target offset, mode $30, target 20/22)."""
    A3 = (GROUP + s16(D2)) & 0xfffff
    d1 = _cellidx(D0, D1)
    d0 = _bhead(m, d1)
    if d0 == 0:
        TRACE.append("4a7a_empty")
        return
    A2 = A4 = A5 = 0
    side = m.bu(A3 - 47)
    bld = None
    while True:
        A1 = (OBJ + s16(d0)) & 0xfffff
        b6 = m.bu(A1 + 6)
        if b6 in (0x02, 0x10):
            if m.bu(A1 + 5) != side:
                bld = A1
                break
        elif b6 in (0x00, 0x0e):
            o = s8(m.bu(A1 + 5))
            if o > 0 and (o & 0xff) != side:
                A2 = A1
        else:
            if b6 == 0x08:
                A4 = A1
            if b6 in (0x14, 0x16):
                A4 = A1
            if b6 == 0x04:
                A5 = A1
        d0 = m.wu(A1 + 0)
        if d0 == 0:
            break
    if bld is not None:
        TRACE.append("4a7a_bld")
        L = (LEADERS + s16(m.wu(bld + 14))) & 0xfffff
        D1l = (L - OBJ) & 0xffffffff
        D3 = m.wu(L + 4)
        m.ww(A3 + 204, 2)
        D3, D4 = _unpack_4b80(D3)
    elif A2:
        TRACE.append("4a7a_man")
        D1l = (A2 - OBJ) & 0xffffffff
        D3, D4 = m.wu(A2 + 8), m.wu(A2 + 10)
        m.ww(A3 + 204, 6)
    elif A4:
        TRACE.append("4a7a_A4")
        D1l = (A4 - OBJ) & 0xffffffff
        D3, D4 = m.wu(A4 + 8), m.wu(A4 + 10)
        m.ww(A3 + 204, 8)
    elif A5:
        TRACE.append("4a7a_A5")
        D1l = (A5 - OBJ) & 0xffffffff
        D3 = m.wu(A5 + 10)
        m.ww(A3 + 204, 0x0c)
        D3, D4 = _unpack_4b80(D3)
    else:
        TRACE.append("4a7a_none")
        return
    P.call_37c2(m, D2)
    m.ww(A3 + 0, 8)
    m.ww(A3 + 24, D1l & 0xffff)
    A1 = (OBJ + s16(m.wu(A3 - 12))) & 0xfffff
    m.wb(A1 + 30, 0x30)
    m.wb(A1 + 31, 0x10)
    m.ww(A1 + 20, D3)
    m.ww(A1 + 22, D4)


def _unpack_4b80(cell):
    """$4b80: D3 = ((cell & $3f) << 8) + $80, D4 = (((cell & $1fc0) << 2)) + $80 (words)."""
    D4 = cell
    D3 = (((cell & 0x3f) << 8) + 0x80) & 0xffff
    D4 = ((((D4 & 0x1fc0) << 2) & 0xffff) + 0x80) & 0xffff
    return D3, D4


# ---------------------------------------------------------------- $5fa0  set men to work (mode $22 arrival)
def call_5fa0(m, A1, A3, A5=0):
    """$5fa0: the group's target (24(A3)) is a leader record; if it is of the lead's side, ask it for a work order
    ($5cde with shift posture - 2) and hand that order to every living roster man (mode D2, 46 = D3, 36 = D4, byte 39 := 4
    when D4 == 0), the lead to mode $92; refused or another side: $35f4."""
    A0 = (OBJ + s16(m.wu(A3 + 24))) & 0xfffff
    if m.bu(A1 + 5) != m.bu(A0 + 0):
        TRACE.append("5fa0_side")
        call_35f4(m, A3)
        return
    D1 = P.call_30fe(m, A1)
    D2, D3, D4 = P.call_5cde(m, A0, D1, A5)
    if (D2 & 0xffff) == 0:
        TRACE.append("5fa0_refused")
        call_35f4(m, A3)
        return
    TRACE.append("5fa0_ok")
    d0 = m.wu(A3 - 36)
    if d0 != 0:
        while True:
            A4 = (OBJ + s16(d0)) & 0xfffff
            if s8(m.bu(A4 + 5)) > 0:
                m.wb(A4 + 31, D2)
                m.ww(A4 + 46, D3)
                m.ww(A4 + 36, D4)
                if (D4 & 0xffff) == 0:
                    m.wb(A4 + 39, 4)
            d0 = m.wu(A4 + 26)
            if d0 == 0:
                break
    m.wb(A1 + 31, 0x92)


# ---------------------------------------------------------------- $600a / $60dc  the gatherer's deposit
GOODS_KIND_ARM = {2: "fell", 6: "fell", 8: "fell", 0xa: "fell", 0xe: "fell", 4: "build", 0xc: "field"}


def call_600a(m, A1):
    """$600a: mode $42 arrival at the deposit object 46(A1): mode $46, dwell 10; a man without flag bit 6 keeps his lord
    (food -= 2, at <= 0 the food is 0 and $3c08 sends him home, return); then the lord's gather_kind (12(leader)) picks
    the arm: 2/6/8/$a/$e $60dc then mode $3e; 4 and $10 (the table at $6062 has nine words, kinds 0..$10; $10 shares $4's) the building counter loop then mode $40; $c $60dc then the field path
    (40(A1) := $16964 - $168ee) and mode $c."""
    m.wb(A1 + 31, 0x46)
    m.ww(A1 + 18, 0x0a)
    A3 = (OBJ + s16(m.wu(A1 + 46))) & 0xfffff
    A3 = (LEADERS + s16(m.wu(A3 + 14))) & 0xfffff
    if not (m.bu(A1 + 7) & 0x40):
        P.call_16848(m, A1)
        x = m.wu(A3 + 6)
        m.ww(A3 + 6, (x - 2) & 0xffff)
        if not (s16(x) > 2):                     # subi.w #2 ; bgt: true signed x - 2 > 0, overflow included
            TRACE.append("600a_hungry")
            m.ww(A3 + 6, 0)
            P.call_3c08(m, A1)
            return
    kind = m.wu(A3 + 12)
    if kind in (2, 6, 8, 0xa, 0xe):
        TRACE.append("600a_fell")
        call_60dc(m, A3)
        m.wb(A1 + 30, 0x3e)
    elif kind in (4, 0x10):
        TRACE.append("600a_build")
        A0 = (SETTL + s16(m.wu(A1 + 36))) & 0xfffff
        deliver = False
        if m.wu(A0 + 8) == 0:
            deliver = True
        else:
            v = (m.wu(A0 + 10) - 1) & 0xffff
            m.ww(A0 + 10, v)
            if v == 0:
                m.ww(A0 + 10, 0x0a)
                v = (m.wu(A0 + 8) - 1) & 0xffff
                m.ww(A0 + 8, v)
                if v == 0:
                    deliver = True
        if deliver:
            call_60dc(m, A3)
        m.wb(A1 + 30, 0x40)
    elif kind == 0xc:
        TRACE.append("600a_field")
        call_60dc(m, A3)
        m.ww(A1 + 40, 0x16964 - 0x168ee)
        m.wb(A1 + 30, 0x0c)
    else:
        raise AssertionError("gather_kind %#x jumps outside the $6062 table" % kind)


def call_60dc(m, A3):
    """$60dc: the leader's goods payoff, throttled by 16(leader): at 0 reload it ($580a6[side].word8 + 4, + $2000 for
    gather_kind >= $e) and credit one goods unit byte 24 + kind/2 - 1 (saturating at $ff)."""
    v = (m.wu(A3 + 16) - 1) & 0xffff
    m.ww(A3 + 16, v)
    if v != 0:
        TRACE.append("60dc_throttle")
        return
    side = s8(m.bu(A3 + 0)) & 0xffff
    A4 = (SIDE_ASSESS + s16((side * 0x20) & 0xffff)) & 0xfffff
    m.ww(A3 + 16, m.wu(A4 + 8) + 4)
    d0 = m.wu(A3 + 12)
    if s16(d0) >= 0x0e:
        m.ww(A3 + 16, m.wu(A3 + 16) + 0x2000)
    d0 = ((d0 >> 1) - 1) & 0xffff
    a = (A3 + 24 + s16(d0)) & 0xfffff
    if m.bu(a) != 0xff:
        TRACE.append("60dc_credit")
        m.wb(a, m.bu(a) + 1)
    else:
        TRACE.append("60dc_full")


# ---------------------------------------------------------------- $6128  take equipment from a cell
def call_6128(m, D0, D1, D2):
    """$6128: scan the cell's chain for the first record of byte6 $a or $2c (or $18 with byte7 $10); none: D0 = 0.
    Found: the group goes to state $a with the cell index*2 as link, the lead to mode $6e (target x, y; byte 21 := $70
    for byte6 $18, $90 when the cell's control bytes 1 / 65 are set), $1d70 re-routes, D0 = 1."""
    d1 = _cellidx(D0, D1)
    d0 = _bhead(m, d1)
    if d0 == 0:
        return 0
    while True:
        A1 = (OBJ + s16(d0)) & 0xfffff
        D3 = m.bu(A1 + 6)
        if D3 in (0x0a, 0x2c) or (D3 == 0x18 and m.bu(A1 + 7) == 0x10):
            break
        d0 = m.wu(A1 + 0)
        if d0 == 0:
            return 0
    P.call_37c2(m, D2)
    A3 = (GROUP + s16(D2)) & 0xfffff
    m.ww(A3 + 24, d1)
    m.ww(A3 + 0, 0x0a)
    A1 = (OBJ + s16(m.wu(A3 - 12))) & 0xfffff
    cell = d1 >> 1
    m.wb(A1 + 20, cell & 0x3f)
    m.wb(A1 + 21, 0x80)
    if D3 == 0x18:
        m.wb(A1 + 21, 0x70)
        A2 = (CELLCTRL + cell) & 0xfffff
        if m.bu(A2 + 1) != 0 or m.bu(A2 + 65) != 0:
            m.wb(A1 + 21, 0x90)
    m.ww(A1 + 22, ((((cell & 0x1fc0) << 2) & 0xffff) + 0x80) & 0xffff)
    m.wb(A1 + 31, 0x10)
    m.wb(A1 + 30, 0x6e)
    P.call_1d70(m, A3)
    return 1


# ---------------------------------------------------------------- $6352 / $638c  hand goods to men's equipment slots
def call_6352(m, A3, D2, D3, D5):
    """$6352: D2 units of item type D3 (2 * (i + 1), i = pike..cannon) join the group's carried stock 84 + D5 (D5 = 12 i):
    the lot is offered to the lead, then to every roster man ($638c); what nobody takes is stored back.  Returns D2."""
    D2 = (D2 + m.wu(A3 + 84 + s16(D5))) & 0xffff
    if D2 == 0:
        return 0
    m.ww(A3 + 84 + s16(D5), 0)
    A2 = (OBJ + s16(m.wu(A3 - 12))) & 0xfffff
    D2 = call_638c(m, A3, A2, D2, D3)
    if D2 == 0:
        return 0
    d0 = m.wu(A3 - 36)
    if d0 != 0:
        while True:
            A2 = (OBJ + s16(d0)) & 0xfffff
            D2 = call_638c(m, A3, A2, D2, D3)
            if D2 == 0:
                return 0
            d0 = m.wu(A2 + 26)
            if d0 == 0:
                break
    m.ww(A3 + 84 + s16(D5), m.wu(A3 + 84 + s16(D5)) + D2)
    return D2


def call_638c(m, A3, A2, D2, D3):
    """$638c: offer one man A2 the item type D3: weapons (D3 <= 6: pike, sword, bow) go to byte 44, tools (7..10) to byte 33;
    D3 >= $e (catapult, cannon) only for a man with flags bit 4, byte 44; $c (pot) and anything $b..$d is refused.  An empty
    slot takes it (D2 - 1); a lower tier is replaced (D2 - 1) and the displaced item goes back through $6352 as one unit.
    Returns the new D2 word."""
    D3b = s8(D3)
    D4 = 0x21
    if not (D3b > 6):
        D4 = 0x2c
    if D3b > 0x0a:
        if not (m.bu(A2 + 7) & 0x10):
            TRACE.append("638c_noflag")
            return D2
        if D3b < 0x0e:
            TRACE.append("638c_pot")
            return D2
        D4 = 0x2c
    D0 = m.bu(A2 + D4)
    if D0 == 0:
        TRACE.append("638c_empty")
        m.wb(A2 + D4, D3)
        return (D2 - 1) & 0xffff
    if D3b <= s8(D0):
        TRACE.append("638c_lower")
        return D2
    TRACE.append("638c_swap")
    m.wb(A2 + D4, D3)
    D2 = (D2 - 1) & 0xffff
    # push A2 ; push D2, D3, D5 ; D3 = D0 ; D2 = 1 ; D5 = (D0 - 2) * 6 ; bsr $6352 ; pop
    call_6352(m, A3, 1, D0, (u16(D0 - 2) * 6) & 0xffff)
    return D2


# ---------------------------------------------------------------- $61f8  take equipment: the arrival executor (mode $6e)
def call_61f8(m, A3, A1_lead_group=None):
    """$61f8: 24(A3) >= 0 is a cell (2 * index): scan its chain: a byte6 $a record (a dropped kit): its equipment bytes 33
    and 44 join the group as one unit each ($6352) and are cleared, the record is unlinked; a byte6 $2c goods drop: each of
    its 8 goods words >> (posture - 2) goes to $6352, the drop is unlinked (byte6 $ff) when nothing (food included) is
    left; a byte6 $18 with byte7 $10: one unit of item $a, the record dies.  24(A3) < 0 is a leader record: each of its 8
    goods bytes >> (posture - 2) moves to the group.  Always ends in $35f4."""
    D6 = m.wu(A3 + 24)
    if s16(D6) < 0:
        TRACE.append("61f8_lord")
        A0 = (OBJ + s16(D6)) & 0xfffff
        A1 = (OBJ + s16(m.wu(A3 - 12))) & 0xfffff
        for D1 in range(8):
            D2 = m.bu(A0 + 24 + D1)
            sh = P.call_30fe(m, A1)
            D2 = P._lsr(D2, sh)
            m.wb(A0 + 24 + D1, m.bu(A0 + 24 + D1) - D2)
            call_6352(m, A3, D2, ((D1 + 1) * 2) & 0xffff, D1 * 12)
        call_35f4(m, A3)
        return
    d0 = _bhead_cell(m, D6)
    if d0 == 0:
        TRACE.append("61f8_empty")
        call_35f4(m, A3)
        return
    D6 >>= 1
    while True:
        A0 = (OBJ + s16(d0)) & 0xfffff
        b6 = m.bu(A0 + 6)
        unlink = False
        if b6 == 0x0a:
            TRACE.append("61f8_kit")
            D3 = m.bu(A0 + 33)
            if D3 != 0:
                call_6352(m, A3, 1, D3, (u16(D3 - 2) * 6) & 0xffff)
            D3 = m.bu(A0 + 44)
            if D3 != 0:
                call_6352(m, A3, 1, D3, (u16(D3 - 2) * 6) & 0xffff)
            m.wb(A0 + 44, 0)
            m.wb(A0 + 33, 0)
            unlink = True
        elif b6 == 0x2c:
            TRACE.append("61f8_drop")
            A1 = (OBJ + s16(m.wu(A3 - 12))) & 0xfffff
            D6s = P.call_30fe(m, A1)
            D7 = m.wu(A0 + 10)
            D5 = 0
            for i in range(8):
                D1 = 2 * i
                D2 = P._lsr(m.wu(A0 + 12 + D1), D6s)
                m.ww(A0 + 12 + D1, m.wu(A0 + 12 + D1) - D2)
                D7 = (D7 + m.wu(A0 + 12 + D1)) & 0xffff
                call_6352(m, A3, D2, (D1 + 2) & 0xffff, D5)
                D5 += 12
            if D7 == 0:
                TRACE.append("61f8_drop_gone")
                m.wb(A0 + 6, 0xff)
                unlink = True
        elif b6 == 0x18 and m.bu(A0 + 7) == 0x10:
            TRACE.append("61f8_18")
            call_6352(m, A3, 1, 0x0a, 0x30)
            m.wb(A0 + 5, 0)
            unlink = True
        if unlink:
            P.bucket_unlink(m, D6, (A0 - OBJ) & 0xffff)
        d0 = m.wu(A0 + 0)
        if d0 == 0:
            break
    call_35f4(m, A3)


def _bhead_cell(m, d6):
    return m.wu(BUCKETS + s16(d6))


# ---------------------------------------------------------------- $311a  relation bump
def call_311a(m, D0, D1, D2):
    """$311a: relation byte 16(A5, side2) of $580a6[side1 * $20] := clamp(byte 15(A5, side2) + D1, <= 100): it READS
    the byte one below the one it writes.  The low clamp ($ff9c) can never bind (the sum is 0..257)."""
    d0 = s8(D0 & 0xff) & 0xffff                  # ext.w D0
    d2 = s8(D2 & 0xff)                          # ext.w D2
    A5 = (SIDE_ASSESS + s16((d0 * 0x20) & 0xffff)) & 0xfffff
    v = (m.bu(A5 + 15 + d2) + D1) & 0xffff
    if s16(v) > 0x64:
        v = 0x64
    if s16(v) < -100:
        v = 0xff9c
    m.wb(A5 + 16 + d2, v)


# ---------------------------------------------------------------- $63f4  trade (mode $78 arrival)
def call_63f4(m, A3):
    """$63f4: the group sells every carried goods unit to the lord at 24(A3) (his stock byte +24+i saturates at $ff) for
    2 * price each, credit D3 = army food (36(A3)) + sales; buys back, in the posture's order ($650a row (posture - 2) * 8,
    $ff entries skipped) as much of each stocked item as the credit pays, into $6352; the credit left becomes the army's
    food (low word), the food spent goes to the lord's food, 14(lord) -= 8 (own) or += 8, $311a(+2), $35f4."""
    A0 = (OBJ + s16(m.wu(A3 + 24))) & 0xfffff
    D3 = m.wu(A3 + 36)
    D4 = 0
    for i in range(8):
        D0 = m.wu(A3 + 84 + 12 * i)
        m.ww(A3 + 84 + 12 * i, 0)
        D4 = m.bu(A0 + 24 + i) + D0
        D4 &= 0xffff
        if s16(D4) > 0xff:
            D4 = 0xff
        m.wb(A0 + 24 + i, D4)
        D5 = (_price(m, i) * 2 * D0) & 0xffffffff
        D3 = (D3 + D5) & 0xffffffff
    off = m.wu(A3 + 60)
    if off != 0:
        off = ((off - 2) & 0xffff) * 8 & 0xffffffff
    A4 = BUYROW + s16(off & 0xffff)
    for D2 in range(8):
        D0 = m.bu(A4 + D2)
        if D0 & 0x80:
            continue
        D4 = (D4 & ~0xff) | m.bu(A0 + 24 + D0)
        if (D4 & 0xff) == 0:
            continue
        D1 = D0 * 12
        D5 = (_price(m, D0) * 2) * (D4 & 0xffff) & 0xffffffff
        D3n = (D3 - D5) & 0xffffffff
        if D3n & 0x80000000:                      # D3 < D5: afford only a part
            TRACE.append("63f4_part")
            D5 = _price(m, D0) * 2
            q, r = D3 // D5, D3 % D5
            assert q <= 0xffff
            D4 = (D4 & ~0xffff) | q
            D3 = r
        else:
            TRACE.append("63f4_all")
            D3 = D3n
        m.wb(A0 + 24 + D0, m.bu(A0 + 24 + D0) - D4)
        call_6352(m, A3, D4 & 0xffff, ((D0 + 1) * 2) & 0xffff, D1)
    D0 = (m.wu(A3 + 36) - (D3 & 0xffff)) & 0xffff
    if not (s16(m.wu(A3 + 36)) < s16(D3 & 0xffff)):          # sub.w D3,D0 ; blt: signed compare, overflow included
        m.ww(A0 + 6, m.wu(A0 + 6) + D0)
    m.ww(A3 + 36, D3 & 0xffff)
    call_35f4(m, A3)
    D0 = m.bu(A0 + 0)
    D2 = m.wu(A3 - 48)
    D1 = 8
    if D0 == D2:
        D1 = -8
    m.ww(A0 + 14, m.wu(A0 + 14) + D1)
    call_311a(m, D0, 2, D2)
