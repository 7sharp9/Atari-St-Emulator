"""Raw literal-pointer scan: does the given address value appear anywhere in a loaded .snap's RAM
as raw data (4-byte and, if it fits, 2-byte, at any byte alignment), independent of whether any
disassembled instruction's own text names it as a branch/call operand.

find_ram_callers.py only finds direct bsr/jsr/jmp/bcc instructions whose own operand text encodes
the target literally - it is blind to indirect calls set up via a jump/dispatch table, where the
target sits as plain data that later gets loaded into a register and jsr'd through. This scan finds
that data reference instead (Cadaver's `$b5a8`, `$67ea` and `$b1e0` are worked examples: reversing/cadaver/mechanics.md
§17a/§17d and §48b).

Caveat: this only matches an absolute address literal. A jump table built from PC/table-relative
16-bit displacements (like the Cadaver spike's verb dispatch table, mechanics.md section 9)
won't contain the plain target address anywhere and needs a different technique (compute the
displacement from a candidate table base and search for that instead).

The 4-byte scan matches the low 24 bits with any top byte (the 68000 ignores it, and games use it as a flag):
Midwinter's action tables store a `jsr` entry as `$8000ec8c` (bit 31 = call and redisplay), which an exact
`$0000ec8c` search reports as 0 hits (reversing/midwinter/ai.md section 2, "When it runs"). Each hit prints its top byte.

Usage: python find_literal_ptr.py <snap> <target_hex> [context_bytes] [--max N]   (default: print 40 hits, say how many more)
"""
import sys
import os
import struct

sys.path.insert(0, os.path.dirname(__file__))
from disassemble import ram_from_snap  # noqa: E402

args = sys.argv[1:]
limit = 40
if "--max" in args:
    j = args.index("--max")
    limit = int(args[j + 1])
    del args[j:j + 2]
snap_path = args[0]
target = int(args[1], 16) & 0xFFFFFF
ctx = int(args[2]) if len(args) > 2 else 16

ram = ram_from_snap(snap_path)
target3 = struct.pack(">I", target)[1:]

print(f"scanning {len(ram)} bytes for 4-byte $xx{target:06x} (any top byte) ...")
hits4 = []
start = 1
while True:
    i = ram.find(target3, start)
    if i == -1:
        break
    hits4.append(i - 1)
    start = i + 1
print(f"  {len(hits4)} hits (4-byte, any alignment)")
for i in hits4[:limit]:
    lo = max(0, i - ctx)
    hi = min(len(ram), i + 4 + ctx)
    print(f"    @{i:#08x} (even={i % 2 == 0}, top byte ${ram[i]:02x}): ...{ram[lo:hi].hex()}...")
if len(hits4) > limit:
    print(f"    ... {len(hits4) - limit} more (--max {len(hits4)})")

if target <= 0xFFFF:
    target2 = struct.pack(">H", target)
    print(f"scanning for 2-byte {target:#06x} ...")
    hits2 = []
    start = 0
    while True:
        i = ram.find(target2, start)
        if i == -1:
            break
        hits2.append(i)
        start = i + 1
    print(f"  {len(hits2)} hits (2-byte, any alignment)")
