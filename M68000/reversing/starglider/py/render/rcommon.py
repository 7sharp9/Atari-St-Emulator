"""Shared helpers for the render scripts: sgcommon import, an own-process REPL driver and a hit capturer.

    cap_calls(snap, addr, hits, out_dir, name, ...)  -> list of dicts {hit, regs, snap, json}
Each capture resumes `snap`, runs `bp addr` to the next wanted hit (a `bpc` count from the snapshot), records the entry registers
(REPL `r` output), snapshots the state (RAM read back with gfxview) and runs `callcap addr` on it (delta JSON).
Only `dotnet exec bin/Debug/net8.0/M68000.dll ... repl` is run, with ATARI_NOTRACE=1, one process, in the foreground."""
import os, sys, re, json, subprocess
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'reversing', 'starglider', 'py'))   # promoted location
import sgcommon
from sgcommon import WORK, DLL, ROOT, SNAP_GAME1, SNAP_GAME2, load_ram

def repl(snap, cmds, timeout=900):
    env = dict(os.environ); env['ATARI_NOTRACE'] = '1'
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl'], input='\n'.join(cmds) + '\nq\n', capture_output=True,
                       text=True, cwd=ROOT, env=env, timeout=timeout)
    return p.stdout + '\n' + p.stderr

REGS = re.compile(r'([DA][0-7]):([0-9a-f]{8})')
def parse_regs(txt):
    """last register block in txt -> dict"""
    r = {}
    for m in REGS.finditer(txt):
        r[m.group(1)] = int(m.group(2), 16)
    m = re.search(r'PC: ([0-9a-f]{8})', txt)
    if m: r['PC'] = int(m.group(1), 16)
    return r

def cap_calls(snap, addr, hits, out, name, callcap_steps=400000, maxsteps=3000000, with_snap=True):
    """hits: ascending hit numbers counted from snap. One REPL process per capture batch."""
    os.makedirs(out, exist_ok=True)
    res = []
    cmds = []
    prev = 0
    for h in hits:
        n = h - prev
        prev = h
        cmds.append(f'bpc {addr:x} {n} {maxsteps}')
        cmds.append('r')
        sp = os.path.join(out, f'{name}_{h}.snap')
        if with_snap: cmds.append(f'snap {sp}')
        cmds.append(f'callcap {addr:x} {callcap_steps} {os.path.join(out, name + "_" + str(h) + ".json")}')
        cmds.append(f'echo =====END {h}')
    txt = repl(snap, cmds)
    open(os.path.join(out, name + '.log'), 'w').write(txt)
    return txt

def cc_jobs(snap, jobs, out, name, steps=400000):
    """jobs: list of dict(addr=int, presets={'D1':v..}, pokes=[('w'|'ww'|'wb', addr, val)]).  One REPL process: each job's pokes are applied, the
    routine is callcap'd (the REPL restores the state afterwards, pokes included? -> no: pokes are re-applied per job from `base` below), delta JSON
    written to out/name_<i>.json.  Pokes are undone by a `snap` taken first and re-poking the previous values is NOT used: instead every job lists
    all pokes it needs, and the poked bytes are restored to the snapshot values after the callcap.  Returns list of parsed JSON dicts."""
    os.makedirs(out, exist_ok=True)
    ram = load_ram(snap)
    cmds = []
    files = []
    for i, j in enumerate(jobs):
        undo = []
        for kind, a, v in j.get('pokes', []):
            if kind == 'wb': cmds.append(f'wb {a:x} {v & 0xff:x}'); undo.append(('wb', a, ram[a]))
            elif kind == 'ww':
                cmds.append(f'ww {a:x} {v & 0xffff:x}'); undo += [('wb', a, ram[a]), ('wb', a + 1, ram[a + 1])]
            else:
                cmds.append(f'w {a:x} {v & 0xffffffff:x}'); undo += [('wb', a + k, ram[a + k]) for k in range(4)]
        f = os.path.join(out, f'{name}_{i}.json')
        files.append(f)
        pre = ' '.join(f'{k}={v & 0xffffffff:x}' for k, v in j.get('presets', {}).items())
        cmds.append(f'callcap {j["addr"]:x} {steps} {f} {pre}'.rstrip())
        for kind, a, v in reversed(undo): cmds.append(f'wb {a:x} {v:x}')
    txt = repl(snap, cmds)
    open(os.path.join(out, name + '.log'), 'w').write(txt)
    res = []
    for f in files:
        try: res.append(json.load(open(f)))
        except Exception: res.append(None)
    return res
