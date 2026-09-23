"""122nd: $5cde (leader settlement herd-op decision) vs the real 68000,
callcap 5cde directly on natural entry states (stopped at a real call with
`bpc 5cde n`, the HARVEST table below), plus minimal pokes for unreached exits.

Tracked: pm_fsm_ref.REGIONS + the whole $4f916 settlement table and its
allocation counter $51536, OBJ slot 0 (the order loop walks it when a
settlement has no units), the $57f68 herd-op table and the $580a6 side table
(both read-only here: any write would be a failure).  Also checks the
returned D2/D3/D4 low words against callcap regN.
    py -3 reversing/powermonger/py/diff_5cde.py [substr] [reuse]
(corpus: scratchpad/pm122/agents/herdop/corpus)
"""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import pm_fsm_ref
from pm_fsm_diff import Harness, State
from pm_fsm_ref import call_5cde, SETTL, SETTL_COUNT, OBJ, HERD_OPS, HERD_OPS_END, LEADERS

pm_fsm_ref.REGIONS = pm_fsm_ref.REGIONS + [
    (SETTL, SETTL_COUNT + 2, "settlement_all"),
    (OBJ, OBJ + 50, "obj_slot0"),
    (HERD_OPS, HERD_OPS_END, "herd_op"),
    (0x580a6, 0x580a6 + 32 * 8, "side_tab"),
]
# stretch -> (stretch-start snapshot, the within-stretch $5cde hit numbers snapped)
HARVEST = {
    "k0s1": ("scratchpad/pm121/k0.snap", [1, 2]),
    "k0s2": ("scratchpad/pm121/run/k0_s1.snap", [1]),
    "k0s3": ("scratchpad/pm121/run/k0_s2.snap", [1, 60, 150, 223]),
    "k0s4": ("scratchpad/pm121/run/k0_s3.snap", [1, 40, 83]),
    "k5s3": ("scratchpad/pm121/run/k5_s2.snap", [1, 38]),
    "k5s4": ("scratchpad/pm121/run/k5_s3.snap", [1, 100, 200, 298]),
    "k25s1": ("scratchpad/pm121/k25.snap", [1, 2]),
    "k25s4": ("scratchpad/pm121/run/k25_s3.snap", [1, 200, 450, 705]),
    "k60s2": ("scratchpad/pm121/run/k60_s1.snap", [1, 5]),
    "k60s4": ("scratchpad/pm121/run/k60_s3.snap", [1, 27, 54]),
    "k5ws1": ("scratchpad/pm121/k5_s0.snap", [1, 200, 397]),
    "k5ws3": ("scratchpad/pm121/run/k5w_s2.snap", [1, 16]),
}
D = "scratchpad/pm122/agents/herdop/corpus"
h = Harness(f"{D}/k0s3_1.snap", f"{D}/k0s3_1.ram", disk="scratchpad/powermonger.st", out_dir=D)
M68 = h.m68
RES = {}          # state name -> expected (D2, D3, D4)
REGN = ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7"]


def entry_regs():
    """name -> {reg: value} from the corpus bpc logs (one bpc block per snap)."""
    out = {}
    for log in (M68 / D).glob("*.log"):
        txt = log.read_text()
        blocks = txt.split("--- breakpoint $00005cde hit")[1:]
        snaps = re.findall(r"^snap (\S+)", txt, re.M)
        names = re.findall(r"saved.*?(\S+\.snap)", txt)
        for b in blocks:
            regs = dict(re.findall(r"([DA][0-7]):([0-9a-f]{8})", b))
            ret = re.search(r"return address \(A7\) = \$([0-9a-f]+)", b)
            out.setdefault(log.stem, []).append(({k: int(v, 16) for k, v in regs.items()},
                                                 int(ret.group(1), 16) if ret else None))
    return out


def nat_states():
    regs = entry_regs()
    S = []
    for k, (_, hs) in HARVEST.items():
        for i, n in enumerate(hs):
            name = f"{k}_{n}"
            if not (M68 / D / f"{name}.ram").exists():
                continue
            r, ret = regs[k][i]
            S.append((name, r, ret))
    return S


def recon_for(name, A0, D1, A5):
    def f(m):
        RES[name] = call_5cde(m, A0, D1, A5)
    return f


def classify(ram, A0, D1, A5):
    """Branch family of a state, computed on a scratch copy (does not gate)."""
    m = pm_fsm_ref.Mem(bytearray(ram))
    r = call_5cde(m, A0, D1, A5)
    if r[0] == 0:
        return "exit_nocap" if m.wu(A0 + 2) else "exit_noset"
    b12 = m.wu(A0 + 12)
    if r[0] == 0x3e:
        return f"herd_{b12:x}"
    if r[0] == 0x6a:
        return "fallback"
    if pm_fsm_ref.Mem(ram).wu(A0 + 18):
        return f"building_{b12:x}"
    return f"newsettl_{b12:x}"


def mk(name, snapname, regs, pokes=(), tag=None, ret=None, D1=None):
    ram = (M68 / D / f"{snapname}.ram").read_bytes()
    A0, A5 = regs["A0"], regs["A5"]
    D1 = regs["D1"] if D1 is None else D1
    assert LEADERS <= A0 < LEADERS + 32 * 40 and (A0 - LEADERS) % 32 == 0, (name, hex(A0))
    pk = h.poked_ram(ram, pokes)
    fam = classify(pk, A0, D1, A5)
    caller = {0x158a0: "c1589a", 0x5fc6: "c5fc0"}.get(ret, "c?") if ret else ""
    return State(name, list(pokes), tag=tag or fam, snap=f"{D}/{snapname}.snap", ram=f"{D}/{snapname}.ram",
                 target="5cde", presets={"A0": A0, "D1": D1, "A5": A5},
                 recon=recon_for(name, A0, D1, A5)), caller


def build():
    S, callers = [], {}
    nat = nat_states()
    by = {}
    for name, r, ret in nat:
        st, c = mk(name, name, r, ret=ret)
        callers[name] = c
        by[name] = (r, ret)
        S.append(st)
    return S, callers, by


def main():
    S, callers, by = build()
    extra = poke_states(by)
    S += extra
    reuse = "reuse" in sys.argv
    res = h.run_corpus(S, min_states=47, min_branches=15, reuse_json=reuse,
                       strict_coverage=True,
                       extra_regions=[(0x2c800, 0x2ca00, "stack (movem save)")])
    # returned-register check (D2/D3/D4 low words, what the $5fc0 caller uses)
    only = next((a for a in sys.argv[1:] if a != "reuse"), None)
    bad = 0; checked = 0
    for st in S:
        if only and only not in st.name:
            continue
        p = M68 / D / f"o_{st.name}.json"
        if st.name not in RES or not p.exists():
            continue
        j = json.load(open(p))
        rn = dict(zip(REGN, j["regN"]))
        exp = RES[st.name]
        got = (rn["D2"] & 0xffff, rn["D3"] & 0xffff, rn["D4"] & 0xffff)
        for i, (e, g) in enumerate(zip(exp, got)):
            if e is None:
                continue
            checked += 1
            if e != g:
                bad += 1
                print(f"REG MISMATCH {st.name} D{2 + i}: real {g:04x} recon {e:04x}")
    print(f"RETURNED REGS: {checked - bad}/{checked} identical (D2/D3/D4 low words)")
    print("callers:", {c: sum(1 for v in callers.values() if v == c) for c in set(callers.values())})
    ok = res["passed"] and bad == 0
    print("GATE", "PASS" if ok else "FAIL")


def poke_states(by):
    """Minimal pokes / presets for exits no natural state reached."""
    S = []
    R = lambda n: (M68 / D / f"{n}.ram").read_bytes()

    def add(name, base, pokes=(), tag=None, D1=None):
        r, ret = by[base]
        st, _ = mk(name, base, r, pokes, tag=tag, ret=ret, D1=D1)
        S.append(st)

    def lw(base, off, v):                     # word at A0+off of the base state's leader
        return h.lw_word(R(base), by[base][0]["A0"] + off, v)

    def ctl(base, v):                         # the leader cell's $3f86c control byte
        r = R(base); a = 0x3f86c + pm_fsm_ref.s16(pm_fsm_ref.Mem(r).wu(by[base][0]["A0"] + 4))
        return h.lw_at(r, a, v)

    # $5ce8: leader with no settlements at all (2(A0) == 0) -> D2 = 0
    add("p_noset", "k0s3_1", [lw("k0s3_1", 2, 0)], "exit_noset")
    # $5ec0 / $5eb8 / $5e9c: the other D1 selectors on a natural herd state (register presets only)
    add("p_herd_d1_1", "k60s4_1", (), D1=1)
    add("p_herd_d1_2", "k60s4_1", (), D1=2)
    add("p_herd_d1_1b", "k0s1_1", (), D1=1)
    add("p_herd_d1_2b", "k0s1_1", (), D1=2)
    # $5dce: leader already building (18(A0) != 0): order $40, arg = 18(A0)
    add("p_building_d1_0", "k0s1_1", [lw("k0s1_1", 18, 0x2be)])
    add("p_building_d1_1", "k0s1_1", [lw("k0s1_1", 18, 0x2be)], D1=1)
    # $5d98/$5da0: cell control >= $10 and no herd op within 20 -> build; flagged unit found -> new settlement ($5e18, $16808)
    add("p_newsettl", "k0s2_1", [ctl("k0s2_1", 0x10)])
    add("p_newsettl_b", "k0s1_1", [ctl("k0s1_1", 0x10)])
    # $5e14: settlement table full ($51536 >= $1c20) -> fallback
    add("p_full", "k0s2_1", [ctl("k0s2_1", 0x10), h.lw_word(R("k0s2_1"), 0x51536, 0x1c20)], "fallback_full")
    # $5e06: no unit with flags bit 0 in the chain -> fallback.  Chain cut to the capital $a2 + $b4
    # (whose units carry no bit 0), unit 18 (the capital's only flagged unit) bit 0 cleared.
    r = R("k0s2_1")
    add("p_noflag", "k0s2_1", [ctl("k0s2_1", 0x10), lw("k0s2_1", 2, 0xa2),
                                h.lw_at(r, h.obase(18) + 7, r[h.obase(18) + 7] & 0xfe)], "fallback_noflag")
    # $5dac: control >= $10, herd op within 20: $57fed bit 0 picks build (set) or herd (clear)
    add("p_fed1", "k60s4_1", [ctl("k60s4_1", 0x10)])
    r = R("k60s4_1")
    add("p_fed0", "k60s4_1", [ctl("k60s4_1", 0x10), h.lw_at(r, 0x57fed, r[0x57fed] & 0xfe)], "herd_via_fed0")
    # $5f24: order >= $e and 16(A0) above the side reload -> no +$2000
    add("p_no2000", "k0s1_1", [lw("k0s1_1", 16, 0x7fff)], "herd_e_no2000")
    # $5f42: a settlement with no units (10 == 0): the order loop has no head test and walks
    # OBJ slot 0; slot 0's owner set to 2 so the write is visible
    r = R("k0s1_1"); m = pm_fsm_ref.Mem(r)
    first = SETTL + m.wu(by["k0s1_1"][0]["A0"] + 2)
    add("p_slot0", "k0s1_1", [h.lw_word(r, first + 10, 0), h.lw_at(r, OBJ + 5, 2)], "slot0_walk")
    return S


if __name__ == "__main__":
    main()
