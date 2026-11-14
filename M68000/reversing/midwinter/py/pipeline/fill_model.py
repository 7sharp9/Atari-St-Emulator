"""Pixel model of the polygon filler $1b1bc/$1b0e4 (+ edge scanner) against emulator screens.
usage: fill_model.py f1_build.snap screens.log tables.log"""
import sys,re; sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from mw import R
import polys
r=R(sys.argv[1]); sc=sys.argv[2]; tl=sys.argv[3]
ROW0=51; NR=131
def hexbytes(chunk):
    bs=[]
    for ln in chunk.split('\n'):
        s=ln.strip()
        if s and re.fullmatch(r'([0-9a-f]{2} ?)+',s): bs+=[int(x,16) for x in s.split()]
    return bs
chunks=re.split(r'--- breakpoint',open(sc).read())[1:]
ev=[]
for i in range(0,len(chunks),2):
    a=hexbytes(chunks[i]); b=hexbytes(chunks[i+1])
    # a: 19e70(2) 1a942(2) 1b1b8(2) screen(20960);  b: screen
    ev.append(dict(h=(a[0]<<8)|a[1],col=(a[2]<<8)|a[3],pre=bytes(a[6:]),post=bytes(b[-20960:]) if len(b)>=20960 else None))
print('events',len(ev),'pre/post sizes ok',sum(1 for e in ev if len(e['pre'])==20960 and e['post'] and len(e['post'])==20960))
# tables from tables.log (same run order)
tch=re.split(r'--- breakpoint',open(tl).read())[1:]
tr=[]
for ch in tch:
    bs=hexbytes(ch); 
    tr.append(dict(ymax=(bs[2]<<8)|bs[3],ymin=(bs[4]<<8)|bs[5],left=[(bs[14+2*i]<<8)|bs[15+2*i] for i in range(200)],right=[(bs[414+2*i]<<8)|bs[415+2*i] for i in range(200)]))
T={0:None}
tab280=[r.m[0x1b280+8*i:0x1b280+8*i+8] for i in range(16)]
def pattern(c0,c1):
    a=tab280[c0]; b=tab280[c1]
    w=[]
    for p in range(4):
        wa=(a[2*p]<<8)|a[2*p+1]; wb=(b[2*p]<<8)|b[2*p+1]
        w.append((wa&0x5555)|(wb&0xaaaa))
    return w
def fill(scr,y,xl,xr,pat):
    """16-px groups; inclusive span [xl,xr]; planes words big-endian"""
    base=(y-ROW0)*160
    for x0 in range((xl>>4)<<4, ((xr>>4)<<4)+16, 16):
        lo=max(xl,x0)-x0; hi=min(xr,x0+15)-x0
        mask=0
        for px in range(lo,hi+1): mask|=0x8000>>px
        g=base+(x0>>4)*8
        for p in range(4):
            o=g+2*p; d=(scr[o]<<8)|scr[o+1]
            d=(d&~mask)|(pat[p]&mask)
            scr[o]=d>>8; scr[o+1]=d&255
def tab340(idx): return list(r.m[0x1b340+4*idx:0x1b340+4*idx+4])
res=[]
import json
MT=json.load(open('scratchpad/midwinter/pipeline/model_tables.json'))
terr_seen=set(); e2e=[0,0]
from collections import Counter
ok_rows=0; tot_rows=0; ok_poly=0; ok_ymax=0; polys_n=0; kinds=Counter(); changed_outside=0
for k,(e,t) in enumerate(zip(ev,tr)):
    ymin,ymax=t['ymin'],t['ymax']
    scr=bytearray(e['pre'])
    b=tab340(e['col'])
    pairA=(b[0],b[1]); pairB=(b[2],b[3])
    first,second=(pairB,pairA) if ymin&1 else (pairA,pairB)
    exp=bytearray(scr)
    for y in range(ymin,ymax+1):
        if (y-ymin)%2==0: c0,c1=first
        else: c0,c1=second
        xl,xr=t['left'][y],t['right'][y]
        if xl>xr: continue
        fill(exp,y,xl,xr,pattern(c0,c1))
    same=bytes(exp)==e['post']
    # end-to-end terrain variant: spans of rows ymin..ymax-1 from the edge model, row ymax from the emulator (stale)
    m=MT.get(str(e['h']))
    if m and e['h'] not in terr_seen and m['ymin']==ymin and m['ymax']==ymax:
        terr_seen.add(e['h']); exp2=bytearray(scr)
        for y in range(ymin,ymax+1):
            c0,c1=first if (y-ymin)%2==0 else second
            xl,xr=(m['left'][y],m['right'][y]) if y<ymax else (t['left'][y],t['right'][y])
            if xl>xr: continue
            fill(exp2,y,xl,xr,pattern(c0,c1))
        e2e[0]+=1; e2e[1]+= bytes(exp2)==e['post']
    # rows: which rows differ
    bad=[ROW0+i//160 for i in range(20960) if exp[i]!=e['post'][i]]
    badrows=sorted(set(bad))
    res.append((k,e['h'],e['col'],ymin,ymax,same,badrows[:6]))
n=len(res); print('polygons (terrain+object) compared',n,'screen-exact (rows ymin..ymax, spans taken from emulator tables)',sum(1 for x in res if x[5]))
print([x for x in res if not x[5]][:12]); print('terrain polygons: edge model + fill model reproduce the screen exactly (ymax row spans from the emulator tables):',e2e[1],'/',e2e[0])

def pix(buf,y,x):
    g=(y-ROW0)*160+(x>>4)*8; v=0
    for p in range(4):
        w=(buf[g+2*p]<<8)|buf[g+2*p+1]; v|=((w>>(15-(x&15)))&1)<<p
    return v
if len(sys.argv)>4:
    k=int(sys.argv[4]); e=ev[k]; t=tr[k]
    print('poly',e['h'],'col',e['col'],tab340(e['col']),'ymin',t['ymin'],'ymax',t['ymax'])
    for y in range(t['ymin'],t['ymax']+1):
        xl,xr=t['left'][y],t['right'][y]
        print(y,xl,xr,'pre ',''.join('%x'%pix(e['pre'],y,x) for x in range(xl-2,min(xr+3,320))))
        print('       post',''.join('%x'%pix(e['post'],y,x) for x in range(xl-2,min(xr+3,320))))
