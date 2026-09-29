"""Live REPL driver for Impossamole (agents/boss). Import: `from repl import Repl`.

`Repl(snap)` starts `resume <snap> repl` with ATARI_NOTRACE=1 and the game disk. `run(*cmds)` sends commands and a
sentinel (`hits 0 fb98`), returning the output lines before it. `mem(addr, n)` reads bytes. Helpers below decode the
hero (base $1a572), the boss (slot 7, $1a5de) and projectile slots 16-19 ($1a9aa, stride 108).
"""
import os, subprocess, sys, threading
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
OUT = os.path.join(ROOT, 'scratchpad/impossamole/agents/boss')
SLOT0, STRIDE = 0x1a2ea, 0x6c


class Repl:
    def __init__(self, snap):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl',
                                   '--disk-a', DISK], cwd=ROOT, env=env, text=True, bufsize=1,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.err = []   # stderr lines (the REPL's `watch` reports go here)
        threading.Thread(target=lambda: [self.err.append(l.rstrip()) for l in self.p.stderr], daemon=True).start()
        self.run('s 1')

    def run(self, *cmds):
        for c in cmds:
            self.p.stdin.write(c + '\n')
        self.p.stdin.write('hits 0 fb98\n'); self.p.stdin.flush()
        out = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError('repl closed')
            if l.startswith('  $00fb98'):
                return [x.rstrip() for x in out if not x.startswith(('enqueued', '---'))]
            out.append(l)

    def mem(self, addr, n):
        return bytes.fromhex(''.join(self.run(f'm {addr:x} {n}')[-1:]).replace(' ', ''))

    def close(self):
        try:
            self.p.stdin.write('q\n'); self.p.stdin.flush(); self.p.wait(timeout=20)
        except Exception:
            self.p.kill()


def w(b, o): return int.from_bytes(b[o:o + 2], 'big')
def sw(b, o): return int.from_bytes(b[o:o + 2], 'big', signed=True)


def slot(r, n):
    return r.mem(SLOT0 + n * STRIDE, STRIDE)


def fmt_slot(b):
    return (f'type={w(b,0)} x={sw(b,2)} y={sw(b,4)} v8={sw(b,8)} v10={sw(b,10)} r={b[12]},{b[13]} '
            f'anim={int.from_bytes(b[22:26],"big"):x} f30={w(b,30):x} 32={sw(b,32)} 34={sw(b,34)} '
            f'79={b[79]} 101={b[101]} 102={b[102]} 103={b[103]} 104={b[104]} 105={b[105]}')
