"""98th-pass acceptance: re-prove the 96th pass (settlement heartbeat mode $7c
on a SYNTHESISED corpus) against the graduated tools/pm_fsm_ref.py +
pm_fsm_diff.py, reusing scratchpad/pm96/o_*.json.

Expected: 85/85 tracked bytes identical over 25 states.

Ported verbatim from scratchpad/pm96/diff_pm96.py build_corpus().
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
from pm_fsm_diff import Harness, State
from pm_fsm_ref import OBJ, REC

h = Harness("scratchpad/pm96/pm78_settle.snap", "scratchpad/pm96/pm78_settle.ram",
            out_dir="scratchpad/pm96")
R = h.anchor_ram_bytes

SETTL = 0x4f916
LEADER = 0x4e514
S1, S5, S6, S10, S11 = 18, 90, 108, 180, 198
FD0, FD0_LW = 0x57fd0, 0x00000188


def free68():
    return [s for s in range(1, 512)
            if R[OBJ + s * REC + 5] != 0 and R[OBJ + s * REC + 31] == 0x68]


def mk7c(slot, settl_off, *, dwell, flags=0x00, b14=None, side=2, link24=0):
    b = OBJ + slot * REC
    p = {b + 31: 0x7c, b + 30: 0x68,
         b + 18: (dwell >> 8) & 0xff, b + 19: dwell & 0xff,
         b + 7: flags, b + 5: side,
         b + 34: (settl_off >> 8) & 0xff, b + 35: settl_off & 0xff,
         b + 24: (link24 >> 8) & 0xff, b + 25: link24 & 0xff,
         b + 45: 0x20}
    if b14 is not None:
        p[b + 14] = b14
    return p


def st(name, keep, pk_bytes, tag):
    pokes = h.disable_others(R, keep, trio=False) + [(FD0, FD0_LW)] + h.bytepokes(R, pk_bytes)
    return State(name, pokes, tag=tag)


def build_corpus():
    s = free68()
    a, b, c, d, e, f, g, hh = s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7]
    S = []
    S.append(st("dwell_gt0_a", [a], mk7c(a, S1, dwell=5), "dwell>0"))
    S.append(st("dwell_gt0_b", [b], mk7c(b, S6, dwell=200), "dwell>0"))
    S.append(st("bit4_s1", [a], mk7c(a, S1, dwell=1, flags=0x10), "bit4"))
    S.append(st("bit4_s6", [b], mk7c(b, S6, dwell=1, flags=0x10), "bit4"))
    p = mk7c(a, S1, dwell=1); p[LEADER + 0 + 8] = 0; p[LEADER + 0 + 9] = 0
    S.append(st("field0_lo0", [a], p, "field0"))
    p = mk7c(b, S6, dwell=1); p[LEADER + 32 + 8] = 0; p[LEADER + 32 + 9] = 0
    S.append(st("field0_lo32", [b], p, "field0"))
    S.append(st("ge_nod5_s1", [a], mk7c(a, S1, dwell=1), "ge_nod5"))
    S.append(st("ge_nod5_s5", [b], mk7c(b, S5, dwell=1), "ge_nod5"))
    S.append(st("ge_d5_s1", [a], mk7c(a, S1, dwell=0xff9d), "ge_d5"))
    S.append(st("ge_d5_s5", [c], mk7c(c, S5, dwell=0xff9d), "ge_d5"))
    p = mk7c(d, S1, dwell=0xff9d); p[LEADER + 0 + 14] = 0x02; p[LEADER + 0 + 15] = 0x55
    S.append(st("ge_d5_near600", [d], p, "ge_d5"))
    S.append(st("lt_d5_s6", [a], mk7c(a, S6, dwell=0xff9d, b14=0x03), "lt_d5"))
    S.append(st("lt_d5_s10", [b], mk7c(b, S10, dwell=0xff9d, b14=0x1b), "lt_d5"))
    S.append(st("lt_nod5_s6", [a], mk7c(a, S6, dwell=1, b14=0x03), "lt_nod5"))
    S.append(st("lt_nod5_s10", [c], mk7c(c, S10, dwell=1, b14=0x07), "lt_nod5"))
    S.append(st("build_s5", [a], mk7c(a, S5, dwell=1), "build"))
    S.append(st("build_s10", [b], mk7c(b, S10, dwell=1), "build"))
    p = mk7c(a, S5, dwell=1); p[SETTL + S5 + 16] = 0x77
    S.append(st("build_done_s5", [a], p, "build_done"))
    p = mk7c(b, S10, dwell=1); p[SETTL + S10 + 16] = 0x77
    S.append(st("build_done_s10", [b], p, "build_done"))
    p = mk7c(a, S1, dwell=1); p[LEADER + 0 + 6] = 0; p[LEADER + 0 + 7] = 0
    S.append(st("floor_s1", [a], p, "floor"))
    p = mk7c(b, S6, dwell=0xff9d, b14=0x03); p[LEADER + 32 + 6] = 0; p[LEADER + 32 + 7] = 0
    S.append(st("floor_s6_d5", [b], p, "floor"))
    S.append(st("adopt_s1", [a], mk7c(a, S1, dwell=1, side=3), "adopt"))
    S.append(st("adopt_s6", [b], mk7c(b, S6, dwell=1, side=3), "adopt"))
    pk = {}
    pk.update(mk7c(a, S1, dwell=1))
    pk.update(mk7c(b, S6, dwell=0xff9d, b14=0x03))
    pk.update(mk7c(c, S5, dwell=1))
    S.append(st("multi3", [a, b, c], pk, "multi"))
    pk = {}
    pk.update(mk7c(d, S1, dwell=0xff9d))
    pk.update(mk7c(e, S5, dwell=0xff9d))
    pk.update(mk7c(f, S10, dwell=1, b14=0x03))
    pk.update(mk7c(g, S6, dwell=1, b14=0x03))
    S.append(st("multi4_sharedleader", [d, e, f, g], pk, "multi"))
    return S


if __name__ == "__main__":
    res = h.run_corpus(build_corpus(), min_states=15, min_branches=8,
                       steps=2_000_000, reuse_json="reuse" in sys.argv)
    sys.exit(0 if (res["passed"] and res["ok"] == res["tot"] == 85) else 1)
