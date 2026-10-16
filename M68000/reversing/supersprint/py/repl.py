"""repl.py - drive the emulator REPL from Python (one process, request/response).

    from repl import Repl
    r = Repl(sscfg.SNAP_RACE)
    out, regs = r.cmd('s 100000')      # any REPL command(s); returns (lines, registers)
    data = r.mem(0x1eb44 - 3690, 8)    # bytes
    r.close()

ATARI_NOTRACE=1 is set for the child: without it every step is logged (GBs).
"""
import collections
import os
import re
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sscfg

HEX = re.compile(r'^([0-9a-f]{2} )*[0-9a-f]{2}$')


class Repl:
    def __init__(s, snap):
        env = dict(os.environ, ATARI_NOTRACE='1')
        s.p = subprocess.Popen(
            ['dotnet', 'exec', sscfg.DLL, 'resume', snap, 'repl', '--disk-a', sscfg.DISK],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=sscfg.R, env=env, bufsize=1)
        # stderr is drained (a `watch` can write a lot) and its tail kept for the error on EOF
        s._errtail = collections.deque(maxlen=50)
        s._t = threading.Thread(target=lambda: [s._errtail.append(l.rstrip()) for l in s.p.stderr], daemon=True)
        s._t.start()

    def _closed(s, out):
        """message for a REPL that ended mid-command: exit code plus the stderr tail (a `REPL error:` line names
        the bad command). Subclasses that send stderr elsewhere (secrets/ssh.py's file) get the file's tail."""
        try:
            rc = s.p.wait(timeout=10)
        except Exception:
            rc = None
        if hasattr(s, '_t'):
            s._t.join(timeout=5)
            tail = '\n'.join(list(s._errtail)[-20:])
        elif hasattr(s, 'errf'):
            s.errf.flush(); s.errf.seek(0, 2); end = s.errf.tell(); s.errf.seek(max(0, end - 2000))
            tail = s.errf.read()
        else:
            tail = ''
        return 'repl closed (exit %s): %s\n%s' % (rc, tail, '\n'.join(out[-20:]))

    def cmd(s, c):
        """send command(s) followed by 'r'; return (output lines, registers dict)"""
        s.p.stdin.write(c.rstrip('\n') + '\nr\n')
        s.p.stdin.flush()
        out = []
        while True:
            line = s.p.stdout.readline()
            if not line:
                raise EOFError(s._closed(out))
            line = line.rstrip('\n')
            out.append(line)
            if line.startswith('PC: '):
                s.p.stdout.readline()
                break
        regs = {}
        for l in out:
            for m in re.finditer(r'\b([DA][0-7]|PC|USP|SSP):\s*([0-9a-f]{8})', l):
                regs[m.group(1)] = int(m.group(2), 16)
        return out, regs

    def mem(s, a, n):
        out, _ = s.cmd('m %x %d' % (a, n))
        bs = bytearray()
        for l in out:
            if HEX.match(l.strip()):
                bs += bytes(int(x, 16) for x in l.split())
        assert len(bs) == n, (len(bs), n)
        return bytes(bs)

    def close(s):
        try:
            s.p.stdin.write('q\n')
            s.p.stdin.flush()
        except Exception:
            pass
        s.p.wait()
