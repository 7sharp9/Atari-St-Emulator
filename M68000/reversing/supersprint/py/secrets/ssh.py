"""ssh.py - helper on top of repl.Repl for the secrets agent: stderr capture (for `watch`), key/joystick injection."""
import os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import sscfg
import repl as _repl

AGENT = os.path.join(sscfg.WORK, 'agents', 'secrets')      # untracked snapshots (snap/) and logs (tmp/)
TMP = os.path.join(AGENT, 'tmp')
os.makedirs(TMP, exist_ok=True)


class R(_repl.Repl):
    def __init__(s, snap, disk=None):
        env = dict(os.environ, ATARI_NOTRACE='1')
        s.errf = tempfile.NamedTemporaryFile('w+', dir=TMP, suffix='.err', delete=False)
        s.p = subprocess.Popen(
            ['dotnet', 'exec', sscfg.DLL, 'resume', snap, 'repl', '--disk-a', disk or sscfg.DISK],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=s.errf,
            text=True, cwd=sscfg.R, env=env, bufsize=1)

    def err(s):
        s.errf.flush()
        s.errf.seek(0)
        t = s.errf.read()
        s.errf.seek(0)
        s.errf.truncate()
        return t

    def a4(s):
        return sscfg.A4

    def w8(s, addr):
        return s.mem(addr, 1)[0]

    def w16(s, addr):
        b = s.mem(addr, 2)
        return (b[0] << 8) | b[1]

    def w32(s, addr):
        b = s.mem(addr, 4)
        return int.from_bytes(b, 'big')

    def g8(s, off):
        return s.w8(sscfg.A4 + off)

    def g16(s, off):
        return s.w16(sscfg.A4 + off)

    def g32(s, off):
        return s.w32(sscfg.A4 + off)

    def close(s):
        super().close()
        try:
            s.errf.close(); os.unlink(s.errf.name)
        except Exception:
            pass
