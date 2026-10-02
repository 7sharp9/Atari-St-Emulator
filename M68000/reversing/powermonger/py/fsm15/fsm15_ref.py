"""Python model of the entity-mode handlers of the $15000 page (fsm15 area).

Each `h_XX(m, A1, D6, D7)` is one mode body of the `$14b62` entity iterator, transcribed from the whole-image listing
(`tools/disassemble.py --snap <snap> --all 14ff8 16a00`).  They plug into `pm_fsm_ref.reconstruct` through its
`SHEP_MODES` dispatch dict (process-local): `install()` adds them, so the iterator, the epilogues ($161c4/$16202/$1622c)
and every callee already modelled (`call_16848`, `call_3c08`, `call_35f4`, `call_1d70`, `call_1b8c`, `call_4bc8`,
`engage_56a6`, `call_4f68`, `call_5c2c`, `step_toward`, `rotate`, `rng_12c9a`) are reused, not copied.

New leaves modelled here: `$34f2` (town summons), `$1b2a` (join a group), `$159a4`/`$159de` (merchant goods),
`$15fa8` (fishing-cell collision), `$5c80`'s return flag.
"""
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_ref import s8, s16, OBJ, SETTL, GROUP, LEADER, BUCKETS

TREES = 0x4d252
PLANES = 0x3f86c
NEXT = None                       # `bra $1622c`: next record, no write-back


def ad(base, w):                  # `lea base,An ; adda.w w,An`: the word is sign-extended
    return (base + s16(w)) & 0xfffff


def dec18(m, A1):
    """`subq/subi.w #1,18(A1)`: store, and return (new word, true signed result): `bge`/`bgt`/`blt` test N xor V, i.e. the
    mathematical sign of (old - 1), which differs from the wrapped word's sign only at old == $8000."""
    old = m.wu(A1 + 18)
    new = (old - 1) & 0xffff
    m.ww(A1 + 18, new)
    return new, s16(old) - 1


def end_161c4(m, A1, D6, D7): P.epilogue_161c4(m, A1, D6, D7)
def end_16202(m, A1, D6, D7): P.epilogue_16202(m, A1, D6, D7)


def end_161bc(m, A1, D6, D7):     # $161bc: clr.w 12(A1) ; clr.b 17(A1) ; fall into $161c4
    m.ww(A1 + 12, 0)
    m.wb(A1 + 17, 0)
    P.epilogue_161c4(m, A1, D6, D7)


def target_cell(m, A1, w, y_mask=True, plus=0x80):
    """`andi.w #$3f,D0 ; move.b D0,20(A1) ; move.b #$80,21(A1) ; ... andi.w #$1fc0 ; lsl.w #2 ; addi.w #$80 ; move.w D0,22(A1)`."""
    m.wb(A1 + 20, w & 0x3f)
    m.wb(A1 + 21, 0x80)
    m.ww(A1 + 22, (((w & 0x1fc0) << 2) + plus) & 0xffff)


def target_cell_nomask(m, A1, w):
    """merchant variant: `lsl.w #2,D0 ; move.b #$80,D0 ; move.w D0,22(A1)` (no mask on the y part)."""
    m.wb(A1 + 20, w & 0x3f)
    m.wb(A1 + 21, 0x80)
    m.ww(A1 + 22, (((w << 2) & 0xff00) | 0x80) & 0xffff)


def upkeep_ret(m, A1):
    """D0 returned by `$5c80` (its Z flag is what `bne` after `jsr $16848` reads): 1 if morale < 0 or the cap exceeds it."""
    morale = m.bs(A1 + 45)
    if morale < 0:
        return 1
    D0 = s8(m.bu(P.SURVIV + (m.bu(A1 + 7) & 0x1f)))
    return 1 if D0 > morale else 0


def call_16848_flag(m, A1):
    r = upkeep_ret(m, A1)                       # computed first: 16848's side byte write does not feed it
    P.call_16848(m, A1)
    return r


# ----------------------------------------------------------------------------------------------- leaves
def call_34f2(m, A3, A5):
    """$34f2: A3 = group, A5 = the lord's record: send every able man of the lord's town chain to the lord's cell
    (20/22 := cell, 31 := $10, 30 := $14, 46 := the lead offset if the group is in state 3); cells step by $50000 in D1."""
    D2 = m.wu(A3 - 12) if m.wu(A3) == 3 else 0
    w4 = m.wu(A5 + 4)
    D1hi = (((w4 & 0x3f) << 8) & 0xff00) | 0x80          # lsl.w #8 ; move.b #$80  -> word
    D1lo = ((((w4 & 0x1fc0) << 2)) & 0xff00) | 0x80
    D1 = ((D1hi << 16) | D1lo) & 0xffffffff
    D0 = m.wu(A5 + 2)
    guard = 0
    while D0 != 0:                                     # $3526
        A0 = ad(SETTL, D0)
        h = m.wu(A0 + 10)
        while h != 0:                                  # $3534
            A1 = ad(OBJ, h)
            guard += 1
            assert guard < 4000
            ok = False
            if m.bs(A1 + 5) > 0 and not (m.bu(A1 + 7) & 0x40):
                if m.bu(A1 + 7) & 0x80:
                    ok = True
                elif not (m.bu(A1 + 7) & 0x10) and m.bu(A1 + 31) not in (0x5c, 0x60, 0x62):
                    ok = True
            if ok:
                m.wl(A1 + 20, D1)
                m.wb(A1 + 31, 0x10)
                m.wb(A1 + 30, 0x14)
                m.ww(A1 + 46, D2)
                D1 = (D1 + 0x50000) & 0xffffffff
            h = m.wu(A1 + 24)
        D0 = m.wu(A0 + 8)                              # next settlement
    return


def call_1b2a(m, A0, A1):
    """$1b2a: A0 = the group lead, A1 = the man: join the group roster (head of the chain word[+26]).  Returns D0 (1 joined, 0 refused)."""
    D2 = m.bu(A0 + 5)
    if D2 != m.bu(A1 + 5):
        A3s = ad(SETTL, m.wu(A1 + 34))
        if m.bu(A3s + 5) != D2:
            return 0
        m.wb(A1 + 5, D2)
    A3 = ad(GROUP, m.wu(A0 + 42))
    m.ww(A3 - 24, m.wu(A3 - 24) + 1)
    m.ww(A1 + 26, m.wu(A3 - 36))
    m.ww(A3 - 36, (A1 - OBJ) & 0xffff)
    m.ww(A1 + 28, (A0 - OBJ) & 0xffff)
    m.wb(A1 + 7, m.bu(A1 + 7) | 0x40)
    return 1


def call_159a4(m, A0, A1):
    """$159a4 merch_gi: bank the two carried item codes (bytes 33, 44) into the lord's goods bytes 23(A0 + code/2)."""
    for off in (33, 44):
        D0 = m.bu(A1 + off)
        if D0 != 0:
            m.wb(A1 + off, 0)
            idx = ((s8(D0) & 0xffff) >> 1) & 0xffff
            a = (A0 + 23 + s16(idx)) & 0xfffff
            if m.bu(a) != 0xff:
                m.wb(a, m.bu(a) + 1)


def call_159de(m, A0, A1):
    """$159de merch_ta: take one good of the kind (tick word $57fec mod 6) from the lord A0 into 33 or 44 of the man."""
    D0 = m.wu(P.TICK_RNG) % 6
    a = (A0 + 24 + D0) & 0xfffff
    if m.bu(a) == 0:
        return
    m.wb(a, m.bu(a) - 1)
    D0 = ((D0 + 1) * 2) & 0xffff
    if s16(D0) >= 8:
        m.wb(A1 + 33, D0)
    else:
        m.wb(A1 + 44, D0)


def call_15fa8(m, D6, D7):
    """$15fa8 check_co: clamp (D6, D7) and test the four corner bytes of the altitude plane cell.  Returns (D0, D6, D7); D0 = 1 blocked."""
    if s16(D6) < 0:
        D6 = 0
    elif s16(D6) >= 0x4000:
        D6 = 0x3fff
    if s16(D7) < 0:
        D7 = (-s16(D7)) & 0xffff
        D7 = 0x7fff if D7 > 0x1f40 else 0
    D0 = (((D7 >> 8) << 6) + (D6 >> 8)) & 0xffff
    A4 = (PLANES + s16(D0)) & 0xfffff
    b0, b1, b64, b65 = m.bu(A4), m.bu(A4 + 1), m.bu(A4 + 64), m.bu(A4 + 65)
    lo6, lo7 = D6 & 0xff, D7 & 0xff
    if b0 == 0:
        if b1 == 0:
            if b64 != 0:                      # $1602e
                if b65 != 0:
                    return 1, D6, D7
                return (1 if lo6 < lo7 else 0), D6, D7           # sub.b D7,D0 ; bcs $1603e
            if b65 == 0:
                return 0, D6, D7
            return (1 if lo6 + lo7 > 0xff else 0), D6, D7         # add.b ; bcc -> 0
        # $1601a
        if b64 != 0 or b65 != 0:
            return 1, D6, D7
        return (0 if lo6 < lo7 else 1), D6, D7                    # sub.b ; bcs $1603a
    # $16000
    if b1 != 0 or b64 != 0 or b65 != 0:
        return 1, D6, D7
    return (0 if lo6 + lo7 > 0xff else 1), D6, D7                 # add.b ; bcs $1603a


# ----------------------------------------------------------------------------------------------- handlers
def h14(m, A1, D6, D7):                          # $1501a at_meeti, mode $14
    A3 = ad(SETTL, m.wu(A1 + 34))
    if not (m.bu(A3 + 7) & 0x80):
        m.wb(A1 + 5, m.bu(A3 + 5))
    m.wb(A1 + 31, 0x2a)
    m.ww(A1 + 18, 0x32)
    end_161c4(m, A1, D6, D7)


def h16(m, A1, D6, D7):                          # $15042 at_farme, mode $16
    P.call_16848(m, A1)
    if m.wu(0x57fd0) == 0:
        m.ww(A1 + 18, 0xff9d)
        m.wb(A1 + 30, m.bu(A1 + 31))
        m.wb(A1 + 31, 0x7c)
        end_161c4(m, A1, D6, D7)
        return
    A3 = ad(SETTL, m.wu(A1 + 34))
    A5 = ad(LEADER, m.wu(A3 + 14))
    m.ww(A5 + 6, m.wu(A5 + 6) + 2)
    if m.bu(A1 + 33) == 8:
        m.ww(A5 + 6, m.wu(A5 + 6) + 2)
    m.wl(A1 + 20, 0)
    m.wb(A1 + 20, m.bu(A1 + 42))
    m.wb(A1 + 22, m.bu(A1 + 43))
    m.wb(A1 + 31, 0x10)
    m.wb(A1 + 30, 0x18)
    end_161c4(m, A1, D6, D7)


def h18(m, A1, D6, D7):                          # $150b0 (farmer reached the field cell), mode $18
    m.ww(A1 + 40, 0x50)
    m.wb(A1 + 31, 0x0c)
    end_161c4(m, A1, D6, D7)


def _shift(m, A1):
    return P.call_30fe(m, A1) & 63                 # register-count shift: count mod 64


def h1a(m, A1, D6, D7):                          # $150c0 at_town_ (take food), mode $1a
    m.ww(0x12a24, m.wu(0x12a24) + 1)
    A3 = ad(GROUP, m.wu(A1 + 42))
    A5 = ad(OBJ, m.wu(A3 + 24))
    sh = _shift(m, A1)
    D2 = (0x10 >> sh) & 0xffff
    m.ww(A5 + 14, m.wu(A5 + 14) + D2)
    D2 = (m.wu(A5 + 6) >> sh) & 0xffff
    m.ww(A5 + 6, m.wu(A5 + 6) - D2)
    m.ww(A3 + 36, m.wu(A3 + 36) + D2)
    call_34f2(m, A3, A5)
    if m.wu(A3) == 0xc:
        m.wb(A1 + 31, 0x26)
        m.ww(A1 + 18, 0x23)
    else:
        P.call_35f4(m, A3)
    end_161c4(m, A1, D6, D7)


def h1c(m, A1, D6, D7):                          # $15122 at_town_ (get men), mode $1c
    A3 = ad(GROUP, m.wu(A1 + 42))
    A5 = ad(OBJ, m.wu(A3 + 24))
    sh = _shift(m, A1)
    m.ww(A1 + 46, (m.wu(A5 + 8) >> sh) & 0xffff)
    call_34f2(m, A3, A5)
    m.wb(A1 + 31, 0x28)
    m.ww(A1 + 18, 0x32)
    end_161c4(m, A1, D6, D7)


def h1e(m, A1, D6, D7):                          # $1515c at_camp, mode $1e
    P.call_35f4(m, ad(GROUP, m.wu(A1 + 42)))
    end_161c4(m, A1, D6, D7)


def h20(m, A1, D6, D7):                          # $15170 in_camp, mode $20
    m.wb(A1 + 31, 0x68)
    if not (m.bu(A1 + 7) & 0x20):
        m.wb(A1 + 6, 0x0e)


def h24(m, A1, D6, D7):                          # $151c2 farmer_f, mode $24
    A3 = ad(SETTL, m.wu(A1 + 34))
    target_cell(m, A1, m.wu(A3 + 12))
    m.wb(A1 + 31, 0x10)
    m.wb(A1 + 30, 0x16)
    end_161c4(m, A1, D6, D7)


def h26(m, A1, D6, D7):                          # $15200 wait_foo, mode $26
    dw, dwt = dec18(m, A1)
    if dw != 0:
        end_161bc(m, A1, D6, D7)
        return
    A3 = ad(GROUP, m.wu(A1 + 42))
    if m.wu(A3) == 0xc:
        target_cell(m, A1, m.wu(A1 + 36))
        m.wb(A1 + 30, 0x74)
        m.wb(A1 + 31, 0x10)
    else:
        P.call_35f4(m, A3)
    end_161c4(m, A1, D6, D7)


def h28(m, A1, D6, D7):                          # $15264 wait_men, mode $28
    dw, dwt = dec18(m, A1)
    if dw != 0:
        end_161bc(m, A1, D6, D7)
        return
    P.call_35f4(m, ad(GROUP, m.wu(A1 + 42)))
    end_161c4(m, A1, D6, D7)


def h2a(m, A1, D6, D7):                          # $15282 wait_mee, mode $2a
    refuse = False
    if m.wu(A1 + 18) == 0x32:
        D0 = m.wu(A1 + 46)
        if D0 != 0:
            A0 = ad(OBJ, D0)
            if m.bs(A0 + 5) <= 0:
                refuse = True
            else:
                A3 = ad(GROUP, m.wu(A0 + 42))
                if m.wu(A3) != 3:
                    refuse = True
                else:
                    old46 = m.wu(A0 + 46)
                    m.ww(A0 + 46, (old46 - 1) & 0xffff)
                    if s16(old46) - 1 >= 0:        # subi.w #1 ; blt: N xor V
                        A4s = ad(SETTL, m.wu(A1 + 34))
                        D0 = m.wu(A4s + 14)
                        if call_1b2a(m, A0, A1) != 0:
                            m.ww(LEADER + s16(D0) + 8, m.wu(LEADER + s16(D0) + 8) - 1)
                            P.call_1d70(m, A3)
                            end_161c4(m, A1, D6, D7)
                            return
    if not refuse:
        dw, dwt = dec18(m, A1)
        if dwt > 0:
            end_161c4(m, A1, D6, D7)
            return
    P.call_3c08(m, A1)
    end_161c4(m, A1, D6, D7)


def h2c(m, A1, D6, D7):                          # $152f8 set_figh, mode $2c
    P.call_4f68(m, A1)


def h2e(m, A1, D6, D7):                          # $15302 at_goto_, mode $2e
    A3 = ad(OBJ, m.wu(A1 + 48))
    D6 = m.wu(A3 + 8)
    D7 = m.wu(A3 + 10)
    m.wb(A1 + 31, 0x32)
    m.wb(A1 + 30, 0x32)
    if s8(m.bu(A3 + 31)) <= 0x2c or s8(m.bu(A3 + 30)) >= 0x3c:       # ble $15332 ; cmpi.b #$3c,30(A3) ; blt skip
        P.engage_56a6(m, A1, A3)
    end_161c4(m, A1, D6, D7)


def h30(m, A1, D6, D7):                          # $1518a at_attac, mode $30
    A3 = ad(GROUP, m.wu(A1 + 42))
    A0 = ad(OBJ, m.wu(A3 + 24))
    P.call_4bc8(m, A0, A1)
    end_161c4(m, A1, D6, D7)


def h34(m, A1, D6, D7):                          # $153b2 shooting, mode $34
    old = m.bu(A1 + 18)
    m.wb(A1 + 18, (old - 1) & 0xff)
    if s8(old) - 1 >= 0:                         # subi.b #1 ; bge: N xor V
        return
    m.wb(A1 + 31, 0x2c)
    m.wb(A1 + 30, 0x2c)


def _contact_38(m, A1):                           # $15468: begin the slaughter
    A3 = ad(OBJ, m.wu(A1 + 48))
    m.ww(A1 + 18, 0x0a)
    m.wb(A1 + 31, 0x38)
    m.wb(A3 + 7, 0x10)


def h36(m, A1, D6, D7):                          # $153cc goto_ani, mode $36 (never natural)
    A3 = ad(OBJ, m.wu(A1 + 48))
    if m.bs(A3 + 5) <= 0:
        m.wb(A1 + 6, 0x0e)
        m.wb(A1 + 31, 0x68)
        return
    tx, ty = P.s16(m.wu(A3 + 8)), P.s16(m.wu(A3 + 10))
    _c, _d, reached = P.step_toward(m, tx & 0xffff, ty & 0xffff, D6, D7, A1)
    D6 = (D6 + s8(m.bu(A1 + 12))) & 0xffff
    D7 = (D7 + s8(m.bu(A1 + 13))) & 0xffff
    if not reached:
        end_161c4(m, A1, D6, D7)
        return
    _contact_38(m, A1)
    end_161c4(m, A1, D6, D7)


def h66(m, A1, D6, D7):                          # $1540c at_goto_, mode $66
    _contact_38(m, A1)
    end_161c4(m, A1, D6, D7)


def h38(m, A1, D6, D7):                          # $1547e fighting (slaughter), mode $38
    dw, dwt = dec18(m, A1)
    if dw != 0:
        return
    A3 = ad(OBJ, m.wu(A1 + 48))
    if m.bs(A1 + 5) > 0:
        m.wb(A1 + 6, 0)
    m.wb(A3 + 6, 0x1c)
    m.wb(A3 + 5, -m.bs(A3 + 5))
    if m.bu(A1 + 7) & 0x50:                       # btst #4 / #6
        D0 = m.wu(A1 + 28)
        A4 = A1 if D0 == 0 else OBJ
        A4 = (A4 + s16(D0)) & 0xfffff
        D0 = m.wu(A4 + 42)
        if D0 != 0:
            A3g = ad(GROUP, D0)
            m.ww(A3g + 36, m.wu(A3g + 36) + 0xb4)
            P.call_35f4(m, A3g)
            if m.bs(A4 + 5) > 0:
                m.wb(A4 + 6, 0)
            return
    A4 = ad(SETTL, m.wu(A1 + 34))
    D0 = m.wu(A4 + 14)
    a = (LEADER + s16(D0) + 6) & 0xfffff
    m.ww(a, m.wu(a) + 0xb4)
    P.call_3c08(m, A1)


def h3a(m, A1, D6, D7):                          # $15518 fighting, mode $3a (never natural)
    A3 = ad(OBJ, m.wu(A1 + 48))
    A0 = (BUCKETS + 2 * s16(m.wu(A3 + 10))) & 0xfffff
    D0 = m.wu(A0)
    guard = 0
    while D0 != 0:
        A0 = ad(OBJ, D0)
        if m.bu(A0 + 6) == 4:
            m.wb(A0 + 7, 0x0d)
        D0 = m.wu(A0)
        guard += 1
        assert guard < 600
    if m.bu(A1 + 7) & 0x10:
        D0 = m.wu(A1 + 42)
        if D0 == 0:
            P.call_3c08(m, A1)
            return
        P.call_35f4(m, ad(GROUP, D0))
        return
    if m.bu(A1 + 7) & 0x40:
        A4 = ad(OBJ, m.wu(A1 + 28))
        D0 = m.wu(A4 + 42)
        P.call_35f4(m, ad(GROUP, D0))
        return
    P.call_3c08(m, A1)


def h3c(m, A1, D6, D7):                          # $15598 run_away, mode $3c
    if call_16848_flag(m, A1) != 0:
        return
    P.call_3c08(m, A1)


def h3e(m, A1, D6, D7):                          # $155ac head_for (the next tree), mode $3e
    A3 = ad(OBJ, m.wu(A1 + 46))
    A3 = ad(LEADER, m.wu(A3 + 14))
    D0 = m.wu(A1 + 36)
    if D0 == 0:
        D0 = m.wu(ad(OBJ, m.wu(A3 + 20)) + 4)
        m.ww(A1 + 36, D0)
    D1 = m.bu(A1 + 14) & 3
    guard = 0
    while True:                                   # $155e2
        A0 = ad(TREES, D0)
        D1 = (D1 - 1) & 0xffff
        found = False
        if s16(D1) < 0 and m.bu(A0 + 7) != 0x0d:
            found = True
        if not found:
            D0 = m.wu(A0 + 8)
            if D0 == 0:
                D0 = m.wu(ad(OBJ, m.wu(A3 + 20)) + 4)
            if D0 == m.wu(A1 + 36):
                break
            guard += 1
            assert guard < 400
            continue
        m.ww(A1 + 36, D0)
        target_cell(m, A1, m.wu(A0 + 10))
        m.wb(A1 + 31, 0x10)
        m.wb(A1 + 30, 0x44)
        return
    if m.bu(A1 + 7) & 0x40:                       # $15612
        D0 = m.wu(A1 + 28)
        A0 = A1 if D0 == 0 else OBJ
        A0 = (A0 + s16(D0)) & 0xfffff
        P.call_35f4(m, ad(GROUP, m.wu(A0 + 42)))
    else:
        P.call_3c08(m, A1)


def h40(m, A1, D6, D7):                          # $15680 head_for (the town), mode $40
    A0 = ad(SETTL, m.wu(A1 + 36))
    target_cell(m, A1, m.wu(A0 + 12))
    m.wb(A1 + 31, 0x10)
    m.wb(A1 + 30, 0x6a)


def h6a(m, A1, D6, D7):                          # $156e0 pottery_/workshop, mode $6a
    A3 = ad(OBJ, m.wu(A1 + 46))
    target_cell(m, A1, m.wu(A3 + 12))
    m.ww(A1 + 18, 0x0a)
    m.wb(A1 + 31, 0x46)
    m.wb(A1 + 30, 0x42)
    end_161c4(m, A1, D6, D7)


def h44(m, A1, D6, D7):                          # $156be at_fores, mode $44
    old = m.bu(A1 + 39)
    m.wb(A1 + 39, (old - 1) & 0xff)
    if not (s8(old) - 1 > 0):                    # subi.b #1 ; bgt
        m.wb(ad(TREES, m.wu(A1 + 36)) + 7, 0x0d)
        m.wb(A1 + 39, 4)
    h6a(m, A1, D6, D7)


def h46(m, A1, D6, D7):                          # $15724 wait_at_, mode $46
    dw, dwt = dec18(m, A1)
    if dw == 0:
        m.wb(A1 + 31, 0x10)


def h48(m, A1, D6, D7):                          # $158da scanning (obstacle sweep), mode $48
    D1 = (-m.bu(A1 + 16)) & 0xffff
    x, y = P.rotate(m, 0, D1, m.bu(A1 + 17))
    D3, D4 = x, y
    m.wb(A1 + 12, D3 & 0xff)
    m.wb(A1 + 13, D4 & 0xff)
    D2 = m.wu(A1 + 18)
    if s16(D2) >= 0x100:
        D2 = 0x100
    p6, p7 = D6, D7
    while True:                                   # $1590e
        p6 = (p6 + D3) & 0xffff
        if s16(p6) < 0:
            break
        p7 = (p7 + D4) & 0xffff
        if s16(p7) < 0:
            break
        if s16(p6) >= 0x4000:
            break
        if P.terrain_sample(m, p6, p7) == 0:      # dbeq: Z (blocked) ends the loop with D2 unchanged
            break
        D2 = (D2 - 1) & 0xffff
        if D2 == 0xffff:
            break
    if s16(D2) < 0:
        m.wb(A1 + 31, 0x12)
        end_16202(m, A1, D6, D7)
        return
    D0 = m.wu(A1 + 40)
    m.wb(A1 + 17, m.bu(A1 + 17) + D0)
    if (D0 & 0x80) == 0:
        m.ww(A1 + 40, (-(D0 + 4)) & 0xffff)
        end_16202(m, A1, D6, D7)
        return
    if D0 != 0x80:
        m.ww(A1 + 40, ((-D0) + 4) & 0xffff)
        end_16202(m, A1, D6, D7)
        return
    dw = (m.wu(A1 + 18) - 8) & 0xffff
    m.ww(A1 + 18, dw)
    if s16(dw) < 0:
        end_161c4(m, A1, D6, D7)
        return
    m.wb(A1 + 31, 0x4a)
    m.wb(A1 + 17, m.bu(A1 + 17) + 0x80)
    end_16202(m, A1, D6, D7)


def h4a(m, A1, D6, D7):                          # $1597a blocked, mode $4a
    D0 = m.wu(A1 + 28)
    if D0 != 0:
        m.wl(A1 + 20, m.lu(ad(OBJ, D0) + 8))
    m.ww(A1 + 40, 8)
    m.wb(A1 + 17, m.bu(A1 + 17) & 0xfc)
    m.wb(A1 + 31, 0x48)
    end_161c4(m, A1, D6, D7)


def h4c(m, A1, D6, D7):                          # $16176 captain_ , mode $4c
    A0 = ad(SETTL, m.wu(A1 + 34))
    if m.bu(A0 + 5) != m.bu(A1 + 5):
        P.call_5c2c(m, A1)
    D2 = m.wu(A1 + 42)
    if D2 != 0:
        P.call_35f4(m, ad(GROUP, D2))
    m.ww(A1 + 30, 0x8a8a)
    m.ww(A1 + 12, 0)
    m.wb(A1 + 17, 0)
    P.upkeep(m, A1)


def h4e(m, A1, D6, D7):                          # $15a0e merch_ar, mode $4e
    A0 = ad(SETTL, m.wu(A1 + 34))
    A0 = ad(LEADER, m.wu(A0 + 14))
    call_159a4(m, A0, A1)
    call_16848_flag(m, A1)
    if m.wu(0x57fd0) == 0:
        m.ww(A1 + 18, 0xff9d)
        m.wb(A1 + 30, m.bu(A1 + 31))
        m.wb(A1 + 31, 0x7c)
    else:
        m.ww(A1 + 18, 0x32)
        m.wb(A1 + 31, 0x54)
    end_161c4(m, A1, D6, D7)


def h50(m, A1, D6, D7):                          # $15a60 merch_st, mode $50
    A0 = ad(LEADER, m.wu(A1 + 46))
    call_159a4(m, A0, A1)
    m.ww(A1 + 18, 0x32)
    m.wb(A1 + 31, 0x52)
    end_161c4(m, A1, D6, D7)


def h52(m, A1, D6, D7):                          # $15a80 merch_se, mode $52
    dw, dwt = dec18(m, A1)
    if dwt >= 0:
        end_161c4(m, A1, D6, D7)
        return
    m.wb(A1 + 30, 0x4e)
    A3 = ad(SETTL, m.wu(A1 + 34))
    target_cell_nomask(m, A1, m.wu(A3 + 12))
    m.wb(A1 + 31, 0x10)
    call_159de(m, ad(LEADER, m.wu(A1 + 46)), A1)
    end_161c4(m, A1, D6, D7)


def h54(m, A1, D6, D7):                          # $15ad2 merch_at, mode $54
    dw, dwt = dec18(m, A1)
    if dwt >= 0:
        return
    A4 = (LEADER + s16(m.wu(0x4f914))) & 0xfffff
    A0s = ad(SETTL, m.wu(A1 + 34))
    A3 = ad(LEADER, m.wu(A0s + 14))
    A0 = A3
    D2 = m.bu(A1 + 14) & 7
    guard = 0
    while True:                                   # $15b00
        guard += 1
        assert guard < 40
        if m.bu(A3) != 0:
            D2 = (D2 - 1) & 0xffff
            if s16(D2) <= 0:
                break
        A0 = (A3 + 32) & 0xfffff                  # `lea 32(A3),A0` (A0, not A3: the walk never leaves the home lord)
        if A3 == A4:
            A3 = LEADER
    m.ww(A1 + 46, (A3 - LEADER) & 0xffff)
    target_cell_nomask(m, A1, m.wu(A3 + 4))
    m.wb(A1 + 30, 0x50)
    m.wb(A1 + 31, 0x10)
    call_159de(m, A0, A1)


def h5e(m, A1, D6, D7):                          # $15b5e fish_arr, mode $5e
    call_16848_flag(m, A1)
    if m.wu(0x57fd0) == 0:
        m.ww(A1 + 18, 0xff9d)
        m.wb(A1 + 30, m.bu(A1 + 31))
        m.wb(A1 + 31, 0x7c)
    else:
        m.ww(A1 + 18, 0x32)
        m.wb(A1 + 31, 0x56)
    end_161c4(m, A1, D6, D7)


def _fish_target(m, A1):
    w = m.wu(A1 + 42)
    m.wb(A1 + 20, w & 0x3f)
    m.wb(A1 + 21, 0x70)
    A3 = ad(PLANES, w)
    if m.bu(A3 + 1) != 0 or m.bu(A3 + 65) != 0:
        m.wb(A1 + 21, 0x90)
    m.ww(A1 + 22, (((w & 0x1fc0) << 2) + 0x80) & 0xffff)


def h56(m, A1, D6, D7):                          # $15b94 fish_at_ (go to the fishing cell), mode $56
    dw, dwt = dec18(m, A1)
    if dwt >= 0:
        end_161c4(m, A1, D6, D7)
        return
    _fish_target(m, A1)
    m.wb(A1 + 30, 0x58)
    m.wb(A1 + 31, 0x10)
    end_161c4(m, A1, D6, D7)


def h58(m, A1, D6, D7):                          # $15bec fish_at_ (arrived), mode $58
    m.ww(A1 + 18, 0x0a)
    m.wb(A1 + 31, 0x5a)
    end_161c4(m, A1, D6, D7)


def h62(m, A1, D6, D7):                          # $15bfc fish_get (idle between trips), mode $62
    dw, dwt = dec18(m, A1)
    if dwt >= 0:
        return
    D0 = m.wu((BUCKETS + s16((m.wu(A1 + 42) * 2) & 0xffff)) & 0xfffff)
    guard = 0
    while D0 != 0:
        A3 = ad(OBJ, D0)
        if m.bu(A3 + 6) == 0x20:
            m.wb(A3 + 6, 0x18)
            break
        D0 = m.wu(A3)
        guard += 1
        assert guard < 600
    m.wb(A1 + 7, m.bu(A1 + 7) & ~0x20)
    P.call_3c08(m, A1)


def h5a(m, A1, D6, D7):                          # $15c46 fish_get (look for the catch), mode $5a
    dw, dwt = dec18(m, A1)
    if dwt >= 0:
        return
    D0 = m.wu((BUCKETS + s16((m.wu(A1 + 42) * 2) & 0xffff)) & 0xfffff)
    A3 = None
    guard = 0
    while D0 != 0:
        a = ad(OBJ, D0)
        if m.bu(a + 6) == 0x18 and m.bu(a + 7) == 0x10:
            A3 = a
            break
        D0 = m.wu(a)
        guard += 1
        assert guard < 600
    if A3 is None:
        m.ww(A1 + 18, 0x64)
        m.wb(A1 + 31, 0x62)
        return
    m.wb(A3 + 6, 0x20)
    m.wb(A1 + 7, m.bu(A1 + 7) | 0x20)
    D6 = m.wu(A1 + 8)
    D7 = m.wu(A1 + 10)
    D1 = 0x14
    while True:                                   # $15cae
        t6, t7 = D6, D7
        r = P.rng_12c9a(m)
        fail = False
        if r & 1:
            t6 = (t6 + 0x20) & 0xffff
            if s16(t6) >= 0x4000:
                fail = True
        if not fail and r & 2:
            t7 = (t7 + 0x20) & 0xffff
            if s16(t7) >= 0x7fff:
                fail = True
        if not fail and r & 4:
            if s16(t6) - 0x20 < 0:                                  # subi.w ; blt: N xor V
                fail = True
            t6 = (t6 - 0x20) & 0xffff
        if not fail and r & 8:
            if s16(t7) - 0x20 < 0:
                fail = True
            t7 = (t7 - 0x20) & 0xffff
        if not fail:
            blocked, t6, t7 = call_15fa8(m, t6, t7)
            if blocked == 0:
                a_ = ((t6 - m.wu(A1 + 8)) << 4) & 0xffff
                x = (a_ + m.wu(A1 + 8)) & 0xffff
                if s16(a_) + s16(m.wu(A1 + 8)) < 0:          # add.w ; bge: N xor V = the mathematical sign of the sum
                    x = 0
                if s16(x) > 0x3f80:
                    x = 0x3f80
                m.ww(A1 + 20, x)
                a_ = ((t7 - m.wu(A1 + 10)) << 4) & 0xffff
                y = (a_ + m.wu(A1 + 10)) & 0xffff
                if s16(a_) + s16(m.wu(A1 + 10)) < 0:
                    y = 0
                if s16(y) > 0x7f80:
                    y = 0x7f80
                m.ww(A1 + 22, y)
                P.step_toward(m, x, y, D6, D7, A1)
                m.wb(A1 + 31, 0x5c)
                m.ww(A1 + 18, 0x14)
                return
        D1 = (D1 - 1) & 0xffff                    # dbf
        if D1 == 0xffff:
            m.wb(A1 + 31, 0x62)
            return


def h5c(m, A1, D6, D7):                          # $15d66 fish_hea (head home), mode $5c
    D6 = (D6 + s8(m.bu(A1 + 12))) & 0xffff
    D7 = (D7 + s8(m.bu(A1 + 13))) & 0xffff
    blocked, D6, D7 = call_15fa8(m, D6, D7)
    if blocked == 0:
        dw, dwt = dec18(m, A1)
        if dwt >= 0:
            end_16202(m, A1, D6, D7)
            return
    m.wb(A1 + 31, 0x60)
    _fish_target(m, A1)
    P.step_toward(m, m.wu(A1 + 20), m.wu(A1 + 22), D6, D7, A1)
    end_16202(m, A1, D6, D7)


def h60(m, A1, D6, D7):                          # $15ddc fish_hea (deliver the catch), mode $60
    D6 = (D6 + s8(m.bu(A1 + 12))) & 0xffff
    D7 = (D7 + s8(m.bu(A1 + 13))) & 0xffff
    dw, dwt = dec18(m, A1)
    if dwt >= 0:
        end_16202(m, A1, D6, D7)
        return
    _c, _d, reached = P.step_toward(m, m.wu(A1 + 20), m.wu(A1 + 22), D6, D7, A1)
    if not reached:
        end_16202(m, A1, D6, D7)
        return
    A3 = ad(SETTL, m.wu(A1 + 34))
    a = (LEADER + s16(m.wu(A3 + 14)) + 6) & 0xfffff
    m.ww(a, m.wu(a) + 4)
    m.wb(A1 + 31, 0x62)
    D6 = m.wu(A1 + 20)
    D7 = m.wu(A1 + 22)
    end_16202(m, A1, D6, D7)


def h64(m, A1, D6, D7):                          # $16044: bra $16202
    end_16202(m, A1, D6, D7)


def h70(m, A1, D6, D7):                          # $160e0: bra $1622c
    return


def h8e(m, A1, D6, D7):                          # $160e4 fight_ge, mode $8e
    m.wb(A1 + 31, 0x2c)
    m.wb(A1 + 30, 0x2c)
    P.call_160f8(m, A1)


def h90(m, A1, D6, D7):                          # $160f2 townee_g, mode $90
    P.call_3c08(m, A1)
    P.call_160f8(m, A1)


def h72(m, A1, D6, D7):                          # $1605a pickup_f, mode $72 (never natural)
    A4 = ad(GROUP, m.wu(A1 + 42))
    D4 = (((m.wu(A1 + 10) >> 2) & 0x1fc0) + m.bu(A1 + 8)) & 0xffff
    D0 = m.wu((BUCKETS + s16((D4 * 2) & 0xffff)) & 0xfffff)
    guard = 0
    while True:
        A3 = ad(OBJ, D0)
        if m.bu(A3 + 6) == 0x2c:
            m.ww(0x12a32, m.wu(0x12a32) + 1)
            D1 = m.wu(A3 + 10)
            m.ww(A4 + 36, m.wu(A4 + 36) + D1)
            m.ww(A3 + 10, m.wu(A3 + 10) - D1)
            k = 0
            while k != 0x12:
                if m.wu(A3 + 10 + k) != 0:
                    break
                k += 2
            else:
                m.wb(A3 + 6, 0xff)
                raise AssertionError("$16778 unlink arm out of scope")
            # a non-empty pile: `bne $160d2`, which exits through $1515c
            P.call_35f4(m, A4)
            end_161c4(m, A1, D6, D7)
            return
        D0 = m.wu(A3)
        guard += 1
        if D0 == 0:
            break
        assert guard < 600
    P.call_35f4(m, A4)       # falls out of the walk into `$160d2 bra $1515c`
    end_161c4(m, A1, D6, D7)


MODES = {0x14: h14, 0x16: h16, 0x18: h18, 0x1a: h1a, 0x1c: h1c, 0x1e: h1e, 0x20: h20, 0x24: h24, 0x26: h26, 0x28: h28,
         0x2a: h2a, 0x2c: h2c, 0x2e: h2e, 0x30: h30, 0x34: h34, 0x36: h36, 0x38: h38, 0x3a: h3a, 0x3c: h3c, 0x3e: h3e,
         0x40: h40, 0x44: h44, 0x46: h46, 0x48: h48, 0x4a: h4a, 0x4c: h4c, 0x4e: h4e, 0x50: h50, 0x52: h52, 0x54: h54,
         0x56: h56, 0x58: h58, 0x5a: h5a, 0x5c: h5c, 0x5e: h5e, 0x60: h60, 0x62: h62, 0x64: h64, 0x66: h66, 0x6a: h6a,
         0x70: h70, 0x72: h72, 0x7e: P.h_mode7c, 0x8e: h8e, 0x90: h90}


def install():
    P.SHEP_MODES.update(MODES)
