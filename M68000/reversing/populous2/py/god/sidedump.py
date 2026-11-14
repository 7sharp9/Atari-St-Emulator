import sys, os
d=os.path.abspath(__file__)
while not os.path.exists(os.path.join(d,'tools','rdis.py')): d=os.path.dirname(d)
sys.path.insert(0,os.path.join(d,'tools'))
from gfxview import load_ram
for snap in sys.argv[1:]:
    ram,_=load_ram(snap)
    w=lambda a:int.from_bytes(ram[a:a+2],'big')
    l=lambda a:int.from_bytes(ram[a:a+4],'big')
    print(snap, 'battle', w(0x473a0), 'tick', l(0x3979a))
    for s,b in ((1,0x470fe),(2,0x47238)):
        print(' side',s,'ctl',w(b+26),'mana',l(b),'76',w(b+76),'104',w(b+104),'106',w(b+106),'148',w(b+148),'150',w(b+150),'36',w(b+36),'28',w(b+28),'plan',[hex(w(b+152+2*i)) for i in range(8)])
