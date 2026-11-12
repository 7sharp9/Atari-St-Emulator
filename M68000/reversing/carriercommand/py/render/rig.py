"""rig.py - drive the emulator REPL from python: run commands from c_s30.snap, parse callcap blocks.
Run from M68000/ (cwd). Always ATARI_NOTRACE=1."""
import pathlib as _pl, sys as _sys; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent)); _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from ccpaths import *
import subprocess, os, re, struct
R = str(ROOT)
W = str(WORK)
SNAP = str(ANCHOR)
RAM = ram(ANCHOR)

def repl(cmds, snap=SNAP):
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', str(DLL), 'resume', snap, 'repl'],
                       input='\n'.join(cmds) + '\nq\n', capture_output=True, text=True, cwd=R, env=env)
    return p.stdout + p.stderr

def parse_callcaps(out):
    """list of dict(addr, regs{name:(old,new)}, mem{addr:(old,new)})"""
    res = []; cur = None
    for line in out.splitlines():
        m = re.match(r'--- callcap \$([0-9a-f]+): (\w+)', line)
        if m:
            cur = dict(addr=int(m.group(1), 16), status=m.group(2), regs={}, mem={}); res.append(cur); continue
        if cur is None: continue
        if line.startswith('regdelta'):
            for n, o, nw in re.findall(r'([DA]\d) \$([0-9a-f]+)->\$([0-9a-f]+)', line):
                cur['regs'][n] = (int(o, 16), int(nw, 16))
        m = re.match(r'mem \$([0-9a-f]+) \$([0-9a-f]+)->\$([0-9a-f]+)', line)
        if m: cur['mem'][int(m.group(1), 16)] = (int(m.group(2), 16), int(m.group(3), 16))
    return res

def apply(base, mem):
    r = bytearray(base)
    for a, (o, n) in mem.items(): r[a] = n
    return r
