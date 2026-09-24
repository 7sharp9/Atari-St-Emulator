"""Does any word/longword-relative jump table resolve to <target>? Neither find_ram_callers.py
(direct bsr/jsr/jmp text) nor find_literal_ptr.py (target as a raw absolute-address literal) can
see this shape: this game's own dispatch idiom (mechanics.md §23a/§23b - `add.w D0,D0; adda.w
0(An,D0.w),An; jmp (An)`, table base held in an address register) stores each entry as
`target - table_base`, so the target address itself never appears anywhere in the image; only the
small per-entry offset does, at some a-priori-unknown table base.

Approach: collect every literal absolute address any instruction in the whole image names (lea,
jsr, jmp, move #imm, ...) as a candidate table base - a table base is always set up by loading a
plain immediate address into a register, so this covers every real table this game's own code can
construct - then, for each candidate base, check up to `--span` word/long-sized entries starting
there for a value equal to (target - base). Validated by re-finding the already-known `$010000`
verb-dispatch table's entry 18 (LOCK, mechanics.md §23a) before trusting it on a new target.

Usage: python find_jump_table_hit.py <snap> <target_hex> [--span N (default 300)]
"""
import sys
import os
import re
import struct

sys.path.insert(0, os.path.dirname(__file__))
from disassemble import Disassembler, ram_from_snap  # noqa: E402

snap_path = sys.argv[1]
target = int(sys.argv[2], 16)
span = 300
if "--span" in sys.argv:
    span = int(sys.argv[sys.argv.index("--span") + 1])

ram = ram_from_snap(snap_path)
dis = Disassembler(ram, rom_base=0)

lit_re = re.compile(r"\$([0-9a-f]+)\.l")

candidates = set()
addr = 0
end = len(ram) - 8
while addr < end:
    try:
        text, nxt = dis.decode_one(addr)
    except (IndexError, KeyError):
        addr += 2
        continue
    for m in lit_re.finditer(text):
        v = int(m.group(1), 16)
        if 0 < v < len(ram):
            candidates.add(v)
    addr += 2

print(f"{len(candidates)} candidate absolute-long literal table bases found")

hits = []
for base in candidates:
    for i in range(0, span * 2, 2):
        p = base + i
        if p + 4 > len(ram):
            break
        w = struct.unpack_from(">H", ram, p)[0]
        signed_w = w - 0x10000 if w >= 0x8000 else w
        if (base + w) & 0xFFFFFF == target or (base + signed_w) & 0xFFFFFF == target:
            hits.append((base, i // 2, w, "word"))
        lw = struct.unpack_from(">I", ram, p)[0]
        if (base + lw) & 0xFFFFFF == target:
            hits.append((base, i // 4, lw, "long"))

print(f"{len(hits)} candidate table-entry hits")
for base, idx, val, kind in hits[:60]:
    resolved = (base + val) & 0xFFFFFF if kind == "long" or val < 0x8000 else (base + val - 0x10000) & 0xFFFFFF
    print(f"  table_base={base:#08x} entry[{idx}]={val:#x} ({kind}) -> {resolved:#08x}")
