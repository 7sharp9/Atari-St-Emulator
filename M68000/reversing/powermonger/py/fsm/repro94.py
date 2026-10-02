"""98th-pass acceptance: re-prove the 94th pass (the four movement modes
$06/$08/$0e/$10 of $14b62) against the graduated tools/pm_fsm_ref.py +
pm_fsm_diff.py, reusing scratchpad/pm94/o_*.json.

Expected: 1335/1335 tracked bytes identical over 32 states.

Ported verbatim from scratchpad/pm94/diff_fsm.py build_corpus().
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
from pm_fsm_diff import Harness, State
from pm_fsm_ref import OBJ, REC

h = Harness("scratchpad/pm88_f1.snap", "scratchpad/pm88_f1.ram", out_dir="scratchpad/pm94")
M68 = h.m68
RAM = {n: (M68 / "scratchpad" / f"{n}.ram").read_bytes()
       for n in ("pm88_f1", "pm78_settle", "pm74_late", "pm73_fight")}


def keep_pokes(ram0, keep):
    return h.disable_others(ram0, keep, trio=True)


def live(ram0, mode):
    return h.slots_in_mode(ram0, mode, positive_only=True)


def mk(name, nm, keep, extra=(), tag=""):
    r = RAM[nm]
    return State(name, keep_pokes(r, keep) + list(extra),
                 tag=tag or name.rsplit("_", 1)[0],
                 snap=f"scratchpad/{nm}.snap", ram=f"scratchpad/{nm}.ram")


def build_corpus():
    S = []
    # mode $0e natural
    for nm in ("pm88_f1", "pm78_settle", "pm73_fight"):
        S.append(mk(f"{nm}_0e_nat", nm, live(RAM[nm], 0x0e), tag="0e_nat"))
    # mode $0e poked spline advance
    for nm in ("pm88_f1", "pm73_fight"):
        s0e = live(RAM[nm], 0x0e)
        b = OBJ + s0e[0] * REC
        S.append(mk(f"{nm}_0e_dw1", nm, s0e, [h.lw_word(RAM[nm], b + 18, 1)], tag="0e_dw1"))
    nm = "pm88_f1"
    s = live(RAM[nm], 0x0e)[0]
    b = OBJ + s * REC
    S.append(mk(f"{nm}_0e_term24", nm, [s],
               [h.lw_word(RAM[nm], b + 18, 1), h.lw_word(RAM[nm], b + 40, 112)], tag="0e_term"))
    S.append(mk(f"{nm}_0e_term92", nm, [s],
               [h.lw_word(RAM[nm], b + 18, 1), h.lw_word(RAM[nm], b + 40, 50)], tag="0e_term"))
    S.append(mk(f"{nm}_0e_loop", nm, [s],
               [h.lw_word(RAM[nm], b + 18, 1), h.lw_word(RAM[nm], b + 40, 34)], tag="0e_loop"))
    # mode $10 natural single-record
    ten = {"pm88_f1": [18], "pm78_settle": [5, 13], "pm74_late": [3, 7, 10, 15, 17],
           "pm73_fight": [18]}
    for nm, slots in ten.items():
        for sl in slots:
            S.append(mk(f"{nm}_10_s{sl}", nm, [sl], tag="10_nat"))
    nm = "pm73_fight"
    b = OBJ + 18 * REC
    S.append(mk(f"{nm}_10_chase", nm, [18, 37], [h.lw_at(RAM[nm], b + 30, 0x2e)], tag="10_chase"))
    S.append(mk(f"{nm}_10_conv2c", nm, [18], [h.lw_at(RAM[nm], b + 30, 0x2e)], tag="10_conv2c"))
    # mode $06
    s06 = live(RAM["pm73_fight"], 0x06)
    S.append(mk("pm73_fight_06_all", "pm73_fight", s06, tag="06_all"))
    for sl in s06[:6]:
        S.append(mk(f"pm73_fight_06_s{sl}", "pm73_fight", [sl], tag="06_nat"))
    b = OBJ + s06[0] * REC
    S.append(mk("pm73_fight_06_dw1", "pm73_fight", [s06[0]],
               [h.lw_word(RAM["pm73_fight"], b + 18, 1)], tag="06_dw1"))
    # mode $08
    for sl in live(RAM["pm73_fight"], 0x08):
        S.append(mk(f"pm73_fight_08_s{sl}", "pm73_fight", [sl], tag="08_nat"))
    return S


if __name__ == "__main__":
    res = h.run_corpus(build_corpus(), min_states=20, min_branches=1,
                       steps=2_000_000, reuse_json="reuse" in sys.argv)
    sys.exit(0 if (res["passed"] and res["ok"] == res["tot"] == 1335) else 1)
