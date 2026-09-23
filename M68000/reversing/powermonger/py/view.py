"""view.py <frame.json> <out.png> [scale] [x0 y0 x1 y1 crop] -- the game's own screen (ref) as PNG"""
import sys, json, base64
from PIL import Image
PAL = json.load(open('reversing/powermonger/port/assets/palette.json'))['palettes'][0]['rgb']
d = json.load(open(sys.argv[1])); ref = base64.b64decode(d['ref'])
sc = int(sys.argv[3]) if len(sys.argv) > 3 else 3
im = Image.new('RGB', (320, 200)); im.putdata([tuple(PAL[v]) for v in ref])
if len(sys.argv) > 7: im = im.crop(tuple(int(v) for v in sys.argv[4:8]))
im.resize((im.width*sc, im.height*sc), Image.NEAREST).save(sys.argv[2])
