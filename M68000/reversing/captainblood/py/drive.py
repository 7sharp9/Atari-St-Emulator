"""drive.py <in.snap> <out.snap> <mx> <my> [settle] [--noclick]
Move the game's pointer (vars $c6ce x, $c6d0 y, words) to (mx,my) with relative packets, click, settle, snapshot, print pointer."""
import sys,subprocess,os,struct
sys.path.insert(0,'tools')
from gfxview import load_ram
def pos(snap):
    ram,_=load_ram(snap); ram=bytes(ram)
    return struct.unpack('>HH',ram[0xc6ce:0xc6d2])
def run(inp,out,mx,my,settle=3000000,click=True,extra=''):
    x,y=pos(inp); lines=[l for l in os.environ.get('PRE','').split(';') if l]
    dx,dy=mx-x,my-y
    while dx or dy:
        sx=max(-100,min(100,dx)); sy=max(-100,min(100,dy))
        lines+= [f'mouse move {sx} {sy}','s 30000']; dx-=sx; dy-=sy
    lines.append('s 100000')
    if click: lines+=['mouse down l','s 40000','mouse up l']
    lines+= [f's {settle}',f'snap {out}']
    env=dict(os.environ,ATARI_NOTRACE='1')
    p=subprocess.run(['dotnet','exec','bin/Debug/net8.0/M68000.dll','resume',inp,'repl'],input='\n'.join(lines)+'\n',capture_output=True,text=True,env=env)
    if not os.path.exists(out): print(p.stderr[-500:]); return None
    return pos(out)
if __name__=='__main__':
    a=sys.argv
    r=run(a[1],a[2],int(a[3]),int(a[4]),int(a[5]) if len(a)>5 and a[5].isdigit() else 3000000,'--noclick' not in a)
    print('pointer now',r)
    subprocess.run(['uv','run','python','tools/snap_render.py',a[2],a[2][:-5]+'.png'],capture_output=True)
