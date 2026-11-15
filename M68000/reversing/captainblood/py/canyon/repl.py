"""Persistent REPL wrapper for the canyon work: Repl(snap) -> .cmd(line), .mem(addr,n), .step(n), .snap(path).
Finds the repo root by walking up to the directory holding tools/rdis.py."""
import os, subprocess, sys

def root():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != '/' and not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        d = os.path.dirname(d)
    return d

ROOT = root()

class Repl:
    def __init__(self, snap, extra_env=None):
        env = dict(os.environ, ATARI_NOTRACE='1')
        if extra_env: env.update(extra_env)
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl'],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, cwd=ROOT, env=env, bufsize=1)
        self.sync()
    def sync(self):
        # sentinel: dump of a fixed 2 bytes; read until that line shows up after a marker echo
        self.p.stdin.write('m c6ce 2\n'); self.p.stdin.flush()
        out = []
        while True:
            l = self.p.stdout.readline()
            if not l: raise RuntimeError('repl exited: ' + ''.join(out[-5:]))
            out.append(l)
            # the dump line is two hex bytes only
            s = l.strip().split()
            if len(s) == 2 and all(len(t) == 2 and all(c in '0123456789abcdef' for c in t) for t in s):
                return ''.join(out)
    def cmd(self, *lines):
        self.p.stdin.write('\n'.join(lines) + '\n'); self.p.stdin.flush()
        return self.sync()
    def mem(self, addr, n):
        self.p.stdin.write(f'm {addr:x} {n}\n'); self.p.stdin.flush()
        while True:
            l = self.p.stdout.readline()
            s = l.strip().split()
            if len(s) == n and all(len(t) == 2 for t in s):
                try: b = bytes(int(t, 16) for t in s)
                except ValueError: continue
                self.sync_pending = False
                return b
    def w(self, addr, n=2):
        b = self.mem(addr, n); return int.from_bytes(b, 'big')
    def step(self, n): return self.cmd(f's {n}')
    def snap(self, path): return self.cmd(f'snap {path}')
    def close(self):
        try: self.p.stdin.write('q\n'); self.p.stdin.flush()
        except Exception: pass
        self.p.wait(timeout=20)
