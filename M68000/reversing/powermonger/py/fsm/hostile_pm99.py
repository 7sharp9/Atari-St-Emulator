"""Hostile re-checks (steps 4 and 5 start the emulator through `pwsh ./run.ps1`) for the flag-bit-4 group-teardown proof
($37c2 / $1d70 / $1b8c / $17a46 behind $3c08's $3c46 arm).

 1. the reconstruction provably never reads the callcap output (Harness builds
    `pk` and `after_real` as separate bytearrays; recon gets Mem(pk)).  -
    structural, unchanged since the 93rd.
 2. each branch family's tracked delta lands where the disasm predicts.
 3. negative controls: break one integer in call_37c2 / call_1d70 / call_1b8c
    and confirm the tracked comparison flips across the affected states.
 4. determinism: two consecutive `callcap 37c2` give a byte-identical delta.
 5. detcheck on the anchor snapshot.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pm_fsm_ref
import diff_pm99 as D
from pm_fsm_ref import OBJ, REC

H = D.h
R = D.R
CORPUS = D.build_corpus()
OUT = H.m68 / "scratchpad/pm99"


def load(name):
    st = next(s for s in CORPUS if s.name == name)
    ram0 = (H.m68 / st.ram).read_bytes() if st.ram else R
    pk = H.poked_ram(ram0, st.pokes)
    j = json.load(open(OUT / f"o_{name}.json"))
    after = bytearray(pk)
    for a, b0, b1 in j["mem"]:
        after[a] = b1
    return st, pk, H.tracked_delta(pk, after), j


def cls(a):
    if OBJ <= a < 0x57f66:
        return f"obj+{(a - OBJ) % REC}"
    if 0x4e514 <= a < 0x4ea14:
        return f"leader+{(a - 0x4e514) % 40}"
    if 0x4f916 <= a < 0x4fa16:
        return f"settl+{(a - 0x4f916) % 18}"
    return hex(a)


def run_recon(ns, st, pk):
    m = ns["Mem"](pk)
    if st.recon is not None:
        # rebuild the same lambda against the patched namespace
        t, pr = st.target, st.presets
        if t == "37c2":
            ns["call_37c2"](m, pr["D2"])
        elif t == "1d70":
            ns["call_1d70"](m, pr["A3"])
        elif t == "3c08":
            ns["call_3c08"](m, pr["A1"])
        elif t == "1b8c":
            ns["call_1b8c"](m, pr["A0"], pr["A1"], pr["D1"])
        elif t == "17a46":
            ns["call_17a46"](m, pr["D2"])
    else:
        ns["reconstruct"](m)
    return H.tracked_delta(pk, m.r)


print("=== (2) per-family tracked-delta address classes ===")
byfam = {}
for st in CORPUS:
    if not (OUT / f"o_{st.name}.json").exists():
        continue
    _, _, real, _ = load(st.name)
    byfam.setdefault(st.tag, set()).update(cls(a) for a in real)
for tg, s in sorted(byfam.items()):
    print(f"  {tg:20} -> {sorted(s)}")

print("\n=== (3) negative controls (break one integer, expect mismatches) ===")
SRC = (Path(__file__).resolve().parents[4] / "tools" / "pm_fsm_ref.py").read_text()
PATCHES = [
    ("$382a troops_field  -= 1  ->  -= 2",
     "m.ww(A2l + s16(D0) + 8,\n                 (m.wu(A2l + s16(D0) + 8) - 1) & 0xffff)   # subi.w #$1,8(A2,D0.w)",
     "m.ww(A2l + s16(D0) + 8,\n                 (m.wu(A2l + s16(D0) + 8) - 2) & 0xffff)   # subi.w #$1,8(A2,D0.w)",
     ("37c2_bit7set_b6clr",)),
    ("$1d70 member mode  30 := $08  ->  $09",
     "m.wb(A1 + 30, 0x08)                     # move.b #$8,30(A1)",
     "m.wb(A1 + 30, 0x09)                     # move.b #$8,30(A1)",
     ("1d70", "3c08_bit4", "e2e", "1d70_state6_w46", "1b8c")),
    ("$1d70 target  asl.w #6  ->  #7  (D1)",
     "m.ww(A1 + 20, (D1s << 6) & 0xffff)      # $1e46 asl.w #6,D1 ; move.w D1,20(A1)",
     "m.ww(A1 + 20, (D1s << 7) & 0xffff)      # $1e46 asl.w #6,D1 ; move.w D1,20(A1)",
     ("1d70", "3c08_bit4", "e2e")),
    ("$37c2 re-parent  5(A0) := byte[-47(A1)]  ->  +1",
     "m.wb(A0 + 5, m.bu(A1 - 47))             # move.b -47(A1),5(A0)",
     "m.wb(A0 + 5, (m.bu(A1 - 47) + 1) & 0xff) # move.b -47(A1),5(A0)",
     ("37c2_bit7set_b6clr", "37c2_bit6set_1b8c")),
    ("$1b8c troops_field  += 1  ->  += 2",
     "m.ww(A2l + s16(d0) + 8,\n             (m.wu(A2l + s16(d0) + 8) + 1) & 0xffff)   # addi.w #$1,8(A2,D0.w)",
     "m.ww(A2l + s16(d0) + 8,\n             (m.wu(A2l + s16(d0) + 8) + 2) & 0xffff)   # addi.w #$1,8(A2,D0.w)",
     ("1b8c", "37c2_bit6set_1b8c")),
]
for label, old, new, tags in PATCHES:
    assert old in SRC, repr(old)
    ns = {"__file__": os.path.abspath(str(Path(__file__).resolve().parents[4] / "tools" / "pm_fsm_ref.py"))}
    exec(SRC.replace(old, new, 1), ns)
    ns["init_tables"](R)
    total = hitn = 0
    for st in CORPUS:
        if st.tag not in tags or not (OUT / f"o_{st.name}.json").exists():
            continue
        _, pk, real, _ = load(st.name)
        try:
            recon = run_recon(ns, st, pk)
        except AssertionError as e:
            print(f"    {st.name}: assert {e}")
            continue
        keys = set(real) | set(recon)
        mm = sum(1 for k in keys if real.get(k) != recon.get(k))
        total += mm
        hitn += mm > 0
    print(f"  {label:44} -> {total} mismatched bytes / {hitn} states  "
          f"{'OK' if total else 'FAIL (did not bite)'}")

print("\n=== (4) determinism: two callcap 37c2 D2=392 ===")
hs = []
for i in (1, 2):
    script = f"callcap 37c2 400000 scratchpad/pm99/det{i}.json D2=188\nq\n"
    subprocess.run(["pwsh", "-NoProfile", "-c",
                    "./run.ps1 -NoBuild rrepl scratchpad/pm97/pm97_map1.snap -DiskA scratchpad/pm69.st"],
                   input=script, capture_output=True, text=True, cwd=H.m68, timeout=200)
    j = json.load(open(OUT / f"det{i}.json"))
    hs.append((j["hash"], tuple(map(tuple, j["mem"]))))
print(f"  hash1={hs[0][0]}  hash2={hs[1][0]}  "
      f"{'IDENTICAL' if hs[0] == hs[1] else 'DIVERGED'}")

print("\n=== (5) detcheck 1000000 on pm97_map1 ===")
p = subprocess.run(["pwsh", "-NoProfile", "-c",
                    "./run.ps1 -NoBuild rrepl scratchpad/pm97/pm97_map1.snap -DiskA scratchpad/pm69.st"],
                   input="detcheck 1000000\nq\n", capture_output=True, text=True,
                   cwd=H.m68, timeout=300)
for ln in p.stdout.splitlines():
    if "detcheck" in ln.lower() or "diverg" in ln.lower() or "identical" in ln.lower():
        print("  " + ln.strip())
