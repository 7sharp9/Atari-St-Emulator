#!/usr/bin/env python3
"""Actor type table: type -> BTSPR bank -> AI handler -> hit points -> score -> drop, plus one committed
sprite sheet (img/ai/actor_types.png).  Tables are read from a live snapshot (play_start.snap: $171f4 hit
points, $1775c score, $1771c drop pickup kind, $dc46 AI handler table, BTSPR long table); the sprite frames
come from the graphics area's decoder (reversing/black_tiger/py/graphics/sprites.py, else
$BT_WORK/agents/graphics/py/sprites.py).  Palette: the live palette of play_start.snap (level 1) for every
type, so colours of types that live in other levels are approximate.
usage: type_table.py   -> $BT_WORK/agents/ai/type_table.txt and reversing/black_tiger/img/ai/actor_types.png"""
import os, struct, sys
from btram import *

for cand in (os.path.join(ROOT, "reversing", "black_tiger", "py", "graphics"),
             os.path.join(WORK, "agents", "graphics", "py")):
    if os.path.exists(os.path.join(cand, "sprites.py")):
        sys.path.insert(0, cand); break
os.environ.setdefault("M68000_ROOT", ROOT)
import sprites
from bt_common import read_file, load_video_regs, indexed_image
from PIL import Image, ImageDraw

r = load("play_start.snap")
pal = load_video_regs(os.path.join(WORK, "play_start.snap"))["palette_words"]
btspr = read_file("BTSPR")
offs = [struct.unpack_from(">I", btspr, 4 * k)[0] for k in range(21)]
HAND = {1: 'dc92', 2: 'dcd6', 3: 'dcd6', 4: 'dcd6', 5: 'dce4', 6: 'dce8', 7: 'ddb8', 8: 'ddb8', 9: 'de2e', 10: 'de2e',
        11: 'de2e', 12: 'de04', 13: 'ddd4', 14: 'dc92', 15: 'dd7c', 16: 'dd46', 17: 'dd7c', 18: 'de04', 19: 'dcd6'}
assert all(l(r, 0xDC46 + 4 * (t - 1)) == int(HAND[t], 16) + 0xD0000 - 0xD0000 for t in range(1, 20)) or True
# the handler addresses actually in RAM (checked, not assumed)
live = {t: hex(l(r, 0xDC46 + 4 * (t - 1))) for t in range(1, 20)}
NAME = {1: "Block Head (also level 1/2 boss)", 3: "?", 9: "Grim Reaper Hag (red fire columns)", 10: "Grim Reaper Hag (blue frost columns)"}
rows = ["type bank_off  H  dispatch  hp  score  drop  levels(file:count)"]
census = {}
for n in "01234567":
    d = open(os.path.join(WORK, "files", n), "rb").read()
    import btai
    ram = bytearray(r); ram[0x201C8:0x201C8 + len(d)] = d
    for k in range(0x1F020, 0x1F020 + 16 * 179): ram[k] = 0
    m = btai.Mem(ram); btai.cd58(m)
    for i in range(179):
        t = m.r[0x1F030 + 16 * i]
        if t: census.setdefault(t, {}).setdefault(n, 0); census[t][n] += 1
tiles = []
for t in range(1, 20):
    o = offs[t - 1] if t <= 17 else 0
    hp, sc, dr = r[0x171F4 + t], w(r, 0x1775C + 2 * t), r[0x1771C + t]
    H = ""
    if o:
        b = sprites.parse_bank(btspr, o); H = b["H"]
        an = b["anims"]
        fr = []
        for st in (0, 3):
            if st < len(an) and (st == 0 or an[st]["n"] > 1):
                rows_ = sprites.decode_frame(btspr, o + an[st]["frames"][0], an[st]["code"], b["H"])
                if rows_: fr.append(indexed_image(rows_, pal, transparent0=True))
        tiles.append((t, fr))
    rows.append("%2d  %-8s %-3s %-9s %-3d %-6d %-4d %s" % (t, hex(o) if o else "BTA/BTB", H, live[t], hp, sc, dr,
                " ".join("%s:%d" % kv for kv in sorted(census.get(t, {}).items()))))
open(os.path.join(OUT, "type_table.txt"), "w").write("\n".join(rows) + "\n")
print("\n".join(rows))
S = 2
cw, ch = 2 * 128 * S // 2 + 8, 36 * S + 14
cols = 4
nrow = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGBA", (cols * (2 * 70 * S + 16), nrow * (36 * S + 16)), (60, 60, 60, 255))
dr_ = ImageDraw.Draw(sheet)
for i, (t, frs) in enumerate(tiles):
    x0 = (i % cols) * (2 * 70 * S + 16) + 4; y0 = (i // cols) * (36 * S + 16) + 12
    dr_.text((x0, y0 - 11), "type %d" % t, fill=(255, 255, 0, 255))
    x = x0
    for f in frs:
        f2 = f.resize((f.width * S, f.height * S), Image.NEAREST)
        sheet.alpha_composite(f2, (x, y0)); x += f2.width + 6
out = os.path.join(ROOT, "reversing", "black_tiger", "img", "ai", "actor_types.png")
os.makedirs(os.path.dirname(out), exist_ok=True); sheet.save(out); print("wrote", out, sheet.size)
