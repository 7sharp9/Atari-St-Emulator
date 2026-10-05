# hudsheet.py : poke each (state, record) into the HUD enemy-bar ring (hudpoke.lua), crop the HUD name text (x 24..99, y 23..30) and stack them with labels
import subprocess,os,sys
ROOT=os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'../../../..'))
OUT=os.environ.get('BB_OUT',os.path.join(ROOT,'scratchpad/finalfight/placement/out'))
from PIL import Image,ImageDraw
here=os.path.dirname(os.path.abspath(__file__)); run=os.environ.get('BB_RUN',os.path.join(ROOT,'scratchpad/finalfight/placement/run'))
items=[('bb_2500','ffbbe8','a k8 +20=1 TEL.BOOTH?'),('bb_3600','ffbb28','a k5 +20=1 DUSTBIN?'),('bb_4380','ffbca8','a k5 +20=5'),('bb_4380','ffbbe8','a k5 +20=2'),
       ('bb_5570','ffbca8','a k6 BARREL?'),('bb_5570','ffbe28','a k4 FREIGHT?'),('bb_7830','ffbd68','a k7 TIRE?'),('bb_7830','ff9a68','tag4 k0 DAMND?')]
if len(sys.argv)>1: items=[tuple(x.split(',')) for x in sys.argv[1:]]
S=4; rows=[]
for st,rec,label in items:
    name='hp_%s_%s.png'%(st,rec); p=os.path.join(run,'snap',name)
    if os.path.exists(p): os.remove(p)
    subprocess.run(['sh',os.path.join(here,'hudpoke.sh'),st,name,rec],env=dict(os.environ,BB_RUN=run),capture_output=True)
    im=Image.open(p).convert('RGB').crop((24,23,100,31)).resize((76*S,8*S),Image.NEAREST); rows.append((label,im))
sheet=Image.new('RGB',(76*S+260,len(rows)*(8*S+4)),(30,30,30)); d=ImageDraw.Draw(sheet)
for k,(label,im) in enumerate(rows):
    y=k*(8*S+4); sheet.paste(im,(0,y)); d.text((76*S+6,y+8),label,fill=(255,255,255))
sheet.save(os.path.join(OUT,'hud_poke_sheet.png')); print(sheet.size)
