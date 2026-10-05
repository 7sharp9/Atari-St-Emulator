"""Input-gating proof. FF_OUT = the dir the runs wrote to. Needs tmp/drive_frames.bin and tmp/ctl_frames.bin from
FF_TRACE=1 FF_TRACE_HI=2030 runs of ffdrive.lua (variants drive, ctl). Frames 1790..2029 (state after each frame)."""
import numpy as np, os
here = os.environ.get('FF_OUT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'scratchpad', 'finalfight', 'run')
LO = 1790
def load(t): return np.fromfile(f'{here}/tmp/{t}_frames.bin', dtype='>u2').reshape(-1, 0x8000)
D, C = load('drive'), load('ctl')
n = D.shape[0]
def W(a, arr=D): return arr[:, (a - 0xff0000)//2].astype(int)
x, y = W(0xff856e), W(0xff8572)
def changed(a): return np.r_[0, (np.diff(a) != 0).astype(int)]
cx, cy = changed(x), changed(y)
phases = {'RIGHT': (1801, 1860), 'LEFT': (1881, 1920), 'UP': (1941, 1970), 'DOWN': (1991, 2010)}
print('phase  held  x_changed  y_changed  first/last changing frame')
for k, (lo, hi) in phases.items():
    fr = range(lo, hi + 1)
    ch = [f for f in range(lo, hi + 10) if cx[f-LO] or cy[f-LO]]
    print(f'{k:6} {len(fr):4} {sum(cx[f-LO] for f in fr):9} {sum(cy[f-LO] for f in fr):10}  {ch[0] if ch else None}..{ch[-1] if ch else None}')
idle = [f for f in range(LO+1, LO+n) if not any(lo <= f <= hi + 2 for lo, hi in phases.values())]
print('idle frames', len(idle), 'x changed', sum(cx[f-LO] for f in idle), 'y changed', sum(cy[f-LO] for f in idle))
print('x range', x.min(), x.max(), ' y range', y.min(), y.max())
# monotonic within phase
for k, (lo, hi) in phases.items():
    seg = x[lo-LO:hi-LO+3] if k in ('RIGHT', 'LEFT') else y[lo-LO:hi-LO+3]
    df = np.diff(seg)
    print(k, 'steps', sorted(set(df.tolist())), 'monotone', bool((df >= 0).all() or (df <= 0).all()))
# control run: x,y constant over whole window (no press in ctl before 2040)
xc, yc = W(0xff856e, C), W(0xff8572, C)
print('CTL x values', sorted(set(xc.tolist())), 'y values', sorted(set(yc.tolist())))
# first frame where work RAM of drive differs from ctl
eq = [(D[i] == C[i]).all() for i in range(n)]
first = next(i for i, e in enumerate(eq) if not e)
print('drive==ctl work RAM for frames', LO, '..', LO + first - 1, '; first differing frame', LO + first,
      '(press level set at end of frame 1800)')
print('differing words at first differing frame:', [hex(0xff0000 + 2*i) for i in np.where(D[first] != C[first])[0]][:12])
