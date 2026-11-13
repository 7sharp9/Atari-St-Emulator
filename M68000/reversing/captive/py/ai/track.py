"""Track creature groups near the party, one sample per 60,000 steps (a main frame in req4.snap;
the natural base's main frame is longer, so a "frame" here is a sample, not a $102a0 call: use sched.py for scheduling).
track.py <snap> <frames> [radius] [keys]  keys: comma list of 'frame:hex' keypad presses made during the run.
Prints, per frame, each group within radius: index, x, y, facing, flags A = bit 3 aware, H = bit 4 hostile, S = bit 5, 6 = bit 6, G = byte 4 bit 7, member 0 word +2 ("w2", hp by guess)."""
import os, sys, struct; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cap import *
s = srv(sys.argv[1]); frames = int(sys.argv[2]); rad = int(sys.argv[3]) if len(sys.argv) > 3 else 8
keys = {}
if len(sys.argv) > 4:
    for kv in sys.argv[4].split(','):
        f, k = kv.split(':'); keys.setdefault(int(f), []).append(int(k, 16))
def groups():
    blob = s.read(A6 + 4532, 0x1000); out = []; a = 0
    while True:
        sz = struct.unpack('>h', blob[a + 2:a + 4])[0]
        if sz < 0: return out
        out.append((len(out), blob[a], blob[a + 1], blob[a + 5], blob[a + 4], blob[a + 8], struct.unpack('>H', blob[a + 10:a + 12])[0], (sz - 8) // 8, blob[a+6]))
        a += sz
prev = {}
for f in range(frames):
    for k in keys.get(f, []):
        s('kbd', bytes=[k]); s('step', n=30000); s('kbd', bytes=[k | 0x80])
    s('step', n=60000 if f not in keys else 30000)
    px, py = w16(s, 26), w16(s, 28)
    line = []
    for g in groups():
        i, x, y, f5, f4, t, hp, n, tm = g
        if abs(x - px) <= rad and abs(y - py) <= rad:
            st = (x, y, f5)
            mark = '*' if prev.get(i) != st else ' '
            prev[i] = st
            line.append(f'{mark}g{i}:t{t:x}x{n}@({x},{y})f{f5 & 3}{"A" if f5 & 8 else "-"}{"H" if f5 & 16 else "-"}{"S" if f5 & 32 else "-"}{"6" if f5 & 64 else "-"}{"G" if f4 & 128 else "-"} w2={hp}')
    print(f'{f:3d} party({px},{py})f{w16(s, 30)} ' + ' '.join(line))
s('save', path=os.environ.get('TRACK_OUT') or os.path.join(OUT, 'track_end.snap'))  # TRACK_OUT: another path, so a run does not replace agents/ai/track_end.snap  # g16_adj.snap is a copy of this from p2.snap, 200 frames; s.close()
