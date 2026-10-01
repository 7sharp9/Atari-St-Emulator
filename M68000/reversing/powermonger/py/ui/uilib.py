"""Helpers for the pm140 `ui` area: run REPL callcaps from a snapshot and render the panel grid they build.
ROOT = M68000/ (this file lives in scratchpad/pm140/agents/ui/ and, once committed, in reversing/powermonger/py/ui/)."""
import os, re, subprocess
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
DLL = ROOT / 'bin/Debug/net8.0/M68000.dll'
DISK = ROOT / 'scratchpad/powermonger.st'
OBJ, REC = 0x51b66, 50
GROUPS, GSTRIDE = 0x51538, 0x13c

def ram_of(snap):
    p = Path(snap).with_suffix('.ram')
    if not p.exists():
        import sys; sys.path.insert(0, str(ROOT / 'tools'))
        from pm_export import ram_from_snap
        p.write_bytes(ram_from_snap(Path(snap)))
    return p.read_bytes()

def repl(snap, cmds, timeout=600):
    env = dict(os.environ, ATARI_NOTRACE='1')
    r = subprocess.run(['dotnet', 'exec', str(DLL), 'resume', str(snap), 'repl', '--disk-a', str(DISK)],
                       input='\n'.join(cmds) + '\nq\n', capture_output=True, text=True, env=env, cwd=ROOT, timeout=timeout)
    return r.stdout + r.stderr

def parse_callcaps(out):
    """-> list of dict(ok, steps_hdr, regs{name:(before,after)}, mem{addr:(before,after)})"""
    res = []; cur = None
    for line in out.splitlines():
        if line.startswith('--- callcap'):
            cur = dict(hdr=line, returned='returned' in line, regs={}, mem={}); res.append(cur)
        elif cur is not None and line.startswith('regdelta'):
            for m in re.finditer(r'([DA]\d) \$([0-9a-f]+)->\$([0-9a-f]+)', line):
                cur['regs'][m.group(1)] = (int(m.group(2), 16), int(m.group(3), 16))
        elif cur is not None and line.startswith('mem '):
            m = re.match(r'mem \$([0-9a-f]+) \$([0-9a-f]+)->\$([0-9a-f]+)', line)
            if m: cur['mem'][int(m.group(1), 16)] = (int(m.group(2), 16), int(m.group(3), 16))
    return res

def regs_args(regs):
    return ' '.join(f'{k}={v:x}' for k, v in regs.items())

def after_ram(base, cc):
    b = bytearray(base)
    for a, (x, y) in cc['mem'].items(): b[a] = y
    return b

def panel_text(base, cc):
    """The text grid of the panel the callcap opened: first slot whose descriptor word0 changed."""
    after = after_ram(base, cc)
    for k in range(4):
        d = 0x7a36 + 8 * k
        if (after[d] << 8 | after[d + 1]) != (base[d] << 8 | base[d + 1]) or (k == 0 and cc['mem'].get(d)):
            pass
    # grid base for slot k = $7a36 + $176 + k*$320 (7b10); pick the slot with the most changed bytes
    best = None
    for k in range(4):
        g = 0x7bac + 0x320 * k
        n = sum(1 for a in cc['mem'] if g <= a < g + 0x320)
        if best is None or n > best[0]: best = (n, g)
    if best[0] == 0: return None
    g = best[1]; w = after[g] * 4; h = after[g + 1]
    rows = []
    for r in range(h):
        row = after[g + 2 + r * w: g + 2 + (r + 1) * w]
        rows.append(''.join(chr(c) if 32 <= c < 127 else '.' for c in row))
    return rows
