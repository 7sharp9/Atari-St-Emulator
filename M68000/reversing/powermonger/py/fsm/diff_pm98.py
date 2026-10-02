"""RIDER 3b routine 5 (98th, commit 2): the REGROUP / RETURN-HOME dispatcher
$3c08 - the `word[$57fd0] != 0` branch of the mode-$7c dispatch $157ba, and a
leaf called from 17 sites across the entity FSM and the group-order system -
PROVEN vs the real 68000.

Method:
  A. direct `callcap 3c08 <n> out.json A1=<record addr>` per state - $3c08's
     entry contract is just A1 (it lea's its own $51538/$4f916/$4e514 bases,
     like every other $14b62 handler).  Compare the tracked delta (obj records
     + $4e514 leaders + $4f916 settlements) against pm_fsm_ref.call_3c08(m, A1),
     which is handed only the poked base RAM.
  B. end-to-end: repurpose a record to mode $7c on pm97_map1 (word[$57fd0] == 4,
     != 0), disable every other live record, `callcap 14b62` -> prologue ->
     $157ba dispatch -> $16892 (goods gate) -> $3c08.  Validates the dispatch
     wiring + call_16892.

Anchor: scratchpad/pm97/pm97_map1.snap/.ram - 47 live records with natural flag
bytes $01/$02/$04/$08/$10/$40, 12 settlements, 3 leaders (all goods == 0 -> the
$16892 gate falls through to $3c08 naturally).

ASSERTED OFF (guarded by raise in pm_fsm_ref.call_3c08 - no corpus state
reaches it): the flag-bit-4 GROUP-TEARDOWN sub-path ($3c46: 42(A1) != 0 ->
jsr $37c2 [-> $1d70 / $1b8c] ; group.state := 7 ; jsr $17a46 [minimap redraw]).
Deferred to its own pass.

PRE-REGISTERED (before any run):
  falsifier : any tracked byte where the reconstruction and the real routine
              disagree, in any state.
  bar       : 100% of tracked changed bytes identical over >= 15 states, with
              >= 1 state per covered sub-branch:
              bit7 / bit0 / bit1 / bit2 / bit3 / bit4-nogroup / none /
              tail-owner<=0 (skip byte-6 clear) / e2e-$3c08 / e2e-$16892-fires.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import pm_fsm_ref
from pm_fsm_diff import Harness, State
from pm_fsm_ref import OBJ, REC, LEADER, SETTL

h = Harness("scratchpad/pm97/pm97_map1.snap", "scratchpad/pm97/pm97_map1.ram",
            out_dir="scratchpad/pm98")
R = h.anchor_ram_bytes


def u16(a):
    return struct.unpack_from(">H", R, a)[0]


def s16(a):
    return struct.unpack_from(">h", R, a)[0]


def live(mode=None, grp=None, flag=None):
    out = []
    for s in range(1, 512):
        b = OBJ + s * REC
        if R[b + 5] == 0:
            continue
        if mode is not None and R[b + 31] != mode:
            continue
        if grp is not None and (u16(b + 42) != 0) != grp:
            continue
        if flag is not None and R[b + 7] != flag:
            continue
        out.append(s)
    return out


def d3c08(name, slot, pk_bytes, tag):
    """a direct `callcap 3c08 A1=<slot>` state."""
    A1 = OBJ + slot * REC
    pokes = h.bytepokes(R, pk_bytes) if pk_bytes else []
    return State(name, pokes, tag=tag, target="3c08", presets={"A1": A1},
                 recon=(lambda m, a=A1: pm_fsm_ref.call_3c08(m, a)))


def e2e(name, slot, pk_bytes, tag):
    """an end-to-end `callcap 14b62` state: record `slot` -> mode $7c, all other
    live records disabled."""
    pokes = h.disable_others(R, keep=[slot], trio=False) + h.bytepokes(R, pk_bytes)
    return State(name, pokes, tag=tag, target="14b62")


def build_corpus():
    S = []
    b0 = live(flag=0x01)          # bit0 -> mode30 $16
    b1 = live(flag=0x02)          # bit1 -> $4e
    b2 = live(flag=0x04)          # bit2 -> $5e   (mode-$56 records; grp!=0 but bit2 path ignores grp)
    b3 = live(flag=0x08)          # bit3 -> $80
    b4g = live(flag=0x10)         # bit4, grp!=0 (slot 21) - NOT tested (asserted off)
    nogrp = [s for s in live(grp=False) if s not in (21,)]   # grp==0 records

    # -- A. direct callcap 3c08, natural flag bytes --
    S.append(d3c08("nat_bit0_a", b0[0], {}, "bit0"))
    S.append(d3c08("nat_bit0_b", b0[1], {}, "bit0"))
    S.append(d3c08("nat_bit1", b1[0], {}, "bit1"))
    S.append(d3c08("nat_bit2_a", b2[0], {}, "bit2"))
    S.append(d3c08("nat_bit2_b", b2[2], {}, "bit2"))
    S.append(d3c08("nat_bit3", b3[0], {}, "bit3"))

    # -- A. direct callcap 3c08, poked flag bytes on grp==0 records --
    g = nogrp[0]                                  # slot 7 (flags $02, grp 0)
    bg = OBJ + g * REC
    S.append(d3c08("poke_bit7", g, {bg + 7: 0x80}, "bit7"))
    S.append(d3c08("poke_none", g, {bg + 7: 0x00}, "none"))
    S.append(d3c08("poke_bit4_nogrp", g, {bg + 7: 0x10}, "bit4_nogrp"))
    g2 = nogrp[1]
    bg2 = OBJ + g2 * REC
    S.append(d3c08("poke_bit4_nogrp_b", g2, {bg2 + 7: 0x10}, "bit4_nogrp"))
    S.append(d3c08("poke_bit3_g", g, {bg + 7: 0x08}, "bit3"))
    S.append(d3c08("poke_bit0_g", g, {bg + 7: 0x01}, "bit0"))

    # -- A. the $3ca2 tail: owner <= 0 skips the `move.b #$0,6(A1)` --
    S.append(d3c08("tail_owner0", g, {bg + 7: 0x02, bg + 5: 0x00,
                                      bg + 6: 0x33}, "tail_le0"))
    S.append(d3c08("tail_ownerneg", g, {bg + 7: 0x04, bg + 5: 0x80,
                                        bg + 6: 0x33}, "tail_le0"))
    # and owner > 0 with byte 6 already dirty -> it IS cleared
    S.append(d3c08("tail_owner_pos", g, {bg + 7: 0x02, bg + 6: 0x33}, "tail_pos"))

    # -- A. multiple flag bits set: the btst chain resolves in order 7,0,1,2,3,4 --
    S.append(d3c08("multi_b7b2", g, {bg + 7: 0x84}, "bit7"))     # 7 wins
    S.append(d3c08("multi_b0b3", g, {bg + 7: 0x09}, "bit0"))     # 0 wins

    # -- B. end-to-end through $14b62 dispatch ($57fd0 == 4 != 0) --
    e = nogrp[0]                                  # slot 7, settl off 72 -> leader 0
    be = OBJ + e * REC
    S.append(e2e("e2e_3c08_bit1", e, {be + 31: 0x7c}, "e2e_3c08"))
    S.append(e2e("e2e_3c08_bit0", e, {be + 31: 0x7c, be + 7: 0x01}, "e2e_3c08"))
    S.append(e2e("e2e_3c08_none", e, {be + 31: 0x7c, be + 7: 0x00}, "e2e_3c08"))
    # $16892 fires: poke owner_leader.goods -> $3c08 skipped, $16892 rewrites record
    S.append(e2e("e2e_16892_g3", e, {be + 31: 0x7c, LEADER + 0 + 24 + 3: 0x05},
                 "e2e_16892"))
    S.append(e2e("e2e_16892_g0", e, {be + 31: 0x7c, LEADER + 0 + 24 + 0: 0x01},
                 "e2e_16892"))
    return S


if __name__ == "__main__":
    res = h.run_corpus(build_corpus(), min_states=15, min_branches=8,
                       steps=400_000)
    sys.exit(0 if res["passed"] else 1)
