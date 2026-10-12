"""hatari_edges.py: the swamp monster's entry edge (the uninitialised word at -146(A6) of $db4c, systems.md 1.3)
measured on real Hatari, as a check on this emulator's interrupt timing.

  python hatari_edges.py run [nframes] [tag] [watch-hex]
  python hatari_edges.py parse <hatari.log> [csv]
  python hatari_edges.py writers <hatari.log>

run: cold-boot $POP_WORK/pop_auto.st in headless Hatari (TOS 1.00 UK, ST, 1 MB; HATARI = the binary, built per
DEVELOPING.md "macOS"), drive it to a one-player CONQUEST game the way ../../drive.txt does (SPACE at the banner,
CONQUEST at pointer (250,176), START GAME at (85,176)), then log at every $db4c entry ($db50, after the link) and at
its unlk ($ef48): A6, A7, VBL, the word at A6-146 and the frame counter $3c4c8. Output: $POP_WORK/hatari_edges/run[_tag]/
(hatari.log, screenshots title/briefing/game/end). Tag `irq` also logs entry to $16d32, $fc0644, $fc2f2c, $fc4c7a;
tag `watch` (or a watch-hex address) logs every change of that word with PC, A7, VBL, SR.
parse: pair each entry record with its unlk record, tally the values, optional CSV.
writers: for a watch run, classify each change as inside $db4c or between calls and tally the PCs.
The same measurement on this emulator: swamp208.py edges <snap> <n>.

Hatari interface, from its source: control.c `hatari-event mousemove dx dy` is relative and ikbd.c
IKBD_UpdateInternalMousePosition clamps the absolute cursor to 0..MaxX/MaxY, so the pointer is pinned with a large
negative move, then moved to the target; `leftdown`/`leftup` click. debug/breakcond.c: `:trace` (no stop), `:quiet`,
`:file <f>` (commands run on each hit; single-quoted expressions expanded by debugui.c). Socket, pty and dummy-SDL
plumbing as in ../../../cadaver/py/secrets/hatari_xp_check.py.

With only the $db50 and $ef48 breakpoints set, Hatari reports the word changed inside the call on 468/1161 and 198/498
calls; with any third trace breakpoint it does not (0/321, 16/450, 0/291), and no handler's A7 reaches $3f418 inside
the call. Read as a debugger artefact (inferred, mechanism not found): compare entry values.
"""
import collections, glob, os, pty, re, shutil, socket, subprocess, sys, threading, time

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from popcfg import R as ROOT, WORK, DISK as SRC_DISK

HATARI = os.environ.get('HATARI', 'hatari')
TOS = os.path.join(ROOT, 'TOS100UK.IMG')


def run(nfr, tag, waddr):
    out = os.path.join(WORK, 'hatari_edges', 'run_' + tag if tag else 'run'); os.makedirs(out, exist_ok=True)
    disk = os.path.join(WORK, 'hatari_edges', 'pop_auto.st')   # Hatari may write to the image: run a copy
    if not os.path.exists(disk): shutil.copy(SRC_DISK, disk)
    irq, watch = tag == 'irq', waddr is not None
    open(os.path.join(out, 'irq.dbg'), 'w').write("echo @I 'pc' 'a7' 'VBL' 'sr'\nm $3f418-$3f41a\n")
    open(os.path.join(out, 'entry.dbg'), 'w').write("echo @E 'a6' 'a7' 'VBL'\nm 'a6-146'-'a6-144'\nm $3c4c8-$3c4ca\n")
    open(os.path.join(out, 'watch.dbg'), 'w').write("echo @W 'pc' 'a7' 'VBL' 'sr'\nm $3f418-$3f41a\n" if watch else '')
    open(os.path.join(out, 'unlk.dbg'), 'w').write("echo @U 'a6' 'a7' 'VBL'\nm 'a6-146'-'a6-144'\n")

    sock_path = '/tmp/hpe-%d.sock' % os.getpid()   # AF_UNIX path length limit: keep it short
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); srv.bind(sock_path); srv.listen(1)
    logp = os.path.join(out, 'hatari.log'); log = open(logp, 'w')
    mfd, sfd = pty.openpty()   # a pty, or Hatari block-buffers the debugger output

    def pump():
        while True:
            try: d = os.read(mfd, 65536)
            except OSError: return
            if not d: return
            log.write(d.decode(errors='replace')); log.flush()
    threading.Thread(target=pump, daemon=True).start()
    cmd = [HATARI, '--tos', TOS, '--machine', 'st', '--memsize', '1', '--disk-a', disk, '--sound', 'off',
           '--fast-forward', 'off', '--confirm-quit', 'off', '--screenshot-dir', out, '--control-socket', sock_path]
    if sys.platform == 'darwin': cmd = ['arch', '-x86_64'] + cmd
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=sfd, stderr=sfd, cwd=out,
                            env=dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy'))
    srv.settimeout(30); conn, _ = srv.accept()

    def send(c, pause=0.2):
        conn.sendall((c + '\n').encode()); time.sleep(pause)
    def logtxt(): return open(logp, errors='replace').read()
    def shot(name):
        before = set(glob.glob(out + '/grab*.png')); send('hatari-shortcut screenshot')
        for _ in range(50):
            time.sleep(0.1); new = set(glob.glob(out + '/grab*.png')) - before
            if new: time.sleep(0.3); shutil.move(new.pop(), '%s/%s.png' % (out, name)); return
    def mem(addr, n):
        mark = '=== %x %f' % (addr, time.time())
        send('hatari-debug echo %s' % mark, 0.1)
        send('hatari-debug m $%x-$%x' % (addr, addr + n), 0.6)
        txt = logtxt(); bs = []
        for line in txt[txt.rfind(mark):].splitlines()[1:]:
            m = re.match(r'\s*\$?([0-9a-fA-F]{5,8}):?\s+((?:[0-9a-fA-F]{2} ?)+)', line)
            if m: bs += [int(x, 16) for x in m.group(2).split()]
            if len(bs) >= n: break
        return bytes(bs[:n])
    def vbl():
        mark = '@V%f' % time.time()
        send("hatari-debug echo %s 'VBL'" % mark, 0.3)
        m = re.findall(re.escape(mark) + r' \$([0-9a-f]+)', logtxt())
        return int(m[-1], 16) if m else None
    def wait_vbl(n, limit=120):
        v0 = vbl(); t = time.time()
        while time.time() - t < limit:
            v = vbl()
            if v is not None and v0 is not None and v - v0 >= n: return v
            time.sleep(0.2)
        raise RuntimeError('VBL did not advance %d in %d s (v0 %s)' % (n, limit, v0))
    def ptr():
        b = mem(0x24748, 4); return int.from_bytes(b[:2], 'big', signed=True), int.from_bytes(b[2:], 'big', signed=True)
    def click():
        send('hatari-event leftdown'); wait_vbl(10); send('hatari-event leftup'); wait_vbl(10)
    def moveto(x, y):
        send('hatari-event mousemove -2000 -2000'); wait_vbl(5)
        send('hatari-event mousemove %d %d' % (x, y)); wait_vbl(5)
        p = ptr(); print('pointer', p, 'want', (x, y), flush=True); return p

    try:
        time.sleep(3)
        send('hatari-debug b pc=$b410 :trace :once')
        t = time.time()
        while 'matched' not in logtxt():
            if time.time() - t > 120: raise RuntimeError('title loop $b410 not reached')
            send('hatari-event keydown 57', 0.3); send('hatari-event keyup 57', 1.5)
        print('reached $b410 (title wait loop), VBL', vbl(), flush=True)
        # DEMO.GOD's title menu times out after 500 frames, so this runs in real time (no fast-forward); its pointer
        # is not $24748 (that is POPULOUS.GOD's), so the move is not read back here: the briefing screenshot is the check
        send('hatari-event mousemove -2000 -2000'); wait_vbl(5)
        send('hatari-event mousemove 250 176'); wait_vbl(5); shot('title')
        click(); print('clicked CONQUEST, VBL', vbl(), flush=True)
        send('hatari-option --fast-forward on', 0.5)
        wait_vbl(4000, 300); shot('briefing')
        p = moveto(85, 176)
        if p != (85, 176): raise RuntimeError('pointer %s' % (p,))
        click(); print('clicked START GAME', flush=True)
        wait_vbl(300); shot('game')
        f0 = int.from_bytes(mem(0x3c4c8, 2), 'big'); wait_vbl(100); f1 = int.from_bytes(mem(0x3c4c8, 2), 'big')
        print('frame counter $3c4c8 %d -> %d over 100 VBL' % (f0, f1), flush=True)
        if f1 == f0: raise RuntimeError('frame counter not advancing: not in gameplay')
        send('hatari-debug b pc=$db50 :trace :quiet :file %s' % os.path.join(out, 'entry.dbg'), 0.5)
        send('hatari-debug b pc=$ef48 :trace :quiet :file %s' % os.path.join(out, 'unlk.dbg'), 0.5)
        if irq:
            for a in (0x16d32, 0xfc0644, 0xfc2f2c, 0xfc4c7a):
                send('hatari-debug b pc=$%x :trace :quiet :file %s' % (a, os.path.join(out, 'irq.dbg')), 0.3)
        if watch:
            send('hatari-debug b ($%x).w ! ($%x).w :trace :quiet :file %s' % (waddr, waddr, os.path.join(out, 'watch.dbg')), 0.5)
        t = time.time()
        while logtxt().count('@U ') < nfr:
            if time.time() - t > 900: print('timeout'); break
            time.sleep(2)
        send('hatari-debug b all', 0.5)
        shot('end')
        print('frame counter at end', int.from_bytes(mem(0x3c4c8, 2), 'big'), 'entries', logtxt().count('@E '),
              'unlks', logtxt().count('@U '), flush=True)
    finally:
        try: send('hatari-shortcut quit')
        except OSError: pass
        time.sleep(1); proc.kill(); os.unlink(sock_path)
    print('log:', logp)


def parse(logp, csvp=None):
    """pair each @E record (A6, A7, VBL, word at A6-146, frame $3c4c8) with the next @U record before the next @E"""
    txt = open(logp, errors='replace').read()
    recs = []
    for m in re.finditer(r'@([EU]) \$([0-9a-f]+) \$([0-9a-f]+) \$([0-9a-f]+)', txt):
        rest = txt[m.end():m.end() + 400]
        dumps = re.findall(r'\n([0-9A-F]{8}): ([0-9a-f]{2}) ([0-9a-f]{2})', rest)
        a6 = int(m.group(2), 16)
        d = {a: int(h1 + h2, 16) for a, h1, h2 in dumps[:2]}
        w = d.get('%08X' % (a6 - 146))
        fr = d.get('0003C4C8') if m.group(1) == 'E' else None
        recs.append((m.group(1), a6, int(m.group(3), 16), int(m.group(4), 16), w, fr))
    rows = []; i = 0
    while i < len(recs):
        if recs[i][0] == 'E':
            e = recs[i]; u = recs[i + 1] if i + 1 < len(recs) and recs[i + 1][0] == 'U' else None
            rows.append((e, u)); i += 2 if u else 1
        else: i += 1
    paired = [(e, u) for e, u in rows if u]
    if not paired: sys.exit('no paired @E/@U records in %s' % logp)
    cnt = collections.Counter(e[4] for e, u in paired)
    same = sum(1 for e, u in paired if e[4] == u[4] and e[1] == u[1])
    a6s = collections.Counter(e[1] for e, u in rows); a7s = collections.Counter(e[2] for e, u in rows)
    if csvp:
        with open(csvp, 'w') as f:
            f.write('frame,vbl_entry,a6,a7_entry,w_entry,vbl_unlk,w_unlk\n')
            for e, u in rows:
                f.write('%s,%d,%x,%x,%s,%s,%s\n' % (e[5], e[3], e[1], e[2], '%04x' % e[4] if e[4] is not None else '',
                                                   u[3] if u else '', '%04x' % u[4] if u and u[4] is not None else ''))
    print('E records %d, paired with U %d, missing word %d' % (len(rows), len(paired), sum(e[4] is None for e, u in rows)))
    print('A6 at entry', {hex(k): v for k, v in a6s.items()}, ' A7 at entry', {hex(k): v for k, v in a7s.items()})
    print('frames %s..%s' % (paired[0][0][5], paired[-1][0][5]), ' VBL %d..%d' % (paired[0][0][3], paired[-1][0][3]))
    print('unchanged entry->unlk %d/%d' % (same, len(paired)))
    print('values:', ', '.join('%04x x%d' % kv for kv in cnt.most_common()))
    print('zero (south) %d/%d = %.1f%%' % (cnt[0], len(paired), 100.0 * cnt[0] / len(paired)))


def writers(logp):
    """classify each @W (change of the watched word: PC after the write, A7, VBL, SR) as inside $db4c or between calls"""
    txt = open(logp, errors='replace').read()
    ev = []
    for m in re.finditer(r'@([EUW]) \$([0-9a-f]+) \$([0-9a-f]+) \$([0-9a-f]+)(?: \$([0-9a-f]{4}))?', txt):
        rest = txt[m.end():m.end() + 300]
        d = re.search(r'0003F418: ([0-9a-f]{2}) ([0-9a-f]{2})', rest)
        if m.group(1) == 'W' and m.group(5) is None: print('unparsed', txt[m.start():m.end() + 40]); continue
        ev.append((m.group(1), [int(g, 16) for g in m.groups()[1:] if g], int(d.group(1) + d.group(2), 16) if d else None))
    inside = False; seen_u = False; c = collections.Counter(); ex = collections.defaultdict(list)
    for k, v, w in ev:
        if k == 'U': seen_u = True
        if not seen_u: continue
        if k == 'E': inside = True
        elif k == 'U': inside = False
        else:
            pc, a7, vb, sr = v
            key = ('INSIDE' if inside else 'between', '%06x' % pc)
            c[key] += 1; ex[key].append('a7=%x sr=%04x val=%04x vbl=%d' % (a7, sr, w, vb))
    for key, n in sorted(c.items(), key=lambda kv: -kv[1]):
        print(key, n, ex[key][:3])


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'run':
        tag = a[2] if len(a) > 2 else ''
        waddr = int(a[3], 16) if len(a) > 3 else (0x3f418 if tag == 'watch' else None)
        run(int(a[1]) if len(a) > 1 else 1100, tag, waddr)
    elif len(a) >= 2 and a[0] == 'parse':
        parse(a[1], a[2] if len(a) > 2 else None)
    elif len(a) >= 2 and a[0] == 'writers':
        writers(a[1])
    else:
        sys.exit(__doc__)
