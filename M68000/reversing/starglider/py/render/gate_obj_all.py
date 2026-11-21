"""Gate: $f6a8 for every object type 1..28 (all 28 models) at random poses, from the g_game2 snapshot with POKES (labelled):
view-space centre 404/406/408(A6) in front of the camera (z 150..5000, x/y within +-z), object angles 378/380/382(A6) random, preset D0 = type, D5 random.
    python3 gate_obj_all.py [poses per type]
Compared: the complete memory delta outside the stack (screen, flag arrays, vertex cache, globals) with rref.f6a8.
Expected: `poses n/n poses n/n` and a per-model pixel count (changed screen bytes)."""
import os, sys, random, collections
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import rcommon as R
import rref as F
A6 = F.A6
random.seed(28)
P = int(sys.argv[1]) if len(sys.argv) > 1 else 3
snap = R.SNAP_GAME2
FN = os.environ.get('FN', 'f6a8')   # FN=f938 gates the debris drawer instead
ram = R.load_ram(snap)
OUT = R.WORK + '/render/caps'
cases = []
for t in range(1, 29):
    for k in range(P):
        z = random.randrange(150, 5000); x = random.randrange(-z, z); y = random.randrange(-z // 2, z // 2)
        pokes = [('ww', A6 + 404, x), ('ww', A6 + 406, y), ('ww', A6 + 408, z),
                 ('ww', A6 + 378, random.randrange(4096)), ('ww', A6 + 380, random.randrange(4096)), ('ww', A6 + 382, random.randrange(512)),
                 ('ww', A6 + 384, 0x7777), ('ww', A6 + 610, random.randrange(0, 15))]    # force the matrix rebuild; 610 = debris age (only $f938 reads it)
        cases.append((t, dict(D0=t, D5=random.randrange(1 << 32), A6=A6), pokes))
jobs = [dict(addr=int(FN, 16), presets=p, pokes=pk) for t, p, pk in cases]
res = R.cc_jobs(snap, jobs, OUT, 'goa', steps=3000000)
ok = 0; pix = collections.Counter(); bad = collections.Counter(); loops = 0
for r, (t, pre, pk) in zip(res, cases):
    base = bytearray(ram)
    for kind, a, v in pk: base[a] = (v >> 8) & 255; base[a + 1] = v & 255
    m = F.Mem(base)
    try:
        (F.f6a8(m, pre['D0'], pre['D5']) if FN == 'f6a8' else F.f938(m, pre['D0']))
    except RuntimeError:
        loops += r['outcome'].startswith('THREW'); ok += r['outcome'].startswith('THREW'); continue
    stack = (r['entrySP'] - 512, r['entrySP'] + 16)
    got = {a: n for a, o, n in r['mem'] if not (stack[0] <= a < stack[1])}
    good = got == m.changes()
    ok += good
    pix[t] += sum(1 for a in got if 0x60000 <= a < 0x80000)
    if not good: bad[t] += 1
print(f'poses {ok}/{len(cases)}  (looping inputs matched as THREW: {loops})  failing types: {dict(bad)}')
print('changed screen bytes per type:', dict(sorted(pix.items())))
