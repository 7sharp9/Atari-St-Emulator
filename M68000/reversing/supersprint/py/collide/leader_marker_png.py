"""leader_marker_png.py - decode the HUD strip (rows 0..27) of back page [-78] from lead1_c1 (car 1 leads, marker blitted) and lead3_c1 (no marker); indices as grey."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py', 'physics'))
import pl
from PIL import Image
d = os.path.join(pl.sscfg.WORK, 'agents', 'collide')
def strip(snap):
    r = pl.Ram(snap); base = r.gl(-78); im = Image.new('L', (320, 28))
    px = im.load()
    for y in range(28):
        for g in range(20):
            w = [r.u16(base + y * 160 + g * 8 + 2 * k) for k in range(4)]
            for b in range(16):
                v = sum(((w[k] >> (15 - b)) & 1) << k for k in range(4)); px[g * 16 + b, y] = v * 17
    return im
a = strip(os.path.join(d, 'snap', 'lead1_c1.snap')); b = strip(os.path.join(d, 'snap', 'lead3_c1.snap'))
out = Image.new('L', (960, 172), 128)
out.paste(a.resize((960, 84), Image.NEAREST), (0, 0)); out.paste(b.resize((960, 84), Image.NEAREST), (0, 88))
out.save(os.path.join(d, 'png', 'hud_marker_lead1_vs_lead3.png'))
