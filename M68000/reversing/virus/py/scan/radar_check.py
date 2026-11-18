"""What the Virus radar shows, checked in the emulator: stop after the HUD's dot loop ($23aa6) on every frame of the
autopilot's wave 0 from demo/S1b.snap and compare the dot list ($2fef6 .. [$27076]) with the actor pool and the ship,
then read each dot's pixel from the screen buffer.   uv run python reversing/virus/py/scan/radar_check.py [frames=1100] [out.json]   (about 1 minute)"""
import collections, json, os, struct, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
os.environ.setdefault('VIRUS_MPC_WORK', os.path.join(d, 'scratchpad', 'virus', 'radar'))   # the server's log goes there
sys.path.insert(0, os.path.join(d, 'reversing', 'virus', 'py', 'mpc'))
import replay as R, shot as S
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1100
s = R._quiet_server(); s('load', snapshot=os.path.join(R.ROOT, 'scratchpad/virus/demo/S1b.snap')); s('bp_set', addrs=[0x23aa6])
rd = lambda a, n: bytes.fromhex(s('read', addr=a, len=n))
W = lambda a: struct.unpack('>H', rd(a, 2))[0]; L = lambda a: struct.unpack('>L', rd(a, 4))[0]
s16 = S.s16
COLOUR = {0x21792: 5, 0x21894: 5, 0x21976: 5, 0x219de: 5, 0x21afe: 0xd, 0x21c64: 0xb, 0x21d08: 0xb, 0x21df6: 0xb}   # read from the append sites
def pix(buf, px, py):                                    # colour index of pixel (px, py) in a 4-plane buffer of 160-byte rows
    o = py * 160 + (px >> 4) * 8; m = 0x8000 >> (px & 15)
    return sum(((struct.unpack('>H', buf[o + 2 * p:o + 2 * p + 2])[0] & m) != 0) << p for p in range(4))
def mpix(mm, px, py):                                    # the same in the minimap buffer (32-byte rows)
    o = py * 32 + (px >> 4) * 8; m = 0x8000 >> (px & 15)
    return sum(((struct.unpack('>H', mm[o + 2 * p:o + 2 * p + 2])[0] & m) != 0) << p for p in range(4))
frames = eq = 0; seen = collections.Counter(); bad = []; kinds = collections.Counter(); wait_dots = 0; waiting_frames = 0
try:
    while frames < N:
        r = s('run', max_steps=8000000)
        if r['reason'] != 'breakpoint': print('stopped:', r['reason']); break
        if r['steps'] < 64: continue                     # the same stop again after an interrupt's RTE
        end = L(0x27076); raw = rd(0x2fef6, end - 0x2fef6)
        dots = [struct.unpack('>3H', raw[i:i + 6]) for i in range(0, len(raw), 6)]
        n = struct.unpack('>h', rd(0x32a3e, 2))[0]; pool = S.unpack_pool(rd(0x31d54, 20 * n))
        ship = struct.unpack('>3H', rd(0x270ce, 6))
        want = [(a[0] & 0xffff, a[2] & 0xffff, COLOUR[a[8]]) for a in pool if a[8] in COLOUR] + [(ship[0], ship[2], 0xf)]
        frames += 1; ok = dots == want; eq += ok
        if not ok and len(bad) < 5: bad.append({'frame': frames, 'dots': dots, 'want': want, 'pool': [hex(a[8]) for a in pool]})
        waiting_frames += any(S.KINDS.get(a[8], ('', ''))[1] == 'wait' for a in pool)
        for a in pool: kinds[hex(a[8])] += 1
        scr = rd(L(0x2705e), 64 * 160); mm = rd(0x2f6f6, 64 * 32)
        for x, z, t in dots:
            px = ((x + 0x8000) & 0xffff) >> 10; py = ((-((z + 0x8000) & 0xffff)) & 0xffff) >> 10
            seen[(t, mpix(mm, px, py), pix(scr, px, py))] += 1
    pal = [W(0xff8240 + 2 * i) & 0x777 for i in range(16)]
finally:
    try: s('shutdown')
    except SystemExit: pass
print('frames', frames, 'dot list == live pool records in pool order + ship:', eq, '/', frames)
print('frames with a waiting record in the pool:', waiting_frames, '(a waiting record never has a dot when the line above is all frames)')
print('pool behaviours seen (record-frames):', dict(kinds))
print('palette', ['%03x' % p for p in pal])
print('(dot type, minimap colour under it, screen colour at the dot): count')
for k, v in sorted(seen.items()): print('  type %x  under %2d  screen %2d : %d' % (*k, v))
for b in bad: print('MISMATCH', b)
if len(sys.argv) > 2: json.dump({'frames': frames, 'eq': eq, 'seen': [[*k, v] for k, v in seen.items()], 'pal': pal, 'bad': bad}, open(sys.argv[2], 'w'))
