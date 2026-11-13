"""(promoted: reversing/captive/py/ai/ratt/walk_to_note.py; outputs under scratchpad/captive/ratt/) Walk the party (natural keypad input) from base1/outside.snap to the compound's note cell and look at it.
Keys: $68 forward, $67/$69 turn, $6a/$6c strafe. Usage: walk_to_note.py [keys-hex,... (default 68,69,68,68,67)] [out-tag (default t1)]. Saves a snapshot and render after each key group in OUT."""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objs import R, StServer, snappath, A6, OUT
s = StServer(R); s('load', snapshot=snappath('base1/outside.snap'))
w = lambda o: int.from_bytes(s.read(A6 + o, 2), 'big')
def key(k):
    s('kbd', bytes=[k]); s('step', n=60000); s('kbd', bytes=[k | 0x80]); s('step', n=300000)
    print(hex(k), 'pos', w(26), w(28), 'face', w(30), 'ahead', hex(s.read(A6 + 15408, 1)[0]))
keys = sys.argv[1] if len(sys.argv) > 1 else '68,69,68,68,67'   # default: (23,18) -> (21,19) facing S, the note cell ahead
tag = sys.argv[2] if len(sys.argv) > 2 else 't1'
for k in [int(x, 16) for x in keys.split(',')]:
    key(k)
p = os.path.join(OUT, tag + '.snap'); s('save', path=p)
subprocess.run(['uv', 'run', 'python', '-I', os.path.join(R, 'tools', 'snap_render.py'), p, p[:-5] + '.png'], cwd=R, check=True, capture_output=True)
s.close()
