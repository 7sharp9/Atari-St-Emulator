"""141st: the commander AI `$6522` and its leaves as a Python model, transcribed from the disassembly of `$6522..$6b38`.

Not a copy of anything in `tools/pm_fsm_ref.py`: that module has `Mem`, the field addresses, `call_4562` (the pigeon, already proven by
`py/gate_pigeon_send.py`) and `s16`; this module imports them and adds the AI.

Register conventions are those of the 68000 code; a leaf takes the registers it reads and returns the ones it writes.  Flags a caller
branches on are returned as booleans (`z`).  Every routine is annotated with the instruction address it transcribes.

    $6522  call_6522        the commander AI: one pass over the 5 command slots
    $66e8  call_66e8        re-issue check for a group in a state other than 6 and 9
    $6762  call_6762        the campaign table `$67d0`
    $67ee  call_67ee        pack the cell of the record A3 and issue the order
    $6822  call_6822        issue an order: slot of the side's own group, or the side's pending record + a captain-select `$22`
    $68ee  call_68ee        the cost of a march
    $68fe  call_68fe        the nearest enemy lord with fewer than D1 men at home
    $69b4  call_69b4        the best own lord by (word D1 of the lord * 8) / distance
    $6a3a  call_6a3a        the order executor loop over the slots 1..4 (the leaves `$6ac6`/`$6b38` through `exec_hook`)
    $6ac6  call_6ac6        route one slot's order: now, or by pigeon
"""
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_ref import s16, u16, s8

OBJ = P.OBJ                   # $51b66
CMD = 0x58016                 # command buffer: 5 slots of 6 bytes
CMD_END = 0x58034
GROUPS = 0x51538              # group-order table: 5 records of $13c
GROUP_XREF = 0x58042          # words: the offset in `$51538` of each side's own group (0 = none)
LORDS = 0x4e514               # leader records, 32 bytes
LORDS_END = 0x4f914
ASSESS = 0x580a6              # per-side block, $20 bytes
TICK = 0x2df72                # the tick counter
RNG_BITS = 0x57fec            # a word read by `$6762`
CAMPAIGN = 0x67d0             # {id, order type, posture} x n, terminated by id 0 (code segment)
STATE_FLAGS = 0x6750          # byte table indexed by the group state, read by `$66e8`
GOAL_STATE = 0x6888           # word table indexed by the order type, read by `$6822`
LINK_FLAG = 0x71fe            # word: `$6a3a` calls `$6eb6` when set


def sx8(v):
    return s8(v)


def sp16(v):
    """A word used as the signed index of `adda.w` / `lea 0(An,Dn.w)`."""
    return s16(v)


# ---------------------------------------------------------------- $6822
def call_6822(m, A0, A1, D7, D0, D1):
    """`$6822` (`set_pack`): issue order D0 (type) with parameter D1 (a packed cell, `x << 8 | y`) for the group of record A1
    (A1 = base + D7, D7 = the group's word offset 0..10) of the slot A0.  Returns D0 = 1 issued, 0 refused.

    `$6888[type]` is the group state that order puts the group in; a group already in it refuses the order (D0 = 0), except
    group 0 with the march order `$0c`.  Otherwise the group's link word 4(A1) := D7 (the "order pending" mark `$6522` tests), and
    D2 = side * $13c + $4c + D7 = the group's offset in the table.  When that is the side's own group (`$58042[2 * side]`) the order
    goes straight into the slot (byte 1, word 2); otherwise it is written to the side's queued-order bytes (base + 1, base + 2: the
    record header, NOT the group's own entry) and the slot gets the type `$22` with D7 as its parameter."""
    d0 = D0 & 0xffff
    d2 = m.wu((GOAL_STATE + sp16(d0)) & 0xfffff)
    if d2 != 0 and d2 == m.wu(A1 + 76):                 # beq $683e ; cmp.w 76(A1),D2 ; bne $683e
        if (D7 & 0xffff) != 0 or d0 != 0xc:             # tst.w D7 ; bne refuse ; cmp.w #$c,D0 ; bne refuse
            return 0
    m.ww(A1 + 4, D7)                                    # $683e  move.w D7,4(A1)
    side = m.wu(A1 + 28)
    d2 = ((side * 0x13c) + 0x4c + (D7 & 0xffff)) & 0xffff   # mulu #$13c ; addi.w #$4c ; add.w D7 (all .w on the low word)
    d3 = (side + side) & 0xffff
    if d2 == m.wu((GROUP_XREF + sp16(d3)) & 0xfffff):   # cmp.w 0(A2,D3.w),D2
        m.wb(A0 + 1, D0)
        m.ww(A0 + 2, D1)
    else:
        nd7 = (-(D7 & 0xffff)) & 0xffff                 # neg.w D7 ; 1(A1,D7.w) = base + 1
        m.wb(A1 + sp16(nd7) + 1, D0)
        m.ww(A1 + sp16(nd7) + 2, D1)
        m.wb(A0 + 1, 0x22)
        m.ww(A0 + 2, D7)
    return 1


# ---------------------------------------------------------------- $67ee
def call_67ee(m, A0, A1, A3, D7, D0):
    """`$67ee` (`set_town`): the cell word 4(A3) {x: bits 0-5, y: bits 6-12} of the record A3 becomes `x << 8 | y`, then `$6822`."""
    c = m.wu(A3 + 4)
    d1 = ((c & 0x3f) << 8) & 0xffff
    d2 = c >> 6
    d1 = (d1 + d2) & 0xffff
    return call_6822(m, A0, A1, D7, D0, d1)


# ---------------------------------------------------------------- $68ee
def call_68ee(D1, D3):
    """`$68ee`: D0 = D3 >> 1; D1 = (((D1 >> 3) + 1) * D0 + D0) low word.  D1 is the men that march (word)."""
    d0 = (D3 & 0xffff) >> 1
    d1 = ((D1 & 0xffff) >> 3) + 1
    d1 = (d1 * d0) & 0xffffffff                         # mulu D0,D1: a long product
    return (d1 + d0) & 0xffff                           # add.w D0,D1 (the high word keeps the product's, never read)


def _cheb(c, x, y):
    """The Chebyshev distance between the packed cell c and (x, y), the way `$68fe`/`$69b4` build it (words, `abs`, exg)."""
    d6 = s16((c & 0x3f) - x)
    d6 = -d6 if d6 < 0 else d6
    d7 = s16((c >> 6) - y)
    d7 = -d7 if d7 < 0 else d7
    return d7 if not s16(d6) > s16(d7) else d6          # cmp.w D7,D6 ; bgt keep ; exg D7,D6


# ---------------------------------------------------------------- $68fe
def call_68fe(m, A1, A2, D1):
    """`$68fe` (`closest_...`): the nearest lord of ANOTHER side than the record A2's (a zero nation is skipped, `$4e514..$4f914`)
    whose men at home (word 8) are fewer than D1 (signed), by Chebyshev distance plus the per-side bias byte
    `$580a6 + own*$20 + 15 + nation*$20 - 1` >> 2 (arithmetic).  Ties go to the later lord.  Returns (D3, A3, z): z means none
    (D3 = $7fff) or, for a group in state `$d` / 8, that the best lord is the group's target already (`100(A1)`)."""
    x = m.bu(A2 + 8)
    y = m.bu(A2 + 10)
    own = m.bu(A2 + 5)
    A4 = (ASSESS + own * 0x20) & 0xfffff
    D3 = 0x7fff
    A3 = None
    a0 = LORDS
    while a0 != LORDS_END:
        nat = m.bu(a0)
        if nat != 0 and nat != own:
            d6 = _cheb(m.wu(a0 + 4), x, y)
            bias = s8(m.bu((A4 + 16 + ((nat * 0x20 - 1) & 0xffff)) & 0xfffff)) >> 2    # asr.b #2
            d6 = (d6 + bias) & 0xffff
            if not s16(D3) < s16(d6):                    # cmp.w D6,D3 ; blt skip
                if s16(D1) > s16(m.wu(a0 + 8)):          # cmp.w 8(A0),D1 ; ble skip
                    D3 = d6
                    A3 = a0
        a0 += 32
    if D3 == 0x7fff:
        return D3, A3, True
    st = m.wu(A1 + 76)
    if st == 0xd or st == 8:
        return D3, A3, ((A3 - OBJ) & 0xffff) == m.wu(A1 + 100)
    return D3, A3, False


# ---------------------------------------------------------------- $69b4
def call_69b4(m, A2, D1, D0=0):
    """`$69b4` (`closest_...`): among the lords of the record A2's OWN side whose word D1 (8 = men at home, 6 = food) is above 1 (signed),
    the best score, taken as the highest: the word << 3, divided by the distance (a lord on A2's own cell scores `$7fff` and is taken
    without comparison; ties go to the later lord).  Returns (D3, A3, z): D3 = `$ffff` / z when there is none.

    The divide is `divu D6,D0` on the whole LONGWORD D0, and only the low word of D0 is loaded per lord (`move.w`, `lsl.w`): the
    high word is the REMAINDER of the previous lord's divide (`divu` leaves remainder:quotient in D0).  So a lord's score is
    `(previous remainder << 16 | word << 3) / distance`: when that overflows 16 bits the divide leaves D0 unchanged and the score is
    the raw `word << 3`; otherwise it is a number far above the true quotient.  D0's high word is 0 on entry (D0 is a `mulu` product
    or a `moveq`/`move.w` of a small value at every call site) and the routine restores D0 on exit."""
    x = m.bu(A2 + 8)
    y = m.bu(A2 + 10)
    own = m.bu(A2 + 5)
    D3 = 0xffff
    A3 = None
    d0 = D0 & 0xffffffff
    a0 = LORDS
    while a0 != LORDS_END:
        nat = m.bu(a0)
        if nat != 0 and nat == own:
            w = m.wu((a0 + (D1 & 0xffff)) & 0xfffff)
            d0 = (d0 & 0xffff0000) | w                           # move.w 0(A0,D1.w),D0
            if s16(w) > 1:
                d0 = (d0 & 0xffff0000) | ((w << 3) & 0xffff)     # lsl.w #3,D0
                d6 = _cheb(m.wu(a0 + 4), x, y)
                if d6 == 0:
                    d0 = (d0 & 0xffff0000) | 0x7fff              # move.w #$7fff,D0 ; bra $6a1c: no comparison
                    D3, A3 = 0x7fff, a0
                else:
                    q, r = divmod(d0, d6)                        # divu D6,D0
                    if q <= 0xffff:
                        d0 = (r << 16) | q
                    if not s16(D3) > s16(d0 & 0xffff):           # cmp.w D0,D3 ; bgt skip
                        D3, A3 = d0 & 0xffff, a0
        a0 += 32
    return D3, A3, D3 == 0xffff


# ---------------------------------------------------------------- $6762
def call_6762(m, A0, A1, D7):
    """`$6762` (`end_rest...`, the campaign table): scan `$67d0` ({id, order type, posture}, 6 bytes, id 0 ends) for the entry whose id
    equals the group's 268(A1); id `$d` additionally needs 280(A1) == 2.  The group's target record (OBJ + 100(A1)) must have byte 0
    equal to the low byte of the group's owner word 28(A1).  Then posture 136(A1) := the entry's posture, or `($57fec & 3) + 2` when
    that is 0, and the order is issued toward the target (`$67ee`).  D0 = 1 even if `$6822` refused, 0 when nothing matched or a
    test failed (the scan ends at the first id match: a failed test does not look at later entries)."""
    a4 = CAMPAIGN
    while True:
        d0 = m.wu(a4)
        if d0 == 0:
            return 0
        if d0 == m.wu(A1 + 268):
            if d0 == 0xd and m.wu(A1 + 280) != 2:
                return 0
            A3 = (OBJ + sp16(m.wu(A1 + 100))) & 0xfffff
            if m.bu(A3) != (m.wu(A1 + 28) & 0xff):
                return 0
            d0 = m.wu(a4 + 2)
            d1 = m.wu(a4 + 4)
            if d1 == 0:
                d1 = ((m.wu(RNG_BITS) & 3) + 2) & 0xffff
            m.ww(A1 + 136, d1)
            call_67ee(m, A0, A1, A3, D7, d0)
            return 1
        a4 += 6


# ---------------------------------------------------------------- $66e8
def call_66e8(m, A0, A1, A2, D2, D7):
    """`$66e8` (`check_va...`): a group in a state other than 6 and 9 re-issues the march-to-the-lead order (`$02`, toward the group's
    own lead A2's cell) when its target no longer fits the state.  `$6750[state]` selects the tests on the target record
    (OBJ + 100(A1)): bit 0 byte0 != D2.b, bit 1 byte0 == D2.b, bit 2 its word 8 <= 1, bit 3 (state `$d`): posture := 2 when
    280(A1) == 4, and 40(A1) (the first man) == 0.  No test fires: D0 = 0.  Returns D0 (the `$6822` result when it fired)."""
    flags = m.bu(STATE_FLAGS + m.wu(A1 + 76))            # the state word is the byte index: a state above $11 reads code
    A3 = (OBJ + sp16(m.wu(A1 + 100))) & 0xfffff
    fire = False
    if flags & 1:
        if m.bu(A3) != (D2 & 0xff):
            fire = True
    if not fire and flags & 2:
        if m.bu(A3) == (D2 & 0xff):
            fire = True
    if not fire and flags & 4:
        if s16(m.wu(A3 + 8)) <= 1:
            fire = True
    if not fire:
        if not flags & 8:
            return 0
        if m.wu(A1 + 280) == 4:
            m.ww(A1 + 136, 2)
        if m.wu(A1 + 40) != 0:
            return 0
    d1 = ((m.wu(A2 + 8) & 0xff00) | m.bu(A2 + 10)) & 0xffff        # move.w 8(A2),D1 ; move.b 10(A2),D1
    return call_6822(m, A0, A1, D7, 2, d1)


# ---------------------------------------------------------------- $6522
TRACE = []                    # the arm each group walked, for the coverage line


def call_6522(m):
    """`$6522` (`_compute...`): once per tick, for each of the 5 command slots at `$58016` whose state byte (4(A0)) is 4 (an AI side)."""
    A0 = CMD
    while A0 != CMD_END:
        if m.bu(A0 + 4) == 4:
            _slot(m, A0)
        A0 += 6


def _slot(m, A0):
    side = m.bu(A0)
    base = (GROUPS + sp16((side * 0x13c) & 0xffff)) & 0xfffff    # mulu #$13c ; lea 0(A1,D0.w): the word is a signed index
    if m.lu(base) != 0:                                          # a queued order (player / script): copy and clear
        m.wb(A0 + 1, m.bu(base + 1))
        m.ww(A0 + 2, m.wu(base + 2))
        m.wl(base, 0)
        TRACE.append("queued")
        return
    D7 = 10
    while D7 >= 0:
        A1 = base + D7
        D2 = m.wu(A1 + 28)
        if s16(D2) <= 0 or m.wu(A1 + 4) != 0:
            TRACE.append("skip_nogroup" if s16(D2) <= 0 else "skip_busy")
            D7 -= 2
            continue
        A2 = (OBJ + sp16(m.wu(A1 + 64))) & 0xfffff
        st = m.wu(A1 + 76)
        r = None
        if st == 9:
            r = _decide(m, A0, A1, A2, D2, D7)
        elif st == 6:
            if s16((m.wu(A1 + 256) + 0x14) & 0xffff) > s16(m.wu(TICK)):       # cmp.w $2df72,D0 ; bgt next
                TRACE.append("wait")
                D7 -= 2
                continue
            if call_6762(m, A0, A1, D7) != 0:
                TRACE.append("campaign")
                return
            r = _decide(m, A0, A1, A2, D2, D7)
        else:
            d0 = call_66e8(m, A0, A1, A2, D2, D7)
            TRACE.append("recheck_issue" if d0 else "recheck_none")
            if d0 != 0:
                return
        if r == "done":
            return
        D7 -= 2


def _decide(m, A0, A1, A2, D2, D7):
    """`$65b4`: the steps 2-4 of `strategy.md`.  Returns "done" when the slot is finished, None for the next group."""
    # step 2: fewer than 22 men -> go and get men from an own lord
    if s16(m.wu(A1 + 52)) < 0x16:
        D3, A3, z = call_69b4(m, A2, 8)
        if not z:
            m.ww(A1 + 136, 2)
            call_67ee(m, A0, A1, A3, D7, 8)
            TRACE.append("getmen")
            return "done"
    # $65dc
    if D7 != 0:
        A3g = A1 - D7
        if m.wu(A3g + 76) == 0xd and m.wu(A3g + 280) == 4:         # escort
            m.ww(A1 + 136, 2)
            A4 = (OBJ + sp16(m.wu(A3g + 292))) & 0xfffff
            d1 = ((m.wu(A4 + 10) & 0xff00) | m.bu(A4 + 8)) & 0xffff   # move.w 10(A4),D1 ; move.b 8(A4),D1
            call_6822(m, A0, A1, D7, 0xc, d1)
            TRACE.append("escort")
            return "done"
    # $661a
    d1 = (m.wu(A1 + 52) - 4) & 0xffff
    A3 = None
    if s16(d1) > 0:
        D3, A3, z = call_68fe(m, A1, A2, d1)
        if not z:
            d1 = call_68ee(d1, D3)
            if not s16(d1) > s16(m.wu(A1 + 112)):                 # cmp.w 112(A1),D1 ; bgt $66a4
                m.ww(A1 + 136, 4)
                call_67ee(m, A0, A1, A3, D7, 0xc)
                TRACE.append("attack")
                return "done"
            D3, A3, z = call_69b4(m, A2, 6)                       # $66a4: the food fallback
            if z:
                TRACE.append("food_none")
                return None
            call_67ee(m, A0, A1, A3, D7, 6)
            TRACE.append("food")
            return "done"
    # $664c
    D3, A3, z = call_69b4(m, A2, 8)
    if not z:
        A4 = A3
        d1 = (m.wu(A1 + 52) + m.wu(A3 + 8)) & 0xffff
        D3b, A3b, z2 = call_68fe(m, A1, A2, d1)
        if not z2:
            m.ww(A1 + 136, 2)
            call_67ee(m, A0, A1, A4, D7, 8)
            TRACE.append("getmen2")
            return "done"
    if D7 == 0:
        TRACE.append("idle0")
        return None
    if m.wu(A1 + 52) == 0:
        TRACE.append("idle_nomen")
        return None
    m.ww(A1 + 136, 2)                                            # $668c: order $04
    call_6822(m, A0, A1, D7, 4, (D7 << 8) & 0xffff)
    TRACE.append("xfer")
    return "done"


# ---------------------------------------------------------------- $6ac6 / $6a3a
def call_6ac6(m, A0, exec_hook):
    """`$6ac6`: route the order of the slot A0.  Type 0: nothing.  Type >= `$22`, a side without a group in `$58042`, a group without a
    sender (word 48) run `exec_hook` (= `$6b38`) at once; a side with no entry in `$58042` does nothing.  Otherwise the sender's cell (bytes 8/10 of
    OBJ + word 48) is compared with the cell of the record OBJ + word at `$51b5a`: equal -> `-72(A1)` := 0 and the order runs at once,
    else `$4562`, the pigeon."""
    t = m.bu(A0 + 1)
    if t == 0:
        return "none"
    if s8(t) >= 0x22:                                             # cmp.b #$22,D0 ; bge (signed byte)
        exec_hook(m, A0, None)
        return "exec_hi"
    d2 = s16(s8(m.bu(A0)) & 0xffff) * 2                           # move.b 0(A0),D2 ; ext.w ; add.w D2,D2
    d2 = m.wu((GROUP_XREF + d2) & 0xfffff)
    if d2 == 0:
        return "none_xref"
    A1 = (GROUPS + sp16(d2)) & 0xfffff
    d0 = m.wu(A1 + 48)
    if d0 == 0:
        exec_hook(m, A0, d2)
        return "exec_nosender"
    A2 = (OBJ + sp16(d0)) & 0xfffff
    A1b = (OBJ + sp16(m.wu(OBJ - 12))) & 0xfffff
    if m.bu(A2 + 8) == m.bu(A1b + 8) and m.bu(A2 + 10) == m.bu(A1b + 10):
        m.ww(A1b - 72, 0)
        exec_hook(m, A0, d2)
        return "exec_same_cell"
    P.call_4562(m, A0, d2)
    return "pigeon"


def call_6a3a(m, exec_hook):
    """`$6a3a` (`_turn...`): the order executor, once per tick: for each of the slots 1..4 at `$5801c` the state byte 4(A0) selects through
    the word table `$6a80` (index = the state byte, offset to `$6a80`): 0 and `$a` do nothing, 2 and 4 run `$6ac6`, 6 and 8 first run the
    serial-link write / read (`$1c390` / `$1c340`, asserted off here); then the slot's type byte and parameter word are cleared.  After
    the loop a nonzero `$71fe` is cleared and `$6eb6` runs (asserted off).  Returns the routes `$6ac6` took."""
    routes = []
    A0 = 0x5801c
    while A0 < CMD_END:
        st = m.bu(A0 + 4)
        assert st in (0, 2, 4, 0xa), f"slot state {st}"
        if st in (2, 4):
            routes.append(call_6ac6(m, A0, exec_hook))
        m.wb(A0 + 1, 0)
        m.ww(A0 + 2, 0)
        A0 += 6
    assert m.wu(LINK_FLAG) == 0, "$71fe set"
    return routes
