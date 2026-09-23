"""capcalls.py <snap> <ncalls> <out.bin>

Runs the game from <snap> (no input) and, for each of the next <ncalls> calls of $ef4c (walker step
decision), records the RAM the decision reads at the call ($36e78..$3d550, god records $21e0c+92,
options $219b0+4), the stack arguments 4(A7) entity pointer / 8(A7) index (from a dump of the
stack page), and the D0 the chosen routine returned (read at $efa8, where the $f2f4 and $f6b2
paths rejoin).

Record: HDR (entity.l, idx.w, d0.w) + REGIONS bytes. `load(path)` -> list of dicts.
"""
import os, re, struct, subprocess, sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from popcfg import R, DLL, DISK

REGIONS = [(0x36e78, 0x3d550 - 0x36e78), (0x21e0c, 92), (0x219b0, 4)]
STACK = (0x3e000, 0x2000)          # the game's supervisor/user stack page (A7 ~ $3f40e in $db4c)
RLEN = sum(n for _, n in REGIONS)
HDR = struct.Struct('>IHH')
HEXLINE = re.compile(r'([0-9a-f]{2} )*[0-9a-f]{2}')


def capture(snap, n):
    L = []
    for _ in range(n):
        L += ['u ef4c 3000000', 'r'] + ['m %x %d' % r for r in REGIONS + [STACK]] + ['u efa8 300000', 'r']
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', os.path.abspath(snap), 'repl', '--disk-a', DISK],
                       input='\n'.join(L + ['q']) + '\n', capture_output=True, text=True, cwd=R, env=env)
    recs, cur, hexes, a7, d0 = [], None, [], 0, 0
    for line in p.stdout.splitlines():
        s = line.strip()
        m = re.search(r'A7:([0-9a-f]{8})', s)
        if m: a7 = int(m.group(1), 16)
        m = re.match(r'D0:([0-9a-f]{8})', s)
        if m: d0 = int(m.group(1), 16)
        m = re.match(r'PC: ([0-9a-f]{8})', s)
        if m:
            pc = int(m.group(1), 16)
            if pc == 0xef4c:
                cur = {'a7': a7}; hexes = []
            elif pc == 0xefa8 and cur is not None and len(hexes) == len(REGIONS) + 1:
                st = hexes[-1]
                o = cur['a7'] - STACK[0]
                cur['e'] = struct.unpack_from('>I', st, o + 4)[0]
                cur['idx'] = struct.unpack_from('>H', st, o + 8)[0]
                cur['d0'] = d0 & 0xffff
                cur['mem'] = b''.join(hexes[:-1])
                recs.append(cur); cur = None
            continue
        if cur is not None and s and HEXLINE.fullmatch(s):
            hexes.append(bytes(int(x, 16) for x in s.split()))
    return recs


def save(recs, out):
    with open(out, 'wb') as f:
        for r in recs:
            f.write(HDR.pack(r['e'], r['idx'], r['d0'])); f.write(r['mem'])


def load(path):
    b = open(path, 'rb').read()
    n = HDR.size + RLEN
    out = []
    for o in range(0, len(b), n):
        e, idx, d0 = HDR.unpack_from(b, o)
        out.append({'e': e, 'idx': idx, 'd0': d0, 'mem': b[o + HDR.size:o + n]})
    return out


def apply(base, mem):
    """base RAM (bytearray) with the captured regions laid over it."""
    m = bytearray(base); o = 0
    for a, n in REGIONS:
        m[a:a + n] = mem[o:o + n]; o += n
    return m


def frame_of(r):
    return struct.unpack_from('>H', r['mem'], 0x3c4c8 - 0x36e78)[0]


if __name__ == '__main__':
    snap, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    recs = capture(snap, n)
    save(recs, out)
    print('calls', len(recs), 'frames', frame_of(recs[0]) if recs else None, '..',
          frame_of(recs[-1]) if recs else None)
