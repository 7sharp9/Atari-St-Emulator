from PIL import Image
GAMEPAL=[0x000,0x222,0x333,0x444,0x555,0x666,0x310,0x420,0x500,0x530,0x550,0x250,0x140,0x131,0x124,0x136]
def rgb(w): return tuple(((w>>s)&7)*255//7 for s in (8,4,0))
def render(buf, wbytes, rows, pal=GAMEPAL, planes=4, interleaved=True):
    """interleaved ST planar: each 16px group = planes words"""
    w=wbytes*8//planes
    img=Image.new('RGB',(w,rows)); px=img.load(); cols=[rgb(c) for c in pal]
    for y in range(rows):
        for g in range(w//16):
            o=y*wbytes+g*2*planes
            pl=[buf[o+2*k]<<8|buf[o+2*k+1] for k in range(planes)]
            for b in range(16):
                px[g*16+b,y]=cols[sum(((pl[k]>>(15-b))&1)<<k for k in range(planes))]
    return img
