"""Damage of pool C hit boxes: byte [(dip&c)/4][box type] of the tables at $fcba (pointer table) times 4 (`$fc34`), the player hit reaction byte `$fdba[box type]`,
and the pool B damage byte `$10122[type]` (no multiplication, `$100b2`). usage: boxdmg.py [box type hex ...]"""
import os, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
l = lambda a: int.from_bytes(rom[a:a + 4], "big")
ptrs = [l(0xfcba + 4 * i) for i in range(4)]
ts = [int(a, 16) for a in sys.argv[1:]] or range(0x30)
print("box  dmg(dip&c = 0,4,8,12) x4 health points   reaction   poolB-damage-byte")
for t in ts:
    print(f"{t:02x}   {[rom[p + t] * 4 for p in ptrs]}   {rom[0xfdba + t]:02x}   {rom[0x10122 + t] if t < 0x58 else '-'}")
