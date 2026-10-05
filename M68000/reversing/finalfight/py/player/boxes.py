"""Decode attack/hurt box descriptors of a character from the ROM. Usage: boxes.py <cody|guy|haggar> [attack|hurt]
box layout (frame.md): 8 bytes hurt: dx dy hw hh (words); attack: 16 bytes: dx dy hw hh, +8 word damage row offset, +10 ?, +11 hard-hit bit7 (byte), +12 byte sound id."""
import sys,os
root=os.path.abspath(os.path.join(os.path.dirname(__file__),'../../../..'))
rom=open(os.path.join(root,'scratchpad/finalfight/ff_main.bin'),'rb').read()
A0s={'guy':0x10b76,'cody':0x12910,'haggar':0x14cfa}  # character index 0 = Guy, 1 = Cody, 2 = Haggar (HUD CODY with +20 = 1, +56 = $12910)
def w(a): return int.from_bytes(rom[a:a+2],'big')
def sw(a):
    v=w(a); return v-0x10000 if v>=0x8000 else v
def attack(ch,i):
    A0=A0s[ch]; a=A0+(i&0x7f)*16+w(A0); 
    return a,[sw(a),sw(a+2),sw(a+4),sw(a+6)],w(a+8),rom[a+10],rom[a+11],rom[a+12],rom[a+13]
def hurt(ch,i):
    A0=A0s[ch]; a=A0+i*8
    return a,[sw(a),sw(a+2),sw(a+4),sw(a+6)]
if __name__=='__main__':
    ch=sys.argv[1]; what=sys.argv[2] if len(sys.argv)>2 else 'attack'
    A0=A0s[ch]; print('A0=%x word(A0)=%x -> %d hurt boxes'%(A0,w(A0),w(A0)//8))
    if what=='attack':
        n=int(sys.argv[3],16) if len(sys.argv)>3 else 0x30
        for i in range(1,n):
            a,b,d,x10,x11,x12,x13=attack(ch,i); print('att %02x @%05x dx,dy,hw,hh=%s dmg_off=%04x b10=%02x b11=%02x b12=%02x b13=%02x'%(i,a,b,d,x10,x11,x12,x13))
    else:
        for i in range(0,w(A0)//8):
            a,b=hurt(ch,i); print('hurt %02x @%05x %s'%(i,a,b))
