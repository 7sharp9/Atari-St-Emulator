"""Verify the four sprite-part emitters of the 68000 ($efc0 plain, $f084 flip when obj+7 == 1, $f150 flip when obj+4 != 1, $f21c flip
when obj+4 == 1) against live list entries logged by lua/emitcheck.lua.
Model (read from the code): part = (xoff.w, yoff.w, code.w, b6, b7);  D4 = -(objX - (camX + 0x100)) & 0x1ff;  D5 likewise with objY and camY;
  w0 = ((yoff + D5) & 0x1ff) | b6 << 8, ^0x2000 if flipped, | 0x1000 if obj+0 bit 4;   w1 = code;
  w2 = ((xoff' + D4) & 0x1ff) | b7 << 9, xoff' = flipped ? -xoff - 16 : xoff;  w3 = 0.
usage: emitcheck.py dumps/e0 dumps/e3 ..."""
import sys, os, collections

def model(em, part, o0, o4, o7, ox, oy, cx, cy):
    xoff = int(part[0:4], 16); yoff = int(part[4:8], 16); code = int(part[8:12], 16); b6 = int(part[12:14], 16); b7 = int(part[14:16], 16)
    d4 = (-(ox - ((cx + 0x100) & 0xffff))) & 0x1ff
    d5 = (-(oy - ((cy + 0x100) & 0xffff))) & 0x1ff
    flip = {1: False, 2: o7 == 1, 3: o4 != 1, 4: o4 == 1}[em]
    w0 = ((yoff + d5) & 0x1ff) | (b6 << 8)
    if flip: w0 ^= 0x2000
    if o0 & 0x10: w0 |= 0x1000
    xo = ((-xoff - 0x10) & 0xffff) if flip else xoff
    w2 = (((xo + d4) & 0x1ff) | (b7 << 9)) & 0xffff
    return w0 & 0xffff, code, w2, 0

tot = collections.Counter(); ok = collections.Counter()
for d in sys.argv[1:]:
    for line in open(os.path.join(d, "emit.txt")):
        p = line.split()
        if len(p) != 15: continue          # an entry cut off by the end of the run
        em = int(p[1]); part = p[3]
        o0, o4, o7 = int(p[4], 16), int(p[5], 16), int(p[6], 16)
        ox, oy, cx, cy = (int(p[i], 16) for i in (7, 8, 9, 10))
        got = tuple(int(x, 16) for x in p[11:15])           # fields: frame em a3 part o0 o4 o7 ox oy cx cy w0 w1 w2 w3
        exp = model(em, part, o0, o4, o7, ox, oy, cx, cy)
        tot[em] += 1
        if got == exp: ok[em] += 1
        elif tot[em] - ok[em] <= 3: print("MISMATCH em%d" % em, line.strip(), "expected %04x %04x %04x %04x" % exp)
for em in sorted(tot): print("emitter %d: %d of %d entries identical to the model" % (em, ok[em], tot[em]))
print("total %d of %d" % (sum(ok.values()), sum(tot.values())))
