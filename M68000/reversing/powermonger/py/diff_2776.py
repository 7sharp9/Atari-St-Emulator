"""122nd: $2776 (group dissolve) vs the real 68000 (4119/4119 over 28 states).

Natural states: the 13 natural $2776 calls in the pm121 50M-step stretches,
each stopped at PC=$2776 (`bpc 2776 1`) and snapshotted into nat/.  callcap
$2776 with the entry A3 as a preset.  Poked states follow, each named for
the one branch it forces.

    py -3 reversing/powermonger/py/diff_2776.py [filter] [reuse]
(corpus: scratchpad/pm122/agents/dissolve/{nat,nat2,out})
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import pm_fsm_ref
import pm_fsm_ref as R
from pm_fsm_diff import Harness, State
from pm_fsm_ref import OBJ, s8, s16

pm_fsm_ref.REGIONS = pm_fsm_ref.REGIONS + [
    (0x4c12c, 0x4c5f2, "fx"),
    (0x4bb4e, 0x4bdee, "drop"),
    (0x51538, 0x51538 + 5 * 0x13c, "group"),
    (0x57fd2, 0x57fd4, "selgroup"),
    (0x57fd8, 0x57fe2, "57fd8"),
    (0x58016, 0x58034, "cmd"),
    (0x58042, 0x5804c, "curgroup"),
    (0x58368, 0x5836c, "1c328"),
]
D = "scratchpad/pm122/agents/dissolve/nat"
h = Harness(f"{D}/k5_s1_1.snap", f"{D}/k5_s1_1.ram", disk="scratchpad/powermonger.st",
            out_dir="scratchpad/pm122/agents/dissolve/out")
M68 = h.m68
(M68 / h.out_dir).mkdir(exist_ok=True)

NAT = {  # name -> entry A3 (from the bpc register dump in nat/<stretch>.log)
    "k0_s2_1": 0x51a74, "k0_s4_1": 0x51800, "k25_s3_1": 0x51a76, "k25_s4_1": 0x517fc,
    "k25_s4_2": 0x51a76, "k5_s1_1": 0x517fc, "k5_s2_1": 0x517fe, "k5_s2_2": 0x51a76,
    "k5w_s1_1": 0x517fc, "k5w_s2_1": 0x51a76, "k5w_s3_1": 0x5193c, "k60_s1_1": 0x51a74,
    "k60_s2_1": 0x51a76,
}
# 5th stretch: continuing each land from pm121/run/<land>_s4.snap (nat2/).
# Both are the LOCAL side 1: k60_x1 is side 1's captain group (its only
# group: the player's loss), step 94,725,510; k5_x1 is side 1's sub-record 2,
# step 92,750,899.
NAT2 = {"k60_x1": 0x516c0, "k5_x1": 0x516c4}
D2 = "scratchpad/pm122/agents/dissolve/nat2"
NAT.update(NAT2)
DIR = {n: (D2 if n in NAT2 else D) for n in NAT}
RAM = {n: (M68 / DIR[n] / f"{n}.ram").read_bytes() for n in NAT}

PRIMARY = ("captain", "member", "39d4_bit5", "39d4_settl", "39d4_drop", "39d4_new",
           "39d4_nofree", "settl_own", "clamp", "b44", "drop_link", "fx_clear", "fx_local", "lead_alive", "187d8", "71ae")


def tag_of(ram, pokes, a3):
    R.DISSOLVE_TRACE.clear()
    m = pm_fsm_ref.Mem(h.poked_ram(ram, pokes))
    R.call_2776(m, a3)
    t = [p for p in PRIMARY if p in R.DISSOLVE_TRACE]
    return "+".join(t)


def st(name, n, a3, pokes=()):
    pokes = list(pokes)
    return State(name, pokes, tag=tag_of(RAM[n], pokes, a3), snap=f"{DIR[n]}/{n}.snap",
                 ram=f"{DIR[n]}/{n}.ram", target="2776", presets={"A3": a3},
                 recon=lambda m, a3=a3: R.call_2776(m, a3))


def snd_idle(n):
    """callcap runs at IPL 7, so the sound driver's wait for the previous
    sample ($1ae40: tst.b $2c993 ; bne) never ends when a sample is still
    playing at entry.  Poke the sound-busy flag $2c993 to 0 (sample finished).
    $2c993 is sound-driver state, outside every tracked region."""
    return [h.lw_at(RAM[n], 0x2c993, 0)] if RAM[n][0x2c993] else []


def build():
    S = [st(f"{n}_nat", n, a3, snd_idle(n)) for n, a3 in NAT.items()]

    def P(name, n, pairs, words=()):
        """a poked state: byte pokes `pairs` {addr: byte}, word pokes `words`
        [(addr, word)], plus the sound-idle poke."""
        r = bytearray(RAM[n])
        for a, v in words:
            r[a], r[a + 1] = (v >> 8) & 0xff, v & 0xff
        allb = dict(pairs)
        for a, v in words:
            allb[a], allb[a + 1] = (v >> 8) & 0xff, v & 0xff
        S.append(st(name, n, NAT[n], h.bytepokes(RAM[n], allb) + snd_idle(n)))

    # member arm, fx record owned by the local side: $27ee..$2812 clears
    # $57fd8[k].  k60_s2_1's matching fx record $4c12c (natural side byte $fc)
    # gets side 1 (= $57ffe); $57fda (k = 1) is 0 naturally, so seed it so
    # the clear is visible.
    P("k60_s2_1_fxlocal", "k60_s2_1", {0x4c12c + 5: 1}, [(0x57fda, 0x1234)])
    # $39d4 finds an existing goods drop ($2c) on the lead's cell ($3a60 via
    # the bucket walk): move k5_s2_2's lead ($51e54) onto the cell $138c of
    # the natural drop $4bb4e (x byte 8 := $0c, y word 10 := $4e80).
    P("k5_s2_2_ondrop", "k5_s2_2", {0x51e54 + 8: 0x0c}, [(0x51e54 + 10, 0x4e80)])
    # $39d4 with every $4bb4e drop record busy (6(A0) > 0): no drop made.
    P("k5_s2_1_dropsfull", "k5_s2_1",
      {a + 6: 0x2c for a in range(0x4bb4e, 0x4bdee, 28)})
    # captain arm, side's (mis-indexed, 3*side) command state 8 / 6 -> $71ae
    P("k5_s1_1_cmd8", "k5_s1_1", {0x58016 + 3 * 2 + 4: 8})
    P("k60_s1_1_cmd6", "k60_s1_1", {0x58016 + 3 * 4 + 4: 6})
    # captain arm of the LOCAL side (the loss trigger): make side 4 local
    # ($57ffe := 4) on k60_s1_1 / k0_s2_1 -> $3ce8 writes $57fd2 and $187d8 runs
    P("k60_s1_1_local", "k60_s1_1", {}, [(0x57ffe, 4)])
    P("k0_s2_1_local", "k0_s2_1", {}, [(0x57ffe, 4)])
    # member arm of the local side: $57ffe := 4 on k5w_s2_1 (side 4, k = 1)
    P("k5w_s2_1_local", "k5w_s2_1", {}, [(0x57ffe, 4)])
    # 44(lead) >= $e (cmpi.b #$e,44(A1)): the lead's item is handed over
    # too.  Natural 44(lead) is 0 or 6 in every state, so poke $0e / $10.
    for n, v in (("k5_s2_1", 0x0e), ("k0_s2_1", 0x10), ("k25_s3_1", 0x10)):
        lead = OBJ + s16(pm_fsm_ref.Mem(RAM[n]).wu(NAT[n] - 12))
        P(f"{n}_item{v:02x}", n, {lead + 44: v})
    # settlement goods byte saturating ($3b70 clamp to $ff): k0_s2_1 hands
    # 8 of goods[4] to the settlement's leader record; set that byte to $fc.
    tag_of(RAM["k0_s2_1"], snd_idle("k0_s2_1"), NAT["k0_s2_1"])
    ldr = R.DISSOLVE_INFO["leader"]
    P("k0_s2_1_clamp", "k0_s2_1", {ldr + 24 + 4: 0xfc})
    # ... and with 44(lead) = $10 on a saturated item byte ((($10-2)>>1) = 7)
    P("k0_s2_1_itemsat", "k0_s2_1", {ldr + 24 + 7: 0xff, OBJ + s16(
        pm_fsm_ref.Mem(RAM["k0_s2_1"]).wu(NAT["k0_s2_1"] - 12)) + 44: 0x10})
    return S


if __name__ == "__main__":
    for s in build():
        print(f"  {s.name:24} {s.tag}")
    h.run_corpus(build(), min_states=28, min_branches=21, reuse_json="reuse" in sys.argv,
                 extra_regions=[])
