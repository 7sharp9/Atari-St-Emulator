"""dmg.py: player damage per pool C attack box type, contact damage, and score per pool A type (the tables of the GRUNTS types).
 box damage = byte[ctype] of the table chosen by (dip $80054 & $c) via the pointer table $fcba, times 4 health points (`$fc34`: D1 = byte*4, `sub.b D1,19(A5)`).
 INDEX = the pool C record's own type (record +2, `move.b 2(A6),D0` at $fc80 with A6 = the pool C box), NOT the owner's pool A type; pool C types are < $2c,
 so the 48-byte tables never alias.
 contact damage: $f78e[pool A type] (1 for all grunt types) subtracted by $f700 (no x4), when an enemy body overlaps a player body (+17 bit 2 clear).
 score: $24952 [pool A type*4] = (hit idx, state-5 idx, death idx, sound), idx -> BCD long at $4016+4*(idx-1) added to the attacker's score (`$3fae`)."""
import os
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
ptrs = [l(0xfcba + 4 * i) for i in range(4)]   # index = (dip & $c) / 4 -> dip 0, 4, 8, 12
BOX = {0x24: "35 st 11", 0x0d: "35 st e", 0x0c: "35 st f", 0x00: "39 st b", 0x01: "39 st c", 0x05: "3f st b", 0x04: "3f st d/e/f/10",
       0x25: "40 st b", 0x26: "40 st c", 0x27: "40 st d", 0x28: "40 st e", 0x0f: "44 st b", 0x10: "44 st c", 0x11: "44 st d", 0x12: "44 st e"}
print("pool C box type -> damage in health points (x4 of the byte) per dip&c = 0 / 4 / 8 / 12   [default dip $80054 = $80 -> column 0]")
for ct in sorted(BOX):
    print(f"  ctype {ct:02x} ({BOX[ct]:14s}): " + " / ".join(f"{rom[p + ct] * 4:3d}" for p in ptrs))
print("score table ($24952): type: hit / state5 (thrown, health>4) / death (BCD)")
for t in (0x35, 0x39, 0x3f, 0x40, 0x44):
    idx = rom[0x24952 + 4 * t:0x24952 + 4 * t + 3]
    b = lambda i: rom[0x4016 + 4 * (i - 1):0x4016 + 4 * i].hex().lstrip("0") or "0"
    print(f"  type {t:02x}: {b(idx[0])} / {b(idx[1])} / {b(idx[2])}  (idx {list(idx)}, sound byte {rom[0x24952 + 4 * t + 3]:02x})")
print("contact damage $f78e:", {hex(t): rom[0xf78e + t] for t in (0x35, 0x39, 0x3f, 0x40, 0x44)})
