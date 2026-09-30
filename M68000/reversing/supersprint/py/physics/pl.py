"""pl.py - shared helpers for the physics agent: RAM from snapshot, A4-relative accessors."""
import os, sys, struct
ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'supersprint', 'py'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sscfg
from repl import Repl
from disassemble import ram_from_snap

A4 = sscfg.A4
OUT = os.path.join(sscfg.WORK, 'agents', 'physics')

def s16(v): return v - 0x10000 if v & 0x8000 else v

class Ram:
    def __init__(s, snap): s.b = ram_from_snap(snap)
    def u8(s, a): return s.b[a]
    def u16(s, a): return (s.b[a] << 8) | s.b[a+1]
    def s16(s, a): return s16(s.u16(a))
    def u32(s, a): return struct.unpack_from('>I', s.b, a)[0]
    def g(s, off): return s.s16(A4 + off)          # signed word global
    def gu(s, off): return s.u16(A4 + off)
    def gl(s, off): return s.u32(A4 + off)
    def arr(s, off, n=4): return [s.s16(A4 + off + 2*i) for i in range(n)]
    def bytes(s, a, n): return s.b[a:a+n]


class Emu(Repl):
    """Repl with stderr merged into stdout (WATCH: lines are returned) and a sentinel-terminated protocol
    (`hits 0 1`), so commands that print their own register dump (bpc/bp/u) do not desynchronise the pipe.
    cmd() returns (lines, regs) where regs is parsed from the LAST register dump seen in the output ({} if none)."""
    def __init__(s, snap):
        env = dict(os.environ, ATARI_NOTRACE='1')
        import subprocess
        s.p = subprocess.Popen(['dotnet', 'exec', sscfg.DLL, 'resume', snap, 'repl', '--disk-a', sscfg.DISK],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, cwd=sscfg.R, env=env, bufsize=1)
        s.p.stdout.readline()   # banner

    def cmd(s, c):
        s.p.stdin.write(c.rstrip('\n') + '\nhits 0 1\n')
        s.p.stdin.flush()
        out = []
        while True:
            line = s.p.stdout.readline()
            if not line:
                raise EOFError('\n'.join(out[-20:]))
            line = line.rstrip('\n')
            if 'hits over 0 step(s)' in line:
                s.p.stdout.readline()
                break
            out.append(line)
        regs = {}
        for l in out:
            if l.startswith('D0:') or l.startswith('PC:') or l.startswith('A0:') or 'D0:' in l:
                pass
        for l in out:
            for m in re.finditer(r'\b([DA][0-7]|PC|USP|SSP):\s*([0-9a-f]{8})', l):
                regs[m.group(1)] = int(m.group(2), 16)
        return out, regs

    def regs(s):
        return s.cmd('r')[1]


import json, re, tempfile, time


class Harness(Emu):
    """Emulator session with helpers for differential tests: stop at a routine entry, snapshot, callcap with a stack arg."""
    def __init__(s, snap):
        s.TMP = os.path.join(OUT, 'tmp', str(os.getpid()))        # per-process scratch: concurrent test runs must not share snapshot files
        os.makedirs(s.TMP, exist_ok=True)
        super().__init__(snap)
        s.n = 0

    def run_to(s, addr, n=1, maxsteps=400000):
        """stop the n-th time PC reaches addr (bpc); returns regs or None when not reached"""
        out, regs = s.cmd('bpc %x %d %d' % (addr, n, maxsteps))
        if any('gave up' in l for l in out):
            return None
        return regs

    def close(s):
        super().close()
        import shutil
        shutil.rmtree(s.TMP, ignore_errors=True)

    def snap_ram(s):
        p = os.path.join(s.TMP, 'st_%d.snap' % (s.n % 4))
        s.n += 1
        s.cmd('snap ' + p)
        return Ram(p)

    def callcap(s, addr, arg=None, arg2=None, steps=400000, presets=('A4=1eb44', 'A5=a304')):
        """callcap a routine (optionally with word args at the stack top), return (mem delta dict, regN dict, outcome)"""
        regs = s.regs()
        sp0 = regs['A7']
        orig = None
        if arg is not None:
            out, _ = s.cmd('m %x 4' % sp0)
            orig = [int(x, 16) for l in out if HEXLINE.match(l.strip()) for x in l.split()][:4]
            a2 = arg2 if arg2 is not None else 0
            s.cmd('w %x %04x%04x' % (sp0, arg & 0xffff, a2 & 0xffff))
        jp = os.path.join(s.TMP, 'cc.json')
        if os.path.exists(jp):
            os.remove(jp)
        out, _ = s.cmd('callcap %x %d %s %s' % (addr, steps, jp, ' '.join(presets)))
        if orig is not None:
            s.cmd('w %x %02x%02x%02x%02x' % (sp0, *orig))
        if not os.path.exists(jp):
            return None, None, ' '.join(out[-3:])
        d = json.load(open(jp))
        return {ad: (a, b) for ad, a, b in d['mem']}, d, d['outcome']


HEXLINE = re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')


def poke_arr(h, off, vals):
    """write four 16-bit words at off(A4) as two longwords (REPL `w` writes longs)"""
    v = [x & 0xffff for x in vals]
    h.cmd('w %x %04x%04x' % (A4 + off, v[0], v[1]))
    h.cmd('w %x %04x%04x' % (A4 + off + 4, v[2], v[3]))
