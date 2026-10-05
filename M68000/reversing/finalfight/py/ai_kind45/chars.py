"""chars.py: character records of kinds 4 and 5 (anim/box base +56, data base +92, health by level, defence class, damage rows, attack boxes)."""
import sys
sys.path.insert(0,'.')
from anim import rom,w,sw
def box(base,idx):
    a=base+(idx&0x7f)*16+w(base)
    return a,[sw(a+2*i) for i in range(6)],rom[a+11],rom[a+12]
def show(name,anim,dat,nbox=6,hurt=True):
    print(name,'anim/box base $%x data base $%x defence class(+64)=%02x'%(anim,dat,rom[dat+64]),'max health by level 0,1,2,7,15,31:',[w(dat+2*i) for i in (0,1,2,7,15,31)])
    tab=dat+0x60
    for idx in range(1,nbox+1):
        a,v,b11,b12=box(anim,idx)
        d=v[4]
        print('   atk box %d @%x dx=%d dy=%d hw=%d hh=%d dmgoff=%d b11=%02x snd=%02x dmg(level 0,7,15,31)=%s'%(idx,a,v[0],v[1],v[2],v[3],d,b11,b12,[rom[tab+d+l] for l in (0,7,15,31)]))
if __name__=='__main__':
    names4=['G.ORIBER','BILL BULL','WONG WHO']
    for sub in range(3):
        a=0x3307c+w(0x3307c+2*sub); d=0x33082+w(0x33082+2*sub)
        show('kind4 sub%d %s'%(sub,names4[sub]),a,d,5)
    names5=['HOLLY WOOD','EL GADO']
    for sub in range(2):
        a=0x36e0a+w(0x36e0a+2*sub); d=0x36e0e+w(0x36e0e+2*sub)
        show('kind5 sub%d %s'%(sub,names5[sub]),a,d,6)
