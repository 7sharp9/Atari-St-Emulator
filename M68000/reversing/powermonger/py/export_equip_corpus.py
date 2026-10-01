"""Export the equipment-exchange gate corpus for the F# port (`port/godot/logic/Equipment.fs`, `py/equip_check.fsx`).

    cd M68000 && python3 reversing/powermonger/py/export_equip_corpus.py [out.json]     # default scratchpad/pm138/equip_corpus.json

Reads the real-68000 `callcap` outputs of `py/gate_equip.py` (scratchpad/pm137/equip_gate/out/o_<state>.json, rerun
`gate_equip.py` first if they are missing) and writes, per state, the entry bytes of the region $4e514..$50116 (leaders and
settlements) plus the man's record, and the bytes the REAL routine left there. The F# check runs `Equipment` on the entry
bytes and compares the ranges in `cmp`. Native cases (the pm136 before/after snapshots) compare the man's bytes 33/44 and
the lord's eight goods counters only, as `gate_equip.native_exchange` does.

Case kinds: tail ($160f8), arriveFight ($160e4), arriveGoods ($160f2: the record is compared on bytes 33 and 44 only,
because $3c08, which the port does not have, rewrites bytes 6, 18..23, 30 and 31), goods ($16892, with d2).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_equip as G
from gate_equip import R, OBJ, REC, SETTL, LEADER, DEST, M68, OUT, RAM, BASES, W, ram_from_snap
from pm_fsm_diff import Harness

LO, HI = LEADER, SETTL + 0x800            # leaders .. settlements (the misdirected credit lands in here)
KIND = {"160f8": "tail", "160e4": "arriveFight", "160f2": "arriveGoods", "16892": "goods"}
REGN = ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7"]


def case(name, kind, entry, expect_ram, cmp, d2=None, d0=None, d1=None, lord=None):
    c = {"name": name, "kind": kind, "lord": lord,
         "lords": entry[LO:HI].hex(), "man": entry[DEST:DEST + REC].hex(),
         "xlords": expect_ram[LO:HI].hex(), "xman": expect_ram[DEST:DEST + REC].hex(),
         "cmp": cmp, "d0": d0, "d1": d1}
    if d2 is not None:
        c["d2"] = d2
    return c


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else M68 / "scratchpad/pm138/equip_corpus.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    cases = []
    for st in G.build():
        p = M68 / OUT / f"o_{st.name}.json"
        d = json.load(open(p))
        base = RAM[next(k for k, v in BASES.items() if str(M68 / v) == st.snap)]
        entry = Harness.poked_ram(base, st.pokes)
        after = bytearray(entry)
        for a, _b0, b1 in d["mem"]:
            if LO <= a < HI or DEST <= a < DEST + REC:
                after[a] = b1
        rn = dict(zip(REGN, d["regN"]))
        kind = KIND[st.target]
        if kind == "arriveGoods":
            cmp = [[LO, HI], [DEST + 33, DEST + 34], [DEST + 44, DEST + 45]]
        else:
            cmp = [[LO, HI], [DEST, DEST + REC]]
        if kind == "goods":
            c = case(st.name, kind, entry, after, cmp, d2=st.presets["D2"], d0=rn["D0"] & 0xffff)
        else:
            c = case(st.name, kind, entry, after, cmp, d0=rn["D0"] & 0xffff, d1=rn["D1"] & 0xffff)
        cases.append(c)
    n_synth = len(cases)
    for k in ("e1", "e2"):
        b = RAM[k]
        a = ram_from_snap(M68 / BASES[k].replace("_before", "_after"))
        for s in range(1, 512):
            r0 = OBJ + s * REC
            if b[r0 + 44] == a[r0 + 44] and b[r0 + 33] == a[r0 + 33]:
                continue
            e = bytearray(b)
            e[DEST:DEST + REC] = b[r0:r0 + REC]                  # the man's record on slot 511, as in the gate
            x = bytearray(e)
            x[DEST:DEST + REC] = a[r0:r0 + REC]
            L = W(b, SETTL + W(b, r0 + 34) + 14)
            x[LEADER + L + 24:LEADER + L + 32] = a[LEADER + L + 24:LEADER + L + 32]
            cases.append(case(f"native_{k}_{s}", "tail", e, x,
                              [[DEST + 33, DEST + 34], [DEST + 44, DEST + 45], [LEADER + L + 24, LEADER + L + 32]], lord=L // 32))
    json.dump({"lo": LO, "hi": HI, "dest": DEST, "rec": REC, "cases": cases}, open(out, "w"))
    print(f"{len(cases)} cases ({n_synth} gate states + {len(cases) - n_synth} native exchanges) -> {out}")


if __name__ == "__main__":
    main()
