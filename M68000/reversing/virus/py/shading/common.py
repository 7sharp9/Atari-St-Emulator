"""Shared helpers for the shading scripts: paths (vcommon), the work directory scratchpad/virus/shading/ (or $VIRUS_WORK/shading),
a REPL runner and the callcap-delta applier.  Imported by path, so the scripts run from any cwd."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
from vcommon import ROOT, WORK, work, load_ram

SW = work('shading')
DLL = os.path.join(ROOT, 'bin', 'Debug', 'net8.0', 'M68000.dll')

def repl(snap, lines, out=None):
    """Run `resume <snap> repl` with the REPL lines on stdin (a final `q` is added); return stdout+stderr text."""
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl'], input='\n'.join(lines + ['q']) + '\n',
                       capture_output=True, text=True, cwd=ROOT)
    text = p.stdout + p.stderr
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'w').write(text)
    return text

def apply_delta(base, js):
    """RAM after a `callcap` delta file (list of [addr, before, after]) on top of the snapshot RAM `base`."""
    r = bytearray(base)
    for a, _b, af in json.load(open(js))['mem']:
        r[a] = af
    return bytes(r)

def gate_dir():
    d = os.path.join(SW, 'gate'); os.makedirs(d, exist_ok=True); return d
