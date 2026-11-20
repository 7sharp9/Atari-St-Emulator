"""hud_match.py: prove which routines draw the HUD numbers by poke-and-render (labelled pokes).

For each trial it pokes the HUD fields of the wave-1 launch pad snapshot (score $2708e, wave $32a50, best $2709a,
lives $32a54, rockets $32a40, next-extra-life threshold $27096 so the HUD redraw runs once), runs the game, saves a
snapshot, reads the live screen, and compares the 1-bit mask (colour index 15) of three number fields with the same
decimal string rendered from the font table $e9fa (10 bytes a glyph: 9 row bytes, MSB left, then the advance width),
(rows 9..15: row 16 of a descender glyph is covered by the HUD bottom border)
placed as $24a92 / $24956 place it (right-aligned in an 8-cell field).
Usage: hud_match.py [snap]   (default $VIRUS_WORK/drive/g_game2.snap).  Output: one line per trial and a total.
"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fcommon import ROOT, OUT as FOUT, G_GAME2, run
sys.path.insert(0, os.path.join(ROOT, "tools"))
import numpy as np
from gfxview import load_ram, load_video_regs

OUT = os.path.join(FOUT, "gate", "hud")
os.makedirs(OUT, exist_ok=True)

def screen_idx(snap):
    ram, _ = load_ram(snap); r = load_video_regs(snap)
    base = r["base"]; img = np.zeros((200, 320), np.uint8)
    for y in range(200):
        for xw in range(0, 320, 16):
            off = base + y * 160 + (xw // 16) * 8
            pl = [int.from_bytes(ram[off + p * 2: off + p * 2 + 2], "big") for p in range(4)]
            for b in range(16):
                img[y, xw + b] = sum(((pl[p] >> (15 - b)) & 1) << p for p in range(4))
    return img, ram

def number_text(v):
    if v < 0: v = -v; pre = "-"
    else: pre = ""
    return "-huge-" if v >= 1000000 else pre + str(v)

def glyph(ram, ch):
    o = 0xe9fa + (ord(ch) - 0x20) * 10
    w = ram[o + 9]; w = w - 256 if w > 127 else w
    return list(ram[o:o + 9]), w

def render(ram, text, x, y):
    m = np.zeros((200, 320), bool)
    for ch in text:
        rows, w = glyph(ram, ch)
        for r, b in enumerate(rows):
            for c in range(8):
                if b & (0x80 >> c) and 0 <= x + c < 320: m[y + r, x + c] = True
        x += w
    return m

def field_x(ram, text, x):             # $24a92: ((x>>3)+7-len)*8 + (x&7)
    return ((x >> 3) + 7 - len(text)) * 8 + (x & 7)

def trial(snap, S, W, B, L, R, tag):
    p = os.path.join(OUT, f"{tag}.snap")
    cmds = [f"ww 32a50 {W:04x}", f"ww 32a54 {L-1:04x}", f"ww 32a40 {R-1:04x}", f"w 2709a {B:08x}",
            f"w 27096 {S:08x}", f"w 2708e {S:08x}", "s 450000", "m 32a54 2", "m 32a40 2", f"snap {p}"]
    out = run(snap, cmds)
    return p, out

def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else G_GAME2
    rng = random.Random(8)
    trials = [(1, 0, 0, 3, 3), (4567, 3, 12345, 5, 6), (999999, 8, 1000000, 2, 1), (10, 0, 99, 9, 9), (100000, 11, 7, 4, 2)]
    trials += [(rng.randrange(1, 200000), rng.randrange(0, 15), rng.randrange(0, 999999), rng.randrange(2, 9), rng.randrange(1, 9)) for _ in range(7)]
    ok = tot = ctrl = 0
    for i, (S, W, B, L, R) in enumerate(trials):
        p, out = trial(snap, S, W, B, L, R, f"t{i:02d}")
        img, ram = screen_idx(p)
        res = []
        for name, val, text, x, y in (("score", S, number_text(S), None, 8), ("wave", W + 1, str(W + 1), 0xcd, 8), ("best", B, number_text(B), 0x106, 8)):
            if name == "score":
                x0 = (14 - len(text)) * 8                  # $249ae..$249bc
            else:
                x0 = field_x(ram, text, x)
            exp = render(ram, text, x0, y)
            lo = {"score": 48, "wave": 232, "best": 264}[name]; hi = {"score": 120, "wave": 264, "best": 320}[name]
            got = (img == 15); a = got[9:16, lo:hi]; b = exp[9:16, lo:hi]
            same = bool((a == b).all()); res.append((name, same, int((a != b).sum())))
            ctext = number_text(val + 1) if name != "score" else number_text(S + 1)       # control: neighbouring value
            cx = (14 - len(ctext)) * 8 if name == "score" else field_x(ram, ctext, x)
            cexp = render(ram, ctext, cx, y)[9:16, lo:hi]
            ctrl += bool((a == cexp).all())
        good = all(r[1] for r in res); ok += good; tot += 1
        lines = [l for l in out.splitlines() if l.startswith("00 ")]
        print(f"trial {i:2d} S={S} wave={W+1} best={B} -> {'MATCH' if good else 'DIFF '} {res} lives/rockets after: {lines[:2]}")
    print(f"{ok}/{tot} trials all three fields match; control (value+1 rendered) matches {ctrl}/{3*tot} fields")
if __name__ == "__main__":
    main()
