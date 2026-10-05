"""Small drawing helpers shared by the sheet scripts (labels, frame cells, grids) and the owner map of the code regions.
Fonts: Menlo if present (macOS), PIL's bitmap font otherwise."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ffframes as F

BG = (28, 28, 36)
CHECK_A, CHECK_B = (46, 46, 58), (38, 38, 48)
FG = (225, 225, 235)
DIM = (140, 140, 160)


def font(size=11):
    for p in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf", "/Library/Fonts/Courier New.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


FONT = font(11)
FONT_S = font(9)


def paste_rgba(canvas, rgba, x, y):
    """Alpha-composite an (H, W, 4) uint8 array onto a PIL RGB canvas at (x, y) (clipped)."""
    im = Image.fromarray(rgba, "RGBA")
    canvas.paste(im, (x, y), im)


# ------------------------------------------------------------------ handler regions: who owns a piece of code
def handler_labels():
    """Sorted list of (start address, label) for every kind handler the object pools dispatch to.  Sources: the long
    tables read by the pool updaters in the ROM: fighters `$5824` (9), bosses `$5a52` (8), weapons `$598c` (6),
    props `$59ce` (19), items `$5ff0` (1), pool 8 `$5872` (60), debris `$601e`."""
    L = []
    FIGHT = ["BRED/DUG/JAKE/SIMONS", "J/TWO.P", "AXL/SLASH", "ANDORE family", "G.ORIBER/BILL BULL/WONG WHO",
             "HOLLY WOOD/EL GADO", "ROXY/POISON", "kind 7", "kind 8"]
    for i in range(9):
        L.append((F.l(0x5824 + 4 * i), "fighter kind %d %s" % (i, FIGHT[i])))
    BOSS = ["DAMND", "SODOM", "EDI.E", "ROLENTO", "ABIGAIL", "BELGER", "BOSSTEST dummy", "scene object"]
    for i in range(8):
        L.append((F.l(0x5a52 + 4 * i), "boss %d %s" % (i, BOSS[i])))
    for i in range(6):
        L.append((F.l(0x598c + 4 * i), "weapon kind %d" % i))
    PROP = ["DOOR", "DRUMCAN", "CHANDELIER", "BILLBOARD", "FREIGHT", "DUSTBIN", "BARREL", "TIRE", "TEL.BOOTH", "GLASS",
            "DRUMCAN", "GLASS", "GLASS", "GLASS", "GLASS", "GRANADE", "FLAME", "FLAME", "WHEELCHAIR"]
    for i in range(19):
        L.append((F.l(0x59ce + 4 * i), "prop kind %d %s" % (i, PROP[i])))
    L.append((F.l(0x5ff0), "item (pickup) handler"))
    for i in range(60):
        L.append((F.l(0x5872 + 4 * i), "pool 8 kind %d" % i))
    L.append((F.l(0x601e), "debris kind 0"))
    L.append((F.l(0x601e + 4), "debris kind 1"))
    L.sort()
    return L


_HL = None


def owner_of(addr):
    """Label of the greatest handler start <= addr, or None below the first (player/engine code)."""
    global _HL
    if _HL is None:
        _HL = handler_labels()
    best = None
    for a, lab in _HL:
        if a <= addr:
            best = lab
        else:
            break
    return best
