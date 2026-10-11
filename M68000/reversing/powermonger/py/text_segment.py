"""Print PowerMonger's GEMDOS header (text/data/bss lengths) from the unpacked DATA/SPRITE40.DAT and the
runtime text range (load offset from a RAM snapshot, via py/s40_symbols.py).  uv run python <this> [disk] [snap]"""
import os, struct, sys
from pathlib import Path
here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / "tools" / "rdis.py").exists())
sys.path.insert(0, str(ROOT / "reversing/powermonger/py"))
import s40_symbols as S
img = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "scratchpad/powermonger.st")
snap = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "scratchpad/pm123/win/m1_ready.snap")
prg = S.unpack(S.read_fat12_file(img, 'DATA/SPRITE40.DAT'))
magic, tl, dl, bl, sl = struct.unpack('>HIIII', prg[:18])
ram = S.ram_from_snap(snap)
delta, n, tot = S.load_offset(prg[28:28 + tl], ram)
print(f"tlen ${tl:x} dlen ${dl:x} blen ${bl:x} slen ${sl:x}; load offset ${delta:x} ({n}/{tot} windows)")
print(f"runtime text ${delta:x}..${delta+tl:x}, data ..${delta+tl+dl:x}, bss ..${delta+tl+dl+bl:x}")
