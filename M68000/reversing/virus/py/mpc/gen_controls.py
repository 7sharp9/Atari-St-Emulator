"""Seeded random control sequences for check 3.  uv run python gen_controls.py   (writes seq_<name>.json)
  mouse1, mouse2: D0 (tilt) a random walk inside the mouse routine's range, D1 (heading) a random walk over the full
          circle, thrust in runs, chosen with the exact model to hold y between about -11000 and -2500.
  fire:   as mouse, tilt up to $7ffe, fire bit on in runs.
  wild:   D0 and D1 piecewise constant anywhere in 0..$ffff (outside what the mouse produces), same altitude hold.
  dive:   mouse-like for 60 ticks, then thrust off: flies into the ground (to see where the model stops).
  lowpass: mouse-like, altitude held low (about 200..500 above the ground) to exercise the object-map test.
"""
import json, os, random, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import exact, replay as R

START = dict(pos=[1604, -6980, 3047], vel=[26, -330, 162], att=[5016, -16383], g=3, fuel=3961)   # arrival 0 of f1.snap

def gen(seed, n=300, tilt_max=0x3000, wild=False, fire=False, dive_at=None, low=False):
    r = random.Random(seed)
    pos, vel, att, fuel = START['pos'], START['vel'], START['att'], START['fuel']
    d0 = 0x1398; d1 = 0xc000; out = []; run = 0; thrust = 0; frun = 0; f = 0; hold = 0
    for k in range(n):
        if wild:
            if hold == 0:
                d0 = r.randrange(0x10000); d1 = r.randrange(0x10000); hold = r.randint(3, 25)
            hold -= 1
        else:
            d0 = min(tilt_max, max(0, d0 + r.randint(-0x300, 0x300)))
            d1 = (d1 + r.randint(-0x500, 0x500)) & 0xffff
        if run == 0:
            run = r.randint(2, 12)
            if low:
                c = exact.clearance([pos[0] + 8 * vel[0], pos[1] + 8 * vel[1], pos[2] + 8 * vel[2]])
                p = 0.95 if c < 0x100 else 0.05 if c > 0x260 else 0.5
            else:
                yp = pos[1] + 20 * vel[1]
                p = 0.9 if yp > -2500 else 0.1 if yp < -11000 else 0.5
            thrust = r.random() < p
        run -= 1
        if dive_at is not None and k >= dive_at:
            thrust = False
        if fire:
            if frun == 0:
                frun = r.randint(1, 8); f = r.random() < 0.3
            frun -= 1
        d2 = (2 if thrust else 0) | (1 if (fire and f) else 0)
        out.append([d0, d1, d2])
        s = exact.step_full(pos, vel, att, d0, d1, d2, START['g'], fuel)
        pos, vel, att, fuel = s['pos'], s['vel'], s['att'], s['fuel']
    return out

def skim(seed, n=600, tilt_max=0x1400, band=0x130, end_dive=None, wild_att=False):
    """Descend, then hold the lowest ship vertex about `band` above the ground with a per-tick rule on vy."""
    r = random.Random(seed)
    pos, vel, att, fuel = START['pos'], START['vel'], START['att'], START['fuel']
    d0 = 0x1398; d1 = 0xc000; out = []
    for k in range(n):
        d0 = min(tilt_max, max(0, d0 + r.randint(-0x300, 0x300)))
        d1 = (d1 + r.randint(-0x500, 0x500)) & 0xffff
        look = [pos[0] + 6 * vel[0], pos[1], pos[2] + 6 * vel[2]]
        c = min(exact.clearance(pos), exact.clearance(look))
        want = max(-60, min(120 if c > 3000 else 40, (c - band) // 8))
        thrust = vel[1] > want
        if end_dive is not None and k >= end_dive:
            thrust = False
        d2 = 2 if thrust else 0
        out.append([d0, d1, d2])
        s = exact.step_full(pos, vel, att, d0, d1, d2, START['g'], fuel)
        pos, vel, att, fuel = s['pos'], s['vel'], s['att'], s['fuel']
    return out

SEQS = {'mouse1': dict(seed=1), 'mouse2': dict(seed=2), 'fire': dict(seed=3, tilt_max=0x7ffe, fire=True),
        'wild': dict(seed=4, wild=True), 'dive': dict(seed=5, dive_at=60), 'lowpass': dict(seed=6, low=True, n=600)}
SKIMS = {'skim1': dict(seed=11), 'skim2': dict(seed=12, band=0xc0), 'skim3': dict(seed=13, band=0x90, tilt_max=0x2800)}
for i in range(12):      # twelve ways into the ground: skim for a while at a seeded tilt, then cut the thrust
    SKIMS[f'crash{i:02d}'] = dict(seed=100 + i, n=400, band=0x100 + 0x40 * (i % 4), tilt_max=0x800 + 0x600 * (i % 6),
                                  end_dive=150 + 17 * i)
if __name__ == '__main__':
    for name, kw in list(SEQS.items()) + list(SKIMS.items()):
        c = skim(**kw) if name in SKIMS else gen(**kw)
        json.dump(c, open(os.path.join(R.WORK, f'seq_{name}.json'), 'w'))
        print(name, len(c), 'ticks; thrust on', sum(1 for x in c if x[2] & 2), 'fire on', sum(1 for x in c if x[2] & 1))
