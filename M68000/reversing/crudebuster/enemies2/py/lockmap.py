"""Camera cell maps of the six levels (pointer table $8908, one word per 256x256 block, row = (y>>8)-1, column = (x>>8)-1, 16 words per row)
and what each word means (`$8876`/`$8a88`/`$8ade`, read):
  low nibble = scroll directions locked: bit0 up, bit1 right, bit2 down, bit3 left (never requested)
  bit 15 ($8000) = camera frozen in this block (final block of the level), bit 13 ($2000) = frozen while $80400 bit 5 (boss flag) is set,
  bit 14 ($4000) = forced scroll: every direction whose lock bit is clear scrolls 1 pixel per frame regardless of the players.
usage: lockmap.py"""
import os
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def w(a): return int.from_bytes(rom[a:a+2], "big")
def l(a): return int.from_bytes(rom[a:a+4], "big")
ptrs = [l(0x8908 + 4 * i) for i in range(6)]
rows = [1, 1, 1, 1, 2, 7]
names = {0x0d: "right", 0x0b: "right+down", 0x0c: "up+right", 0x0f: "none"}
for lv, p in enumerate(ptrs):
    width = {0: 8, 1: 8, 2: 10, 3: 10}.get(lv, 16)
    print(f"level {lv}: cell map ${p:06x}, {rows[lv]} row(s)")
    for r in range(rows[lv]):
        for c in range(width):
            v = w(p + 32 * r + 2 * c) if lv >= 4 else w(p + 2 * c)
            if lv < 4 and r: break
            tag = []
            if v & 0x8000: tag.append("FROZEN (end block)")
            if v & 0x2000: tag.append("frozen while boss flag $80400 bit5")
            if v & 0x4000: tag.append("forced scroll")
            free = [n for b, n in ((0, "up"), (1, "right"), (2, "down")) if not v & (1 << b)]
            print(f"  block x=${(c+1)<<8:03x} y=${(r+1)<<8:03x} (row {r+1}, col {c+1}): ${v:04x}  free: {','.join(free) or '-':14s} {'; '.join(tag)}")
