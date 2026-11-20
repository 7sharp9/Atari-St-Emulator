"""capture_screen.py <snap> <skip_frames> <nframes> <out.json>
Draw-order gate capture.  Stops at $24478 (the painter has drawn every tile row and every bucket: the loop's last
instruction before the return) and writes the ten bucket lists, the camera, the draw screen's address ($27062) and the
screen's 32,000 bytes, plus once the dot routines' code ($16fb4..$173b4) and the three pixel-mask tables.
Own stserver process; output only to the path given (gate_painter.sh uses scratchpad/virus/painter/gate/, or $VIRUS_WORK)."""
import os, sys, struct, json
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
ROOT = d
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer

def pc_of(r):
    p = r['pc']; return int(p.lstrip('$'), 16) if isinstance(p, str) else p

def main():
    snap, skip, nframes, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    s = StServer(ROOT); s('load', snapshot=os.path.join(ROOT, snap) if not os.path.isabs(snap) else snap)
    s('bp_set', addrs=[0x24478])
    res = {'code': s.read(0x16fb4, 0x400).hex(), 'tab_16f72': s.read(0x16f72, 32).hex(), 'tab_16f92': s.read(0x16f92, 32).hex(),
           'tab_ce9a': s.read(0xce9a, 32).hex(), 'table_24488': s.read(0x24488, 40).hex(), 'frames': []}
    seen = 0; last = None; guard = 0
    while len(res['frames']) < nframes and guard < (nframes + skip) * 4:
        guard += 1
        r = s('run', max_steps=3000000)
        if r['reason'] != 'breakpoint': print('stopped', r['reason']); break
        if r['steps'] < 64 and last == 1: continue
        last = 1
        if seen < skip: seen += 1; continue
        ends = struct.unpack('>20L', s.read(0x23caa, 80)); starts = struct.unpack('>20L', s.read(0x23cfa, 80))
        scr = struct.unpack('>L', s.read(0x27062, 4))[0]
        res['frames'].append({'cam': struct.unpack('>3h', s.read(0x270ce, 6)), 'scr': scr, 'screen': s.read(scr, 32000).hex(),
            'buckets': [s.read(starts[2 * b], ends[2 * b] - starts[2 * b]).hex() for b in range(10)]})
    s.close(); json.dump(res, open(out, 'w')); print('frames', len(res['frames']))
main()
