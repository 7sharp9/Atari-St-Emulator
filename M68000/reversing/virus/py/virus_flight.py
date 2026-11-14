"""Gate for Virus's flight tick ($255c2 .. $257fa).  Input: a REPL log made with
   bp 255d4 / r / m 270b0 12 / m 32a32 4 / m 32a3a 2 / m 32a2e 2 / m 270d4 18 / m 254a8 1   repeated (flight_bp.txt).
Model of one tick, state = pos(x,y,z) vel(vx,vy,vz) at $270b0 (6 words), att(yaw,pitch) at $32a32, matrix $270d4:
   target (D0,D1) and flags D2 come from the input routine ($254aa mouse / $2538c keys).
   if y < $c900 (signed) thrust is cancelled; if neither thrust (D2 bit1) nor the $62a63 latch: other path ($25a6e, not modelled)
   att += -(clamp((att - target), upper limit $2800 only, no lower limit)) >> 1       (low-pass, half way per tick)
   matrix = rot(att)  ($1f646: products of table sines, 2*hi(a*b))
   vel -= vel >> 6  (drag 1/64 per tick, per axis)
   thrust: vel -= column >> 3 where column = high bytes of matrix words 2, 8, 14;  fuel $32a2e -= 3
   pos += vel ;  vel_y += g ($32a3a: 3,4,5,6 by wave)
Compared: next stop's pos, vel, att, matrix.  Usage: python virus_flight.py <flight_bp.txt> <snap> [--break]
"""
import os, re, struct, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'tools'))
import gfxview

def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v
def w(v): return v & 0xffff

snap = sys.argv[2]
r0 = bytes(gfxview.load_ram(snap)[0])
S = struct.unpack('>1024h', r0[0xd0fa:0xd0fa + 2048])
sin = lambda a: S[(w(a) >> 5 & 0xffff & 0xfffe) // 2]
def matrix(a0, a1):
    cos0 = sin(a0 + 0x4000); cos1 = sin(a1 + 0x4000); s0 = sin(a0); s1 = sin(a1)
    hi = lambda x, y: w(((x * y) >> 16) * 2)       # muls ; swap ; add.w D,D
    m = {}
    m[14] = hi(s0, s1); m[0] = hi(cos0, cos1)
    m[12] = w(-hi(cos0, s1)); m[2] = w(-hi(s0, cos1))
    m[6] = w(s0); m[4] = w(s1); m[8] = w(cos0); m[16] = w(cos1); m[10] = 0
    return m

txt = open(sys.argv[1]).read().split('\n')
stops = []; cur = None
i = 0
while i < len(txt):
    l = txt[i]
    if l.startswith('--- breakpoint'):
        cur = {'mem': [], 'reg': {}}; stops.append(cur)
    if cur is not None:
        for k, v in re.findall(r'([DA]\d):([0-9a-f]{8})', l): cur['reg'][k] = int(v, 16)
        if re.fullmatch(r'([0-9a-f]{2} )+[0-9a-f]{2}', l.strip()) or re.fullmatch(r'[0-9a-f]{2}', l.strip()):
            cur['mem'].append(bytes.fromhex(l.strip().replace(' ', '')))
    i += 1
brk = '--break' in sys.argv
ok = {'pos': 0, 'vel': 0, 'att': 0, 'mat': 0}; n = 0; skipped = 0; allok = 0; nt = [0, 0]; cnt = {}
for a, b in zip(stops, stops[1:]):
    if len(a["mem"]) < 6 or len(b["mem"]) < 6: continue
    pv = list(struct.unpack('>6h', a['mem'][0])); att = list(struct.unpack('>2h', a['mem'][1]))
    g = struct.unpack('>h', a['mem'][2])[0]
    D0, D1, D2 = (a['reg'][k] & 0xffff for k in ('D0', 'D1', 'D2'))
    if s16(pv[1]) < s16(0xc900): D2 &= ~2
    thrust = bool(D2 & 2)                  # thrust off: same tick without the thrust term, if the $62a63 latch is set
    t = [D0, D1]; new = []
    for j in range(2):
        d5 = s16(att[j] - t[j])
        if d5 >= 0 and w(d5) >= 0x2800: d5 = 0x2800
        d5 >>= 1
        new.append(s16(att[j] - d5))
    m = matrix(new[0], new[1])
    v = pv[3:6]
    v = [s16(x - (x >> 6)) for x in v]
    col = [struct.unpack('>b', bytes([(m[o] >> 8) & 0xff]))[0] for o in (2, 8, 14)]
    sh = 4 if brk else 3
    if thrust:
        v = [s16(x - (c >> sh)) for x, c in zip(v, col)]
    p = [s16(pv[j] + v[j]) for j in range(3)]
    v[1] = s16(v[1] + g)
    got_pv = list(struct.unpack('>6h', b['mem'][0])); got_att = list(struct.unpack('>2h', b['mem'][1]))
    got_m = {o: struct.unpack('>H', b['mem'][4][o:o + 2])[0] for o in range(0, 18, 2)}
    n += 1
    ok['pos'] += p == got_pv[:3]; ok['vel'] += v == got_pv[3:]; ok['att'] += new == got_att
    ok['mat'] += all(m[o] == got_m[o] for o in m)
    good = (p == got_pv[:3] and v == got_pv[3:] and new == got_att)
    allok += good; nt[thrust] += 1
    if good: nt[thrust] += 0
    cnt[thrust] = cnt.get(thrust, 0) + good
print(f'{len(stops)} stops; {n} thrust ticks modelled ({skipped} non-thrust ticks skipped): ' +
      ', '.join(f'{k} {v}/{n}' for k, v in ok.items()) + f'; pos+vel+att all equal {allok}/{n} (thrust ticks {cnt.get(True,0)}/{nt[1]}, no-thrust ticks {cnt.get(False,0)}/{nt[0]})')
