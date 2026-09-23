"""121st: $1623c (dying-entity path) vs the real 68000 through callcap 14b62,
over dead records that the game made itself on later lands (no synthetic
kills). Every other live record's owner byte is zeroed, so $14b62 only runs
$1623c. Tracked: pm_fsm_ref.REGIONS + the player's pigeon record ($4c112, 26 B)
+ the pigeon request word $57ff4.
    py -3 reversing/powermonger/py/diff_1623c.py   (corpus: scratchpad/pm121/corpus_1623c)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import pm_fsm_ref
from pm_fsm_diff import Harness, State
from pm_fsm_ref import OBJ, REC, s8, LEADERS

pm_fsm_ref.REGIONS = pm_fsm_ref.REGIONS + [(0x4c112, 0x4c112 + 26, "pigeon"), (0x57ff4, 0x57ff6, "pigeon_req")]
D = "scratchpad/pm121/corpus_1623c"
h = Harness(f"{D}/k5_12_0.snap", f"{D}/k5_12_0.ram", disk="scratchpad/powermonger.st", out_dir=D)
M68 = h.m68
ANCH = ["k5_12_0", "k5_s1", "k5_s2", "k0_s2", "k0_s3", "k25_s1", "k25_s3", "k60_s2"]
R = {n: (M68 / D / f"{n}.ram").read_bytes() for n in ANCH}


def dying(r):
    return [s for s in range(1, 512) if s8(r[OBJ + s * REC + 5]) < 0]


def st(name, n, extra=(), tag="nat", keep=None):
    r = R[n]
    k = dying(r) if keep is None else keep
    for s in k:
        h.obase(s)                               # (END-OBJ)/REC bound
    return State(name, h.disable_others(r, k) + list(extra), tag=tag,
                 snap=f"{D}/{n}.snap", ram=f"{D}/{n}.ram")


def w18(n, slot, v):
    return h.lw_word(R[n], OBJ + slot * REC + 18, v)


def build():
    S = [st(f"{n}_nat", n) for n in ANCH]
    # countdown reaching 0 on natural records: not found / found (goods credited)
    for n, slot, tag in (("k5_12_0", 198, "zero_nf"), ("k5_12_0", 205, "zero_found"),
                         ("k0_s2", 29, "zero_found"), ("k0_s2", 39, "zero_found_nogoods"),
                         ("k0_s2", 100, "zero_found"), ("k0_s2", 101, "zero_nf"),
                         ("k60_s2", 21, "zero_found"), ("k5_s2", 15, "zero_nf")):
        S.append(st(f"{n}_{slot}_to0", n, [w18(n, slot, 1)], tag, keep=[slot]))
    # flags bit 5 set: always byte6 $20 + unlink (natural b7 = $30 / $21 on land 25)
    for slot in (55, 68):
        S.append(st(f"k25_s3_{slot}_bit5", "k25_s3", [w18("k25_s3", slot, 1)], "zero_bit5", keep=[slot]))
    # goods counter already $ff: no credit
    r = R["k0_s2"]; b = OBJ + 100 * REC
    lead = LEADERS + (((r[0x4f916 + 0] << 8) | 0) * 0)   # placeholder, replaced below
    m = pm_fsm_ref.Mem(bytearray(r))
    head = m.wu(pm_fsm_ref.BUCKETS + 2 * pm_fsm_ref._cell_word(m, b))
    while head:
        a0 = pm_fsm_ref._objaddr(pm_fsm_ref.s16(head))
        if r[a0 + 6] in (2, 0x10, 0x1e):
            break
        head = m.wu(a0)
    lead = LEADERS + m.ws(a0 + 14)
    sat = h.bytepokes(r, {lead + 24 + (r[b + 33] - 2) // 2: 0xff, lead + 24 + (r[b + 44] - 2) // 2: 0xff})
    S.append(st("k0_s2_100_sat", "k0_s2", [w18("k0_s2", 100, 1)] + sat, "zero_sat", keep=[100]))
    # pigeon request ($16308): natural request, a record already at 0 -> launch
    S.append(st("k0_s2_101_req", "k0_s2", [w18("k0_s2", 101, 0)], "req_launch", keep=[101]))
    S.append(st("k5_12_0_199_req", "k5_12_0", [w18("k5_12_0", 199, 0)], "req_launch", keep=[199]))
    # request with the pigeon busy (natural byte6 20): request cleared, nothing else
    S.append(st("k5_s1_req_busy", "k5_s1", [h.lw_word(R["k5_s1"], 0x57ff4, 0x141e)], "req_busy"))
    # request, pigeon free, first record met is byte6 $0a remains -> launch + unlink
    S.append(st("k5_s1_req_remains", "k5_s1",
                [h.lw_word(R["k5_s1"], 0x57ff4, 0x141e), h.lw_at(R["k5_s1"], 0x4c112 + 6, 0)], "req_unlink"))
    return S


h.run_corpus(build(), min_states=20, min_branches=8)
