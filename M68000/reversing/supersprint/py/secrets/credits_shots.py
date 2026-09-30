import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import *
r = R(sscfg.SNAP_ATTRACT)
r.cmd('s 20000000')
imgs = []
for k in range(8):
    r.cmd('s 700000')
    im, b = grab(r); imgs.append(im)
sheet = Image.new('RGB', (2 * 640, 4 * 400))
for i, im in enumerate(imgs):
    sheet.paste(im.resize((640, 400), Image.NEAREST), ((i % 2) * 640, (i // 2) * 400))
sheet.save(os.path.join(AGENT, 'credits_frames.png'))
r.close()
