"""Which enemies the Virus 3D view draws, checked in the emulator.  Every behaviour that draws its record jumps to the
tail $215ea, which queues the record for the painter only if it is inside a window around the camera:
    (x - (camx - $680)) & $ffff < $d00   and   (z - (camz - $600)) & $ffff < $c00          (unsigned, so it wraps)
and gives it the depth z - camz + $e00.  This stops at $215ea (D0, D2 = the record's x, z; $270e6 = the window's
corner), $2165c (passed the window) and $216c2 (next record) over the autopilot's wave 0 from demo/S1b.snap and checks
the test record by record, then counts what was in view on each frame ($23aa6 = the HUD, once a frame).
  uv run python reversing/virus/py/scan/view_check.py [frames=1100] [out.json]"""
import collections, json, os, struct, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
os.environ.setdefault('VIRUS_MPC_WORK', os.path.join(d, 'scratchpad', 'virus', 'radar'))
sys.path.insert(0, os.path.join(d, 'reversing', 'virus', 'py', 'mpc'))
import replay as R, shot as S
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1100
s = R._quiet_server(); s('load', snapshot=os.path.join(R.ROOT, 'scratchpad/virus/demo/S1b.snap'))
s('bp_set', addrs=[0x215ea, 0x2165c, 0x216c2, 0x23aa6])
rd = lambda a, n: bytes.fromhex(s('read', addr=a, len=n))
def inwin(x, z, cx, cz): return ((x - (cx - 0x680)) & 0xffff) < 0xd00 and ((z - (cz - 0x600)) & 0xffff) < 0xc00
frames = 0; pend = None; arrive = ok = 0; passed = collections.Counter(); bad = []; last = None
tail_kinds = collections.Counter(); per_frame = []; cur = []; off = collections.Counter(); model_eq = 0; depth = []
try:
    while frames < N:
        r = s('run', max_steps=8000000)
        if r['reason'] != 'breakpoint': print('stopped:', r['reason']); break
        pc = R.hx(r['pc'])
        if pc == last and r['steps'] < 64: continue      # the same stop again after an interrupt's RTE
        last = pc
        if pend is not None and pc in (0x2165c, 0x216c2, 0x215ea):
            got = pc == 0x2165c; arrive += 1; ok += got == pend[0]; passed[(pend[0], got)] += 1
            if got != pend[0] and len(bad) < 5: bad.append(pend)
            if got: cur.append(pend[1]); depth.append(pend[2])
            pend = None
        if pc == 0x215ea:
            g = s('regs'); x, z = R.hx(g['d0']) & 0xffff, R.hx(g['d2']) & 0xffff
            a0, a1, a2 = struct.unpack('>3H', rd(0x270e6, 6)); idx = struct.unpack('>h', rd(0x32a42, 2))[0]
            beh = struct.unpack('>L', rd(0x31d54 + 20 * idx + 16, 4))[0]; tail_kinds[hex(beh)] += 1
            pend = (((x - a0) & 0xffff) < 0xd00 and ((z - a2) & 0xffff) < 0xc00, idx, ((z - a2) & 0xffff) + 0x800,
                    {'x': x, 'z': z, 'a0': a0, 'a2': a2, 'idx': idx, 'frame': frames})
        elif pc == 0x23aa6:
            n = struct.unpack('>h', rd(0x32a3e, 2))[0]; pool = S.unpack_pool(rd(0x31d54, 20 * n))
            cam = struct.unpack('>3h', rd(0x270ce, 6)); ship = struct.unpack('>3h', rd(0x270b0, 6))
            off[(S.s16(cam[0] - ship[0]), S.s16(cam[2] - ship[2]))] += 1
            live = [i for i, a in enumerate(pool) if S.KINDS.get(a[8], ('', ''))[1] not in ('wait', '')]
            model = sorted(i for i in live if inwin(pool[i][0], pool[i][2], cam[0], cam[2]))
            model_eq += model == sorted(cur)
            per_frame.append({'frame': frames, 'live': len(live), 'view': sorted(cur), 'model': model,
                              'kinds': [S.KINDS[pool[i][8]][0] for i in sorted(cur) if i < n and pool[i][8] in S.KINDS]})
            frames += 1; cur = []
finally:
    try: s('shutdown')
    except SystemExit: pass
print('frames', frames)
print('arrivals at $215ea:', arrive, ' window test predicts $2165c or not:', ok, '/', arrive, ' (predicted, reached):', dict(passed))
print('behaviours arriving at $215ea:', dict(tail_kinds))
print('per frame, records queued == live pool records inside the window of the frame-end camera:', model_eq, '/', frames)
fl = [f for f in per_frame if f['live']]
print('frames with a live enemy:', len(fl), ' with one in view:', sum(bool(f['view']) for f in fl))
print('enemy-frames live:', sum(f['live'] for f in fl), ' in view:', sum(len(f['view']) for f in fl))
kc = collections.Counter(k for f in per_frame for k in f['kinds']); print('in-view enemy-frames by kind:', dict(kc))
print('camera minus ship (x, z): frames', off.most_common(5))
if depth: print('depth of queued records: min', min(depth), 'max', max(depth), ' units per pixel', min(depth) / 256, 'to', max(depth) / 256)
for b in bad: print('MISMATCH', b)
if len(sys.argv) > 2: json.dump({'frames': frames, 'arrive': arrive, 'ok': ok, 'per_frame': per_frame, 'depth': depth}, open(sys.argv[2], 'w'))
