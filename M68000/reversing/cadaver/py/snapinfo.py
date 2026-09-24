"""snapinfo.py - compare room state and display-buffer parity across several .snap files in one
line each, for reconciling "does this differ from that other snapshot, and why" questions.

Added in the 46th pass to resolve mechanics.md's shifter-base-flip conflict (cadaver.md Open item
1): printed, per snapshot, the current room record pointer (`164(A5)`), `(A5)+0` (the inactive
display half per §34a), and the live hardware shifter base (`tools/gfxview.py`'s
`load_video_regs`). Reuses gfxview.py's header parsing rather than re-deriving the .snap format -
only RAM-field reads here are new.

Usage: python snapinfo.py <snap> [<snap> ...]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools"))
from gfxview import load_ram, load_video_regs, snapshot_regs  # noqa: E402


def a5_field(ram, base_a5, offset, size=4):
    """Read a big-endian field at (A5)+offset - RAM bytes are the CPU's own big-endian image,
    independent of the little-endian header fields load_ram/snapshot_regs already handle."""
    addr = (base_a5 + offset) & 0xFFFFFF
    fmt = {1: "B", 2: "H", 4: "I"}[size]
    return struct.unpack(">" + fmt, ram[addr:addr + size])[0]


for path in sys.argv[1:]:
    regs, ok = snapshot_regs(path)
    if not ok:
        print(f"{path}: not a snapshot")
        continue
    ram, _ = load_ram(path)
    vid = load_video_regs(path)
    a5 = regs["a5"] & 0xFFFFFF
    room_rec = a5_field(ram, a5, 164)
    inactive_half = a5_field(ram, a5, 0)
    print(f"{path}: PC={regs['pc']:#x} A5={a5:#x} room_rec@164(A5)={room_rec:#x} "
          f"(A5)+0={inactive_half:#x} shifter_base={vid['base']:#x}")
