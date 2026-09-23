"""frames.py <out.png> <hex frame>... : decode $33000 8x11 frames from the export sheet, 8x scale"""
import sys, json
from PIL import Image
PAL = json.load(open('reversing/powermonger/port/assets/palette.json'))['palettes'][0]['rgb']
sh = open('reversing/powermonger/port/assets/sprites/sheet_raw.bin','rb').read()
fs = [int(a,16) for a in sys.argv[2:]]
im = Image.new('RGB', (len(fs)*10, 11), (255,0,255))
for k,f in enumerate(fs):
    for row in range(11):
        o = f*55+row*5; m,p = sh[o], sh[o+1:o+5]
        for x in range(8):
            b = 7-x
            if not (m>>b)&1:
                v = sum(((p[i]>>b)&1)<<i for i in range(4)); im.putpixel((k*10+x,row), tuple(PAL[v]))
im.resize((im.width*8, im.height*8), Image.NEAREST).save(sys.argv[1])
print(len(sh)//55, 'frames in sheet')
