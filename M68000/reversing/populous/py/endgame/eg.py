"""eg.py - shared helpers for the endgame scripts (paths from popcfg, REPL runner, poker)."""
import os, re, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))))
from popcfg import R, WORK, DLL, DISK          # noqa: E402
from popmem import ram, w, sw, l, cstr          # noqa: E402

OUT = os.path.join(WORK, 'endgame')
os.makedirs(OUT, exist_ok=True)
ENT, ESZ = 0x3b278, 0x16
HUMAN, OTHER = 0x3affe, 0x22284
SIDE = 0x3b226
GOD = 0x21e0c
ROWS = 0x225d8
SCORE = 0x36cea
BATTLES = 0x3c514
NENT = 0x3c4e2
WORLD = 0x3c51a


def repl(snap, lines, timeout=3000):
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl', '--disk-a', DISK],
                       input='\n'.join(list(lines) + ['q']) + '\n', capture_output=True,
                       text=True, cwd=R, env=env, timeout=timeout)
    return p.stdout + p.stderr


def regs(out):
    return {m.group(1): int(m.group(2), 16)
            for m in re.finditer(r'\b([DA][0-7]|PC):\s*([0-9a-f]{8})', out)}


class Poker:
    """tracks a RAM image and emits `w` lines (big-endian longs) for changed 4-byte blocks."""
    def __init__(self, m): self.m = bytearray(m); self.dirty = set()
    def b(self, a, v): self.m[a] = v & 0xff; self.dirty.add(a & ~3)
    def w(self, a, v): self.b(a, v >> 8); self.b(a + 1, v)
    def l(self, a, v): self.w(a, v >> 16); self.w(a + 2, v)
    def flush(self):
        out = ['w %x %08x' % (a, struct.unpack_from('>I', self.m, a)[0]) for a in sorted(self.dirty)]
        self.dirty = set(); return out


def entities(m):
    n = w(m, NENT)
    for i in range(n):
        e = ENT + ESZ * i
        yield i, e, dict(flags=m[e], side=m[e + 1], str=sw(m, e + 4), cell=w(m, e + 8),
                         anim=w(m, e + 12), knight=l(m, e + 14))


def rowtext(m, r):
    return cstr(m, ROWS + 0x2e * r + 6)


def import_popworld():
    import popworld
    return popworld
