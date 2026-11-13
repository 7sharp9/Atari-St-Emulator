"""Name the file behind every sector an ATARI_TRACE_FDC log reads, grouped into runs.

The game loads with its own FDC code, so ATARI_TRACE_GEMDOS shows nothing after the depacker.
This walks the image's FAT12 directory tree and maps each `FDC read drive=0 track side sector
dma` line to (file, sector of the file), merging consecutive sectors of one file into one run
with the DMA address of its first sector.

usage: uv run python reversing/populous2/py/fdc_files.py <image.st> <fdc.log>
"""
import sys,re,struct
img=open(sys.argv[1],'rb').read(); log=open(sys.argv[2]).read().splitlines()
bps,spc,res,nfat,nroot,tot,_,spf,spt,heads=struct.unpack_from('<HBHBHHBHHH',img,11)
rootsec=res+nfat*spf; datasec=rootsec+(nroot*32+bps-1)//bps
fat=img[res*bps:(res+spf)*bps]
def nxt(c):
    o=c*3//2; v=fat[o]|fat[o+1]<<8; return (v>>4) if c&1 else (v&0xfff)
owner={}
def walk(dirsec,nsec,prefix,chain=None):
    data=b''.join(img[s*bps:(s+1)*bps] for s in (range(dirsec,dirsec+nsec) if chain is None else chain))
    for i in range(0,len(data),32):
        e=data[i:i+32]
        if e[0] in (0,0xe5) or e[11]&8: continue
        name=e[0:8].decode('latin1').strip()+('.'+e[8:11].decode('latin1').strip() if e[8:11].strip() else '')
        if name in ('.','..'): continue
        c=struct.unpack_from('<H',e,26)[0]; secs=[]
        while 2<=c<0xff0:
            for k in range(spc): secs.append(datasec+(c-2)*spc+k)
            c=nxt(c)
        if e[11]&0x10: walk(None,None,prefix+name+'\\',secs)
        else:
            for k,s in enumerate(secs): owner[s]=(prefix+name,k)
    return
walk(rootsec,(nroot*32)//bps,'')
for s in range(rootsec): owner[s]=('<boot/FAT>',s)
for s in range(rootsec,datasec): owner[s]=('<root dir>',s-rootsec)
runs=[]
for ln in log:
    m=re.match(r'FDC read\s+drive=0 track=(\d+) side=(\d+) sector=(\d+) dma=\$([0-9a-f]+) -> (\w+)',ln)
    if not m: continue
    t,sd,sc,dma,res_=int(m[1]),int(m[2]),int(m[3]),int(m[4],16),m[5]
    lsec=(t*heads+sd)*spt+sc-1
    f,k=owner.get(lsec,('?',lsec))
    if runs and runs[-1][0]==f and k==runs[-1][2]+1: runs[-1][2]=k; runs[-1][4]+=1
    else: runs.append([f,dma,k,dma,1])
for f,dma,k,_,n in runs: print(f'{f:22s} first-sector-dma=${dma:06x} sectors={n} (to file sector {k})')
