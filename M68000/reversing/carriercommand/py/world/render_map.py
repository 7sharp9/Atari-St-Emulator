# Renders the 64-island archipelago from the fixed data table at $4d41a (22 bytes/island), names from $4d184, supply graph from $22afa.
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import struct,sys
from PIL import Image,ImageDraw,ImageFont
d=ram(WORK / 'c_mv.snap')          # pre-world-creation RAM: data, not generated state
live=ram(ANCHOR)          # c_s30 for adjacency/ownership
t=0x4d184; offs=struct.unpack('>64H',d[t:t+128]); names=[d[t+o:d.index(b'\0',t+o)].decode() for o in offs]
isl=[struct.unpack('>11h',d[0x4d41a+22*k:0x4d41a+22*k+22]) for k in range(64)]
own=live[0x69b40:0x69b80]; typ=[live[0x66ec0+50*k]&3 for k in range(64)]
xs=[i[0] for i in isl]; ys=[i[1] for i in isl]
S=0.062; W=int((max(xs)-min(xs))*S)+260; H=int((max(ys)-min(ys))*S)+200
img=Image.new('RGB',(W,H),(14,40,70)); g=ImageDraw.Draw(img)
def P(k): return (int((xs[k]-min(xs))*S)+130, int((max(ys)-ys[k])*S)+100)
for k in range(64):
    b=0x22afa+32*k; n=struct.unpack('>H',live[b:b+2])[0]
    for j in range(n):
        c,nb=struct.unpack('>HH',live[b+2+4*j:b+6+4*j]); nb&=0x7fff
        if nb>k: g.line([P(k),P(nb)],fill=(60,90,120),width=1)
col={0:(120,200,120),1:(230,90,80),2:(90,160,240)}
font=ImageFont.load_default()
for k in range(64):
    x,y=P(k); w=isl[k][2]*512*S/512*0.5*8/ (1) # footprint w,h (long units/512 -> words) exaggerated x8 below
    ww=max(4,isl[k][2]/1000*1.6); hh=max(4,isl[k][3]/1000*1.6)
    c=(200,200,60) if own[k]==1 else ((220,70,70) if own[k]==2 else (150,150,150))
    g.ellipse([x-ww,y-hh,x+ww,y+hh],fill=(96,130,80),outline=c,width=3)
    g.text((x+ww+2,y-5),f"{k} {names[k]}",fill=(230,230,230),font=font)
g.text((10,10),"Carrier Command: 64 islands (fixed table $4d41a), supply graph ($22afa). Yellow=player start, red=enemy start (c_s30), grey=free",fill=(255,255,255),font=font)
img.save(str(area_dir('world') / 'island_map.png')); print(img.size)
