"""Dump (1) the sound-event table at $1290c (14-byte entries, 59 used from $1291a) and (2) the five 16-colour palettes at $1a2d8..$1a417
as a swatch PNG (STe 4-bit nibbles: $0RGB, `_show_a_` $1a82a rotates each nibble into the hardware bit order).

    cd M68000 && .venv/bin/python reversing/powermonger/py/sound/events_pal.py [snap]
Writes events.txt and palettes.png next to this script."""
import os
import struct
import sys
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT") or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / "tools"))
from pm_export import ram_from_snap  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = ROOT / "scratchpad/pm140/agents/sound"      # outputs go to the gitignored scratchpad, not next to the script
DATA.mkdir(parents=True, exist_ok=True)
snap = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "scratchpad/pm123/win/m1_s0.snap"
ram = ram_from_snap(snap)
w = lambda a: struct.unpack_from(">H", ram, a)[0]
l = lambda a: struct.unpack_from(">I", ram, a)[0]
rows = ["idx addr    w0(pending) l2(cooldown) w6(id) w8(chan) w10(prio) w12(flags)"]
for k in range(60):
    a = 0x1290C + 14 * k
    rows.append(f"{k:3d} ${a:05x} {w(a):5d} {l(a+2):6d} {w(a+6):5d} {w(a+8):04x} {w(a+10):5d} {w(a+12):04x}")
(DATA / "events.txt").write_text("\n".join(rows) + "\n")
names = ["work_pa", "zero_pa", "game_pa", "con_pal", "lost_pa"]
img = Image.new("RGB", (16 * 24, 5 * 24), (40, 40, 40))
for r, a in enumerate((0x1A2D8, 0x1A318, 0x1A358, 0x1A398, 0x1A3D8)):
    for c in range(16):
        v = w(a + 2 * c)
        rgb = tuple(((v >> s) & 15) * 17 for s in (8, 4, 0))
        for y in range(r * 24, r * 24 + 24):
            for x in range(c * 24, c * 24 + 24):
                img.putpixel((x, y), rgb)
img.save(DATA / "palettes.png")
print("wrote events.txt, palettes.png; palette rows:", names)
