import sys; sys.path.insert(0,'.')
from tkcommon import *
from cmp_bg import compare
import numpy as np
t=int(sys.argv[1])
li,pi,eq=compare(t)
ys,xs=np.where(~eq)
print('diff bbox', xs.min(),xs.max(),ys.min(),ys.max())
# row histogram
import collections
rows=collections.Counter(ys//8*8); print(sorted(rows.items()))
cols=collections.Counter(xs//16*16); print(sorted(cols.items()))
from gfxview import load_video_regs
pal=load_video_regs(out('snaps','race_%d.snap'%t))['palette_words']
img=np.zeros((200,320,3),'uint8'); 
P=np.array([st_rgb(w) for w in pal],'uint8')
img[:]=P[pi]; img[~eq]=(255,0,255)
Image.fromarray(img).resize((640,400),Image.NEAREST).save(out('dbg','diff%d.png'%t))
