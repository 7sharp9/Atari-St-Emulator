"""Annotated live frames of the hazard systems (Track 5, race counter poked to 0 / 5 / 17): boxes from the game's own state
variables (-1868/-1878 oil, -1756/-1764 cones, -1780/-1782 tornado, -1852/-1854 wrench, INIT -1686 arrow signs)."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import struct
from gfxview import load_video_regs
from PIL import ImageDraw
T = 4
def frame(n):
    snap = out('snaps', 'haz_t%d_r%d.snap' % (T, n)); ram = load_snap(snap); regs = load_video_regs(snap)
    idx = planar_to_idx(ram[regs['base']:regs['base'] + 32000]); im = idx_to_img(idx, regs['palette_words']).resize((640, 400), Image.NEAREST)
    d = ImageDraw.Draw(im)
    w = lambda o, k=1: struct.unpack('>%dh' % k, ram[A4 + o:A4 + o + 2 * k])
    lab = []
    for i in range(w(-1858)[0]):
        c, r = w(-1868, 3)[i], w(-1878, 3)[i]; d.rectangle([c*16, r*16, c*16+31, r*16+15], outline=(0, 255, 255)); d.text((c*16, r*16-11), 'oil type %d' % w(-1888, 3)[i], fill=(0, 255, 255))
    for i in range(w(-1766)[0]):
        c, r = w(-1756, 4)[i], w(-1764, 4)[i]; d.rectangle([c*16, r*16, c*16+31, r*16+15], outline=(255, 128, 0)); d.text((c*16, r*16-11), 'cone', fill=(255, 128, 0))
    if w(-1776)[0]:
        x, y = w(-1780)[0], w(-1782)[0]; d.rectangle([x*2-8, y*2-4, x*2+24, y*2+40], outline=(255, 0, 255)); d.text((x*2-8, y*2-16), 'tornado', fill=(255, 0, 255))
    c, r = w(-1852)[0], w(-1854)[0]
    if w(-1850)[0] == 4: d.rectangle([c*16, r*16, c*16+31, r*16+15], outline=(255, 255, 0)); d.text((c*16, r*16-11), 'wrench', fill=(255, 255, 0))
    if w(-1792)[0]:
        arr = struct.unpack('>24H', g_init[-1686])[T*3:T*3+3]
        for o in arr: d.rectangle([(o % 160)*4 - 2, (o // 160)*2 - 2, (o % 160)*4 + 34, (o // 160)*2 + 18], outline=(255, 255, 255)); 
        d.text(((arr[0] % 160)*4 - 30, (arr[0] // 160)*2 - 14), 'flashing sign', fill=(255, 255, 255))
    d.text((4, 4), 'Track %d, race counter %d' % (T + 1, n), fill=(255, 255, 255))
    return im
if __name__ == '__main__':
    import trackrender as TR
    g_init = TR.Gfx().init
    ims = [frame(n) for n in (0, 5, 17)]
    sheet = Image.new('RGB', (640, 400 * 3)); [sheet.paste(im, (0, 400 * i)) for i, im in enumerate(ims)]
    sheet.save(out('png', 'hazards_track5_race0_5_17.png')); print('ok')
