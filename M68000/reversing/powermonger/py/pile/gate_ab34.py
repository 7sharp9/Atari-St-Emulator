"""gate_ab34.py [snap ...]: differential gate of the camera "go to" dispatcher `_map_zoo` $ab34 (jump table $ab56 on byte 6), the generic reader
of chain-record offsets 8/10/12. For up to 3 chain records of each byte-6 category (the $47970 bucket walk of the snapshot; piles are chain
elements at a negative offset) run `callcap ab34 D0=<offset>` with the camera words $4bb3a/$4bb3c poked to a sentinel, and compare the camera after
with the model: byte6 in {0,8,a,c,e,12,14,16,1a,1c,22}: (byte 8, byte 10); {2,10,1e}: word 12; {4}: word 10; {6,18,2c}: word 8 (x = w & 3f, y = w >> 6);
{20,24..2a} and >= 2e: unchanged. Output: $PM_WORK/piles/gate_ab34.txt. The camera pokes are `w 4bb3a 77777777` (longword, covers $4bb3a..$4bb3d).
Run from anywhere: the repo root is found by walking up to tools/rdis.py."""
import os, re, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve()
while not (R / "tools" / "rdis.py").exists(): R = R.parent
ROOT = Path(os.environ.get("M68000_ROOT", R))
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "reversing/powermonger/py"))
from pm_export import ram_from_snap
from census import walk
WORK = ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork") / "piles"; WORK.mkdir(parents=True, exist_ok=True)
snaps = sys.argv[1:] or ["scratchpad/pm143/run/p0k0_s4.snap"]
SENT = 0x7777
BYTE8 = {0x0, 0x8, 0xa, 0xc, 0xe, 0x12, 0x14, 0x16, 0x1a, 0x1c, 0x22}
W12, W10, W8 = {0x2, 0x10, 0x1e}, {0x4}, {0x6, 0x18, 0x2c}
def model(rec):
    c = rec[6]
    def w(o): return (rec[o] << 8) | rec[o+1]
    if c in BYTE8: return rec[8], rec[10]
    for S, o in ((W12, 12), (W10, 10), (W8, 8)):
        if c in S: v = w(o); return v & 0x3f, (v >> 6) & 0xffff
    return SENT, SENT
tot = ok = 0; out = open(WORK / "gate_ab34.txt", "w")
for snap in snaps:
    base = ram_from_snap(ROOT / snap)
    recs, torn = walk(base)
    pick = {}
    for o, cx, cy, rec in recs:
        if len(pick.setdefault(rec[6], [])) < 3: pick[rec[6]].append((o, rec))
    cmds = ["disk scratchpad/powermonger.st"]; meta = []
    for c, L in sorted(pick.items()):
        for o, rec in L:
            cmds += [f"w 4bb3a {SENT:04x}{SENT:04x}", f"callcap ab34 20000 D0={(o - 0x51b66) & 0xffff:x}"]; meta.append((c, o, rec))
    r = subprocess.run(["dotnet", "exec", str(ROOT / "bin/Debug/net8.0/M68000.dll"), "resume", str(ROOT / snap), "repl"], input="\n".join(cmds) + "\nq\n",
                       capture_output=True, text=True, env=dict(os.environ, ATARI_NOTRACE="1"), cwd=ROOT, timeout=900)
    txt = r.stdout + r.stderr; (WORK / ("gate_ab34_raw_" + Path(snap).stem + ".txt")).write_text(txt)
    blocks = re.split(r"(?m)^--- callcap", txt)[1:]
    print(f"{snap}: {len(meta)} calls, {len(blocks)} callcap blocks, torn={torn}", file=out); print(f"{snap}: {len(meta)} calls, {len(blocks)} callcap blocks, torn={torn}")
    for (c, o, rec), blk in zip(meta, blocks):
        cam = {}
        for m in re.finditer(r"(?m)^mem \$([0-9a-f]+) \$([0-9a-f]+)->\$([0-9a-f]+)", blk): cam[int(m.group(1), 16)] = int(m.group(3), 16)
        b = [cam.get(0x4bb3a + i, 0x77) for i in range(4)]   # unchanged bytes stay the sentinel $77
        got = ((b[0] << 8) | b[1], (b[2] << 8) | b[3]); exp = model(rec)
        good = got == exp; tot += 1; ok += good
        print(f"  byte6 ${c:02x} rec ${o:x} exp {exp} got {got} {'ok' if good else 'MISMATCH'} returned={'returned' in blk.splitlines()[0]}", file=out)
        if not good: print(f"  MISMATCH byte6 ${c:02x} rec ${o:x} exp {exp} got {got}")
print(f"{ok}/{tot}", file=out); print(f"{ok}/{tot}")
