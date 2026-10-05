"""Print n longword (code address) entries at an address: ptable.py <addr hex> <n>. Words (-w) with --w."""
import os, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
a, n = int(sys.argv[1], 16), int(sys.argv[2])
for i in range(n): print(f"[{i:x}] ${int.from_bytes(rom[a + 4 * i:a + 4 * i + 4], 'big'):06x}")
