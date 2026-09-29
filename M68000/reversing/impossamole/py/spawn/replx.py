"""Live-REPL driver shared by the spawn-type proofs (adapted from reversing/impossamole/py/boss_kill.py).

    from replx import Repl
    r = Repl('scratchpad/impossamole/pass103/room188.snap')
    r.run('s 1000', 'kbd ff')         # commands; returns the REPL output lines
    r.mem(0x1a5de, 108) -> bytes
    r.obj(slot) -> dict of the fields the spawn proofs use

The snapshot path is relative to M68000/ (the dotnet process's directory). Every process started here is stopped by
`close()`; a `with Repl(..) as r:` block does that. ATARI_NOTRACE=1 is set for the child.
"""
import os, subprocess, struct

ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
BASE = 0x1a2ea
STRIDE = 108


class Repl:
    def __init__(self, snap):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl',
                                   '--disk-a', DISK], cwd=ROOT, env=env, text=True, bufsize=1,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.run('s 1')

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def close(self):
        try:
            self.p.stdin.write('q\n'); self.p.stdin.flush()
            self.p.wait(timeout=20)
        except Exception:
            self.p.kill()

    def run(self, *cmds):
        """Send commands, then the sentinel `hits 0 fb98`; return the output lines before it."""
        for c in cmds:
            self.p.stdin.write(c + '\n')
        self.p.stdin.write('hits 0 fb98\n'); self.p.stdin.flush()
        out = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError('repl closed; last output: ' + ''.join(out[-5:]))
            if l.startswith('  $00fb98'):
                return [x.rstrip() for x in out if not x.startswith(('enqueued', '---'))]
            out.append(l)

    def mem(self, addr, n):
        lines = self.run(f'm {addr:x} {n}')
        hexs = ''.join(l.split(':', 1)[1] if ':' in l else l for l in lines)
        return bytes.fromhex(''.join(c for c in hexs if c in '0123456789abcdefABCDEF'))[:n]

    def obj(self, slot):
        a = BASE + slot * STRIDE
        b = self.mem(a, STRIDE)
        W = lambda o: struct.unpack_from('>H', b, o)[0]
        S = lambda o: struct.unpack_from('>h', b, o)[0]
        return dict(slot=slot, addr=a, tw=W(0), x=S(2), y=S(4), frame=W(6), w16=S(16), w18=S(18), b20=b[20], b21=b[21],
                    anim=struct.unpack_from('>I', b, 22)[0], fidx=W(26), tick28=b[28], tick29=b[29], f30=W(30),
                    b78=b[78], b79=b[79], b80=b[80], w82=W(82), w84=W(84), b98=b[98], st=b[100], dead=b[101],
                    inv=b[102], hp=b[103], dmg=b[104], raw=b)


def _poke(self, addr, data):
    """Write `data` bytes at `addr` through `w <hex> <8 hex digits>` (longword, big-endian) by read-modify-write on the
    aligned longwords that cover it. A labelled poke: callers say what they set."""
    a0 = addr & ~3
    end = addr + len(data)
    cmds = []
    for a in range(a0, end, 4):
        cur = bytearray(self.mem(a, 4))
        for i in range(4):
            if addr <= a + i < end:
                cur[i] = data[a + i - addr]
        cmds.append(f'w {a:x} {cur.hex()}')
    self.run(*cmds)


Repl.poke = _poke
