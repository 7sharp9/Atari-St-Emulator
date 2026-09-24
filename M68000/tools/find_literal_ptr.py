"""Raw literal-pointer scan: does the given address value appear anywhere in a loaded .snap's RAM
as raw data (4-byte and, if it fits, 2-byte, at any byte alignment), independent of whether any
disassembled instruction's own text names it as a branch/call operand.

find_ram_callers.py only finds direct bsr/jsr/jmp/bcc instructions whose own operand text encodes
the target literally - it is blind to indirect calls set up via a jump/dispatch table, where the
target sits as plain data that later gets loaded into a register and jsr'd through. This scan finds
that data reference instead (the Cadaver spike used this ad hoc, un-promoted, for `$b5a8`/`$67ea` -
mechanics.md's 19th pass, §17a/§17d - and again for `$b1e0`, 48th pass).

Caveat: this only matches an absolute address literal. A jump table built from PC/table-relative
16-bit displacements (like the Cadaver spike's own 59-entry verb dispatch table, mechanics.md §24)
won't contain the plain target address anywhere and needs a different technique (compute the
displacement from a candidate table base and search for that instead).

Usage: python find_literal_ptr.py <snap> <target_hex> [context_bytes]
"""
import sys
import os
import struct

sys.path.insert(0, os.path.dirname(__file__))
from disassemble import ram_from_snap  # noqa: E402

snap_path = sys.argv[1]
target = int(sys.argv[2], 16)
ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 16

ram = ram_from_snap(snap_path)
target4 = struct.pack(">I", target)

print(f"scanning {len(ram)} bytes for 4-byte {target:#010x} ...")
hits4 = []
start = 0
while True:
    i = ram.find(target4, start)
    if i == -1:
        break
    hits4.append(i)
    start = i + 1
print(f"  {len(hits4)} hits (4-byte, any alignment)")
for i in hits4[:40]:
    lo = max(0, i - ctx)
    hi = min(len(ram), i + 4 + ctx)
    print(f"    @{i:#08x} (even={i % 2 == 0}): ...{ram[lo:hi].hex()}...")

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
