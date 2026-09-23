"""pm124: $4f68 (mode $2c target picker) + $539a (conquest arm) vs the real 68000.

Natural states: every one of the 169 $4f68 calls in the 50M steps after the
win-run attack click (scratchpad/pm123/win/m1_atk.snap), captured by
    python3 tools/capture_hits.py scratchpad/pm123/win/m1_atk.snap 4f68 1,...,169 \
        scratchpad/pm124/conquest/cap --name w4f68
each called directly (`callcap 4f68 A1=...`).  Hit 169 is the natural
conquest: arm $12 -> $539a -> $550e (lord 0 to side 1).  The same state is
also called at $539a directly.  Then minimal pokes for arms the natural run
misses (named below).

    python3 reversing/powermonger/py/diff_4f68.py [filter] [reuse] [nat]
"""
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
import pm_fsm_ref as R
from pm_fsm_diff import Harness, State
import pm_fsm_ref as X

D = "scratchpad/pm124/conquest"
CAP = json.load(open(HERE.parents[2] / D / "cap" / "w4f68.json"))
R.REGIONS = R.REGIONS + [
    (0x4e514, 0x4f914, "leader_all"),
    (0x4f916, 0x4f916 + 240 * 18, "settlement_all"),
    (0x51538, 0x51538 + 5 * 0x13c, "group"),
    (X.FX, X.FX + 0x10 * 0x32, "projectiles"),
    (X.STATS_12B74 - 0x40, X.STATS_12B74 + 0x80, "stats_12b74"),
    (X.STATS_12B12, X.STATS_12B12 + 2, "stats_12b12"),
    (R.RNG_SEED, R.RNG_SEED + 4, "rng_seed"),
    (0x4cff8, 0x4d252, "garrison_markers"),
]
h = Harness(CAP[0]["snap"], CAP[0]["ram"], disk="scratchpad/powermonger.st", out_dir=f"{D}/out")
(h.m68 / D / "out").mkdir(exist_ok=True)
REUSE = "reuse" in sys.argv
SOUND_IDLE = 0x2c993
ACK = [(0x2c800, 0x2c948, "stack"), (0x2c992, 0x2c9a0, "snd_vars"),
       (0x2cba2, 0x2cba6, "snd_ptr"), (0x1af3a, 0x1af3e, "snd_vector"),
       (0x78000, 0x80000, "screen"), (0x580a6, 0x580a6 + 5 * 0x20, "side_assess")]
RAM = {}


def ram(e):
    if e["ram"] not in RAM:
        RAM[e["ram"]] = (h.m68 / e["ram"]).read_bytes()
    return RAM[e["ram"]]


def tag_of(fn, e, pokes, A1):
    m = R.Mem(h.poked_ram(ram(e), pokes))
    try:
        return fn(m, A1)
    except AssertionError as ex:
        return "ASSERT"


def st(e, name, pokes=(), target="4f68", A1=None, tag=None):
    A1 = e["regs"]["A1"] if A1 is None else A1
    pokes = [h.lw_at(ram(e), SOUND_IDLE, 0)] + list(pokes)
    fn = X.call_4f68 if target == "4f68" else X.call_539a
    t = tag or tag_of(fn, e, pokes, A1)
    return State(name, pokes, tag=t, snap=e["snap"], ram=e["ram"], target=target,
                 presets={"A1": A1}, recon=lambda m, A1=A1, fn=fn: fn(m, A1))


def pk(e, b=None, w=None):
    b = dict(b or {})
    for a, v in (w or {}).items():
        b[a] = (v >> 8) & 0xff
        b[a + 1] = v & 0xff
    return h.bytepokes(ram(e), b)


def build(nat_only=False):
    S = [st(e, f"w_{e['hit']:03d}") for e in CAP]
    last = CAP[-1]                                   # hit 169: the natural conquest
    S.append(st(last, "c539a_nat", target="539a"))
    if nat_only:
        return S
    A1 = last["regs"]["A1"]
    r = ram(last)
    m = R.Mem(r)
    lord0 = 0x4e514
    # $539a direct: 38 = $14 (target was a group): no $550e, only $35f4
    S.append(st(last, "c539a_k14", pk(last, b={A1 + 38: 0x14}), target="539a"))
    # $539a direct: not the local side -> the $12b74 stats word is left alone
    S.append(st(last, "c539a_notlocal", pk(last, w={X.LOCAL_SIDE: 3}), target="539a",
                tag="539a_notlocal"))
    # arm $12, the lead (28(A1)) in melee ($32) on a live enemy -> $5458 -> pick
    lead = X._A539(X.OBJ, m.wu(A1 + 28)) if m.wu(A1 + 28) else A1
    enemy = CAP[0]["regs"]["A1"]
    tgt = None
    for s in range(1, 512):                          # any live side-2 man near us
        a = h.obase(s)
        if r[a + 5] == 2 and r[a + 30] != 0x3c:
            tgt = a
            break
    if tgt and lead != A1:
        S.append(st(last, "k12_leadfight", pk(last, b={lead + 30: 0x32},
                                               w={lead + 48: (tgt - X.OBJ) & 0xffff})))
    # arm $12 with flags bits 4 and 6 clear -> $3c08
    S.append(st(last, "k12_noflags", pk(last, b={A1 + 7: r[A1 + 7] & ~0x50})))
    # arm $14 / $16: same group-done walk, $539a without $550e
    S.append(st(last, "k14_done", pk(last, b={A1 + 38: 0x14})))
    # arm 0 (-> $4fc4 via the nop at $4fc2) on a leader with no field men -> advance
    S.append(st(last, "k00_nofield", pk(last, b={A1 + 38: 0}, w={lord0 + 8: 0})))
    # arm $18 (-> $4fc2 too)
    S.append(st(last, "k18_lord", pk(last, b={A1 + 38: 0x18})))
    # arm 2 by a man with no weapon (44 = 0) and flag bit 6 clear -> $16892 first
    e0 = CAP[0]
    a0 = e0["regs"]["A1"]
    r0 = ram(e0)
    lordA1 = X._A539(X.LEADERS, R.Mem(r0).wu(X._A539(X.SETTL, R.Mem(r0).wu(a0 + 34)) + 14))
    S.append(st(e0, "p16892_goods", pk(e0, b={a0 + 44: 0, a0 + 7: r0[a0 + 7] & ~0x40,
                                             lordA1 + 24: 1})))
    S.append(st(e0, "p16892_none", pk(e0, b={a0 + 44: 0, a0 + 7: r0[a0 + 7] & ~0x40,
                                            lordA1 + 24: 0, lordA1 + 25: 0,
                                            lordA1 + 26: 0, lordA1 + 27: 0})))
    # arm 6: 46(A1) a single man (a live enemy / a dead one)
    S.append(st(e0, "k06_live", pk(e0, b={a0 + 38: 6}, w={a0 + 46: (tgt - X.OBJ) & 0xffff})))
    S.append(st(e0, "k06_dead", pk(e0, b={a0 + 38: 6, tgt + 5: 0x80 | 2},
                                  w={a0 + 46: (tgt - X.OBJ) & 0xffff})))
    # arm 8: follow a live man ($36/$66) / his death with the three $510e exits
    S.append(st(e0, "k08_follow", pk(e0, b={a0 + 38: 8}, w={a0 + 46: (tgt - X.OBJ) & 0xffff})))
    dead = {a0 + 38: 8, tgt + 5: 0xfe}
    S.append(st(e0, "k08_gone_b6", pk(e0, b={**dead, a0 + 7: 0x40}, w={a0 + 46: (tgt - X.OBJ) & 0xffff})))
    S.append(st(e0, "k08_gone_none", pk(e0, b={**dead, a0 + 7: 0x00}, w={a0 + 46: (tgt - X.OBJ) & 0xffff})))
    S.append(st(e0, "k08_gone_b4g", pk(e0, b={**dead, a0 + 7: 0x10},
                                       w={a0 + 46: (tgt - X.OBJ) & 0xffff})))
    # arm $a: shoot a live man (weapon 2 -> $57f0 type $28; weapon 6 -> no-op)
    S.append(st(e0, "k0a_shoot", pk(e0, b={a0 + 38: 0xa}, w={a0 + 46: (tgt - X.OBJ) & 0xffff})))
    S.append(st(e0, "k0a_w6", pk(e0, b={a0 + 38: 0xa, a0 + 44: 6}, w={a0 + 46: (tgt - X.OBJ) & 0xffff})))
    # arm $c: walk to 46's cell
    S.append(st(e0, "k0c_walk", pk(e0, b={a0 + 38: 0xc}, w={a0 + 46: (tgt - X.OBJ) & 0xffff})))
    # arm $e/$10: help an ally of my lord; natural: none in $2e..$34 at home -> $5402
    S.append(st(e0, "k0e_help", pk(e0, b={a0 + 38: 0xe})))
    S.append(st(last, "k10_help", pk(last, b={A1 + 38: 0x10})))
    # arm 6 on the nearest live side-2 man (in range) -> picked
    near = min((h.obase(s) for s in range(1, 512)
                if r0[h.obase(s) + 5] == 2 and r0[h.obase(s) + 30] != 0x3c),
               key=lambda a: max(abs(R.Mem(r0).ws(a + 8) - R.Mem(r0).ws(a0 + 8)),
                                 abs(R.Mem(r0).ws(a + 10) - R.Mem(r0).ws(a0 + 10))))
    S.append(st(e0, "k06_near", pk(e0, b={a0 + 38: 6}, w={a0 + 46: (near - X.OBJ) & 0xffff})))
    # arm 8, target dead, A1 a group lead's member with flag bit 4 and 42 = the group -> $35f4
    g = R.Mem(r).wu(lead + 42)
    S.append(st(last, "k08_gone_35f4", pk(last, b={A1 + 38: 8, A1 + 7: 0x10, tgt + 5: 0xfe},
                                          w={A1 + 42: g, A1 + 46: (tgt - X.OBJ) & 0xffff})))
    return S


if __name__ == "__main__":
    nat = "nat" in sys.argv
    S = build(nat_only=nat)
    h.run_corpus(S, min_states=len(S), min_branches=5 if nat else 12, reuse_json=REUSE,
                 strict_coverage=True, extra_regions=ACK,
                 only=next((a for a in sys.argv[1:] if a not in ("reuse", "nat")), ""))
