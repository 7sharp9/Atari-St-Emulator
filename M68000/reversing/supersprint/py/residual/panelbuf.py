"""Render the pristine HUD-panel buffer -4940(A4) (0x6e0 B = 11 rows x 160 B = screen rows 7..17) and compare with the live stash rows 7..17."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
from common import *
from PIL import Image
snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
r = Ram(snap); regs = load_video_regs(snap); pal = [st_rgb(w) for w in regs['palette_words']]
bg = bytes(r.b[r.g(-4940):r.g(-4940) + 0x6e0]); st = bytes(r.b[r.g(-86):r.g(-86) + 32000])
print('buf ptr %x stash ptr %x draw %x shown %x' % (r.g(-4940), r.g(-86), r.g(-78), r.g(-82)))
full = bytearray(32000); full[0x460:0x460 + 0x6e0] = bg
a = decode_st_screen(bytes(full), pal).crop((0, 7, 320, 18)); b = decode_st_screen(st, pal).crop((0, 7, 320, 18))
W = Image.new('RGB', (960, 66 + 6)); W.paste(a.resize((960, 33), Image.NEAREST), (0, 0)); W.paste(b.resize((960, 33), Image.NEAREST), (0, 39))
W.save(os.path.join(AGENT, 'out', 'panelbuf_vs_stash.png'))
pa, pb = a.load(), b.load()
print('rows 7..17 pixels equal between the -4940 buffer and the live stash: %d / 3520' % sum(pa[x, y] == pb[x, y] for y in range(11) for x in range(320)))
