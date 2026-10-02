"""116th-pass differential test: $4bc8's kind==2 (leader/settlement) branch -
$4ee8 (the recursive per-other-side contact sweep) + the settlement/garrison
reset loop in $4cb8's kind-2 case ($4cd0).  This is what $5c2c's real call
site (A0 always a $4e514 leader record) needed to complete $4bc8 end-to-end;
deferred out of the 115th pass as its own item, closed here.

Anchor/conventions: same as diff_4bc8.py (scratchpad/pm97/pm97_map0.snap,
dead object slots, self-contained pokes).  The synthetic leader records live
at LEADER_LO+0x400/+0x500 (within $4de2's classify range but past the
tracked LEADER region's real data, which $4bc8 never writes to anyway).  The
self-side $51538 per-side tables live at side index 3/4 (arbitrary, disjoint,
well clear of both real small group_off values and the object table).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
from pm_fsm_diff import Harness, State
import pm_fsm_ref
from pm_fsm_ref import OBJ, REC, GROUP, SETTL, LEADER_LO

h = Harness("scratchpad/pm97/pm97_map0.snap", "scratchpad/pm97/pm97_map0.ram",
            out_dir="scratchpad/pm115")
R = h.anchor_ram_bytes


def obase(slot):
    return h.obase(slot)   # bounds-checked (Harness.obase) - see pm_fsm_diff.py


def wpoke(d, addr, val16):
    d[addr] = (val16 >> 8) & 0xff
    d[addr + 1] = val16 & 0xff


def obj_pokes(slot, fields):
    return {obase(slot) + k: v for k, v in fields.items()}


FAR_SETTL = 100    # a settlement offset used purely as a far dest-cell anchor


def far_from_settlement(p, slot, owner, settl_off=FAR_SETTL):
    p.update(obj_pokes(slot, {5: owner, 6: 0x00, 7: 0x00, 30: 0x00, 31: 0x10,
                               8: 250, 10: 250}))
    wpoke(p, obase(slot) + 34, settl_off)
    wpoke(p, SETTL + settl_off + 12, 0xffff)   # cx=63, cy=1023 -> always far


def build_corpus():
    states = []

    def leaf(name, tag, a, b, pokes):
        states.append(State(name, h.bytepokes(R, pokes), tag=tag, target="4bc8",
                             presets={"A0": a, "A1": b},
                             recon=lambda m, x=a, y=b: pm_fsm_ref.call_4bc8(m, x, y)))

    # ---- kind2 -> $4ee8 recursion: leader's side-3 slot 0 is active with a
    #      nearby other-side lead -> nested call_4bc8 fires for real ----
    LEADER1 = LEADER_LO + 0x400
    SIDE3 = GROUP + 3 * 0x13c
    p = {}
    p[LEADER1 + 0] = 3               # self_side / byte_class
    wpoke(p, LEADER1 + 2, 0)         # settlement chain head: none (isolate $4ee8)
    wpoke(p, LEADER1 + 4, 0)         # home cell (0,0)
    for i in range(6):
        wpoke(p, SIDE3 + 28 + i * 2, 1 if i == 0 else 0)
        wpoke(p, SIDE3 + 76 + i * 2, 0)
    wpoke(p, SIDE3 + 64, 509 * REC)  # slot 509 = the nearby other-side lead
    p.update(obj_pokes(509, {5: 40, 6: 0x00, 7: 0x00, 30: 0x00, 31: 0x10,
                              8: 5, 10: 5}))
    wpoke(p, obase(509) + 34, FAR_SETTL)
    p.update(obj_pokes(510, {5: 41, 6: 0x00, 7: 0x00, 30: 0x00, 31: 0x10,
                              8: 250, 10: 250}))
    wpoke(p, obase(510) + 34, FAR_SETTL)
    wpoke(p, SETTL + FAR_SETTL + 12, 0xffff)
    leaf("kind2_ee8_recurse", "kind2-ee8", LEADER1, obase(510), p)

    # ---- kind2 -> settlement/garrison sweep: a 2-settlement chain, one
    #      garrison reset, two garrisons skipped (bit4+42!=0, bit6) ----
    LEADER2 = LEADER_LO + 0x500
    SIDE4 = GROUP + 4 * 0x13c
    SETTL_A, SETTL_B = 18, 36
    p = {}
    p[LEADER2 + 0] = 4
    wpoke(p, LEADER2 + 2, SETTL_A)
    wpoke(p, LEADER2 + 4, 0)
    for i in range(6):
        wpoke(p, SIDE4 + 28 + i * 2, 0)      # no $4ee8 hits - isolate the sweep
        wpoke(p, SIDE4 + 76 + i * 2, 0)
    wpoke(p, SETTL + SETTL_A + 10, 460 * REC)   # settlement A's garrison chain head
    wpoke(p, SETTL + SETTL_A + 8, SETTL_B)      # next settlement
    wpoke(p, SETTL + SETTL_B + 10, 461 * REC)   # settlement B's garrison
    wpoke(p, SETTL + SETTL_B + 8, 0)            # end of settlement chain
    p.update(obj_pokes(460, {5: 7, 6: 0x00, 7: 0x00, 30: 0x00, 31: 0x10}))
    wpoke(p, obase(460) + 24, 463 * REC)        # chain to a 2nd garrison at settlement A
    p.update(obj_pokes(463, {5: 9, 6: 0x00, 7: 0x10}))   # bit4 set + 42 != 0 -> skip
    wpoke(p, obase(463) + 42, 0x999)
    wpoke(p, obase(463) + 24, 0)
    p.update(obj_pokes(461, {5: 8, 6: 0x00, 7: 0x40}))   # bit6 set -> skip
    wpoke(p, obase(461) + 24, 0)
    far_from_settlement(p, 462, 50, settl_off=FAR_SETTL + 40)
    leaf("kind2_settlement_sweep", "kind2-sweep", LEADER2, obase(462), p)

    return states


if __name__ == "__main__":
    h.run_corpus(build_corpus(), min_states=2, min_branches=2,
                 reuse_json="reuse" in sys.argv)
