#!/usr/bin/env python3
"""anim.py <boxbase hex> <hdr hex>... : decode animation lists of a record whose 56(A6) = boxbase (as $3b1c/$3b3c walk them).
An animation header is a list of 4-byte entries (frame offset word relative to the entry, timer word; bit 15 of the timer = loop back by the offset). A frame record is
w0, b2, b3 (stored at 42/43), hurt box index b4 (44), attack box index b5 (45), w6 (48). Box entry (16 bytes) = boxbase + word(boxbase) + 16*(idx & 0x7f) for attack,
boxbase + word(boxbase)... see frame.md: hurt = boxbase + 8*idx (A0 = 56(A6)); attack = boxbase + 16*(idx&0x7f) + word(boxbase); fields dx, dy, hw, hh (words),
+8 damage row offset (word), +11 reaction byte (bit 7 hard), +12 sound id."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def w(a): return int.from_bytes(rom[a:a+2], 'big')
def sw(a):
    v = w(a); return v - 65536 if v >= 32768 else v
def anim(hdr):
    out = []; a = hdr
    for _ in range(64):
        off = sw(a); tm = w(a + 2)
        rec = a + off
        out.append((a, rec, tm))
        if tm & 0x8000: break
        a += 4
    return out
def atkbox(base, idx):
    p = base + (idx & 0x7f) * 16 + w(base)
    return p, [sw(p), sw(p + 2), w(p + 4), w(p + 6), w(p + 8), rom[p + 10], rom[p + 11], rom[p + 12]]
def hurtbox(base, idx):
    p = base + idx * 8
    return p, [sw(p), sw(p + 2), w(p + 4), w(p + 6)]
if __name__ == '__main__':
    base = int(sys.argv[1], 16)
    for h in sys.argv[2:]:
        hdr = int(h, 16)
        print('anim %x' % hdr)
        for a, rec, tm in anim(hdr):
            if tm & 0x8000:
                print('  entry %x: LOOP back to %x' % (a, rec)); continue
            b2, b3, hurt, atk, w6 = rom[rec + 2], rom[rec + 3], rom[rec + 4], rom[rec + 5], w(rec + 6)
            print('  entry %x rec %x w0=%04x timer=%d/%02x b2=%02x b3=%02x hurt=%d atk=%d w6=%04x' % (a, rec, w(rec), tm >> 8, tm & 0xff, b2, b3, hurt, atk, w6))
            if atk:
                p, bx = atkbox(base, atk); print('       attack box %x dx,dy,hw,hh,dmgrow,b10,b11,snd = %s' % (p, bx))
            if hurt:
                p, bx = hurtbox(base, hurt); print('       hurt box %x = %s' % (p, bx))
