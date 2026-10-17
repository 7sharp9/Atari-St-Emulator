"""scan_off8.py [listing]: census of every operand with displacement 8 on an address register in the text segment $10a6..$1c48a.
Two independent passes:
 (1) the disassembly listing (`tools/disassemble.py --snap <snap> --all 10a6 1c600`, regenerated if missing): every `8(An)` / `8(An,Xn)` operand
     with the instruction, the routine (nearest symbol start from reversing/powermonger/*.sym) and access (read/write by operand position).
 (2) a raw every-even-address scan of the snapshot RAM image: a word with EA mode 5 (d16(An)) in bits 5..3 followed by extension word 8, or
     mode 6 (d8(An,Xn)) whose extension low byte is 8, found at every even address (also where the linear listing prints data/garbage).
Prints (2) minus (1) so decode gaps (handlers behind longword state tables) show up. Output: $PM_WORK/piles/off8.txt.
"""
import os, re, subprocess, sys, struct
from pathlib import Path
R = Path(__file__).resolve()
while not (R / "tools" / "rdis.py").exists(): R = R.parent
ROOT = Path(os.environ.get("M68000_ROOT", R))
WORK = ROOT / os.environ.get("PM_WORK", "scratchpad/pmwork") / "piles"; WORK.mkdir(parents=True, exist_ok=True)
SNAP = ROOT / "scratchpad/pm142/rand1.snap"
LST = WORK / "all.asm"
if not LST.exists():
    with open(LST, "w") as f: subprocess.run([sys.executable, str(ROOT/"tools/disassemble.py"), "--snap", str(SNAP), "--all", "10a6", "1c600"], stdout=f, check=True, cwd=ROOT)
starts = []
for fn in ("powermonger.sym", "powermonger_orig.sym"):
    for line in open(ROOT/"reversing/powermonger"/fn):
        p = line.split()
        if line.startswith("#") or len(p) < 2: continue
        try: starts.append((int(p[0], 16), p[1]))
        except ValueError: pass
starts.sort()
def routine(a):
    best = None
    for s, n in starts:
        if s <= a: best = (s, n)
        else: break
    return best
ins = []
for line in open(LST):
    m = re.match(r"\s+\$([0-9a-f]+): (.*)$", line)
    if m: ins.append((int(m.group(1), 16), m.group(2).strip()))
OP8 = re.compile(r"(?<![-\w$])8\((A[0-7])(?:,([AD][0-7])\.[wl])?\)")
rows1 = {}
for a, t in ins:
    if OP8.search(t): rows1[a] = t
# raw scan: RAM image from the snapshot via the disassembler's own extractor
sys.path.insert(0, str(ROOT/"tools"))
import importlib.util
spec = importlib.util.spec_from_file_location("dis", ROOT/"tools/disassemble.py"); dis = importlib.util.module_from_spec(spec); spec.loader.exec_module(dis)
ram = None
for name in ("load_snapshot_ram", "extract_ram", "ram_from_snap", "read_snapshot"):
    if hasattr(dis, name): ram = getattr(dis, name)(str(SNAP)); break
if ram is None:
    print("no snapshot extractor in disassemble.py; attributes:", [n for n in dir(dis) if "snap" in n.lower() or "ram" in n.lower()]); sys.exit(1)
rows2 = {}
starts_set = {a for a, _ in ins}
def w16(a): return struct.unpack(">H", bytes(ram[a:a+2]))[0]
for p in range(0x10a8, 0x1c48c, 2):
    if w16(p) != 8: continue
    for k in (1, 2, 3):
        o = p - 2*k
        w = w16(o)
        hi = w >> 12
        srcm = (w >> 3) & 7
        dstm = (w >> 6) & 7
        hit = None
        if hi in (1, 2, 3) and dstm == 5: hit = "move dst d16"
        elif srcm in (5, 6) and k == 1: hit = "src/ea mode %d" % srcm
        elif srcm == 5 and k in (2, 3) and (hi == 0 or w in (0x4880, 0x48c0, 0x4c80, 0x4cc0) or (w & 0xff00) in (0x0800, 0x0a00, 0x0c00, 0x0400, 0x0600, 0x0200, 0x0000, 0x0a00)): hit = "ea d16 after %d prefix words" % (k-1)
        elif hi in (1, 2, 3) and srcm == 5 and k == 1: hit = "move src d16"
        if hit and o in starts_set:
            rows2[(o, p)] = (w, hit)
            break
out = open(WORK/"off8.txt", "w")
def P(s=""): print(s); out.write(s + "\n")
P(f"listing hits: {len(rows1)}; raw even-address hits: {len(rows2)}")
P("--- raw hits whose address has no listing hit (candidates: data, mid-instruction, or undecoded code)")
for (o, p) in sorted(rows2):
    if o not in rows1: P(f"  op ${o:06x} w={rows2[(o,p)][0]:04x} ext@${p:06x}=8 {rows2[(o,p)][1]}  listing: {dict(ins).get(o)}  routine={routine(o)}")
P("--- listing hits")
for a in sorted(rows1):
    r = routine(a); P(f"  ${a:06x} {rows1[a]:48s} {r[1] if r else '?'} ${r[0]:x}" if r else f"  ${a:06x} {rows1[a]}")
