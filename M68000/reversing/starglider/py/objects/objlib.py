"""Shared helpers for the objects gates: REPL runner and callcap parser, a byte-RAM with big-endian accessors.
Scripts walk up to the directory holding tools/rdis.py, then import reversing/starglider/py/sgcommon.py."""
import os, sys, struct, subprocess, re

def _root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            raise SystemExit('repo root not found')
        d = p
    return d
ROOT = _root()
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'starglider', 'py'))
import sgcommon as sg

A6 = sg.GLOBALS

class Mem:
    """1 MB RAM, big-endian accessors, byte log of writes."""
    def __init__(self, ram):
        self.b = bytearray(ram)
    def copy(self):
        return Mem(self.b)
    def rb(self, a): return self.b[a & 0xffffff]
    def rw(self, a): a &= 0xffffff; return (self.b[a] << 8) | self.b[a + 1]
    def rws(self, a):
        v = self.rw(a); return v - 0x10000 if v & 0x8000 else v
    def rl(self, a): a &= 0xffffff; return int.from_bytes(self.b[a:a + 4], 'big')
    def wb(self, a, v): self.b[a & 0xffffff] = v & 0xff
    def ww(self, a, v):
        a &= 0xffffff; self.b[a] = (v >> 8) & 0xff; self.b[a + 1] = v & 0xff
    def wl(self, a, v):
        a &= 0xffffff; self.b[a:a + 4] = (v & 0xffffffff).to_bytes(4, 'big')

def repl_run(snap, lines, env=None, dll=None):
    """Feed lines to a REPL resumed from snap; return stdout as text."""
    e = dict(os.environ); e['ATARI_NOTRACE'] = '1'
    if env: e.update(env)
    p = subprocess.run(['dotnet', 'exec', dll or sg.DLL, 'resume', snap, 'repl'], input='\n'.join(lines) + '\nq\n',
                       capture_output=True, text=True, cwd=ROOT, env=e)
    return p.stdout

def parse_callcaps(out):
    """Return a list of dicts {status, regs:{name:(old,new)}, mem:{addr:(old,new)}} in output order."""
    res = []; cur = None
    for ln in out.split('\n'):
        m = re.match(r'--- callcap \$([0-9a-f]+): (.*?), trace hash', ln)
        if m:
            cur = {'addr': int(m.group(1), 16), 'status': m.group(2), 'regs': {}, 'mem': {}}
            res.append(cur); continue
        if cur is None: continue
        if ln.startswith('regdelta'):
            for r in re.finditer(r'(\w+) \$([0-9a-f]+)->\$([0-9a-f]+)', ln):
                cur['regs'][r.group(1)] = (int(r.group(2), 16), int(r.group(3), 16))
        elif ln.startswith('mem '):
            m = re.match(r'mem \$([0-9a-f]+) \$([0-9a-f]+)->\$([0-9a-f]+)', ln)
            if m: cur['mem'][int(m.group(1), 16)] = (int(m.group(2), 16), int(m.group(3), 16))
    return res

def poke_lines(P):
    """REPL poke lines for a {addr: byte} dict: aligned longs where four bytes are present, else bytes"""
    lines = []; done = set()
    for a in sorted(P):
        if a in done: continue
        if a % 4 == 0 and all((a + i) in P for i in range(4)):
            lines.append('w %x %x' % (a, int.from_bytes(bytes(P[a + i] for i in range(4)), 'big'))); done.update(range(a, a + 4))
        else:
            lines.append('wb %x %x' % (a, P[a])); done.add(a)
    return lines
