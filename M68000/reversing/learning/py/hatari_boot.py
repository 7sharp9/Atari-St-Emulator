"""hatari_boot.py <ours.json> [outdir] [--snap <S1b.snap>] [--ticks N] [--control]: Virus's first demo flight from a COLD BOOT of
the disk in real Hatari, compared tick by tick with this emulator's flight (the ours.json a hatari_game.py run wrote).

hatari_game.py starts Hatari from this emulator's snapshot, so the boot, the disk loader, the crack's menus and the
keyboard path ran only here.  This script lets Hatari do all of that itself:

1. Hatari (TOS 1.00 UK, ST, 1 MB, headless, fast-forward) boots a copy of scratchpad/virus/aha.st.
2. Keys go in over Hatari's control socket, as reversing/virus/drive.sh sends them here: F1 at the MULTI2 menu until
   the Union trainer runs, then N five times and Return until Virus itself starts (its RNG seed at $2300a executes).
   No key after that: the title and the "Press R" page time out into the demo.
3. As demo/capture.sh does here, the game start is the first $230c0 after the first enemy spawn $20e74.  There Hatari
   saves all 1 MB of RAM (start.bin) and its registers, then logs hatari_game.py's RANGES at every Ship_Tick ($255c2)
   arrival and quits at arrival N (default: as many as ours.json holds).
4. Compare arrival k with arrival k (hatari_game.compare), and with --snap report the RAM bytes that differ between
   Hatari at the game start and this emulator's snapshot of the same moment.

Key timing is wall-clock against a fast-forwarded machine, so the frame each key lands on differs run to run; equality
then also says the flight does not depend on it.  --control has Hatari change one pool byte ($31d57) at the game start
and must report arrival 0 different.  Output: <outdir> (default scratchpad/learning/hatari_boot/run/):
hatari.log, start.bin, the debugger scripts.  Exit status 0 when every arrival agrees, 1 when one differs, 2 when the
drive failed.  Socket and pty plumbing as in reversing/populous/py/systems/hatari_edges.py.
"""
import json, os, pty, re, shutil, socket, subprocess, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hatari_callcap import ROOT, HATARI, TOS, RAM_OFF, RAM_LEN
from hatari_game import RANGES, parse_log, compare

TICK = 0x255c2
F1, N, RETURN = 59, 49, 28          # ST scancodes $3b, $31, $1c, decimal for `hatari-event keydown`
TRAINER_PC = 0x63efa                # where drive.sh's g_trainer.snap stands: the Union trainer is running


def run(out, n, ctl=None):
    p = lambda f: os.path.join(out, f)
    disk = p('aha.st'); shutil.copy(os.path.join(ROOT, 'scratchpad', 'virus', 'aha.st'), disk)   # Hatari may write to it
    for f in ('hatari.log', 'start.bin'):
        if os.path.exists(p(f)): os.remove(p(f))
    open(p('m1.dbg'), 'w').write("echo @M1 'VBL'\n")
    open(p('m2.dbg'), 'w').write("echo @M2 'VBL'\n")
    open(p('spawn.dbg'), 'w').write("echo @P 'VBL'\nb pc = $230c0 :once :trace :file %s\n" % p('start.dbg'))
    open(p('start.dbg'), 'w').write("echo @S 'VBL'\nr\nsavebin %s $0 $100000\n" % p('start.bin') + ('w $31d57 $%02x\n' % ctl if ctl is not None else '') +
                                    'b pc = $%x :trace :quiet :file %s\n' % (TICK, p('tick.dbg')) +
                                    'b pc = $%x :%d :once :trace :file %s\n' % (TICK, n, p('quit.dbg')))
    open(p('tick.dbg'), 'w').write("echo @T 'VBL'\n" + ''.join('m $%x-$%x\n' % (a, a + ln) for _, a, ln in RANGES))
    open(p('quit.dbg'), 'w').write('quit\n')
    open(p('init.dbg'), 'w').write(
        'b pc = $%x :once :trace :file %s\n' % (TRAINER_PC, p('m1.dbg')) +
        'b pc = $2300a && ($2300a).l = $23fc1234 :once :trace :file %s\n' % p('m2.dbg') +
        'b pc = $20e74 && ($230c0).w = $4239 :once :trace :file %s\n' % p('spawn.dbg'))

    sock_path = '/tmp/hvb-%d.sock' % os.getpid()        # AF_UNIX path length limit: keep it short
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); srv.bind(sock_path); srv.listen(1)
    log = open(p('hatari.log'), 'w')
    mfd, sfd = pty.openpty()                            # a pty, or Hatari block-buffers the debugger output
    seen = {'txt': ''}                                  # everything before the tick records start (small)

    def pump():
        while True:
            try: d = os.read(mfd, 1 << 16)
            except OSError: return
            if not d: return
            t = d.decode(errors='replace').replace('\r', '')
            log.write(t); log.flush()
            if '@T ' not in seen['txt']: seen['txt'] += t
    threading.Thread(target=pump, daemon=True).start()
    cmd = [HATARI, '--configfile', '/dev/null', '--machine', 'st', '--memsize', '1', '--tos', TOS, '--disk-a', disk,
           '--fast-forward', 'on', '--sound', 'off', '--confirm-quit', 'off', '--control-socket', sock_path,
           '--parse', p('init.dbg')]
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=sfd, stderr=sfd, cwd=out,
                            env=dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy'))
    srv.settimeout(30); conn, _ = srv.accept()

    def send(c, pause=0.2):
        conn.sendall((c + '\n').encode()); time.sleep(pause)
    def vbl():
        mark = '@V%f' % time.time()
        send("hatari-debug echo %s 'VBL'" % mark, 0.3)
        m = re.findall(re.escape(mark) + r' \$([0-9a-f]+)', seen['txt'])
        return int(m[-1], 16) if m else -1
    def key(code):
        send('hatari-event keydown %d' % code, 0.3); send('hatari-event keyup %d' % code, 0.5)
    def until(mark, press, limit, what):
        t = time.time()
        while mark not in seen['txt']:
            if time.time() - t > limit or proc.poll() is not None: raise RuntimeError(what + ' not reached')
            press()
        m = re.search(re.escape(mark) + r' \$([0-9a-f]+)', seen['txt'])
        print('%s at Hatari VBL %d' % (what, int(m.group(1), 16)), flush=True)

    ok = False
    try:
        time.sleep(2)
        def f1():
            if vbl() > 300: key(F1)
            time.sleep(1)
        until('@M1', f1, 180, 'trainer ($%x)' % TRAINER_PC)
        def answers():
            time.sleep(2)
            for _ in range(5):
                if '@M2' in seen['txt']: return
                key(N)
            time.sleep(1)
            if '@M2' not in seen['txt']: key(RETURN)
        until('@M2', answers, 300, 'Virus start ($2300a)')
        until('@P', lambda: time.sleep(1), 600, 'first spawn ($20e74)')
        until('@S', lambda: time.sleep(0.5), 120, 'game start ($230c0)')
        t = time.time()
        while proc.poll() is None:                      # quit.dbg ends Hatari; a dump's ASCII column can hold any marker text
            if time.time() - t > 1800: raise RuntimeError('flight not finished in 30 minutes')
            time.sleep(2)
        ok = True
    except RuntimeError as e:
        print('drive failed: %s (Hatari VBL %d)' % (e, vbl() if proc.poll() is None else -1))
    finally:
        try: send('hatari-shortcut quit')
        except OSError: pass
        time.sleep(1); proc.kill(); os.unlink(sock_path); time.sleep(0.5); log.close()
    return ok


def ram_diff(out, snap):
    """bytes that differ between Hatari's RAM at the game start and this emulator's snapshot of the same moment"""
    h = open(os.path.join(out, 'start.bin'), 'rb').read()
    o = open(snap, 'rb').read()[RAM_OFF:RAM_OFF + RAM_LEN]
    if len(h) != RAM_LEN: print('start.bin is %d bytes, not %d' % (len(h), RAM_LEN)); return
    bad = [i for i in range(8, RAM_LEN) if h[i] != o[i]]
    runs = []
    for i in bad:
        if runs and i - runs[-1][1] <= 16: runs[-1][1] = i
        else: runs.append([i, i])
    in_ranges = sum(1 for i in bad if any(a <= i < a + ln for _, a, ln in RANGES))
    print('RAM at the game start, $8-$fffff: %d of %d bytes differ from %s, in %d runs (gaps up to 16 joined); %d inside the logged ranges'
          % (len(bad), RAM_LEN - 8, os.path.basename(snap), len(runs), in_ranges))
    for a, b in sorted(runs, key=lambda r: r[0] - r[1])[:25]:
        k = sum(1 for i in bad if a <= i <= b)
        print('  $%05x-$%05x  %6d differ of %6d' % (a, b, k, b - a + 1))


def main():
    a = sys.argv[1:]
    snap = None; n = None; ctl = '--control' in a
    a = [x for x in a if x != '--control']
    if '--snap' in a: k = a.index('--snap'); snap = os.path.abspath(a[k + 1]); a = a[:k] + a[k + 2:]
    if '--ticks' in a: k = a.index('--ticks'); n = int(a[k + 1]); a = a[:k] + a[k + 2:]
    if not a: sys.exit(__doc__)
    o = json.load(open(a[0]))
    if n: o = o[:n]
    n = len(o)
    out = os.path.abspath(a[1] if len(a) > 1 else os.path.join(ROOT, 'scratchpad', 'learning', 'hatari_boot', 'run'))
    os.makedirs(out, exist_ok=True)
    if not run(out, n, int(o[0]['pool'][6:8], 16) ^ 0xff if ctl else None): sys.exit(2)
    if snap: ram_diff(out, snap)
    h, vbls = parse_log(open(os.path.join(out, 'hatari.log'), errors='replace').read())
    sys.exit(0 if compare(o, h, vbls, TICK, n) else 1)


if __name__ == '__main__':
    main()
