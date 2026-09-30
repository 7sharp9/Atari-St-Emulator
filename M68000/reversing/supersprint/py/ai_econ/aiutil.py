"""aiutil.py - shared helpers for the ai_econ scripts.

  from aiutil import *      # paths via sscfg, Repl2 (sentinel-synchronised REPL, stderr merged so `watch` is seen)

Repl2.cmd(c) sends c, then `m 0 4` (address 0 is `60 1e 01 00`, a ROM-mirror constant) and `r`; it reads
until that sentinel line and the following register dump, so commands that print their own registers
(bp/bpc/u) or that print nothing do not desynchronise the pipe (repl.Repl.cmd stops at the first `PC:`).
"""
import os, re, struct, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sscfg

AGENT = os.path.join(sscfg.WORK, 'agents', 'ai_econ')      # untracked data, snapshots, logs
A4 = sscfg.A4
DATA = os.path.join(AGENT, 'data')
os.makedirs(DATA, exist_ok=True)
SENT = '60 1e 01 00'
HEX = re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')


def sx(v, bits=16):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


class Repl2:
    def __init__(s, snap, disk=True):
        env = dict(os.environ, ATARI_NOTRACE='1')
        args = ['dotnet', 'exec', sscfg.DLL, 'resume', snap, 'repl']
        if disk:
            args += ['--disk-a', sscfg.DISK]
        s.p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, cwd=sscfg.R, env=env, bufsize=1)
        s.cmd('')

    def cmd(s, c):
        """returns (lines before the sentinel, registers dict from the trailing `r`)"""
        s.p.stdin.write((c.rstrip('\n') + '\n' if c else '') + 'm 0 4\nr\n')
        s.p.stdin.flush()
        out = []
        while True:
            line = s.p.stdout.readline()
            if not line:
                raise EOFError('\n'.join(out[-20:]))
            line = line.rstrip('\r\n')
            if line.strip() == SENT:
                break
            out.append(line)
        regs = {}
        while True:
            line = s.p.stdout.readline()
            if not line:
                raise EOFError
            for m in re.finditer(r'\b([DA][0-7]|PC|USP|SSP):\s*([0-9a-f]{8})', line):
                regs[m.group(1)] = int(m.group(2), 16)
            if line.startswith('PC: '):
                s.p.stdout.readline()
                break
        return out, regs

    def mem(s, a, n):
        out, _ = s.cmd('m %x %d' % (a, n))
        bs = bytearray()
        for l in out:
            if HEX.match(l.strip()):
                bs += bytes(int(x, 16) for x in l.split())
        assert len(bs) == n, (len(bs), n, out[-3:])
        return bytes(bs)

    def words(s, addr, n):
        return list(struct.unpack('>%dh' % n, s.mem(addr, 2 * n)))

    def a4w(s, off, n=4):
        return s.words(A4 + off, n)

    def close(s):
        try:
            s.p.stdin.write('q\n')
            s.p.stdin.flush()
        except Exception:
            pass
        try:
            s.p.wait(timeout=20)
        except Exception:
            s.p.kill()


def setwords(r, pokes):
    """pokes {addr: value}: write 16-bit words by read-modify-write of the containing aligned longwords
    (REPL `w` writes a longword; poking a bare word would clobber its neighbour)."""
    las = sorted({ad & ~3 for ad in pokes} | {(ad + 1) & ~3 for ad in pokes})
    img = {la: bytearray(r.mem(la, 4)) for la in las}
    for ad, v in pokes.items():
        v &= 0xFFFF
        for i, byte in ((0, v >> 8), (1, v & 0xFF)):
            a = ad + i
            img[a & ~3][a & 3] = byte
    for la, b in img.items():
        r.cmd('w %x %s' % (la, bytes(b).hex()))
