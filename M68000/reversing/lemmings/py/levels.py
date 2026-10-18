import struct, ice
F='scratchpad/lemmings/files/'
ld,_=ice.depack(open(F+'LEVELDAT','rb').read())
tab=struct.unpack('>180H', ld[0x290fc-0x27522:0x290fc-0x27522+360])
odd=open(F+'ODDTABLE','rb').read()
files={}
def lvl(s):
    """s = slot-1. returns dict"""
    fi=s>>3
    if fi not in files:
        files[fi],ok=ice.depack(open(F+'LEVEL%03d'%fi,'rb').read()); assert ok
    img=files[fi][((s>>1)&3)*2048:((s>>1)&3)*2048+2048]
    w=list(struct.unpack('>12H',img[:24])); name=img[0x7e0:0x800]
    gs,sp=struct.unpack('>HH',img[24+0:28])[0:2] if False else (struct.unpack('>H',img[26:28])[0], struct.unpack('>H',img[28:30])[0])
    xs=struct.unpack('>H',img[24:26])[0]
    if s&1:
        r=odd[(s>>1)*56:(s>>1)*56+56]
        w=list(struct.unpack('>12H',r[:24])); name=r[24:56]
    return dict(s=s,file=fi,idx=(s>>1)&3,odd=s&1,rate=w[0],n=w[1],save=w[2],mins=w[3],skills=w[4:12],xs=xs,gs=gs,sp=sp,name=name.decode('latin1').strip())
if __name__=="__main__":
    ratings=['Fun','Tricky','Taxing','Mayhem']
    used={}
    for n in range(180):
        sl=tab[n]
        if sl==0: continue
        used.setdefault(sl,[]).append(n)
    for n in range(140):
        L=lvl(tab[n]-1)
        print("%3d %-6s %2d slot%3d f%02d.%d %s rate%3d n%3d save%3d t%2d sk%s gs%d sp%d  %s"%(n,ratings[n//30] if n<120 else '??',n%30+1,tab[n],L['file'],L['idx'],'O' if L['odd'] else ' ',L['rate'],L['n'],L['save'],L['mins'],L['skills'],L['gs'],L['sp'],L['name']))
    print("---- two-player (160+)")
    for n in range(160,180):
        L=lvl(tab[n]-1)
        print("%3d slot%3d f%02d.%d %s %s"%(n,tab[n],L['file'],L['idx'],'O' if L['odd'] else ' ',L['name']))
    print("---- unused slots")
    for sl in range(1,201):
        if sl not in used:
            L=lvl(sl-1)
            print("slot%3d f%02d.%d %s rate%3d n%3d save%3d t%2d sk%s gs%d sp%d  %s"%(sl,L['file'],L['idx'],'O' if L['odd'] else ' ',L['rate'],L['n'],L['save'],L['mins'],L['skills'],L['gs'],L['sp'],L['name']))
