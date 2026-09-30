"""Minimal live REPL wrapper (no build, uses the existing DLL).  Every call is ATARI_NOTRACE=1.
    r = Repl(snap)                      # snap relative to M68000/ or absolute
    r.cmd('s 20000'); r.mem(0xbb74, 4); r.kbd(0xff, 0x80); r.hits(steps, addr...)
watch output (stderr) is collected in r.err (list of lines)."""
import os, subprocess, threading, sys
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
SENT = 'hits 0 fb98'
class Repl:
    def __init__(self, snap, disk=DISK):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', disk],
                                  cwd=ROOT, env=env, text=True, bufsize=1, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        self.err = []
        self._t = threading.Thread(target=self._drain, daemon=True); self._t.start()
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
    def pc(self):
        for l in self.cmd('r'):
            if l.startswith('PC:'): return int(l.split()[1], 16)
    def until(self, addr, maxsteps=20000000):
        out = self.cmd(f'u {addr:x} {maxsteps}')
        for l in out:
            if 'reached PC' in l:
                self.steps += int(l.split('after ')[1].split()[0]); return True
        return False
    def kbd(self, *bytes_):
        for x in bytes_:
            self.cmd(f'kbd {x:02x}', 's 200')
    def joy(self, bits):            # joystick 1 packet: header $ff then status
        self.cmd('kbd ff', 's 300', f'kbd {bits:02x}')
    def snap(self, path): return self.cmd(f'snap {path}')
    def close(self):
        try:
            self.p.stdin.write('q\n'); self.p.stdin.flush()
        except Exception: pass
        try: self.p.wait(timeout=10)
        except Exception: self.p.kill()
