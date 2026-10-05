# hidediff.py <state> <addr>[:label] ...   : picture with each record hidden vs reference; prints the bbox of the changed pixels; writes out/hd_<state>_<label>.png (reference with the bbox drawn)
import sys,os,subprocess
ROOT=os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'../../../..'))
OUT=os.environ.get('BB_OUT',os.path.join(ROOT,'scratchpad/finalfight/placement/out'))
import numpy as np
from PIL import Image,ImageDraw
here=os.path.dirname(os.path.abspath(__file__))
run=os.environ.get('BB_RUN',os.path.join(ROOT,'scratchpad/finalfight/placement/run'))
def shot(state,name,addrs):
    p=os.path.join(run,'snap',name)
    if os.path.exists(p): os.remove(p)
    env=dict(os.environ,BB_RUN=run)
    subprocess.run(['sh',os.path.join(here,'hide.sh'),state,name,addrs],env=env,capture_output=True)
    return np.array(Image.open(p).convert('RGB')).astype(int)
state=sys.argv[1]
ref=shot(state,'hd_ref_%s.png'%state,'')
img=Image.fromarray(ref.astype('uint8'))
for item in sys.argv[2:]:
    addr,_,label=item.partition(':'); label=label or addr
    a=shot(state,'hd_%s_%s.png'%(state,label),addr)
    d=np.abs(a-ref).sum(axis=2)>0
    ys,xs=np.nonzero(d)
    if len(xs)==0: print(label,addr,'no change'); continue
    print(label,addr,'bbox x %d..%d y %d..%d  (%d px changed)'%(xs.min(),xs.max(),ys.min(),ys.max(),len(xs)))
    im=img.copy(); dr=ImageDraw.Draw(im); dr.rectangle([xs.min()-1,ys.min()-1,xs.max()+1,ys.max()+1],outline=(255,0,0))
    im.save(os.path.join(OUT,'hd_%s_%s.png'%(state,label)))
