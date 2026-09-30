import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import *
r = R(sscfg.SNAP_ATTRACT)
frames = []
for k in range(28):
    r.cmd('s 1000000')
    img, base = grab(r)
    frames.append(img)
from PIL import Image
cols = 7
sheet = Image.new('RGB', (cols * 160, 4 * 100))
for i, im in enumerate(frames):
    sheet.paste(im.resize((160, 100)), ((i % cols) * 160, (i // cols) * 100))
sheet.save(os.path.join(AGENT, 'attract_tour.png'))
r.close()
