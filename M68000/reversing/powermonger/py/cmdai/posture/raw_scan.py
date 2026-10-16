"""raw_scan.py <snap> [lo hi]: decode at EVERY even address of the text segment (not a linear listing, so code
behind a misdecoded data run is not missed) and print each instruction whose destination operand is a posture
word in either frame: 136(Ax) (side-record frame) or 60(Ax) (group-offset frame), indexed or not; also any
instruction naming an absolute address in a group posture block. Prints the bytes at the posture-indexed tables."""
import os, re, sys
from pathlib import Path
here = Path(__file__).resolve()
root = next(p for p in here.parents if (p / "tools/rdis.py").exists())
sys.path.insert(0, str(root / "tools"))
from disassemble import Disassembler, ram_from_snap
snap = sys.argv[1]
lo, hi = (int(sys.argv[2], 16), int(sys.argv[3], 16)) if len(sys.argv) > 3 else (0x10a6, 0x1c48a)
ram = ram_from_snap(snap)
dis = Disassembler(ram, rom_base=0)
dst = re.compile(r",(-?)(136|60)\(A[0-7](,[DA][0-7][^)]*)?\)\s*$")
any_ = re.compile(r"(?<![0-9$-])(136|60)\(A[0-7]")
for a in range(lo, hi, 2):
    try:
        text, nxt = dis.decode_one(a)
    except Exception:
        continue
    op = text.split()[0] if text.split() else ""
    if dst.search(text) or (any_.search(text) and op.split(".")[0] in ("clr", "neg", "not", "addq", "subq", "tas", "st", "sf", "movem")):
        print(f"${a:06x}: {text}")
