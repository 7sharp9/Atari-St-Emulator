"""Batch REPL helper for the frontend scripts: run one emulator process over a command list and return its output.
`run(snap, cmds)` resumes <snap> (disk remounted from the .prov.json sidecar), feeds the commands on stdin, appends
`q`, always with ATARI_NOTRACE=1, and returns stdout+stderr text. `key(make)` returns the kbd/s/kbd lines for a
tap long enough for the game's poll (hold >= 100,000 steps). `render(snap, png)` runs tools/snap_render.py."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
d = HERE
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    p = os.path.dirname(d)
    if p == d:
        raise SystemExit('repo root not found')
    d = p
sys.path.insert(0, os.path.join(d, 'reversing', 'starglider', 'py'))
import sgcommon

def run(snap, cmds, env=None, disk=None):
    e = dict(os.environ)
    e['ATARI_NOTRACE'] = '1'
    if env:
        e.update(env)
    args = ['dotnet', 'exec', sgcommon.DLL] + (['--disk-a', disk] if disk else []) + ['resume', snap, 'repl']
    p = subprocess.run(args, input='\n'.join(list(cmds) + ['q']) + '\n', capture_output=True, text=True, cwd=sgcommon.ROOT, env=e)
    return p.stdout + p.stderr

def key(make, hold=150000, after=0):
    brk = '%x' % (int(make, 16) | 0x80)
    out = ['kbd ' + make, 's %d' % hold, 'kbd ' + brk]
    if after:
        out.append('s %d' % after)
    return out

def render(snap, png):
    subprocess.run(['uv', 'run', 'python', os.path.join(sgcommon.ROOT, 'tools', 'snap_render.py'), snap, png],
                   cwd=sgcommon.ROOT, check=True, capture_output=True)
