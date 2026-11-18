"""hatari_callcap.py <snap> <hexaddr> [nth] [outdir]: run one call of a game routine on real Hatari's CPU from this
emulator's state, and compare the result with this emulator's own `callcap`.

1. This emulator: resume <snap>, run to the nth arrival at <hexaddr> (`bp` / `bpc`), save a snapshot there and
   `callcap` the routine (interrupts masked, sentinel return address $00DEAD00 pushed at A7-4).
2. Hatari (TOS 1.00 UK, ST, 1 MB, headless): boot for 200 VBLs, then a debugger script loads the snapshot's 1 MB of RAM
   from address 8 (`loadbin`; $0-$7 are ROM on a real ST), sets D0-A7, USP, ISP, SR (interrupt mask 7) and PC, and
   runs to the return address, where a second script saves RAM (`savebin`), prints the registers and quits. The
   return address on Hatari is $00FC0000 (the ROM's first word): Hatari bus-errors fetching $00DEAD00, which is
   outside a 1 MB machine, before its breakpoint is tested. The four-byte return slot is left out of the compare.
3. Compare: Hatari's RAM after the call against the snapshot RAM with this emulator's callcap delta applied, over
   $8-$fffff, and the sixteen registers.

Only RAM and the CPU registers cross over. Hatari's hardware registers (video, MFP, YM, ACIA, FDC) keep whatever its
own boot left, so a routine that reads one is outside what this checks. Output and working files: <outdir>
(default scratchpad/learning/hatari_callcap/<addr>_<nth>/).

HATARI = the binary (default ~/Downloads/hatari-snapshot/Hatari.app/Contents/MacOS/Hatari, the universal 2.6.1-devel
build; an x86_64 source build per DEVELOPING.md "macOS" also works).
--control flips one byte of the RAM handed to Hatari ($7fff0, or the address after --control) and must report
exactly that byte as different: it shows the compare reads Hatari's output.
Exit status 0 when RAM and registers agree, 1 when they differ, 2 when a run failed.
"""
import json, os, re, subprocess, sys


def _root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        nd = os.path.dirname(d)
        if nd == d: sys.exit('M68000 root not found (no tools/rdis.py above this script); set M68000_ROOT')
        d = nd
    return d


ROOT = os.environ.get('M68000_ROOT') or _root()
HATARI = os.environ.get('HATARI', os.path.expanduser('~/Downloads/hatari-snapshot/Hatari.app/Contents/MacOS/Hatari'))
DLL = os.path.join(ROOT, 'bin', 'Debug', 'net8.0', 'M68000.dll')
TOS = os.path.join(ROOT, 'TOS100UK.IMG')
RAM_OFF, RAM_LEN, SENTINEL = 87, 0x100000, 0x00FC0000   # RAM_OFF: where address 0 sits in a snapshot file
NAMES = ['d%d' % i for i in range(8)] + ['a%d' % i for i in range(8)]


def ours(snap, addr, nth, out):
    esnap, cc = os.path.join(out, 'entry.snap'), os.path.join(out, 'cc.json')
    for p in (esnap, cc):
        if os.path.exists(p): os.remove(p)
    go = 'bp %x 50000000' % addr if nth == 1 else 'bpc %x %d 50000000' % (addr, nth)
    script = '%s\nr\nsnap %s\ncallcap %x 2000000 %s\nq\n' % (go, esnap, addr, cc)
    r = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl'], input=script, capture_output=True, text=True, cwd=ROOT)
    log = r.stdout + r.stderr
    open(os.path.join(out, 'ours.log'), 'w').write(log)
    if not (os.path.exists(esnap) and os.path.exists(cc)): sys.exit('this emulator: no snapshot or callcap (see ours.log)')
    j = json.load(open(cc))
    if j['outcome'] != 'returned': sys.exit('this emulator: callcap ' + j['outcome'])
    head = log[:log.index('--- state saved')]
    sr = int(re.findall(r'CCR: ([01]{16})', head)[-1], 2)
    usp, ssp = [int(x, 16) for x in re.findall(r'USP:([0-9a-f]{8}) SSP:([0-9a-f]{8})', head)[-1]]
    pc = int(re.findall(r'PC: ([0-9a-f]{8})', head)[-1], 16)
    if pc != addr: sys.exit('this emulator stopped at $%x, not $%x (see ours.log)' % (pc, addr))
    return esnap, j, sr, usp, ssp


def hatari(ram, j, sr, usp, ssp, addr, out):
    p = lambda n: os.path.join(out, n)
    open(p('ram8.bin'), 'wb').write(ram[8:])
    for f in ('after.bin', 'hatari.log'):
        if os.path.exists(p(f)): os.remove(p(f))
    reg0, sr = j['reg0'], (sr | 0x0700) & 0xffff
    if not sr & 0x2000: usp = reg0[15] - 4          # the live stack is the user stack
    else: ssp = reg0[15] - 4
    lines = ['loadbin %s $8' % p('ram8.bin'), 'r sr=$%04x' % sr, 'r usp=$%x' % usp, 'r isp=$%x' % ssp]
    lines += ['r %s=$%x' % (NAMES[i], reg0[i]) for i in range(15)]
    lines += ['r a7=$%x' % (reg0[15] - 4), 'r pc=$%x' % addr,
              'b pc = $%x :once :trace :file %s' % (SENTINEL, p('save.dbg'))]
    open(p('load.dbg'), 'w').write('\n'.join(lines) + '\n')
    open(p('save.dbg'), 'w').write('savebin %s $0 $%x\nr\nquit\n' % (p('after.bin'), RAM_LEN))
    open(p('init.dbg'), 'w').write('b VBL = 200 :once :trace :file %s\n' % p('load.dbg'))
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    cmd = [HATARI, '--configfile', '/dev/null', '--machine', 'st', '--memsize', '1', '--tos', TOS, '--fast-forward', 'on',
           '--sound', 'off', '--confirm-quit', 'off', '--run-vbls', '4000', '--parse', p('init.dbg')]
    r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, cwd=out)
    log = r.stdout + r.stderr
    open(p('hatari.log'), 'w').write(log)
    if not os.path.exists(p('after.bin')): print('Hatari: the call never reached the return address (see hatari.log)'); sys.exit(2)
    tail = log[log.rindex('> r\n'):] if '> r\n' in log else ''
    regs = {}
    for n, v in re.findall(r'\b([DA][0-7])[ =:]+\$?([0-9A-Fa-f]{8})', tail): regs.setdefault(n.lower(), int(v, 16))
    return open(p('after.bin'), 'rb').read(), regs


def main():
    a = sys.argv[1:]
    ctl = None
    if '--control' in a:
        k = a.index('--control'); ctl = int(a[k + 1], 16) if k + 1 < len(a) and len(a) > 3 and k + 1 == len(a) - 1 else 0x7fff0
        a = a[:k]
    if len(a) < 2: sys.exit(__doc__)
    snap, addr, nth = os.path.abspath(a[0]), int(a[1], 16), int(a[2]) if len(a) > 2 else 1
    out = os.path.abspath(a[3] if len(a) > 3 else os.path.join(ROOT, 'scratchpad', 'learning', 'hatari_callcap', '%x_%d' % (addr, nth)))
    os.makedirs(out, exist_ok=True)
    esnap, j, sr, usp, ssp = ours(snap, addr, nth, out)
    ram = bytearray(open(esnap, 'rb').read()[RAM_OFF:RAM_OFF + RAM_LEN])
    slot = j['entrySP'] - 4
    ram[slot:slot + 4] = SENTINEL.to_bytes(4, 'big')
    hram = bytearray(ram)
    if ctl is not None: hram[ctl] ^= 0xff
    after, hregs = hatari(bytes(hram), j, sr, usp, ssp, addr, out)
    want = bytearray(ram)
    for ad, _, new in j['mem']: want[ad] = new
    cells = [i for i in range(8, RAM_LEN) if not slot <= i < slot + 4]
    diff = [i for i in cells if after[i] != want[i]]
    moved = sum(1 for i in cells if after[i] != ram[i])
    print('$%06x call %d: %d steps here; this emulator changed %d byte(s), Hatari changed %d' % (addr, nth, j['steps'], len(j['mem']), moved))
    print('RAM $8-$fffff after the call: %d/%d bytes equal' % (len(cells) - len(diff), len(cells)))
    for i in diff[:20]: print('  $%06x before %02x  this emulator %02x  Hatari %02x' % (i, ram[i], want[i], after[i]))
    rbad = [n for k, n in enumerate(NAMES) if hregs.get(n) != j['regN'][k]]
    print('registers after the call: %d/16 equal%s' % (16 - len(rbad), ''.join('  %s ours %08x Hatari %s' % (
        n, j['regN'][NAMES.index(n)], '%08x' % hregs[n] if n in hregs else '?') for n in rbad)))
    sys.exit(1 if diff or rbad else 0)


if __name__ == '__main__':
    main()
