"""Look at the HUD band (rows 0..29) of the live race snapshot: tile-rebuilt background vs live stash vs live draw screen."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
import proof_playfield as PF
from common import *
from PIL import Image
r = PF.r
regs = load_video_regs(sscfg.SNAP_RACE); pal = [st_rgb(w) for w in regs['palette_words']]
scr = bytes(PF.build(0))
stash = bytes(r.b[r.g(-86):r.g(-86) + 32000]); draw = bytes(r.b[r.g(-78):r.g(-78) + 32000]); shown = bytes(r.b[r.g(-82):r.g(-82) + 32000])
imgs = [decode_st_screen(b, pal).crop((0, 0, 320, 32)) for b in (scr, stash, draw, shown)]
diff = Image.new('RGB', (320, 32)); dp = diff.load(); a = imgs[0].load(); b = imgs[1].load()
for y in range(32):
    for x in range(320):
        dp[x, y] = (255, 0, 0) if a[x, y] != b[x, y] else (0, 0, 0)
W = Image.new('RGB', (320 * 3, 32 * 5 * 3))
for i, im in enumerate(imgs + [diff]): W.paste(im.resize((960, 96), Image.NEAREST), (0, i * 96))
W.save(os.path.join(AGENT, 'out', 'hudband_compare.png'))
print('stash==draw rows0..29:', stash[:30*160] == draw[:30*160], 'stash==shown', stash[:30*160] == shown[:30*160])
n = sum(1 for y in range(30) for x in range(320) if a[x, y] != b[x, y]); print('rebuilt vs stash differing px rows0..29', n)
