"""Whole-RAM BSR/Bcc/JSR/JMP caller scan against a loaded .snap, since disassemble.py --callers
only scans the TOS ROM (abs-long JSR/JMP only) and can't see references inside a loaded game
image at all. Decodes every even address in the snapshot's RAM (a program image, not a ROM -
game code isn't self-describing about where routines start, so this necessarily also decodes
data as if it were code; a real hit is still a real hit, false ones read as garbage in context)
and keeps any instruction whose resolved branch/call target matches one of the given addresses.

Game-agnostic - built for the Cadaver reversing spike (18th/19th passes; see
M68000/reversing/cadaver/mechanics.md) but takes any .snap.

Usage: python find_ram_callers.py <snap> <target_hex> [<target_hex> ...]
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(__file__))
from disassemble import Disassembler, ram_from_snap  # noqa: E402

snap_path = sys.argv[1]
targets = {int(t, 16) for t in sys.argv[2:]}

ram = ram_from_snap(snap_path)
dis = Disassembler(ram, rom_base=0)

# Matches the trailing target of "bsr $xxxx", "bra $xxxx", "jsr $xxxx.l", "jmp $xxxx.w", etc. -
# strips the optional .l/.w size suffix disassemble.py's abs-long/abs-word EA text appends.
target_re = re.compile(r"\$([0-9a-f]+)(?:\.[lw])?$")

hits = {t: [] for t in targets}
addr = 0
end = len(ram) - 8
while addr < end:
    try:
        text, nxt = dis.decode_one(addr)
    except (IndexError, KeyError):
        addr += 2
        continue
    if text.startswith(("bsr", "jsr", "jmp", "b")) and "$" in text:
        m = target_re.search(text.split(" == ")[0])
        if m:
            t = int(m.group(1), 16)
            if t in targets:
                hits[t].append((addr, text))
    addr += 2

for t in targets:
    print(f"=== callers of ${t:x} ({len(hits[t])} hits) ===")
    for a, text in hits[t]:
        print(f"  ${a:06x}: {text}")
