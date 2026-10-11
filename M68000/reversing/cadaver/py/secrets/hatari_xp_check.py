"""hatari_xp_check.py [--patch] [outdir]: verb 5 pays 26 XP whatever its operand, checked on real Hatari rather than this
emulator; with --patch, a 26-byte fix makes it pay its operand.

Boots the Empire one-disk image cold in a headless Hatari (TOS 1.00 UK, 1 MB ST), drives the crack intro, ESC at the restore
prompt and a key at the levels prompt into CAVERN, then pushes event 0 for object 161 onto the game's own ring queue
(entry at the write pointer 304(A5), pointer += 8, count 1154(A5) += 1). Object 161's only block is `06 00 05 36 17`: on
event 0, verb 5 with operand $36 = 54. The game's consumer, gate and handler `$0102cc` run on Hatari's CPU.

Then the same for objects 27 (verb 5, 50), 256 (verb 5, 55) and 131 (verb 5, 30, then verb 6: gold 100, XP 100/4), one push
each, 4 s apart. Expected unpatched: handler and record bytes as in `gameplay_empire.snap`, control window XP 0, each verb 5
pays 26 (131: 26 + 25), gold only from 131, every block's event byte becomes $ff (one-shot) except 131's, deleted.

--patch writes PATCH at $0102d0 after the boot (the same bytes sit unpacked at disk offset $13ad0). It saves the operand
across the sound call the way verbs 6 and 86 already do (`move.l D0,-(A7)` / `move.l (A7)+,D0` around `jsr $158f8`):
`tst.l D0` becomes `move.l D0,-(A7)` (same size and flags), both `jsr $158f8.l` become `bsr.w`, and the pop lands just
before the shared `add.l D0,1192(A5)` at $0102ea, which verbs 6 and 86 enter from $01031c and which stays put.
Expected patched: 161 +54, 27 +50, 256 +55, 131 +30 +25, gold as unpatched.

Hatari: no binary ships for the Mac; build `~/GitHub/hatari` out of tree as x86_64 (the Homebrew libs are x86_64):
`cmake ~/GitHub/hatari -DENABLE_OSX_BUNDLE=0 -DCMAKE_OSX_ARCHITECTURES=x86_64 && make hatari`, then point `HATARI` at
`<build>/src/hatari`. Driving notes: debugger commands sent while `hatari-stop` has paused it are ignored, so every read and
write is sent while running, one write batch per control message; the debugger prints to stdout, so Hatari gets a pty.
A single-character key argument is ASCII (`1` is the digit): ESC is `0x01`.
Addresses are the one-disk Empire build's (A5 = $018152, mechanics.md conventions)."""
import glob, os, pty, re, shutil, socket, subprocess, sys, threading, time

def _root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        nd = os.path.dirname(d)
        if nd == d: sys.exit('M68000 root not found (no tools/rdis.py above this script); set M68000_ROOT')
        d = nd
    return d
ROOT = os.environ.get('M68000_ROOT') or _root()
HATARI = os.environ.get('HATARI', 'hatari')
TOS = os.path.join(ROOT, 'TOS100UK.IMG')
DISK = os.environ.get('CADAVER_DISK', os.path.join(ROOT, '..', 'Cadaver', 'Cadaver (1990)(Image Works)[cr Empire][one disk].st'))
PATCHED = '--patch' in sys.argv
args = [a for a in sys.argv[1:] if a != '--patch']
OUT = os.path.abspath(args[0] if args else os.path.join(ROOT, 'scratchpad', 'cadaver', 'hatari_xp' + ('_patch' if PATCHED else '')))

A5 = 0x018152
QPTR, QCNT, GOLD, XP = A5 + 304, A5 + 1154, A5 + 1188, A5 + 1192
REC161, HANDLER = 0x06fb74, 0x0102cc
EXP_HANDLER = '700010194a806a0c303c00244eb9000158f8600a303c001a4eb9000158f8d1ad'
EXP_REC161 = '1f0f0b8000a1003f01a42f01162020000600053617170508020000000a010000'
PATCH_AT = 0x0102d0
PATCH = '2f006a0a303c00246100561e600a303c001a610056144e71201f'
# object: (record, offset of its event-0 block, (XP unpatched, XP patched), gold); 131's block ends in verb 2 (DELETE the
# current object), which frees the record, so its one-shot byte is not checked
OBJS = {161: (0x06fb74, 0x10, (26, 54), 0), 27: (0x06ede2, 0x10, (26, 50), 0),
        256: (0x0705fe, 0x16, (26, 55), 0), 131: (0x06f898, 0x10, (26 + 25, 30 + 25), 100)}

for p, what in ((TOS, 'TOS ROM'), (DISK, 'disk image (set CADAVER_DISK)')):
    if not os.path.exists(p): sys.exit('%s not found: %s' % (what, p))
os.makedirs(OUT, exist_ok=True)
sock_path = '/tmp/hxp-%d.sock' % os.getpid()      # macOS caps AF_UNIX paths near 104 bytes
srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); srv.bind(sock_path); srv.listen(1)
logp = os.path.join(OUT, 'hatari.log'); log = open(logp, 'w')
mfd, sfd = pty.openpty()
def pump():
    while True:
        try: d = os.read(mfd, 4096)
        except OSError: return
        if not d: return
        log.write(d.decode(errors='replace')); log.flush()
threading.Thread(target=pump, daemon=True).start()
cmd = [HATARI, '--tos', TOS, '--machine', 'st', '--memsize', '1', '--disk-a', DISK, '--sound', 'off',
       '--fast-forward', 'on', '--confirm-quit', 'off', '--screenshot-dir', OUT, '--control-socket', sock_path]
if sys.platform == 'darwin': cmd = ['arch', '-x86_64'] + cmd
proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=sfd, stderr=sfd, cwd=OUT,
                        env=dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy'))
srv.settimeout(30); conn, _ = srv.accept()

def send(c, pause=0.3):
    conn.sendall((c + '\n').encode()); time.sleep(pause)
def key(code):
    send('hatari-event keydown %s' % code, 1.0); send('hatari-event keyup %s' % code)
def shot(name):
    before = set(glob.glob(OUT + '/grab*.png')); send('hatari-shortcut screenshot')
    for _ in range(50):
        time.sleep(0.1); new = set(glob.glob(OUT + '/grab*.png')) - before
        if new: time.sleep(0.3); shutil.move(new.pop(), '%s/%s.png' % (OUT, name)); return
def mem(addr, n):
    mark = '=== %x %f' % (addr, time.time())
    send('hatari-debug echo %s' % mark, 0.1)
    send('hatari-debug m $%x-$%x' % (addr, addr + n), 0.8)
    txt = open(logp, errors='replace').read()
    bs = []
    for line in txt[txt.rfind(mark):].splitlines()[1:]:
        m = re.match(r'\s*\$?([0-9a-fA-F]{5,8}):?\s+((?:[0-9a-fA-F]{2} ?)+)', line)
        if m: bs += [int(x, 16) for x in m.group(2).split()]
        if len(bs) >= n: break
    return bytes(bs[:n])
u32 = lambda a: int.from_bytes(mem(a, 4), 'big')
u16 = lambda a: int.from_bytes(mem(a, 2), 'big')

ok = []
try:
    time.sleep(4); key(57); time.sleep(16); key('0x01'); time.sleep(8); key(57); time.sleep(12)
    shot('cavern')
    h, r = mem(HANDLER, 32).hex(), mem(REC161, 32).hex()
    print('handler  %s %s' % (h, 'same' if h == EXP_HANDLER else 'DIFFERENT'))
    print('rec161   %s %s' % (r, 'same' if r == EXP_REC161 else 'DIFFERENT'))
    ok += [h == EXP_HANDLER, r == EXP_REC161]
    if PATCHED:
        send('hatari-debug w b $%x %s' % (PATCH_AT, ' '.join('$' + PATCH[i:i + 2] for i in range(0, len(PATCH), 2))), 0.5)
        pb = mem(PATCH_AT, len(PATCH) // 2).hex()
        print('patch    %s %s' % (pb, 'written' if pb == PATCH else 'NOT WRITTEN'))
        ok.append(pb == PATCH)
    time.sleep(4)
    xc, gc = u32(XP), u32(GOLD)
    print('control: XP %d gold %d  (4 s, nothing injected)' % (xc, gc))
    ok.append(xc == 0 and gc == 0)
    for oid, (rec, boff, xps, gexp) in OBJS.items():
        x0, g0, q, c = u32(XP), u32(GOLD), u32(QPTR), u16(QCNT)
        send('\n'.join(['hatari-debug w l $%x $%08x $%08x' % (q, rec >> 16, (rec & 0xffff) << 16),
                        'hatari-debug w l $%x $%08x' % (QPTR, q + 8),
                        'hatari-debug w w $%x $%04x' % (QCNT, c + 1)]), 0.1)
        time.sleep(4)
        x, g, ev = u32(XP), u32(GOLD), mem(rec + boff + 1, 1).hex()
        want = xps[PATCHED]
        print('object %3d: XP +%d (want +%d), gold +%d (want +%d), block event byte %s' % (oid, x - x0, want, g - g0, gexp, ev))
        ok += [x - x0 == want, g - g0 == gexp] + ([] if oid == 131 else [ev == 'ff'])
    shot('after')
finally:
    try: send('hatari-shortcut quit')
    except OSError: pass
    time.sleep(1); proc.kill(); os.unlink(sock_path)
n = 2 + 1 + 3 * len(OBJS) - 1 + PATCHED
print('%s %s: %d/%d checks' % ('patched' if PATCHED else 'unpatched', 'ok' if all(ok) and len(ok) == n else 'FAIL', sum(ok), n))
