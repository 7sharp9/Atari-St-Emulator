"""Whole-RAM scan for every decoded instruction whose operand text names a given (A5)+N (or any
other) displacement/field string, to find its writer(s) (or all references) directly instead of
tracing call chains by hand. Mirrors the Cadaver spike's 16th-pass method for 2455(A5) and the
19th pass's for 2518(A5) - see M68000/reversing/cadaver/mechanics.md.

Game-agnostic - takes any .snap and any operand substring (e.g. "2518(A5)", "1162(A5)").

Usage: python find_field_writers.py <snap> "<field text>"
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from disassemble import Disassembler, ram_from_snap  # noqa: E402

snap_path = sys.argv[1]
field = sys.argv[2]

ram = ram_from_snap(snap_path)
dis = Disassembler(ram, rom_base=0)

addr = 0
end = len(ram) - 8
hits = []
while addr < end:
    try:
        text, nxt = dis.decode_one(addr)
    except (IndexError, KeyError):
        addr += 2
        continue
    if field in text and "???" not in text:
        hits.append((addr, text))
    addr += 2

print(f"=== instructions referencing {field} ({len(hits)} hits) ===")
for a, text in hits:
    print(f"  ${a:06x}: {text}")
