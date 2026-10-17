"""uc.py - shared helpers for the `unused` agent (repo root via sscfg/M68000_ROOT; untracked output under scratchpad/supersprint/agents/unused/)."""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
def _find_root():
    d = _HERE
    while not os.path.exists(os.path.join(d, 'reversing', 'supersprint', 'py', 'sscfg.py')):
        nd = os.path.dirname(d)
        if nd == d: raise SystemExit('cannot find M68000/ (set M68000_ROOT)')
        d = nd
    return d
_ROOT = os.environ.get('M68000_ROOT') or _find_root()
os.environ.setdefault('M68000_ROOT', _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'reversing', 'supersprint', 'py'))
sys.path.insert(0, os.path.join(_ROOT, 'reversing', 'supersprint', 'py', 'tracks'))
import sscfg
from repl import Repl
from tkcommon import Repl2
AGENT = os.path.join(sscfg.WORK, 'agents', 'unused')
SNAP = os.path.join(AGENT, 'snap'); TMP = os.path.join(AGENT, 'tmp'); DATA = os.path.join(AGENT, 'data'); PNG = os.path.join(AGENT, 'png')
for d in (SNAP, TMP, DATA, PNG): os.makedirs(d, exist_ok=True)
A4 = sscfg.A4
BUF = 0x28e00            # SUPER.DAT load address; runtime address = BUF + file offset
# the seven candidate 4 KB blocks (file offsets)
BLOCKS = [0x3000, 0xf000, 0x1b000, 0x23000, 0x24000, 0x25000, 0x2b000]

def snapath(n):
    """snapshot name -> path: as given, else agents/unused/snap/, else the work dir (ss_*.snap), else another agent's snap dir"""
    import glob
    for c in (n, os.path.join(SNAP, n), os.path.join(sscfg.WORK, n)):
        if os.path.exists(c): return c
    g = glob.glob(os.path.join(sscfg.WORK, 'agents', '*', 'snap*', n)) + glob.glob(os.path.join(sscfg.WORK, 'agents', '*', 'data', n))
    if g: return g[0]
    raise FileNotFoundError(n)

class ReplErr(Repl):
    """Repl that keeps the whole stderr (a `watch` reports its hits there) in a file under agents/unused/tmp/."""
    def __init__(s, snap):
        import subprocess, tempfile
        env = dict(os.environ, ATARI_NOTRACE='1')
        s.errf = tempfile.NamedTemporaryFile('w+', dir=TMP, suffix='.err', delete=False)
        s.p = subprocess.Popen(['dotnet', 'exec', sscfg.DLL, 'resume', snap, 'repl', '--disk-a', sscfg.DISK],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=s.errf, text=True, cwd=sscfg.R, env=env, bufsize=1)
    def err(s):
        s.errf.flush(); s.errf.seek(0); t = s.errf.read(); s.errf.seek(0); s.errf.truncate(); return t
    def close(s):
        super().close()
        try: s.errf.close(); os.unlink(s.errf.name)
        except Exception: pass
