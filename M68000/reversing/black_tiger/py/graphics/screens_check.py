"""screens_check.py - intro (BT001 + story text), title, game over/hi-score, ending against the files and strings.
Snapshots: agents/graphics/screens/intro_*.snap (title_screen.snap + fire, bp $ec02/$ec10/$ec6e: natural, no pokes),
agents/systems/go_prompt/go_hi.snap (systems drive_gameover_hiscore.txt, which pokes lives/score/hero: see their doc),
tl/t24 (attract title)."""
import numpy as np
from text import *
from pics import degas


def scr_of(n):
    ram = load_snap(n); regs = load_video_regs(snap_path(n))
    return ram, regs, np.array(screen_indices(ram, regs["base"]), dtype=np.uint8)


def main():
    # 1. intro picture
    ram, regs, scr = scr_of("agents/graphics/screens/intro_pic.snap")
    res, pal, rows = degas("BT001.PI1")
    ref = np.array(rows, dtype=np.uint8)
    print("intro BT001: indices equal %d/64000, palette equal %s" % ((scr == ref).sum(), regs["palette_words"] == pal))
    # 2. flash palettes
    for a in (0x17296, 0x172b6, 0x17256, 0x17276, 0x172d6, 0x172f6):
        print("palette @%x:" % a, " ".join("%03x" % w16(ram, a + 2 * i) for i in range(16)))
    ram, regs, scr = scr_of("agents/graphics/screens/intro_flash.snap")
    print("snapshot at $ec10 (before the first palette swap): palette == BT001 file palette %s" % (regs["palette_words"] == pal))
    # 3. story text
    ram, regs, scr = scr_of("agents/graphics/screens/intro_text_before.snap")
    s = bytes(ram[0x17351:0x17351 + 400]).split(b"\0")[0].decode("latin1")
    lines = s.split("\r")
    print("story text at $17351:", repr(s[:60]))
    ok = 0
    for i, ln in enumerate(l for l in lines if l.strip()):
        mask = string_mask(ram, ln)
        h = locate_text(scr, mask)
        print("  line", repr(ln), h[:1])
        ok += bool(h)
    print("story lines found with exact glyph/background match:", ok)
    print("story screen palette == $17296:", regs["palette_words"] == [w16(ram, 0x17296 + 2 * i) for i in range(16)],
          "== $172b6:", regs["palette_words"] == [w16(ram, 0x172b6 + 2 * i) for i in range(16)])


def locate_text(scr, mask):
    """glyph pixels all one colour (pen) and the other pixels of the box are anything (the picture is behind the text)"""
    H, W = mask.shape
    for y in range(0, 200 - H + 1):
        for x in range(0, 320 - W + 1, 8):
            win = scr[y:y + H, x:x + W]
            on = win[mask == 1]
            if len(on) and (on == on[0]).all() and on[0] == 15 and (win[mask == 0] != 15).all():
                return [(x, y, int(on[0]))]
    return []


def ending():
    from pics import pic_rows
    d = read_file("BT5")
    ref = np.array(pic_rows(d, 0), dtype=np.uint8)
    for tag, addr in (("end_pic", None), ("end_text1", 0x1741c), ("end_text2", 0x174b7), ("end_text3", 0x174f8), ("end_text4", 0x17543)):
        ram, regs, scr = scr_of("agents/graphics/screens/%s.snap" % tag)
        sub = scr[44:44 + 112, 0:96]
        line = "%s: BT5 96x112 at (0,44): %d/%d equal; palette == $172f6: %s" % (
            tag, int((sub == ref).sum()), ref.size, regs["palette_words"] == [w16(ram, 0x172f6 + 2 * i) for i in range(16)])
        if addr:
            s = bytes(ram[addr:addr + 300]).split(b"\0")[0].decode("latin1")
            lines = [l for l in s.split("\r") if l.strip()]
            f = 0
            for ln in lines:
                H = string_mask(ram, ln)
                hh, ww = H.shape
                found = False
                for y in range(0, 200 - hh + 1):
                    for x in range(0, 320 - ww + 1, 8):
                        win = scr[y:y + hh, x:x + ww]
                        on = win[H == 1]
                        if len(on) and (on == on[0]).all() and on[0] == 3 and (win[H == 0] == 0).all():
                            found = True
                            break
                    if found:
                        break
                f += found
            line += "; text lines found (pen 3 on black) %d/%d" % (f, len(lines))
        print(line)


main()
ending()
