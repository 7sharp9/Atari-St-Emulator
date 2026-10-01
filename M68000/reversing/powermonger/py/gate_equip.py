"""137th gate: pm_fsm_ref.call_160f8 / call_160e4 / call_160f2 / call_16892(D2) vs the real 68000 (201 states, 385/385 bytes).

    cd M68000 && python3 reversing/powermonger/py/gate_equip.py [name-substring] [reuse]
(corpus and callcap output under scratchpad/pm137/equip_gate/)

Method.  $160f8 ends in `bra $1622c`, the iterator's next-record step, so a plain `callcap 160f8` would run on into the
mode handlers.  The man's record is therefore COPIED (50 bytes, via `w` pokes) onto record slot 511 ($57f34, the last record);
$1622c then does `lea 50(A1),A1 ; cmpa.l #$57f66,A1 ; bne` and falls to its `rts`, which callcap sees as a clean return.
The tail reads only 7(A1), 33(A1), 34(A1), 44(A1), so a copied record is the same entry state as the original.
`callcap 160f8 ... A1=57f34` is then compared over pm_fsm_ref.REGIONS (obj, bucket, leader, settlement; leader widened here to
$4f916 because the stale-D0 credit can land up to 4*(lord>>3) leader records past the lord) and, strictly, any real write
outside them is a failure.  Also compared: the final low words of D0 and D1 (regN of the callcap).

Corpus: NATURAL = live men of the base snapshots copied unmodified (any man with a non-zero lord goods[0..3], a weapon in byte 44,
a carried item, plus a few plain ones); SYNTH = pokes of goods[0..3], byte 44, byte 33, byte 7 bit 0 and the lord index
(14(settlement 0) := 32*idx, 34(man) := 0) over every arm.  Plus the stubs $160e4/$160f2, $16892 with D2=$8e/$90, and
NATIVE-EXCHANGE: the real e1/e2 exchange in the pm136 before/after snapshots, replayed through the model.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "scratchpad/pm137/equip_gate"
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref
R = pm_fsm_ref
from pm_fsm_ref import SETTL, LEADER, OBJ, REC, Mem
from pm_fsm_diff import Harness, State
from pm_export import ram_from_snap

M68 = ROOT
LEADER_END = 0x4f916
pm_fsm_ref.REGIONS = [r for r in pm_fsm_ref.REGIONS if r[2] != "leader"] + [(LEADER, LEADER_END, "leader_wide")]
OUT = "scratchpad/pm137/equip_gate/out"
(M68 / OUT).mkdir(parents=True, exist_ok=True)
(HERE / "ram").mkdir(parents=True, exist_ok=True)

SLOT = 511
DEST = OBJ + SLOT * REC            # $57f34
BASES = {                          # name -> snapshot (M68000-relative)
    "k5s4": "scratchpad/pm121/run/k5_s4.snap",
    "e1": "scratchpad/pm136/equip/e1_before.snap",
    "e2": "scratchpad/pm136/equip/e2_before.snap",
    "k25s3": "scratchpad/pm121/run/k25_s3.snap",
}
RAM = {}
for k, s in BASES.items():
    p = HERE / "ram" / (k + ".ram")
    if not p.exists():
        p.write_bytes(ram_from_snap(M68 / s))
    RAM[k] = p.read_bytes()
h = Harness(BASES["k5s4"], str(HERE / "ram" / "k5s4.ram"), disk="scratchpad/powermonger.st", out_dir=OUT)

W = lambda r, a: (r[a] << 8) | r[a + 1]
RES, ARMS = {}, {}                 # name -> (D0.w, D1.w) / (bool,)  ;  name -> arm tag set


def men(ram):
    """Live men (side 1..127, category 0) with a valid home settlement and lord: (slot, addr, lord_idx)."""
    out = []
    nset = W(ram, 0x51536)
    for s in range(1, 512):
        a = OBJ + s * REC
        if not (1 <= ram[a + 5] <= 127) or ram[a + 6] != 0:
            continue
        so = W(ram, a + 34)
        if so % 18 or so >= nset:
            continue
        L = W(ram, SETTL + so + 14)
        if L % 32 or L >= 32 * 64:
            continue
        out.append((s, a, L // 32))
    return out


def lord_goods(ram, a):
    L = W(ram, SETTL + W(ram, a + 34) + 14)
    return list(ram[LEADER + L + 24:LEADER + L + 28])


def arms_of(ram, pk, A1, fn):
    m = Mem(bytearray(pk))
    del R.EQUIP_TRACE[:]
    fn(m, A1)
    t = list(R.EQUIP_TRACE)
    del R.EQUIP_TRACE[:]
    L = W(pk, SETTL + W(pk, A1 + 34) + 14)
    return t, L // 32


def mk(name, base, src_addr, edits=None, target="160f8", D2=None, fn=None):
    """State: record at src_addr copied onto slot 511, then `edits` {addr: byte} on top."""
    ram = RAM[base]
    e = {DEST + i: ram[src_addr + i] for i in range(50)}
    e.update(edits or {})
    pokes = Harness.bytepokes(ram, e)
    pk = Harness.poked_ram(ram, pokes)
    fn = fn or {"160f8": R.call_160f8, "160e4": R.call_160e4, "160f2": R.call_160f2}.get(target)
    presets = {"A1": DEST}
    if D2 is not None:
        presets["D2"] = D2
        f = lambda m, D2=D2: RES.__setitem__(name, (int(R.call_16892(m, DEST, D2)),))
        tr, lord = [], None
        m = Mem(bytearray(pk)); ok = R.call_16892(m, DEST, D2)
        tag = f"d2_{D2:x}_{'hit' if ok else 'miss'}"
        ARMS[name] = {tag}
    else:
        def f(m, fn=fn):
            RES[name] = fn(m, DEST)
        tr, lord = arms_of(ram, pk, DEST, fn)
        ARMS[name] = set(tr) | {"lord_ge8" if lord >= 8 else "lord_lt8"}
        tag = "+".join(sorted(set(tr))) + ("+lord%d" % (lord >> 3 if lord >= 8 else 0))
    return State(name, pokes, tag=tag, snap=str(M68 / BASES[base]), ram=str(HERE / "ram" / (base + ".ram")),
                 target=target, presets=presets, recon=f)


def synth_edits(ram, lord, goods, b44, farmer, b33, job_src):
    e = {}
    L = 32 * lord
    e[SETTL + 14], e[SETTL + 15] = L >> 8, L & 0xff          # settlement 0's lord
    e[DEST + 34] = e[DEST + 35] = 0                          # man's home := settlement 0
    for i, g in enumerate(goods):
        e[LEADER + L + 24 + i] = g
    e[DEST + 44] = b44
    e[DEST + 33] = b33
    b7 = ram[job_src + 7] & ~0x11                            # clear farmer bit 0 and the group bit 4
    e[DEST + 7] = b7 | (1 if farmer else 0)
    return e


GOODS = {"Z": (0, 0, 0, 0), "P": (1, 0, 0, 0), "S": (0, 1, 0, 0), "B": (0, 0, 1, 0), "ALL": (1, 1, 1, 1),
         "PL": (0, 0, 0, 2), "BS": (0, 2, 1, 0)}
COMBO = {"c1": (0, False, 0), "c2": (6, False, 0), "c3": (0, True, 0), "c4": (2, True, 8), "c5": (0, True, 10),
         "c6": (4, True, 4)}


def build():
    S = []
    # ---- natural: unmodified men of the base snapshots
    for base, ram in RAM.items():
        ms = men(ram)
        pick = [x for x in ms if any(lord_goods(ram, x[1])) or ram[x[1] + 44] or (ram[x[1] + 7] & 1 and ram[x[1] + 33])]
        plain = [x for x in ms if x not in pick][:2]
        pick = pick[:10] + plain
        for s, a, lord in pick:
            S.append(mk(f"nat_{base}_{s}", base, a))
    # ---- synthetic arms, on a farmer-free base man of k5s4 (record copied, fields poked)
    ram = RAM["k5s4"]
    src = men(ram)[0][1]
    for lord in (3, 8, 16):
        for gk, g in GOODS.items():
            for ck, (b44, fm, b33) in COMBO.items():
                if ck == "c6" and gk != "ALL":
                    continue
                S.append(mk(f"syn_L{lord}_{gk}_{ck}", "k5s4", src, synth_edits(ram, lord, g, b44, fm, b33, src)))
    for lord in (7, 15, 31):
        for gk in ("ALL", "PL", "B"):
            for ck in ("c1", "c4", "c5"):
                b44, fm, b33 = COMBO[ck]
                S.append(mk(f"syn_L{lord}_{gk}_{ck}", "k5s4", src, synth_edits(ram, lord, GOODS[gk], b44, fm, b33, src)))
    # ---- stubs (byte 7 bit 4 cleared so $3c08 stays out of the group-teardown subtree)
    for tgt in ("160e4", "160f2"):
        for lord, gk, ck in ((3, "ALL", "c4"), (8, "PL", "c5"), (12, "BS", "c2"), (3, "Z", "c1")):
            b44, fm, b33 = COMBO[ck]
            S.append(mk(f"stub{tgt}_L{lord}_{gk}_{ck}", "k5s4", src, synth_edits(ram, lord, GOODS[gk], b44, fm, b33, src), target=tgt))
    # ---- $16892 with the caller's D2
    for D2 in (0x8e, 0x90):
        for lord, gk in ((3, "Z"), (3, "P"), (8, "PL"), (16, "B"), (9, "Z")):
            S.append(mk(f"g16892_{D2:x}_L{lord}_{gk}", "k5s4", src, synth_edits(ram, lord, GOODS[gk], 0, False, 0, src),
                        target="16892", D2=D2))
    return S


def native_exchange():
    """e1/e2: the real exchange in the pm136 before/after snapshots, through the model (no callcap)."""
    ok = n = 0
    for k in ("e1", "e2"):
        b = RAM[k]
        a = ram_from_snap(M68 / BASES[k].replace("_before", "_after"))
        for s in range(1, 512):
            r0 = OBJ + s * REC
            if b[r0 + 44] != a[r0 + 44] or b[r0 + 33] != a[r0 + 33]:
                m = Mem(bytearray(b))
                del R.EQUIP_TRACE[:]
                R.call_160f8(m, r0)
                L = W(b, SETTL + W(b, r0 + 34) + 14)
                got = (m.bu(r0 + 44), m.bu(r0 + 33), bytes(m.r[LEADER + L + 24:LEADER + L + 32]))
                real = (a[r0 + 44], a[r0 + 33], bytes(a[LEADER + L + 24:LEADER + L + 32]))
                n += 1
                ok += got == real
                print(f"native {k} slot {s} lord {L // 32} arms {R.EQUIP_TRACE}: model {got[0]},{got[1]},{got[2].hex()} real {real[0]},{real[1]},{real[2].hex()} {'ok' if got == real else 'DIFF'}")
    print(f"NATIVE EXCHANGES: {ok}/{n}")


def main():
    S = build()
    res = h.run_corpus(S, min_states=100, min_branches=10, steps=50000, reuse_json="reuse" in sys.argv, strict_coverage=True,
                     extra_regions=[(0x2c800, 0x2ca00, "stack ($3c08 movem save)")])
    only = next((x for x in sys.argv[1:] if x != "reuse"), None)
    failed = {f[0] for f in res["fails"]}
    REGN = ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7"]
    bad = chk = 0
    for st in S:
        if only and only not in st.name:
            continue
        p = M68 / OUT / f"o_{st.name}.json"
        if st.name not in RES or not p.exists():
            continue
        rn = dict(zip(REGN, json.load(open(p))["regN"]))
        exp = RES[st.name]
        got = (rn["D0"] & 0xffff, rn["D1"] & 0xffff) if len(exp) == 2 else (rn["D0"] & 0xffff,)
        chk += 1
        if tuple(exp) != got:
            bad += 1
            failed.add(st.name)
            print(f"REG MISMATCH {st.name}: real {[hex(x) for x in got]} model {[hex(x) for x in exp]}")
    print(f"RETURNED REGS: {chk - bad}/{chk} identical (D0.w, D1.w; D0 only for $16892)")
    arms = {}
    for st in S:
        if only and only not in st.name:
            continue
        for a in ARMS.get(st.name, ()):
            t = arms.setdefault(a, [0, 0])
            t[1] += 1
            t[0] += st.name not in failed
    print("PER-ARM  (pass/total):", {k: f"{v[0]}/{v[1]}" for k, v in sorted(arms.items())})
    native_exchange()
    print("GATE", "PASS" if res["passed"] and not bad else "FAIL")


if __name__ == "__main__":
    main()
