"""Live REPL wrapper for the Cadaver spike (no build, existing DLL, always ATARI_NOTRACE=1).
    r = Repl(snap)                      # snap relative to M68000/ or absolute
    r.cmd('s 20000'); r.mem(a, n); r.b/w/l(a); r.key(make); r.hits(steps, addr...)
Start snapshot for everything in this directory: scratchpad/cadaver/gameplay_empire.snap (CAVERN, day 1).
Scancodes go in as make, hold, break with real step counts in between (README "Keyboard discipline": the game's IKBD ISR
keeps one cell that the main loop polls, a make+break inside one poll is lost)."""
import os, subprocess, threading
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
DISK = '../Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st'
SNAP = 'scratchpad/cadaver/gameplay_empire.snap'
A5 = 0x18152
SENT = 'hits 0 fb98'

class Repl:
    def __init__(self, snap=SNAP, disk=DISK):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', disk],
                                  cwd=ROOT, env=env, text=True, bufsize=1, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        self.err = []
        threading.Thread(target=self._drain, daemon=True).start()
        self.steps = 0
        self.cmd('s 1')
    def _drain(self):
        for l in self.p.stderr:
            self.err.append(l.rstrip())
    def cmd(self, *cmds):
        for c in cmds:
            self.p.stdin.write(c + '\n')
            if c.startswith('s '):
                self.steps += int(c.split()[1])
        self.p.stdin.write(SENT + '\n'); self.p.stdin.flush()
        out = []
        while True:
            l = self.p.stdout.readline()
            if not l: raise RuntimeError('repl closed')
            if l.startswith('  $00fb98'):
                return [x.rstrip() for x in out if not x.startswith(('enqueued', '--- hits over'))]
            out.append(l)
    def mem(self, a, n):
        return bytes.fromhex(''.join(self.cmd(f'm {a:x} {n}')).replace(' ', ''))
    def b(self, a): return self.mem(a, 1)[0]
    def w(self, a): return int.from_bytes(self.mem(a, 2), 'big')
    def l(self, a): return int.from_bytes(self.mem(a, 4), 'big')
    def a5(self, off, n=1): return self.mem(A5 + off, n)
    def pc(self):
        for l in self.cmd('r'):
            if l.startswith('PC:'): return int(l.split()[1], 16)
    def hits(self, steps, *addrs):
        """{addr: count} over `steps` steps."""
        out = self.cmd(f'hits {steps} ' + ' '.join(f'{a:x}' for a in addrs))
        self.steps += steps
        d = {}
        for l in out:
            t = l.split()
            if len(t) >= 2 and t[0].startswith('$'):
                d[int(t[0][1:], 16)] = int(t[1])
        return d
    def key(self, make, hold=40000, after=200000):
        self.cmd(f'kbd {make:02x}', f's {hold}', f'kbd {make | 0x80:02x}', f's {after}')
    def joy(self, bits):
        self.cmd('kbd ff', 's 300', f'kbd {bits:02x}')
    def snap(self, path): return self.cmd(f'snap {path}')
    def close(self):
        try:
            self.p.stdin.write('q\n'); self.p.stdin.flush()
        except Exception: pass
        try: self.p.wait(timeout=10)
        except Exception: self.p.kill()
