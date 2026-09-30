"""record_paths.py [mode] [steps] [stride] [out.json]  - sample every car's world position/waypoint/speed through a race.

Resumes data/prerace_k.snap (race-start initialiser, human in slot 1) and steps `steps` (default 12M) in `stride`
(default 3000) increments; after each increment one `m` dump of A4-3920..A4-3670 gives, per car slot,
lap counter, stun, wp index, world pos (x8), speed, cap, heading, target heading, turn accumulator, screen pos.
mode: idle (human never presses), fire (human holds accelerate).  Output data/paths_<mode>.json.
"""
from aiutil import *
import json
mode = sys.argv[1] if len(sys.argv) > 1 else 'idle'
steps = int(sys.argv[2]) if len(sys.argv) > 2 else 12_000_000
stride = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
outp = sys.argv[4] if len(sys.argv) > 4 else os.path.join(DATA, 'paths_%s.json' % mode)
LO = A4 - 3920
r = Repl2(os.path.join(DATA, 'prerace_k.snap'))
if mode == 'fire':
    r.cmd('kbd fe 80')
F = {'lap': -3906, 'ddrone': -3914, 'stun': -3810, 'wp': -3802, 'px': -3738, 'py': -3746, 'spd': -3730, 'cap': -3874,
     'hd': -3706, 'thd': -3714, 'acc': -3866, 'sx': -3690, 'sy': -3698, 'flags': -3826, 'div': -3882, 'chk': -3850, 'wr': -3954}
rows = []
done = 0
while done < steps:
    r.cmd('s %d' % stride)
    done += stride
    b = r.mem(LO, 250)
    row = {'t': done}
    for k, off in F.items():
        row[k] = [dm_s for dm_s in struct.unpack('>4h', b[A4 + off - LO: A4 + off - LO + 8])]
    rows.append(row)
json.dump(rows, open(outp, 'w'))
print('wrote', outp, len(rows), 'samples; final lap', rows[-1]['lap'])
r.close()
