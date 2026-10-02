"""98th-pass acceptance: re-prove the 95th pass (the combat path mode $32 +
$56a6 / $5590 / $30fe) against the graduated tools/pm_fsm_ref.py +
pm_fsm_diff.py, reusing scratchpad/pm95/o_*.json.

Expected: 413/413 tracked bytes identical over 48 states.

Ported verbatim from scratchpad/pm95/diff_fsm.py build_corpus().
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
from pm_fsm_diff import Harness, State
from pm_fsm_ref import OBJ, REC

ANCHORS = ["pm73_melee", "mel_g1", "mel_g2", "mel_g3", "mel_g4", "mel_g5"]
h = Harness("scratchpad/pm95/pm73_melee.snap", "scratchpad/pm95/pm73_melee.ram",
            out_dir="scratchpad/pm95")
M68 = h.m68
R = {n: (M68 / "scratchpad/pm95" / f"{n}.ram").read_bytes() for n in ANCHORS}


def m32(ram0):
    return h.slots_in_mode(ram0, 0x32, positive_only=False)


def dis(ram0, keep):
    return h.disable_others(ram0, keep, trio=False)


def st(name, n, keep, extra, tag):
    return State(name, dis(R[n], keep) + list(extra), tag=tag,
                 snap=f"scratchpad/pm95/{n}.snap", ram=f"scratchpad/pm95/{n}.ram")


def build_corpus():
    S = []
    for n in ANCHORS:
        S.append(st(f"{n}_nat", n, m32(R[n]), [], "mutual"))

    kill_pairs = {"mel_g5": [(10, 44), (9, 45), (8, 42), (7, 43), (5, 41)],
                  "mel_g4": [(10, 44), (9, 45), (8, 32)],
                  "mel_g3": [(9, 35), (8, 28)]}
    for n, pairs in kill_pairs.items():
        for a, b in pairs:
            ba, bb = OBJ + a * REC, OBJ + b * REC
            S.append(st(f"{n}_kill_{a}_{b}", n, [a, b],
                        [h.lw_at(R[n], ba + 7, 0), h.lw_at(R[n], bb + 7, 0),
                         h.lw_at(R[n], ba + 45, 1)], "kill"))

    eng_pairs = {"mel_g5": [(10, 44), (9, 45), (7, 43), (5, 41)],
                 "mel_g4": [(10, 44), (8, 32), (7, 29)],
                 "mel_g3": [(10, 30), (9, 35)]}
    for n, pairs in eng_pairs.items():
        for a, b in pairs:
            bb = OBJ + b * REC
            ex = h.bytepokes(R[n], {bb + 7: 0, bb + 31: 0x12, bb + 38: 0xee,
                                    bb + 46: 0xaa, bb + 47: 0x55,
                                    bb + 48: 0x33, bb + 49: 0xcc})
            S.append(st(f"{n}_eng_{a}_{b}", n, [a, b], ex, "engage"))

    lost = {"mel_g5": [(10, 44), (30, 10), (22, 2)],
            "mel_g3": [(10, 30), (27, 5)]}
    for n, pairs in lost.items():
        for a, b in pairs:
            bb = OBJ + b * REC
            S.append(st(f"{n}_lost_{a}_{b}", n, [a],
                        [h.lw_at(R[n], bb + 5, 0)], "lost"))

    grpkill_pairs = {"mel_g5": [(10, 44), (9, 45), (8, 42), (7, 43)],
                     "mel_g4": [(10, 44), (9, 45), (8, 32)],
                     "mel_g3": [(10, 30), (9, 35), (8, 28)]}
    for n, pairs in grpkill_pairs.items():
        for a, b in pairs:
            ba, b21 = OBJ + a * REC, OBJ + 21 * REC
            ex = h.bytepokes(R[n], {ba + 7: 0x20, ba + 45: 1, b21 + 31: 0x12})
            S.append(st(f"{n}_grpkill_{a}_{b}", n, [a, b, 21], ex, "grpkill"))

    GRP60 = 0x51538 + 392 + 60
    for n in ("mel_g5", "mel_g4"):
        for a, b in [(10, 44), (9, 45)]:
            ba, b21 = OBJ + a * REC, OBJ + 21 * REC
            ex = h.bytepokes(R[n], {ba + 7: 0x20, ba + 45: 1, b21 + 31: 0x12,
                                    GRP60: 0x00, GRP60 + 1: 0x05})
            S.append(st(f"{n}_rng_{a}_{b}", n, [a, b, 21], ex, "rng"))

    for n, (a, b) in [("mel_g1", (10, 30)), ("mel_g5", (10, 44)),
                      ("mel_g5", (5, 41)), ("mel_g3", (9, 35))]:
        S.append(st(f"{n}_pair_{a}_{b}", n, [a, b], [], "mutual"))
    return S


if __name__ == "__main__":
    res = h.run_corpus(build_corpus(), min_states=15, min_branches=4,
                       steps=2_000_000, reuse_json="reuse" in sys.argv)
    sys.exit(0 if (res["passed"] and res["ok"] == res["tot"] == 413) else 1)
