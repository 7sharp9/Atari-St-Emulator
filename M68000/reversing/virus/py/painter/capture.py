"""capture.py <snap> <skip_frames> <nframes> <out.json>
Painter gate capture (Virus). From a snapshot, skip <skip_frames> frames first, then for <nframes> frames stop at
$1fa72 (the object walker's entry: camera and object pool before the walk) and $24098 (the painter's entry: the ten
bucket lists as the two walkers and the ship tick left them, plus both pools and the camera) and write one JSON
record per frame.  Output goes only to the path given.  Own stserver process, no other process is touched.
"""
import os, sys, struct, json
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
ROOT = d
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer

RTS = {0x1fb16, 0x1fbba, 0x1fc56, 0x1fc88}   # the four rts of the object walker $1fa72

def pc_of(r):
    p = r['pc']
    return int(p.lstrip('$'), 16) if isinstance(p, str) else p

def main():
    snap, skip, nframes, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    s = StServer(ROOT)
    s('load', snapshot=os.path.join(ROOT, snap) if not os.path.isabs(snap) else snap)
    s('bp_set', addrs=[0x1fa72, 0x24098] + sorted(RTS))
    frames = []; cur = None; last = None; guard = 0; seen = 0
    while len(frames) < nframes and guard < (nframes + skip) * 8:
        guard += 1
        r = s('run', max_steps=3000000)
        if r['reason'] != 'breakpoint':
            print('stopped', r['reason']); break
        pc = pc_of(r)
        if pc == last and r['steps'] < 64:   # same stop again after an interrupt's RTE
            continue
        last = pc
        cam = struct.unpack('>3h', s.read(0x270ce, 6))
        if pc == 0x1fa72:
            n = struct.unpack('>h', s.read(0x32a3c, 2))[0]
            cur = {'cam_obj': cam, 'nobj0': n, 'obj0': s.read(0x302f6, 18 * n).hex(),
                   'tick': struct.unpack('>h', s.read(0x32a44, 2))[0]}
        elif pc in RTS and cur is not None and 'obj_walked' not in cur:
            n = struct.unpack('>h', s.read(0x32a3c, 2))[0]
            cur['obj_walked'] = s.read(0x302f6, 18 * n).hex(); cur['nobj_walked'] = n
        elif pc == 0x24098 and cur is not None and seen < skip:
            seen += 1; cur = None
        elif pc == 0x24098 and cur is not None:
            n = struct.unpack('>h', s.read(0x32a3c, 2))[0]; na = struct.unpack('>h', s.read(0x32a3e, 2))[0]
            ends = struct.unpack('>20L', s.read(0x23caa, 80)); starts = struct.unpack('>20L', s.read(0x23cfa, 80))
            bk = []
            for b in range(10):
                bk.append(s.read(starts[2 * b], ends[2 * b] - starts[2 * b]).hex())
            cur.update({'cam': cam, 'nobj': n, 'obj': s.read(0x302f6, 18 * n).hex(), 'nact': na,
                        'act': s.read(0x31d54, 20 * na).hex(), 'buckets': bk,
                        'ship': struct.unpack('>6h', s.read(0x270b0, 12)),
                        'step': s('regs').get('step') if False else None})
            frames.append(cur); cur = None
    s.close()
    json.dump(frames, open(out, 'w'))
    print('frames', len(frames))

main()
