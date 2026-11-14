"""Tiny REPL driver: run(snap, cmds) -> stdout lines. Finds the repo root by walking up to tools/rdis.py."""
import os, subprocess, sys
def root():
    p = os.path.abspath(os.path.dirname(__file__))
    while not os.path.exists(os.path.join(p, 'tools', 'rdis.py')):
        q = os.path.dirname(p)
        if q == p: raise SystemExit('repo root not found')
        p = q
    return p
def run(snap, cmds, extra_env=None, disk=None):
    r = root()
    env = dict(os.environ, ATARI_NOTRACE='1'); env.update(extra_env or {})
    args = ['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll']
    if disk: args += ['--disk-a', disk]
    args += ['resume', snap, 'repl']
    out = subprocess.run(args, input='\n'.join(cmds) + '\nq\n', capture_output=True, text=True, cwd=r, env=env)
    return out.stdout.splitlines() + out.stderr.splitlines()
def mem(lines):
    """return bytes lists for each 'm' output line (hex byte rows)"""
    rows = []
    for l in lines:
        t = l.split()
        if t and all(len(x) == 2 and all(c in '0123456789abcdef' for c in x) for x in t):
            rows.append(bytes(int(x, 16) for x in t))
    return rows
