"""list render records of given byte6 values: recs.py <snap> <b6,b6,...>"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from census import walk
from pm_export import ram_from_snap
from pathlib import Path
r = ram_from_snap(Path(sys.argv[1])); want = {int(x) for x in sys.argv[2].split(',')}
recs,_ = walk(r)
print('cam', int.from_bytes(r[0x4bb3a:0x4bb3c],'big'), int.from_bytes(r[0x4bb3c:0x4bb3e],'big'), 'yaw', hex(int.from_bytes(r[0xff9a:0xff9c],'big')), 'zoom', int.from_bytes(r[0x57ffc:0x57ffe],'big'))
for o,x,y,rec in recs:
    if rec[6] in want: print(f'{rec[6]:3d} ${o:05x} cell({x:2d},{y:3d}) {rec[:34].hex(" ")}')
