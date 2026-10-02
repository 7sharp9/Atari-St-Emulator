"""115th-pass differential test: $4bc8 contact reconcile ("nation-pair
peace-break + player notify"), the primary target named in ai.md's
Corroborated-not-Proven backlog.

Entry: A0, A1 = the two object records in contact.  Real natural call sites:
$5778 (gstate != $d), $1518a (mode $10 group-state-8 hand-off), $5c2c
(owner-mismatch, via $16176 removal / $16848).  $5778 and $1518a always pass
plain $51b66 object records (never leader-range) - covered here.  $5c2c
always passes a LEADER record for A0, which classifies as kind 2 and drives
the recursive $4ee8 settlement/leader sweep - ASSERTED OFF in
tools/pm_fsm_ref.py, its own separate item, NOT exercised by this corpus.

Anchor: scratchpad/pm97/pm97_map0.snap (settled first-mission view, same
anchor the 96th-99th passes used).  Every test state lives entirely in dead
object slots 480-511 + unused $51538 group offsets (0x100/0x140) - no
dependency on the anchor's own live game state, so no need to disable other
records (call_4bc8 never iterates the whole object table itself; the only
table walk is the synthetic group's own roster chain, entirely under this
script's control).  Kind-6 fixtures explicitly zero settlement slot 0's
dest-cell (word 12) so the settlement-distance fallback is deterministic
rather than depending on the anchor's own settlement data; that field is
never written by $4bc8 itself, so poking it introduces no diff noise.

Coverage deliberately scoped to what's needed by the two in-scope call
sites: kind combos {4,6,8,10,12} through both the mismatch/notify path and
the same-class group-free path, INCLUDING $35f4's full ring-scatter + lead-
to-formation-follower conversion.  $35f4's own $4cff8 GARRISON-table
marker-placement sub-path (call_3744) is bypassed by construction (lead's
bit5 flag set) - that table isn't in pm_fsm_ref.REGIONS, so a diff there
would be invisible anyway; noted as a followup, not silently assumed correct.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
from pm_fsm_diff import Harness, State
import pm_fsm_ref
from pm_fsm_ref import OBJ, REC, GROUP, SETTL

h = Harness("scratchpad/pm97/pm97_map0.snap", "scratchpad/pm97/pm97_map0.ram",
            out_dir="scratchpad/pm115")
R = h.anchor_ram_bytes


def obase(slot):
    return h.obase(slot)   # bounds-checked (Harness.obase) - see pm_fsm_diff.py


def gbase(off):
    return GROUP + off


G1 = 0x100    # kind-4 test group #1 (state $d -> skip $37c2)
G2 = 0x140    # the $35f4-under-test group (state 8)


def obj_pokes(slot, fields):
    return {obase(slot) + k: v for k, v in fields.items()}


def grp_pokes(off, fields):
    return {gbase(off) + k: v for k, v in fields.items()}


def wpoke(d, addr, val16):
    d[addr] = (val16 >> 8) & 0xff
    d[addr + 1] = val16 & 0xff


def far_from_settlement0(p, slot, owner):
    """flags=0 (neither bit4 nor bit6) + settlement 0's dest-cell zeroed +
    a far-away own position -> the settlement-distance fallback, kind 6."""
    p.update(obj_pokes(slot, {5: owner, 6: 0x00, 7: 0x00, 30: 0x00, 31: 0x10,
                               8: 200, 10: 200}))   # byte fields, not words
    wpoke(p, obase(slot) + 34, 0)          # settlement index 0
    wpoke(p, SETTL + 12, 0)                # settlement 0's dest cell := (0,0)


def build_corpus():
    states = []

    def leaf(name, tag, a, b, pokes):
        states.append(State(name, h.bytepokes(R, pokes), tag=tag, target="4bc8",
                             presets={"A0": obase(a), "A1": obase(b)},
                             recon=lambda m, x=obase(a), y=obase(b): pm_fsm_ref.call_4bc8(m, x, y)))

    # ---- mismatch/notify, both kind-6 (owner-based class) ----
    p = {}
    far_from_settlement0(p, 480, 1)
    far_from_settlement0(p, 481, 2)
    leaf("notify_6_6", "notify-6-6", 480, 481, p)

    # ---- mismatch/notify, kind6 (owner-based class) vs kind8 (class always 0) ----
    p = {}
    far_from_settlement0(p, 482, 3)
    p.update(obj_pokes(483, {5: 1, 6: 0x08, 7: 0x00}))          # kind8 (no-op case)
    leaf("notify_6_8", "notify-6-8", 482, 483, p)

    # ---- same class, both trivial no-op kinds (8 vs 10): confirms a total no-op ----
    p = {}
    p.update(obj_pokes(484, {5: 1, 6: 0x08, 7: 0x00}))          # kind8, class 0
    p.update(obj_pokes(485, {5: 1, 6: 0x14, 7: 0x00}))          # kind10 (0xa), class 0
    leaf("sameclass_8_10", "sameclass-noop", 484, 485, p)

    # ---- same class, both kind6 (equal owner byte): confirms $4dae is NOT
    #      invoked outside the notify path ----
    p = {}
    far_from_settlement0(p, 486, 7)
    far_from_settlement0(p, 487, 7)
    leaf("sameclass_6_6", "sameclass-noop", 486, 487, p)

    # ---- kind4 (bit4, direct group-check on self) vs kind6, mismatch ----
    # 491 = A0 (bit4 set, owner=11=its own byte_class, own 42-field -> G1);
    # 492 = A1 (kind6, far-settlement fallback, owner=99).
    # G1's roster: 493 (live) -> 494 (dead, must be skipped) -> 0.
    p = {}
    p.update(obj_pokes(491, {5: 11, 6: 0x00, 7: 0x10, 30: 0x00, 31: 0x10}))
    wpoke(p, obase(491) + 28, 0)            # link unused by the bit4-direct path
    wpoke(p, obase(491) + 42, G1)
    far_from_settlement0(p, 492, 99)
    p.update(obj_pokes(493, {5: 5, 30: 0x00, 31: 0x10}))
    wpoke(p, obase(493) + 26, 494 * REC)
    p.update(obj_pokes(494, {5: 0}))                       # dead - roster walk must skip it
    wpoke(p, obase(494) + 26, 0)
    wpoke(p, gbase(G1) + 0, 0x000d)                        # state $d -> classify() skips $37c2
    wpoke(p, gbase(G1) - 36, 493 * REC)                    # roster head -> 493
    leaf("notify_4_6", "notify-4-6", 491, 492, p)

    # ---- same class, kind4 vs kind6, group state==8 -> $35f4 free-slot ----
    # 495 = A0 (bit4 set, owner=22, own 42-field -> G2, state 8 -> skips
    #       $37c2 AND is the same group the same-side branch inspects/frees);
    # 497 = A1 (kind6 far-settlement fallback, owner=22 -> same class).
    # G2 (state 8): lead=498 (bit5 set -> skips the untracked GARRISON path),
    # roster: 499 (ring 0, live) -> 0.
    p = {}
    p.update(obj_pokes(495, {5: 22, 6: 0x00, 7: 0x10}))
    wpoke(p, obase(495) + 28, 0)
    wpoke(p, obase(495) + 42, G2)
    far_from_settlement0(p, 497, 22)
    p.update(obj_pokes(498, {5: 5, 6: 0x00, 7: 0x20}))
    wpoke(p, obase(498) + 8, 100)
    wpoke(p, obase(498) + 10, 100)
    wpoke(p, obase(498) + 30, 0x1010)
    p.update(obj_pokes(499, {5: 6, 44: 0, 31: 0x10, 30: 0x10}))
    wpoke(p, obase(499) + 26, 0)
    wpoke(p, gbase(G2) + 0, 0x0008)
    wpoke(p, gbase(G2) - 12, 498 * REC)
    wpoke(p, gbase(G2) - 36, 499 * REC)
    leaf("sameside_4_free", "sameside-4-free", 495, 497, p)

    # ---- mismatch/notify, kind6 vs kind12 (cat==4, trivial class-0 case) ----
    p = {}
    far_from_settlement0(p, 500, 4)
    p.update(obj_pokes(501, {5: 1, 6: 0x04, 7: 0x00}))
    leaf("notify_6_12", "notify-6-12", 500, 501, p)

    # ---- same class, kind4 on the A1 side (D7==4) -> the mirror $35f4 check ----
    # 503 = A0 (kind6 far-settlement fallback, owner=33);
    # 502 = A1 (bit4 set, owner=33, own 42-field -> G3, state 8).
    G3 = 0x180
    p = {}
    far_from_settlement0(p, 503, 33)
    p.update(obj_pokes(502, {5: 33, 6: 0x00, 7: 0x10}))
    wpoke(p, obase(502) + 28, 0)
    wpoke(p, obase(502) + 42, G3)
    p.update(obj_pokes(506, {5: 8, 6: 0x00, 7: 0x20}))
    wpoke(p, obase(506) + 8, 150)
    wpoke(p, obase(506) + 10, 150)
    wpoke(p, obase(506) + 30, 0x1010)
    p.update(obj_pokes(507, {5: 9, 44: 0, 31: 0x10, 30: 0x10}))
    wpoke(p, obase(507) + 26, 0)
    wpoke(p, gbase(G3) + 0, 0x0008)
    wpoke(p, gbase(G3) - 12, 506 * REC)
    wpoke(p, gbase(G3) - 36, 507 * REC)
    leaf("sameside_4_free_A1", "sameside-4-free", 503, 502, p)

    return states


if __name__ == "__main__":
    h.run_corpus(build_corpus(), min_states=6, min_branches=4,
                 reuse_json="reuse" in sys.argv)
