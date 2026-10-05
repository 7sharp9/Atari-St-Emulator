"""anim.py <addr> [<addr>...]: decode an animation script ($3b1c/$3b3c): entries of (word offset to frame block, word duration|flags);
frame block +2..+5 = bytes 42,43,44(hurt box idx),45(attack box idx), +6 word -> +48. Prints per entry: dur, flags, hurt idx, attack idx.
A negative duration word ends the list (offset then points back to the loop target)."""
import sys,os
root=os.path.abspath(os.path.join(os.path.dirname(__file__),'../../../..'))
rom=open(os.path.join(root,'scratchpad/finalfight/ff_main.bin'),'rb').read()
def w(a): return int.from_bytes(rom[a:a+2],'big')
def sw(a):
    v=w(a); return v-0x10000 if v>=0x8000 else v
def decode(a, maxn=40):
    out=[]; e=a
    for i in range(maxn):
        off=w(e); dur=w(e+2)
        blk=e+off
        b=rom[blk+2:blk+6]
        out.append((i,e,dur,blk,b[0],b[1],b[2],b[3],w(blk+6)))
        if dur&0x8000: break
        e+=4
    return out
if __name__=='__main__':
    for s in sys.argv[1:]:
        a=int(s,16); print('anim %05x:'%a)
        for i,e,dur,blk,b42,b43,b44,b45,x48 in decode(a):
            print('  #%d @%05x dur=%04x blk=%05x b42=%02x b43=%02x hurt=%02x att=%02x w48=%04x'%(i,e,dur,blk,b42,b43,b44,b45,x48))
