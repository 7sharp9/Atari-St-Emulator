"""(promoted: reversing/captive/py/ai/ratt/keys_from.py; outputs under scratchpad/captive/ratt/) Press keypad keys from a snapshot and save: keys_from.py <snap> <hexkeys,..> <out-tag>"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, OUT
s = StServer(R); s('load', snapshot=snappath(sys.argv[1]))
for k in [int(x, 16) for x in sys.argv[2].split(',')]:
    s('kbd', bytes=[k]); s('step', n=60000); s('kbd', bytes=[k | 0x80]); s('step', n=600000)
w = lambda o: int.from_bytes(s.read(A6 + o, 2), 'big')
print('party', w(26), w(28), w(30), 'tile under', hex(s.read(A6 + 15416, 1)[0]))
p = os.path.join(OUT, sys.argv[3] + '.snap'); s('save', path=p)
subprocess.run(['uv', 'run', 'python', '-I', os.path.join(R, 'tools', 'snap_render.py'), p, p[:-5] + '.png'], cwd=R, check=True, capture_output=True)
s.close()
