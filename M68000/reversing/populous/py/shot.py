# shot.py <snap> <out.png> [screenbase_hex]  - regs via one REPL call, RAM straight from the snapshot
import sys,subprocess,struct,os,re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg import DLL
from PIL import Image
snap,out=sys.argv[1],sys.argv[2]
r=subprocess.run(['dotnet','exec',DLL,'resume',snap,'repl'],input='m ffff8201 1\nm ffff8203 1\nm ffff8240 32\nm ffff8260 1\nq\n',capture_output=True,text=True,env=dict(os.environ,ATARI_NOTRACE='1'))
lines=[l for l in r.stdout.splitlines() if re.match(r'^[0-9a-f]{2}( |$)',l)]
base=int(lines[0].strip()+lines[1].strip()+'00',16)
if len(sys.argv)>3: base=int(sys.argv[3],16)
pal=bytes.fromhex(lines[2].replace(' ',''))
s=open(snap,'rb').read(); off=5+19*4+2; ln=struct.unpack_from('<I',s,off)[0]; ram=s[off+4:off+4+ln]
cols=[]
for i in range(16):
  w=pal[2*i]<<8|pal[2*i+1]
  cols.append(tuple(((w>>sh)&7)*255//7 for sh in (8,4,0)))
img=Image.new('RGB',(320,200))
px=img.load()
for y in range(200):
  for x in range(0,320,16):
    o=base+y*160+(x//16)*8
    pl=[ram[o+2*k]<<8|ram[o+2*k+1] for k in range(4)]
    for b in range(16):
      c=sum(((pl[k]>>(15-b))&1)<<k for k in range(4)); px[x+b,y]=cols[c]
img.resize((640,400),Image.NEAREST).save(out); print(out,'base=%x'%base)
