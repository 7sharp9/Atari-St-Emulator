"""RIDER 3b routine 6 (99th): the flag-bit-4 GROUP-TEARDOWN subtree behind
$3c08's $3c46 arm - PROVEN vs the real 68000.

  $37c2  group-lead re-parent / disband
  $1d70  route-string expander (send every roster member home along a
         terrain-following path)
  $1b8c  roster unlink (+ a recursive $3c08 on the unlinked lead)
  $17a46 minimap redraw - a tracked-region NO-OP

Method (unchanged since the 93rd):
  A. direct  `callcap 37c2 <n> out.json D2=<group_off>`  (entry contract: D2)
     and     `callcap 1d70 <n> out.json A3=<grouprec>`   (entry contract: A3)
     and     `callcap 3c08 <n> out.json A1=<record>`     (the whole arm)
     compared against pm_fsm_ref.call_37c2 / call_1d70 / call_3c08, handed
     only the poked base RAM.
  B. end-to-end `callcap 14b62`: a record poked to mode $7c on pm97_map1
     (word[$57fd0] == 4 != 0), all other live records disabled -> prologue ->
     $157ba -> $16892 gate -> $3c08 -> $3c46 teardown.

Anchor: scratchpad/pm97/pm97_map1.snap/.ram.  The one natural grouped record
is slot 21 (flags $10, group 392, group.state 6): its lead entity is itself,
26 roster members (slots 22..47) chained via word[+26] off word[grouprec-36].
The teardown drives $37c2 (bit7-clear) -> $1d70 over all 26 members.

PRE-REGISTERED (before any run):
  falsifier : any tracked byte where the reconstruction and the real routine
              disagree, in any state.
  bar       : 100% of tracked changed bytes identical over >= 12 states, with
              >= 1 state per covered sub-branch:
                3c08_bit4 (full arm) / 37c2_bit7clr / 1d70 (direct) /
                17a46_noop / 37c2_bit7set_b6clr ($382a troops_field -= 1) /
                37c2_bit6set_1b8c / 1d70_state6_w46 / e2e.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import pm_fsm_ref
from pm_fsm_diff import Harness, State
from pm_fsm_ref import OBJ, REC, GROUP

h = Harness("scratchpad/pm97/pm97_map1.snap", "scratchpad/pm97/pm97_map1.ram",
            out_dir="scratchpad/pm99")
R = h.anchor_ram_bytes

S21 = OBJ + 21 * REC          # the natural grouped lead
G392 = 392                    # slot 21's group offset
GR392 = GROUP + G392          # 0x516c0


def d(name, target, presets, recon, tag, pokes=None):
    return State(name, pokes or [], tag=tag, target=target,
                 presets=presets, recon=recon)


def build_corpus():
    S = []

    # -- A. direct callcap, natural state --
    S.append(d("d3c08_s21", "3c08", {"A1": S21},
               lambda m: pm_fsm_ref.call_3c08(m, S21), "3c08_bit4"))
    S.append(d("d37c2_g392", "37c2", {"D2": G392},
               lambda m: pm_fsm_ref.call_37c2(m, G392), "37c2_bit7clr"))
    S.append(d("d1d70_g392", "1d70", {"A3": GR392},
               lambda m: pm_fsm_ref.call_1d70(m, GR392), "1d70"))
    S.append(d("d17a46_g392", "17a46", {"D2": G392},
               lambda m: pm_fsm_ref.call_17a46(m, G392), "17a46_noop"))

    # -- A. poked: $37c2 bit-7 SET, bit-6 clear -> owner_leader.troops_field -= 1
    #    (economy.md's $382a row) + owner/settlement re-parent + flag flips --
    S.append(d("p37c2_b7clr6", "37c2", {"D2": G392},
               lambda m: pm_fsm_ref.call_37c2(m, G392), "37c2_bit7set_b6clr",
               pokes=h.bytepokes(R, {S21 + 7: 0x90})))            # bit7|bit4

    # -- A. poked: $37c2 bit-7 SET, bit-6 SET -> $1b8c (roster-unlink walk +
    #    recursive $3c08 + troops_field += 1) --
    S.append(d("p37c2_b6set", "37c2", {"D2": G392},
               lambda m: pm_fsm_ref.call_37c2(m, G392), "37c2_bit6set_1b8c",
               pokes=h.bytepokes(R, {S21 + 7: 0xd0}) +            # bit7|bit6|bit4
                     [h.lw_word(R, S21 + 28, 1100),               # lead.word28 -> slot 22
                      h.lw_word(R, OBJ + 1100 + 42, G392)]))      # slot22.word42 -> group 392

    # -- A. poked: $1d70 state-6 + lead.word46 in [$4cff8,$4d250) --
    w46 = (-(OBJ - 0x4cff8)) & 0xffff                             # -> obj[w46] == $4cff8
    S.append(d("p1d70_st6w46", "37c2", {"D2": G392},
               lambda m: pm_fsm_ref.call_37c2(m, G392), "1d70_state6_w46",
               pokes=[h.lw_word(R, S21 + 46, w46)]))

    # -- A. direct callcap 1d70 with a shorter roster (poke a mid-chain member's
    #    word[+26] to 0 -> the chain terminates early; exercises the loop tail) --
    S.append(d("d1d70_short", "1d70", {"A3": GR392},
               lambda m: pm_fsm_ref.call_1d70(m, GR392), "1d70",
               pokes=[h.lw_word(R, OBJ + 1150 + 26, 0)]))         # slot 23 -> chain end

    # -- A. direct callcap 1d70, a member with a different byte44 (target char) --
    S.append(d("d1d70_b44", "1d70", {"A3": GR392},
               lambda m: pm_fsm_ref.call_1d70(m, GR392), "1d70",
               pokes=h.bytepokes(R, {OBJ + 2350 + 44: 0x00,       # slot 47 byte44 -> 'N'
                                     OBJ + 2300 + 44: 0x04})))    # slot 46 byte44 -> 'S'

    # -- A. direct callcap 1b8c: head-unlink + D1 != 0 -> $1d70 tail +
    #    recursive $3c08 (flags-clear "none" arm) --
    S.append(d("d1b8c_head", "1b8c",
               {"A0": OBJ + 21 * REC, "A1": OBJ + 2350, "D1": 1},
               lambda m: pm_fsm_ref.call_1b8c(m, OBJ + 21 * REC, OBJ + 2350, 1),
               "1b8c"))

    # -- A. $3c08 bit-4 arm, settlement cell poked -> different $3ca2 tail --
    S.append(d("d3c08_cell", "3c08", {"A1": S21},
               lambda m: pm_fsm_ref.call_3c08(m, S21), "3c08_bit4",
               pokes=[h.lw_word(R, pm_fsm_ref.SETTL + 198 + 12, 0x0af3)]))

    # -- B. end-to-end through $14b62 dispatch ($57fd0 == 4 != 0) --
    e_pokes = h.disable_others(R, keep=[21], trio=False) + \
        h.bytepokes(R, {S21 + 31: 0x7c})
    S.append(State("e2e_s21_7c", e_pokes, tag="e2e", target="14b62"))

    # $16892 fires: poke owner_leader.goods -> $3c08 skipped, $16892 rewrites
    # slot 21 only.  leader for settl 198 is word14/2 -> index 64.
    e2_pokes = h.disable_others(R, keep=[21], trio=False) + \
        h.bytepokes(R, {S21 + 31: 0x7c, pm_fsm_ref.LEADER + 64 + 24 + 2: 0x07})
    S.append(State("e2e_s21_16892", e2_pokes, tag="e2e_16892", target="14b62"))

    return S


if __name__ == "__main__":
    res = h.run_corpus(build_corpus(), min_states=12, min_branches=7,
                       steps=400_000)
    sys.exit(0 if res["passed"] else 1)
