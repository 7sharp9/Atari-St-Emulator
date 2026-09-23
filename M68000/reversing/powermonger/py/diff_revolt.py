"""122nd: $550e / $5c2c / $25d6 vs the real 68000 through callcap (1778/1778 over 49 states).

Natural states: every $550e the game ran on lands 0, 5 (two runs), 25 and 60 in
the pm121 200M-step stretches (captured by capture.py: `bpc 550e 1` from each
stretch start, snapshot + entry registers), called directly with their own entry
registers as presets; the $5c2c / $25d6 calls reached naturally (land 60 inside
the revolt, land 25 via the heartbeat's $16848) called directly on their own.
Then minimal pokes for branches the natural states miss (named below).

    py -3 reversing/powermonger/py/diff_revolt.py [filter] [reuse]
(corpus: scratchpad/pm122/agents/revolt/{nat,nat2,out})
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import pm_fsm_ref
import pm_fsm_ref as R
from pm_fsm_diff import Harness, State

pm_fsm_ref.REGIONS = pm_fsm_ref.REGIONS + [
    (0x4e514, 0x4f914, "leader_all"),
    (0x4f916, 0x4f916 + 240 * 18, "settlement_all"),
    (0x51538, 0x51538 + 5 * 0x13c, "group"),
    (0x58016, 0x58034, "cmd_slot"),
    (0x4c12c, 0x4c5f2, "small_obj"),
    (0x580a6, 0x580a6 + 5 * 0x20, "side_assess"),
    (0x57fd8, 0x57fe4, "pigeon_tgt"),
    (0x58042, 0x5804c, "sel_group"),
    (0x4bb4e, 0x4bdee, "piles"),
    (R.CNT_A, R.CNT_A + 2, "cnt_12abe"),
    (R.CNT_B, R.CNT_B + 2, "cnt_12acc"),
    (R.RNG_SEED, R.RNG_SEED + 4, "rng_seed"),
]
D = "scratchpad/pm122/agents/revolt"
NAT = f"{D}/nat"
h = Harness(f"{NAT}/k60_4_0_550e.snap", f"{NAT}/k60_4_0_550e.ram",
            disk="scratchpad/powermonger.st", out_dir=f"{D}/out")
(h.m68 / D / "out").mkdir(exist_ok=True)
M68 = h.m68
REUSE = "reuse" in sys.argv


def regs_from_logs():
    """{snap path: {reg: value}} from the capture logs (the register dump
    printed by the bp/bpc just before each `snap`)."""
    out = {}
    for log in sorted((M68 / NAT).glob("*.log")) + sorted((M68 / D / "nat2").glob("*.log")):
        cur = None
        for line in log.read_text().splitlines():
            if line.startswith("--- breakpoint"):
                cur = {}
            elif line.startswith("--- gave up"):
                cur = None
            elif cur is not None and re.match(r"^[DA]\d:", line):
                for k, v in re.findall(r"([DA]\d):([0-9a-f]{8})", line):
                    cur[k] = int(v, 16)
            else:
                mm = re.match(r"Snapshot written to (\S+) at", line)
                if mm and cur is not None:
                    out[mm.group(1)] = dict(cur)
    return out


REGS = regs_from_logs()
RAM = {}


def ram(snap):
    if snap not in RAM:
        RAM[snap] = (M68 / (snap[:-5] + ".ram")).read_bytes()
    return RAM[snap]


def dry(fn, snap, pokes, *args):
    m = pm_fsm_ref.Mem(h.poked_ram(ram(snap), pokes))
    try:
        return fn(m, *args)
    except AssertionError:
        return "ASSERT"


# ---------------------------------------------------------------- $550e path tags
def revolt_tag(snap, pokes, A0, A1, D3):
    """Branch family of one $550e call: the transcription's own path, run on a
    copy of the base RAM (never the callcap output)."""
    try:
        return "550e_" + dry(R.call_550e, snap, pokes, A0, A1, D3)
    except AssertionError as e:
        return "550e_ASSERT"


def st550e(snap, name=None, pokes=(), tag=None):
    rg = REGS[snap]
    A0, A1, D3 = rg["A0"], rg["A1"], rg["D3"]
    t = tag or revolt_tag(snap, [sound_idle(snap)] + list(pokes), A0, A1, D3)
    pokes = [sound_idle(snap)] + list(pokes)
    return State(name or Path(snap).stem, pokes, tag=t, snap=snap, ram=snap[:-5] + ".ram",
                 target="550e", presets={"A0": A0, "A1": A1, "D3": D3},
                 recon=lambda m, A0=A0, A1=A1, D3=D3: R.call_550e(m, A0, A1, D3))


def st5c2c(snap, name, pokes=(), A1=None, D3=None, tag=None):
    rg = REGS.get(snap, {})
    A1 = rg["A1"] if A1 is None else A1
    D3 = rg["D3"] if D3 is None else D3
    pokes = [sound_idle(snap)] + list(pokes)
    t = tag or ("5c2c_" + dry(R.call_5c2c, snap, pokes, A1, D3))
    return State(name, list(pokes), tag=t, snap=snap, ram=snap[:-5] + ".ram", target="5c2c",
                 presets={"A1": A1, "D3": D3}, recon=lambda m, A1=A1, D3=D3: R.call_5c2c(m, A1, D3))


def st25d6(snap, name, pokes=(), A1=None, D3=None, tag=None):
    rg = REGS.get(snap, {})
    A1 = rg["A1"] if A1 is None else A1
    D3 = rg["D3"] if D3 is None else D3
    pokes = [sound_idle(snap)] + list(pokes)
    t = tag or ("25d6_" + dry(R.call_25d6, snap, pokes, A1, D3))
    return State(name, list(pokes), tag=t, snap=snap, ram=snap[:-5] + ".ram", target="25d6",
                 presets={"A1": A1, "D3": D3}, recon=lambda m, A1=A1, D3=D3: R.call_25d6(m, A1, D3))


# callcap masks interrupts (IPL 7), so the sound driver's timer ISR never runs
# and $1ba3e -> $1b978 -> $1ae36 spins forever on the busy byte $2c993 (the
# ISR clears it at $1b802).  Every state starts with it clear: a sound-driver
# byte outside every tracked region.
SOUND_IDLE = 0x2c993
ACK = [(0x2c800, 0x2c948, "stack"), (0x2c992, 0x2c9a0, "snd_vars"),
       (0x2cba2, 0x2cba6, "snd_ptr"), (0x1af3a, 0x1af3e, "snd_vector"),
       (0x78000, 0x80000, "screen")]   # player-side states redraw the group panel


def sound_idle(snap):
    return h.lw_at(ram(snap), SOUND_IDLE, 0)


def build():
    S = []
    for p in sorted((M68 / NAT).glob("*_550e.snap")):
        S.append(st550e(f"{NAT}/{p.name}"))
    C60, D60 = f"{NAT}/k60_4_0_5c2c.snap", f"{NAT}/k60_4_0_25d6.snap"
    C25, D25 = f"{D}/nat2/k25_4_5c2c.snap", f"{D}/nat2/k25_4_25d6.snap"
    S.append(st5c2c(C60, "k60_4_0_5c2c"))           # inside the land-60 revolt
    S.append(st25d6(D60, "k60_4_0_25d6"))
    S.append(st5c2c(C25, "k25_4_5c2c"))             # land 25, from the $16176 removal path
    S.append(st25d6(D25, "k25_4_25d6"))             #   (man leads a group: $2776 arm)

    # ---- minimal pokes, one per branch the natural states miss ----
    def pk(snap, **kw):
        """bytes {addr: v} / words {addr: v} -> merged longword pokes."""
        b = dict(kw.get("b", {}))
        for a, v in kw.get("w", {}).items():
            b[a] = (v >> 8) & 0xff
            b[a + 1] = v & 0xff
        return h.bytepokes(ram(snap), b)

    def units(snap, A0, side):
        """(settlement, unit) pairs $550e walks for settlements not yet on `side`."""
        m = pm_fsm_ref.Mem(ram(snap))
        out, D0 = [], m.wu(A0 + 2)
        while D0:
            A2 = R._adda(R.SETTL, D0)
            if m.bu(A2 + 5) != side:
                U = m.wu(A2 + 10)
                while U:
                    A3 = R._adda(pm_fsm_ref.OBJ, U)
                    h.obase((A3 - pm_fsm_ref.OBJ) // pm_fsm_ref.REC)
                    out.append(A3)
                    U = m.wu(A3 + 24)
            D0 = m.wu(A2 + 8)
        return out

    # $550e: leader with no settlement chain (2(A0) = 0): only side + loyalty 300 written
    s = f"{NAT}/k0_2_1_550e.snap"
    S.append(st550e(s, "p550e_nochain", pk(s, w={REGS[s]["A0"] + 2: 0})))
    # $550e: mode-$3c units with flag bit 4 (natural $3c units have bit 4 clear) -> candidate
    s = f"{NAT}/k0_2_2_550e.snap"
    u = units(s, REGS[s]["A0"], ram(s)[REGS[s]["A1"] + 5])
    r0 = ram(s)
    S.append(st550e(s, "p550e_garr3c", pk(s, b={u[0] + 7: r0[u[0] + 7] | 0x10}), tag="550e_garr3c"))
    # both $3c units flagged: the LAST one walked is the one reconciled
    S.append(st550e(s, "p550e_garr_last", pk(s, b={u[0] + 7: r0[u[0] + 7] | 0x10,
                                                   u[1] + 7: r0[u[1] + 7] | 0x10}), tag="550e_garr_last"))
    # $550e: the land-60 garrison man already on the new side -> $5c2c returns at once
    s = f"{NAT}/k60_4_0_550e.snap"
    S.append(st550e(s, "p550e_garr_same", pk(s, b={0x52368 + 5: 3})))

    # $5c2c: man on his leader's side -> nothing
    S.append(st5c2c(C60, "p5c2c_same", pk(C60, b={0x52368 + 5: 3})))
    # $5c2c: man leads a group that still has members (-36 != 0) -> $4bc8
    #   (member chain = the man himself; his 26(A1) link is 0)
    S.append(st5c2c(C25, "p5c2c_4bc8_members", pk(C25, w={0x517fc - 36: 0x2af8})))
    # $5c2c: man leads an empty group but his leader has no troops_field -> $4bc8
    S.append(st5c2c(C25, "p5c2c_4bc8_nofield", pk(C25, w={0x4e6d4 + 8: 0})))

    # $25d6: D3 == 2 (the value $5c2c loads into D2) -> the $12abe/$12acc counters
    S.append(st25d6(D60, "p25d6_d3eq2", D3=2, tag="25d6_d3eq2"))
    # $25d6: new side's command slot kind != 4 -> 36(sub) stays 0
    S.append(st25d6(D60, "p25d6_cmd_not4", pk(D60, b={R.CMD + 3 * 6 + 4: 0}), tag="25d6_cmd_not4"))
    # $25d6: all six sub-records of side 3 owned -> no group, D3 = 0
    base3 = R.GROUP + 3 * 0x13c
    S.append(st25d6(D60, "p25d6_full", pk(D60, w={base3 + 28 + 2 * k: 3 for k in range(6)})))
    # $25d6: new side is the player's but D3 == 0 -> the jingle/UI arm is skipped
    S.append(st25d6(D60, "p25d6_player_d3_0", pk(D60, w={R.LOCAL_SIDE: 3}), D3=0,
                    tag="25d6_player_d3_0"))
    # $2776 via $25d6, sub-record != 0: the man's link points at side 2's sub 1
    sub1 = {0x5465e + 42: 0x2c6}
    S.append(st25d6(D25, "p2776_sub1", pk(D25, w=sub1), tag="25d6_2776_sub1_lost"))
    # $39d4 variants on that sub-1 disband (lead $51b66+$2292, group $517fe):
    G1, L1 = 0x517fe, R._adda(pm_fsm_ref.OBJ, 0x2292)
    r = ram(D25)
    #   (natural: this lead has flag bit 5 set -> $3aee "stores lost" arm; the pile
    #   variants below clear bit 5 so $39d4 reaches its cell walk)
    nb5 = {L1 + 7: r[L1 + 7] & ~0x20}
    #   group carries goods (84(A3)+12j) and the lead carries an item (44(lead) >= $e) -> pile gets them
    S.append(st25d6(D25, "p39d4_pile_goods", pk(D25, w={**sub1, G1 + 84: 5, G1 + 84 + 36: 3},
                                                 b={**nb5, L1 + 44: 0x10}), tag="39d4_pile_goods"))
    #   bit 5 set (natural) with goods and an item -> all of it is simply lost ($3aee)
    S.append(st25d6(D25, "p39d4_lost", pk(D25, w={**sub1, G1 + 84: 5}, b={L1 + 44: 0x10}), tag="39d4_lost"))
    #   every $4bb4e record in use -> no pile, nothing dropped
    S.append(st25d6(D25, "p39d4_piles_full", pk(D25, w=sub1, b={**nb5, **{a + 6: 1 for a in range(R.DROP_LO, R.DROP_HI, 28)}}),
                    tag="39d4_piles_full"))
    #   a $2c pile already heads the lead's cell chain -> added to it
    m = pm_fsm_ref.Mem(r)
    D6 = (m.wu(L1 + 10) >> 2) & 0x1fc0
    D6 = (D6 & 0xff00) | ((D6 + m.bu(L1 + 8)) & 0xff)
    bk = pm_fsm_ref.BUCKETS + 2 * D6
    S.append(st25d6(D25, "p39d4_pile_exists", pk(D25, w={**sub1, bk: (R.DROP_LO - pm_fsm_ref.OBJ) & 0xffff,
                                                          R.DROP_LO + 0: m.wu(bk), R.DROP_LO + 2: 0},
                                                 b={**nb5, R.DROP_LO + 6: 0x2c}), tag="39d4_pile_exists"))
    #   settlement-leader arm with the lead's item: goods[(44-2)/2] += 1 ($3b94)
    S.append(st25d6(D25, "p39d4_leader_item", pk(D25, b={0x5465e + 44: 0x10}), tag="39d4_leader_item"))
    # $2776 sub != 0: a player-side small object (pigeon) addressed to the lead -> its
    #   $57fd8 slot cleared and it is unlinked
    S.append(st25d6(D25, "p2776_pigeon", pk(D25, w={**sub1, R.FX_LO + 20: 0x2292},
                                            b={R.FX_LO + 5: 1, R.FX_LO + 6: 0x14}), tag="2776_pigeon"))
    return S


if __name__ == "__main__":
    h.run_corpus(build(), min_states=49, min_branches=24, reuse_json=REUSE,
                  strict_coverage=True, extra_regions=ACK)
