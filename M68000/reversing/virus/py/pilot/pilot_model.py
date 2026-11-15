"""Gated model of one Virus pilot tick: Input_Autopilot $2538c with its callees (reversing/virus/demo.md, "The pilot").

Transliterated from the disassembly of $2538c, $2529a (nearest-record scan), $24754 (ground height), $22c1e (steering
update) and $1f646 (attitude matrix).  Registers are modelled as 32-bit values, because the routine leaves part-word
results in D3..D7 and the gate compares all of them.  Gate: every `callcap 2538c` of a captured demo flight
(capture_pilot.py): final D0..D7 and A0..A3, every byte of the tracked memory ($270a2 controller word, $270a6 target
pointer, $270aa aim point, $270d4 matrix, $62a60 countdown) must equal the model's, and every byte callcap changed must lie
in the tracked memory or the stack frame below the entry SP.  The pilot's sensor data (ship words, the 20-byte records of
the pool $31d54, the tick word, the sine table and the height map) is read from the dump and the start snapshot, never from
the callcap result.
Usage (from M68000/):  uv run python <this> <ticks.log> [snap] [--control NAME]
Controls (a deliberately wrong model must fail): scan_lt (ties go to the earlier record), thrust_cap ($3200 -> $3400),
  turn_step (+2/-2 -> +3/-3), no_asr (aim offset not halved), fire_range ($900 -> $a00).
"""
import os, re, struct, sys
from collections import Counter
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')): d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'tools'))
import gfxview

M = 0xffff; L = 0xffffffff
CTRL = set()
def s16(v): v &= M; return v - 0x10000 if v & 0x8000 else v
def s8(v): v &= 0xff; return v - 0x100 if v & 0x80 else v
def sx(v): return s16(v) & L                       # movem.w / move.w from memory into a data register
def setw(r, v): return (r & 0xffff0000) | (v & M)
def swap(r): return ((r << 16) | (r >> 16)) & L
def muls(rn, rm): return (s16(rn) * s16(rm)) & L   # muls Dm,Dn
def asr1(v): v &= M; return (v >> 1) | (v & 0x8000)
def absw(r):                                       # sub.w result in r; bpl; neg.w
    r &= M; return r if not r & 0x8000 else (-r) & M
def addv(a, b):                                    # add.w b,a -> (word, V)
    r = (a + b) & M; return r, bool((~(a ^ b)) & (a ^ r) & 0x8000)

class Flight:
    """Static data not in the per-tick dump: sine table $d0fa and height map $42a58 (from the start snapshot)."""
    def __init__(self, snap):
        ram = bytes(gfxview.load_ram(snap)[0])
        self.sin = struct.unpack('>1024h', ram[0xd0fa:0xd0fa + 2048])
        self.hmap = ram[0x42a58:0x42a58 + 0x10000]

def matrix(F, a0, a1):
    """$1f646 Attitude_Matrix: the nine words at $270d4 + offset, from angles D0 = a0, D1 = a1."""
    sn = lambda a: F.sin[((a & M) >> 5 & 0xfffe) // 2]
    c0 = sn(a0 + 0x4000); c1 = sn(a1 + 0x4000); s0 = sn(a0); s1 = sn(a1)
    hi = lambda x, y: ((muls(x, y) >> 16) * 2) & M
    return {14: hi(s0, s1), 0: hi(c0, c1), 12: (-hi(c0, s1)) & M, 2: (-hi(s0, c1)) & M,
            6: s0 & M, 4: s1 & M, 8: c0 & M, 16: c1 & M, 10: 0}

def ground(F, x, z):
    """$24754 Landscape_HeightAt, D1 word: $420 when x and z are both below $900 (launch pad), else map byte * 8 - $298."""
    if (x & M) < 0x900 and (z & M) < 0x900: return 0x420
    return (F.hmap[((z & 0xff00) + ((x & M) >> 8)) & 0xffff] * 8 - 0x298) & M

def scan(pool, ship, count, tags):
    """$2529a Target_FindNearest: index of the record with the smallest Manhattan distance to the ship (word arithmetic,
    saturating to $7fff; a tie goes to the later record), skipping y = $f100 and the long at +16 = $228de; 0 if none."""
    best, d5 = 0, 0x7fff
    for i in range(count):
        r = pool[i * 20:i * 20 + 20]
        w = lambda o: struct.unpack('>H', r[o:o + 2])[0]
        d3 = absw(ship[0] - w(0)); d4 = absw(ship[1] - w(2))
        d3, v = addv(d3, d4)
        if v: d3 = 0x7fff
        else:
            d4 = absw(ship[2] - w(4)); d3, v = addv(d3, d4)
            if v: d3 = 0x7fff
        if ('scan_lt' in CTRL and s16(d5) <= s16(d3)) or s16(d5) < s16(d3): continue
        if w(2) == 0xf100: tags['scan_skip_y_f100'] += 1; continue
        if struct.unpack('>I', r[16:20])[0] == 0x228de: tags['scan_skip_228de'] += 1; continue
        d5 = d3; best = i
    return best

def tick(F, st, tags):
    """One call of $2538c.  st: D, A (entry registers), ctrl ($270a2), ptr ($270a6), ship (six signed words from $270b0),
    tick ($32a44), cd ($62a60), count ($32a3e), pool.  Returns (D, A, memory dict address -> byte)."""
    R = list(st['D']); A = list(st['A']); cd = st['cd']
    if cd:                                          # $25372: launch countdown, thrust only
        tags['A countdown'] += 1
        R[2] = 2; R[0] = 0; R[1] = 0
        return R, A, {0x62a60: (cd - 1) & 0xff}
    ptr = st['ptr']
    if st['tick'] & 7 == 0:                         # every eighth tick: pick the target record
        tags['B scan tick'] += 1
        ptr = 0x31d54 + 20 * scan(st['pool'], st['ship'][:3], st['count'], tags)
    else: tags['B hold tick'] += 1
    sh = st['ship']; pi = (ptr - 0x31d54) // 20
    rec = struct.unpack('>6h', st['pool'][pi * 20:pi * 20 + 12])
    for k in range(6): R[k] = sx(rec[k])
    # aim point = record position + 4 * record velocity - 4 * ship velocity (word arithmetic, high halves kept)
    for k in range(3):
        R[3 + k] = setw(R[3 + k], R[3 + k] << 2); R[k] = setw(R[k], R[k] + R[3 + k])
    for k in range(3): R[3 + k] = sx(sh[3 + k])
    for k in range(3):
        R[3 + k] = setw(R[3 + k], R[3 + k] << 2); R[k] = setw(R[k], R[k] - R[3 + k])
    aim = [R[k] & M for k in range(3)]
    R[6] = setw(R[6], sh[0]); R[7] = setw(R[7], sh[2])
    h = ground(F, sh[0], sh[2]); R[7] = setw(R[7], h)
    ctrl = st['ctrl']
    # ---- $22c1e Autopilot_Steer, D6 = controller word
    hw = ctrl >> 16
    mat = matrix(F, (hw << 8) & M, hw & M)
    for k in range(3): R[k] = sx(sh[k])
    for k in range(3): R[3 + k] = sx(aim[k])
    for k in range(3):
        R[k] = setw(R[k], R[k] - R[3 + k])
        R[k] = setw(R[k], R[k] if 'no_asr' in CTRL else asr1(R[k]))
    d7 = (h - sh[1]) & M                            # D7 low in $22c1e, restored to h on exit
    c = ctrl
    def dot(o3, o4, o5):
        for k, o in ((3, o3), (4, o4), (5, o5)):
            R[k] = setw(R[k], asr1(mat[o])); R[k] = muls(R[k], R[k - 3]); R[k] = swap(R[k]); R[k] = setw(R[k], R[k] + R[k])
        R[3] = setw(R[3], R[3] + R[4]); R[3] = setw(R[3], R[3] + R[5])
        return bool(R[3] & 0x8000)
    step = 3 if 'turn_step' in CTRL else 2
    neg = False
    if s16(d7) >= 0x200:
        tags['C steer: above-ground test passed'] += 1
        neg = dot(2, 8, 14)
    else: tags['C steer: near ground, dot skipped'] += 1
    if neg:
        tags['C steer: row-1 dot negative (turn +2)'] += 1
        c |= 1 << 11
        b = (((c >> 16) & 0xff) + step) & 0xff
        if s8(b) > 0x3f: b = 0x3f
        c = (c & 0xff00ffff) | (b << 16)
    else:
        c &= ~(1 << 11)
        b = ((c >> 16) & 0xff)
        b = 0 if b < step else b - step
        c = (c & 0xff00ffff) | (b << 16)
    neg2 = dot(4, 10, 16)
    if neg2: tags['C steer: row-2 dot negative (-$700)'] += 1; c |= 1 << 12; c = (c & 0x0000ffff) | ((((c >> 16) - 0x700) & M) << 16)
    else: c &= ~(1 << 12); c = (c & 0x0000ffff) | ((((c >> 16) + 0x700) & M) << 16)
    c &= ~(1 << 10)
    if s16(sh[1]) < s16(0xc900): tags['C steer: y below $c900'] += 1; c |= (1 << 10) | (1 << 11)
    # ---- back in $2538c
    R[3] = setw(R[3], -(sh[1] - h) & M)             # height term: h - y
    for k in range(3): R[k] = sx(sh[k])
    R[4] = setw(R[4], R[0] - aim[0]); R[4] = setw(R[4], absw(R[4]))
    R[5] = setw(R[5], R[1] - aim[1]); R[5] = setw(R[5], absw(R[5]))
    r, v = addv(R[4] & M, R[5] & M); R[4] = setw(R[4], r)
    if v: R[4] = setw(R[4], 0x7fff)
    else:
        R[5] = setw(R[5], R[2] - aim[2]); R[5] = setw(R[5], absw(R[5]))
        r, v = addv(R[4] & M, R[5] & M); R[4] = setw(R[4], r)
        if v: R[4] = setw(R[4], 0x7fff)
    D3, D4 = R[3] & M, R[4] & M
    R[2] = 2
    if D4 >= (0x3400 if 'thrust_cap' in CTRL else 0x3200) and D3 >= 0x600: tags['D thrust cut: far and high'] += 1; R[2] &= ~2
    R[1] = swap(c); R[0] = setw(R[0], R[1]); R[0] = setw(R[0], R[0] << 8)
    if c & (1 << 11): tags['D thrust cut: controller bit 11'] += 1; R[2] &= ~2
    if D4 < (0xa00 if 'fire_range' in CTRL else 0x900): tags['D fire (D4 < $900)'] += 1; R[2] |= 1
    if D4 >= 0x2800: tags['D D0 = $2000 (D4 >= $2800)'] += 1; R[0] = setw(R[0], 0x2000)
    if D4 >= 0x5a00: tags['D D0 = $3500 + thrust (D4 >= $5a00)'] += 1; R[0] = setw(R[0], 0x3500); R[2] |= 2
    if D3 >= 0xc400 and D4 >= 0xc00: tags['D D0 = $1000 (height >= $c400)'] += 1; R[0] = setw(R[0], 0x1000)
    R[4] = setw(R[4], sh[4]); R[4] = setw(R[4], R[4] << 2); R[3] = setw(R[3], R[3] - R[4])
    if s16(R[3]) <= 0x400: tags['D ground-avoid reflex'] += 1; R[2] |= 2; R[0] = setw(R[0], 0x400)
    if not R[2] & 1: tags['E cruise (no fire)'] += 1
    else: tags['E attack (fire)'] += 1
    R[6] = c
    R[7] = setw(R[7], h)
    A[0] = 0xd0fa; A[1] = 0x270d4; A[2] = 0x270aa; A[3] = 0x270b0
    mem = {}
    def put(a, b):
        for i, x in enumerate(b): mem[a + i] = x
    put(0x270a2, struct.pack('>I', c)); put(0x270a6, struct.pack('>I', ptr)); put(0x270aa, struct.pack('>3H', *aim))
    put(0x270d4, b''.join(struct.pack('>H', mat[o]) for o in range(0, 18, 2))); mem[0x62a60] = 0
    return R, A, mem

# ---------------------------------------------------------------- the capture log
HEX = re.compile(r'^[0-9a-f]{2}( [0-9a-f]{2})*$')
def parse(path):
    txt = open(path).read()
    chunks = re.split(r'(?m)^(?=--- (?:breakpoint|gave up))', txt)[1:]
    out = []; gaveup = 0
    for ch in chunks:
        if ch.startswith('--- gave up'): gaveup += 1; continue
        if '--- callcap' not in ch: continue          # the last chunk of the log (snap, q)
        regs = dict((k, int(v, 16)) for k, v in re.findall(r'\b([DA][0-7]):([0-9a-f]{8})', ch.split('--- callcap')[0]))
        rows = [bytes.fromhex(l.replace(' ', '')) for l in ch.split('--- callcap')[0].split('\n') if HEX.match(l.strip())]
        cc = ch.split('--- callcap')[1].split('\n')
        sp = re.search(r'entrySP=\$([0-9a-f]+)', cc[0]); esp = int(sp.group(1), 16)
        rd = {}; md = {}
        for l in cc[1:]:
            if l.startswith('regdelta'):
                for k, a, b in re.findall(r'([DA][0-7]) \$([0-9a-f]{8})->\$([0-9a-f]{8})', l): rd[k] = (int(a, 16), int(b, 16))
            m = re.match(r'mem \$([0-9a-f]+) \$([0-9a-f]{2})->\$([0-9a-f]{2})', l)
            if m: md[int(m.group(1), 16)] = (int(m.group(2), 16), int(m.group(3), 16))
        out.append(dict(regs=regs, rows=rows, rd=rd, md=md, esp=esp))
    return out, gaveup

def main():
    args = [a for a in sys.argv[1:]]
    for i, a in enumerate(args):
        if a == '--control': CTRL.add(args[i + 1]); del args[i:i + 2]; break
    log = args[0]; snap = args[1] if len(args) > 1 else 'scratchpad/virus/demo/S1b.snap'
    F = Flight(snap); ticks, gaveup = parse(log)
    tags = Counter(); ok = 0; bad = Counter(); first = []
    for n, t in enumerate(ticks):
        ctrl, ship, mat, cnt, tk, cd, pool = t['rows']
        ptr = struct.unpack('>I', ctrl[4:8])[0]
        st = dict(D=[t['regs']['D%d' % i] for i in range(8)], A=[t['regs']['A%d' % i] for i in range(8)],
                  ctrl=struct.unpack('>I', ctrl[:4])[0], ptr=ptr, ship=struct.unpack('>6h', ship),
                  tick=struct.unpack('>H', tk)[0], cd=cd[0], count=struct.unpack('>H', cnt)[0], pool=pool)
        assert 0x31d54 <= ptr < 0x31d54 + len(pool), hex(ptr)
        D, A, mem = tick(F, st, tags)
        # expected = pre-state + callcap delta
        pre = {}
        for i, b in enumerate(ctrl): pre[0x270a2 + i] = b
        for i, b in enumerate(mat): pre[0x270d4 + i] = b
        pre[0x62a60] = cd[0]
        act = dict(pre); extra = 0; stack = 0
        for a, (o, nw) in t['md'].items():
            if t['esp'] - 0x40 <= a < t['esp']: stack += 1; continue
            if a in pre: act[a] = nw
            else: extra += 1
        why = []
        for k in range(8):
            ex = t['rd']['D%d' % k][1] if 'D%d' % k in t['rd'] else st['D'][k]
            if ex != D[k]: why.append('D%d' % k)
        for k in range(4):
            ex = t['rd']['A%d' % k][1] if 'A%d' % k in t['rd'] else st['A'][k]
            if ex != A[k]: why.append('A%d' % k)
        # the 14 pilot bytes $270a2..$270af (controller, pointer, aim), the matrix and the countdown are compared in full
        for a, b in mem.items():
            if act.get(a) != b: why.append('mem%x' % a)
        if extra: why.append('unexpected write')
        if why:
            bad[tuple(sorted(set(why)))] += 1
            if len(first) < 3: first.append((n, st['tick'], why))
        else: ok += 1
    print('callcaps compared: %d   (log chunks skipped as "gave up": %d)' % (len(ticks), gaveup))
    print('model == callcap: %d/%d   control=%s' % (ok, len(ticks), sorted(CTRL) or 'none'))
    if bad: print('mismatch classes:', dict(bad.most_common(6)), 'first:', first)
    print('per-branch counts (model view of the %d ticks):' % len(ticks))
    for k in sorted(tags): print('  %-46s %d' % (k, tags[k]))
if __name__ == '__main__': main()
