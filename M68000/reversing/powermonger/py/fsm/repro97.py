"""98th-pass acceptance: re-prove the 97th pass (settlement heartbeat mode $7c
on a NATURAL corpus - pm97_map0) against the graduated tools/pm_fsm_ref.py +
pm_fsm_diff.py, reusing scratchpad/pm97/o_*.json.

Expected: 99/99 tracked bytes identical over 27 states.

Ported verbatim from scratchpad/pm97/diff_pm97.py build_corpus().
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
from pm_fsm_diff import Harness, State
from pm_fsm_ref import OBJ, REC

h = Harness("scratchpad/pm97/pm97_map0.snap", "scratchpad/pm97/pm97_map0.ram",
            out_dir="scratchpad/pm97")
R = h.anchor_ram_bytes
SETTL = 0x4f916
LEADER = 0x4e514

SL = [s for s in range(1, 512)
      if R[OBJ + s * REC + 5] != 0 and R[OBJ + s * REC + 31] == 0x7c]
assert len(SL) == 19, SL
S3 = [s for s in SL if R[OBJ + s * REC + 5] == 3]
S2 = [s for s in SL if R[OBJ + s * REC + 5] == 2]


def settl_off(s):
    return struct.unpack_from(">h", R, OBJ + s * REC + 34)[0]


CONSTR = [s for s in SL if R[SETTL + settl_off(s) + 7] == 0x0a]


def dwell(slot, v):
    b = OBJ + slot * REC
    return {b + 18: (v >> 8) & 0xff, b + 19: v & 0xff}


def leaderfield(loff, off, v):
    a = LEADER + loff + off
    return {a: (v >> 8) & 0xff, a + 1: v & 0xff}


def a14eq3(slot):
    return {OBJ + slot * REC + 14: (R[OBJ + slot * REC + 14] & ~3) | 3}


def st(name, keep, pk, tag):
    return State(name, h.disable_others(R, keep, trio=False) + h.bytepokes(R, pk), tag=tag)


def build_corpus():
    a, b, c, d, e = S3[0], S2[0], S3[2], S3[3], S2[2]
    con1, con2 = CONSTR[0], CONSTR[1]
    S = []
    S.append(st("nat_raw_all", SL, {}, "dwell>0"))
    S.append(st("dwell_gt0_a", [a], dwell(a, 50), "dwell>0"))
    S.append(st("dwell_gt0_b", [b], dwell(b, 300), "dwell>0"))
    S.append(st("pulse_s3", [a], dwell(a, 1), "ge_nod5"))
    S.append(st("pulse_s2", [b], dwell(b, 1), "ge_nod5"))
    S.append(st("pulse_s3_c", [c], dwell(c, 1), "ge_nod5"))
    S.append(st("ge_d5_s3", [a], dwell(a, 0xff9d), "ge_d5"))
    S.append(st("ge_d5_s2", [b], dwell(b, 0xff9d), "ge_d5"))
    p = dwell(d, 0xff9d); p.update(leaderfield(0, 14, 597))
    S.append(st("ge_d5_near600", [d], p, "ge_d5"))
    S.append(st("floor_s3", [a], dwell(a, 1), "floor"))
    p = dwell(b, 1); p.update(leaderfield(32, 6, 1))
    S.append(st("floor_s2_r1", [b], p, "floor"))
    p = dwell(a, 0xff9d); p.update(leaderfield(0, 6, 200)); p.update(a14eq3(a))
    S.append(st("lt_d5_s3", [a], p, "lt_d5"))
    p = dwell(b, 0xff9d); p.update(leaderfield(32, 6, 200)); p.update(a14eq3(b))
    S.append(st("lt_d5_s2", [b], p, "lt_d5"))
    p = dwell(c, 1); p.update(leaderfield(0, 6, 200)); p.update(a14eq3(c))
    S.append(st("lt_nod5_s3", [c], p, "lt_nod5"))
    p = dwell(e, 1); p.update(leaderfield(32, 6, 200)); p.update(a14eq3(e))
    S.append(st("lt_nod5_s2", [e], p, "lt_nod5"))
    S.append(st("bit4_s3", [a], {**dwell(a, 1), OBJ + a * REC + 7: R[OBJ + a * REC + 7] | 0x10}, "bit4"))
    S.append(st("bit4_con", [con1], {**dwell(con1, 1), OBJ + con1 * REC + 7: R[OBJ + con1 * REC + 7] | 0x10}, "bit4"))
    p = dwell(a, 1); p.update(leaderfield(0, 8, 0))
    S.append(st("field0_s3", [a], p, "field0"))
    p = dwell(b, 1); p.update(leaderfield(32, 8, 0))
    S.append(st("field0_s2", [b], p, "field0"))
    S.append(st("build_con1", [con1], dwell(con1, 1), "build"))
    S.append(st("build_con2", [con2], dwell(con2, 1), "build"))
    so1 = settl_off(con1)
    p = dwell(con1, 1); p[SETTL + so1 + 16] = 0x77
    S.append(st("build_done_1", [con1], p, "build_done"))
    so2 = settl_off(con2)
    p = dwell(con2, 1); p[SETTL + so2 + 16] = 0x77
    S.append(st("build_done_2", [con2], p, "build_done"))
    p = dwell(a, 1); p[OBJ + a * REC + 5] = 2
    p[OBJ + a * REC + 7] = R[OBJ + a * REC + 7] & ~0x90
    S.append(st("adopt_s3", [a], p, "adopt"))
    p = dwell(b, 1); p[OBJ + b * REC + 5] = 3
    p[OBJ + b * REC + 7] = R[OBJ + b * REC + 7] & ~0x90
    S.append(st("adopt_s2", [b], p, "adopt"))
    pk = {}
    for s in S3[:4]:
        pk.update(dwell(s, 1))
    for s in S2[:4]:
        pk.update(dwell(s, 0xff9d))
    S.append(st("multi_all", SL, pk, "multi"))
    pk = {}
    pk.update(dwell(con1, 1)); pk.update(dwell(con2, 1))
    pk.update(dwell(S3[0], 0xff9d)); pk.update(dwell(S2[0], 0xff9d))
    S.append(st("multi_con", [con1, con2, S3[0], S2[0]], pk, "multi"))
    return S


if __name__ == "__main__":
    res = h.run_corpus(build_corpus(), min_states=15, min_branches=8,
                       steps=3_000_000, reuse_json="reuse" in sys.argv)
    sys.exit(0 if (res["passed"] and res["ok"] == res["tot"] == 99) else 1)
