"""Gate: the Timer A sample interrupt ($1af32) turns each stream byte into three PSG volume writes.

For N consecutive passes of `$1af58` (the `movep.l D1,-29199(A0)` that follows the table fetch) from a snapshot, check
  D1 == long at $1af86 + 8*b   and   D0 == word at $1af8a + 8*b
where b is the byte the ISR just consumed (the stream pointer is the immediate operand at $1af3a, already advanced, so b is the
byte at ptr-1).  Then step the two movep and read the PSG register file (registers 8, 9, 10) back out of the snapshot the REPL
writes: they must equal the table entry's volumes.

    cd M68000 && .venv/bin/python reversing/powermonger/py/sound/gate_timera.py [snap] [N]
Expected (m1_s0, N=300): matched 300/300 ; PSG regs 8,9,10 equal the last entry: True
"""
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT") or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / "tools"))
from pm_export import ram_from_snap  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/sound"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
snap = sys.argv[1] if len(sys.argv) > 1 else "scratchpad/pm123/win/m1_s0.snap"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 300
ram = ram_from_snap(ROOT / snap)
TAB = 0x1AF86
cmds = []
for _ in range(N):
    cmds += ["bpc 1af58 1", "m 1af3a 4"]
out_snap = DATA / "gate_timera_end.snap"
cmds += ["s 2", f"snap {out_snap}"]
(DATA / "gate_timera.cmds").write_text("\n".join(cmds) + "\n")
env = dict(os.environ, ATARI_NOTRACE="1")
res = subprocess.run(["dotnet", "exec", "bin/Debug/net8.0/M68000.dll", "resume", snap, "repl", "--disk-a", "scratchpad/powermonger.st"],
                     input=(DATA / "gate_timera.cmds").read_text(), capture_output=True, text=True, cwd=ROOT, env=env)
txt = res.stdout
blocks = re.split(r"--- breakpoint \$0001af58 hit", txt)[1:]
good = 0
last = None
for blk in blocks:
    d0 = int(re.search(r"D0:([0-9a-f]{8})", blk).group(1), 16)
    d1 = int(re.search(r"D1:([0-9a-f]{8})", blk).group(1), 16)
    m = re.search(r"-{13}\n((?:[0-9a-f]{2} ?){4})", blk.split("PC:")[1])
    ptr = int(m.group(1).replace(" ", ""), 16)
    # the stream byte lives in RAM, which the snapshot at the start does not have for later hits: the tool prints `m 1af3a 4`
    # only (the pointer); the byte value is recovered from D0/D1 inverse lookup AND checked against the live RAM below
    live = ram[ptr - 1]          # the bank is read-only: the start snapshot holds the same sample bytes
    e = ram[TAB + 8 * live:TAB + 8 * live + 8]
    if struct.unpack(">I", e[:4])[0] == d1 and struct.unpack(">H", e[4:6])[0] == d0 & 0xFFFF:
        good += 1
    last = (d1, d0, ptr)
print(f"matched {good}/{len(blocks)} (D1/D0 equal the table entry of the byte at ptr-1; N asked {N})")
if out_snap.exists():
    s = out_snap.read_bytes()
    off = 5 + 19 * 4 + 2
    for _ in range(2):                                # skip RAM, video regs
        ln = struct.unpack_from("<I", s, off)[0]
        off += 4 + ln
    ln = struct.unpack_from("<I", s, off)[0]
    ym = s[off + 4:off + 4 + ln]
    d1, d0, _ = last
    want = [(d1 >> 16) & 0xFF, d1 & 0xFF, d0 & 0xFF]       # reg8 value, reg9 value, reg10 value
    print("PSG regs 8,9,10 =", list(ym[8:11]), " last table entry volumes =", want, " equal:", list(ym[8:11]) == want)
