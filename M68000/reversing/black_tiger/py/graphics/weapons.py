"""weapons.py - hero-overlay (weapon) sprites embedded in COMMAND.PRG data.

Table at $1cbde (longs, indexed by the overlay record's sprite index) -> per-index array of longs
indexed by the weapon level ($1f00a, 0..4) -> sprite record: word width code, word H, pixel data
(code 1 = 16 px: H rows x 8 bytes interleaved; same piece formats as the actor sprites).
Read by $e3cc..$e43e (index/level lookup) and drawn by $e722..$e75c via $ed4c.
"""
import os
import sys

from bt_common import *  # noqa
from sprites import decode_frame, piece_bytes, PIECES, mirror


def weapon_sprites(ram):
    out = {}
    for t in range(3):
        p = l32(ram, 0x1cbde + 4 * t)
        for lvl in range(5):
            q = l32(ram, p + 4 * lvl)
            code, H = w16(ram, q), w16(ram, q + 2)
            rows = decode_frame(ram, q + 4, code, H)
            out[(t, lvl)] = (q, code, H, rows)
    return out


if __name__ == "__main__":
    ram = load_snap("agents/graphics/snaps/L0a.snap")
    ws = weapon_sprites(ram)
    t = read_file("T0")
    pal = pal_from_bytes(t, 0)
    cell = 20
    img = Image.new("RGBA", (5 * cell, 3 * cell), (40, 0, 40, 255))
    for (ty, lv), (q, code, H, rows) in ws.items():
        print("type %d level %d at $%05x code %d H %d" % (ty, lv, q, code, H))
        img.alpha_composite(indexed_image(rows, pal, True), (lv * cell + 2, ty * cell + 2))
    img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
    img.save(os.path.join(PNG, "spr_weapon_overlays.png"))
