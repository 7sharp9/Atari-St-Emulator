"""pwlib.py - shared helpers for the power scripts.

repl_batch(snap, lines): one REPL session, returns stdout+stderr.
get_regs(snap): registers at the snapshot (A7 = callcap entry SP).
Poker: tracks a RAM image, emits `w` lines for changed longwords.
load_cc(path): callcap JSON -> (outcome, {addr: new byte}).
"""
import json, os, re, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..')))  # reversing/populous/py
from popcfg import R, WORK, DLL, DISK
PD = os.path.join(WORK, 'powers')                                # snaps/ and cc/ go here
os.makedirs(os.path.join(PD, 'snaps', 'tmp'), exist_ok=True)
os.makedirs(os.path.join(PD, 'cc'), exist_ok=True)
from popmem import ram


def repl_batch(snap, lines, timeout=3600):
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl', '--disk-a', DISK],
                       input='\n'.join(list(lines) + ['q']) + '\n', capture_output=True, text=True,
                       cwd=R, env=env, timeout=timeout)
    return p.stdout + p.stderr


def get_regs(snap):
    out = repl_batch(snap, ['r'])
    return {k: int(v, 16) for k, v in re.findall(r'\b([DA][0-7]|PC):\s*([0-9a-f]{8})', out)}


class Poker:
    def __init__(self, m): self.m = m; self.dirty = set()
    def b(self, a, v): self.m[a] = v & 0xff; self.dirty.add(a & ~3)
    def w(self, a, v): self.b(a, v >> 8); self.b(a + 1, v)
    def l(self, a, v): self.w(a, (v >> 16) & 0xffff); self.w(a + 2, v & 0xffff)
    def flush(self):
        out = ['w %x %08x' % (a, struct.unpack_from('>I', self.m, a)[0]) for a in sorted(self.dirty)]
        self.dirty = set(); return out


def load_cc(path):
    d = json.load(open(path))
    return d['outcome'], {a: x1 for a, _x0, x1 in d['mem']}, d


def rw(m, a): return struct.unpack_from('>H', m, a)[0]
def rsw(m, a): return struct.unpack_from('>h', m, a)[0]
def rl(m, a): return struct.unpack_from('>I', m, a)[0]
def rsl(m, a): return struct.unpack_from('>i', m, a)[0]
def ww(m, a, v): struct.pack_into('>H', m, a, v & 0xffff)
def wl(m, a, v): struct.pack_into('>I', m, a, v & 0xffffffff)


class Repl2:
    """persistent REPL like repl.Repl, but a `bp`/`bpc` command (which prints the registers itself)
    waits for two register dumps, so the request/response stream stays in step."""
    HEX = re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')

    def __init__(self, snap):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', DLL, 'resume', snap, 'repl', '--disk-a', DISK],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, cwd=R, env=env, bufsize=1)

    def cmd(self, c):
        self.p.stdin.write(c.rstrip('\n') + '\nr\n'); self.p.stdin.flush()
        need = 2 if c.split()[0] in ('bp', 'bpc') else 1
        out = []
        while need:
            line = self.p.stdout.readline()
            if not line:
                raise EOFError('\n'.join(out[-20:]))
            line = line.rstrip('\n'); out.append(line)
            if line.startswith('PC: '):
                need -= 1
                if need:
                    continue
                self.p.stdout.readline()
        regs = {}
        tail = out[max(i for i, l in enumerate(out) if l.startswith('PC: ')) - 8:]
        for l in tail:
            for mm in re.finditer(r'\b([DA][0-7]|PC|USP|SSP):\s*([0-9a-f]{8})', l):
                regs[mm.group(1)] = int(mm.group(2), 16)
        return out, regs

    def mem(self, a, n):
        out, _ = self.cmd('m %x %d' % (a, n))
        bs = bytearray()
        for l in out:
            if self.HEX.match(l.strip()):
                bs += bytes(int(x, 16) for x in l.split())
        assert len(bs) == n, (len(bs), n, out)
        return bytes(bs)

    def close(self):
        try:
            self.p.stdin.write('q\n'); self.p.stdin.flush()
        except Exception:
            pass
        self.p.wait()
