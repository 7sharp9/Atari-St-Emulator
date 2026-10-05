import os
root=os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'../../../..'))
rom=open(os.path.join(root,'scratchpad/finalfight/ff_main.bin'),'rb').read()
def b(a): return rom[a]
def w(a): return int.from_bytes(rom[a:a+2],'big')
def sw(a):
    v=w(a); return v-65536 if v&0x8000 else v
def l(a): return int.from_bytes(rom[a:a+4],'big')
