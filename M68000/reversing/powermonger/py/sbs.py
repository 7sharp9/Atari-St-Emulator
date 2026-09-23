"""sbs.py <port.bin> <ref.json> <out.png> x0 y0 x1 y1 [scale]: game | port | diff (red = port drew, game differs)"""
import sys, json, base64
from PIL import Image
PAL = json.load(open('reversing/powermonger/port/assets/palette.json'))['palettes'][0]['rgb']
port = open(sys.argv[1],'rb').read(); ref = base64.b64decode(json.load(open(sys.argv[2]))['ref'])
x0,y0,x1,y1 = map(int, sys.argv[4:8]); sc = int(sys.argv[8]) if len(sys.argv) > 8 else 4
w,h = x1-x0, y1-y0
im = Image.new('RGB', (w*3+8, h), (255,0,255))
for y in range(h):
    for x in range(w):
        i = (y0+y)*320 + x0+x
        g = tuple(PAL[ref[i]]); im.putpixel((x,y), g)
        p = port[i]; im.putpixel((w+4+x,y), tuple(PAL[p]) if p != 255 else (40,0,40))
        im.putpixel((2*w+8+x,y), (255,0,0) if p != 255 and p != ref[i] else tuple(c//3 for c in g))
im.resize((im.width*sc, im.height*sc), Image.NEAREST).save(sys.argv[3])
