"""Correction 7: vitality 0 is not a death condition. Armour 0, an actor of type 3 poked onto the hero (labelled poke, record $1f670),
3M steps (about 40 ticks, several contact hits). Vitality 1 -> the first hit kills (lives 5 -> 4, vitality reset to 3);
vitality 0 -> nothing happens (`$e0b6: tst.w $1f00e / beq $e138`, no check anywhere else reads $1f00e for death)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import btlib as b
snap = os.path.join(b.WORK, "play_start.snap")
for vit in (3, 2, 1, 0):
    lines = ["w 1f006 00000000", "w 1f00c 0005%04x" % vit, "w 1f670 03000000", "w 1f674 00c002d0", "w 1f678 05000000", "s 3000000", "m 1f00c 4", "m 1f010 1"]
    out = b.repl(snap, lines).splitlines()
    h = [l for l in out if re.fullmatch(r"([0-9a-f]{2} ?)+", l.strip())]
    v = [int(x, 16) for x in h[0].split()]
    print("start vitality %d: lives %d vitality %d alive-flag $%s" % (vit, (v[0] << 8) | v[1], (v[2] << 8) | v[3], h[1].strip()))
