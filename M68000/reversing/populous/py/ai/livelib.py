"""livelib.py - persistent REPL session + snapshot helpers for the live AI checks."""
import json, os, re, struct, subprocess
from aicfg import *
import popmem

HEX = re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')


def snap_step(path):
    """absolute emulator stepCount stored in a .snap (format v11, see Program.fs SaveState)."""
    b = open(path, 'rb').read()
    o = 83
    for _ in range(4):
        n = struct.unpack_from('<i', b, o)[0]; o += 4 + n
    o += 7 + 7 + 6 + 6 + 5 + 3 + 1
    return struct.unpack_from('<Q', b, o)[0]


class Sess:
    """one emulator REPL process. cmd() sends lines + 'r' and returns the text up to the register dump."""
    def __init__(self, snap, errfile=None):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.err = open(errfile, 'w') if errfile else subprocess.DEVNULL
        self.p = subprocess.Popen(['dotnet', 'exec', DLL, 'resume', os.path.abspath(snap), 'repl', '--disk-a', DISK],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err,
                                  text=True, cwd=R, env=env, bufsize=1)
        self.steps = 0          # steps run since the snapshot (u / s only; callcap restores)
        self.cmd('')

    def cmd(self, c):
        self.p.stdin.write((c.rstrip('\n') + '\n' if c else '') + 'r\n'); self.p.stdin.flush()
        out = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise EOFError('\n'.join(out[-30:]))
            line = line.rstrip('\n'); out.append(line)
            if line.startswith('PC: '):
                self.p.stdout.readline(); break
        self.regs = {k: int(v, 16) for k, v in re.findall(r'\b([DA][0-7]|PC):\s*([0-9a-f]{8})', '\n'.join(out))}
        return out

    def step(self, n):
        self.cmd('s %d' % n); self.steps += n

    def until(self, addr, cap):
        """run to PC == addr (at least one step first). Returns True if reached."""
        self.step(1)
        out = '\n'.join(self.cmd('u %x %d' % (addr, cap)))
        m = re.search(r'reached PC=\$[0-9a-f]+ after (\d+) step', out)
        if m:
            self.steps += int(m.group(1)); return True
        m = re.search(r'gave up after (\d+) step', out)
        self.steps += int(m.group(1)); return False

    def mem(self, a, n):
        out = self.cmd('m %x %d' % (a, n))
        bs = bytearray()
        for l in out:
            if HEX.match(l.strip()): bs += bytes(int(x, 16) for x in l.split())
        assert len(bs) == n, (len(bs), n)
        return bytes(bs)

    def snapram(self, path):
        self.cmd('snap ' + os.path.abspath(path))
        return bytearray(popmem.ram(path))

    def callcap(self, addr, path, cap=3000000):
        if os.path.exists(path): os.remove(path)
        self.cmd('callcap %x %d %s' % (addr, cap, path))
        return json.load(open(path))

    def close(self):
        try:
            self.p.stdin.write('q\n'); self.p.stdin.flush()
        except Exception:
            pass
        self.p.wait()
