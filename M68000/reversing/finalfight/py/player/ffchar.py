"""Shared ROM readers for the player-side gates. Character index (+20 of a player record): 0 = Guy, 1 = Cody, 2 = Haggar."""
import os
root=os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__),'../../../..'))
rom=open(os.path.join(root,'scratchpad/finalfight/ff_main.bin'),'rb').read()
def w(a): return int.from_bytes(rom[a:a+2],'big')
def sw(a):
    v=w(a); return v-0x10000 if v>=0x8000 else v
def l(a): return int.from_bytes(rom[a:a+4],'big')
NAMES={0:'guy',1:'cody',2:'haggar'}
# $a124: per character {+92 data pointer, +56 box/animation base}: long pairs at $a124 + 8*idx (92 first, 56 second)
def data_ptr(ch): return l(0xa124+8*ch)
def box_base(ch): return l(0xa124+8*ch+4)
def damage_row_value(ch,off,rank=4):
    """byte[92 + off] with 92 = data + rank + $60 (the +$60 and the rank are added by $a2d2)."""
    return rom[data_ptr(ch)+rank+0x60+off]
def attack_box(ch,idx):
    A0=box_base(ch); a=A0+(idx&0x7f)*16+w(A0)
    return dict(addr=a,dx=sw(a),dy=sw(a+2),hw=sw(a+4),hh=sw(a+6),off=w(a+8),hit=rom[a+11]&0x7f,hard=bool(rom[a+11]&0x80),sound=w(a+12))
# award per hit ($7aa8): word[$7ac6 + word[$7ac6+2*ch] + 2*(off>>5)]
AMT={0:0,1:10,2:50,3:100,4:10000,5:5000,6:3000,7:1000,8:1,9:20,10:30,11:200,12:250,13:300,14:350,15:400,16:500,17:600,18:800,19:1200,20:1400,21:1500,22:1600,23:2000,24:2500,25:15000,26:20000,27:30000,28:50000,29:4000,30:40000,31:100000,32:42910,33:700}
def hit_award(ch,off):
    base=0x7ac6+w(0x7ac6+2*ch)
    code=w(base+2*(off>>5))
    return code, AMT.get(code&0x7f)
# $db6e grapple strike damage: word[$db6e + 8*ch + step] step=0,2,4,6
def strike_damage(ch,step): return w(0xdb6e+8*ch+step)
# combo limit $be92 (stage != 6)
def combo_limit(ch): return w(0xbe92+2*ch)
# walk accumulator threshold $c0c4 (long per char)
def walk_threshold(ch): return l(0xc0c4+4*ch)
# horizontal jump speed $ac76: (80, 82) words per char
def jump_speed(ch): return w(0xac76+4*ch), w(0xac78+4*ch)
if __name__=='__main__':
    for ch in (0,1,2):
        print(NAMES[ch],'data %06x boxbase %06x'%(data_ptr(ch),box_base(ch)),'combo limit',combo_limit(ch),'walk thr %06x'%walk_threshold(ch),'jump vx %04x/%04x'%jump_speed(ch),'strikes',[strike_damage(ch,s) for s in (0,2,4,6)])

# $3f7a: hp of a thrown fighter after it lands. table $3fd8: words (kill threshold, halve threshold, flat) at +0 for thrower index 0 (Guy), +6 for the others
def thrown_hp(hp, thrower):
    a = 0x3fd8 + (0 if thrower == 0 else 6)
    t1, t2, flat = w(a), w(a + 2), w(a + 4)
    d = hp - t1
    if d <= 0: return -1
    d -= t2
    if d <= 0: return hp >> 1
    return hp - flat
