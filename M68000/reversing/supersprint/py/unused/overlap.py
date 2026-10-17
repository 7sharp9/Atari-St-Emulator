"""overlap.py: which asset (B-block / sub-asset) each candidate 1 KB block of SUPER.DAT lies in.  Offsets from reversing/supersprint/tracks.md
(B0..B12) and engine/INDEX.txt (B5 sub-assets, B4 tile pack: 10-byte header, 11 maps of 2000 B, banks of 10/18/26/32 B tiles)."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uc import *
B = [('B0 hi-score car', 0x0, 3488), ('B1 ready-screen RLE', 0xda0, 9120), ('B2 wheel', 0x3140, 7190), ('B3 cars', 0x4d56, 32768),
     ('B4 tile pack', 0xcd56, 80000), ('B5 object sprites', 0x205d6, 30000), ('B6', 0x27b06, 3000), ('B7', 0x286be, 3520), ('B8', 0x2947e, 2000),
     ('B9 prize frames', 0x29c4e, 12300), ('B10', 0x2cc5a, 480), ('B11', 0x2ce3a, 7100), ('B12 credits RLE', 0x2e9f6, 8000)]
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
pack = dat[0xcd56:0xcd56 + 80000]
nm, n0, n1, n2, n3 = struct.unpack_from('>5H', pack, 0)
bank_off = []; o = 10 + nm * 2000
for c, st in zip((n0, n1, n2, n3), (10, 18, 26, 32)): bank_off.append((o, st, c)); o += c * st
B5 = [('tornado+trees 3x128', 0, 384), ('barriers 5x576', 0x180, 2880), ('score/oil/wrench/cone labels 22x64', 0xcc0, 1408), ('smoke 44x32', 0x1240, 1408),
      ('posts 12x96', 0x1740, 1152), ('dressing 36x64', 0x1bc0, 2304), ('heli small 8x720', 0x24c0, 5760), ('heli large 8x1040', 0x3b40, 8320),
      ('explosion 26x112', 0x5bc0, 2912), ('HUD captions 6x336', 0x6720, 2016), ('HUD icons 10x48', 0x6f00, 480), ('trees 4x128', 0x70e0, 512), ('tree shadows 4x32', 0x72e0, 128)]
def describe(lo, hi):
    out = []
    for name, off, ln in B:
        a, b = max(lo, off), min(hi, off + ln)
        if a < b:
            s = '%s [+%x..+%x)' % (name, a - off, b - off)
            if name.startswith('B2'):
                s += ' (header 0x96, then 5 stored 1408-B frames: frames %.1f..%.1f)' % ((a - off - 0x96) / 1408, (b - off - 0x96) / 1408)
            if name.startswith('B4'):
                r0, r1 = a - off, b - off
                if r0 < 10 + nm * 2000: s += ' maps %.2f..%.2f' % ((r0 - 10) / 2000, (min(r1, 10 + nm * 2000) - 10) / 2000)
                for bk, (bo, st, c) in enumerate(bank_off):
                    if r1 > bo and r0 < bo + st * c: s += ' bank%d tiles %d..%d' % (bk, max(0, (r0 - bo)) // st, (min(r1, bo + st * c) - bo) // st)
            if name.startswith('B5'):
                for sn, so, sl in B5:
                    if a - off < so + sl and b - off > so: s += ' | %s: %.1f..%.1f' % (sn, (a - off - so) / (sl / (int(sn.split('x')[0].split()[-1]) if 'x' in sn else 1)) if False else (a - off - so), (b - off - so))
            if name.startswith('B9'):
                s += ' (16 frames x 768 B: frames %.2f..%.2f)' % ((a - off) / 768, (b - off) / 768)
            if name.startswith('B3'):
                s += ' (frames %.2f..%.2f of 128; car-row = frame//16)' % ((a - off) / 256, (b - off) / 256)
            out.append(s)
    return out
if __name__ == '__main__':
    for lo in [0x3000, 0xf000, 0x1b000, 0x23000, 0x24000, 0x25000, 0x2b000]:
        print('%06x-%06x:' % (lo, lo + 0x1000)); [print('   ', s) for s in describe(lo, lo + 0x1000)]
