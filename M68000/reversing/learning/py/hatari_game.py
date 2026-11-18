"""hatari_game.py <snap> <hexaddr> <nticks> [outdir] [--until <hexaddr>] [--control]: let a game RUN on real Hatari from this emulator's
state, interrupts live, and compare the game state at every arrival at <hexaddr> (a once-per-tick routine) with this
emulator's own run from the same snapshot.

1. This emulator (`stserver`): load <snap>, breakpoint at <hexaddr>, and at each of <nticks> arrivals read RANGES.
2. Hatari (TOS 1.00 UK, ST, 1 MB, headless): boot for 200 VBLs, load the snapshot's RAM from address 8, set D0-A7, USP,
   ISP, SR and PC as the snapshot has them (interrupt mask NOT forced: the game's own interrupts run), and log the same
   RANGES with a trace breakpoint at <hexaddr>; quit at arrival <nticks>.
3. Compare arrival k with arrival k, range by range, and report the first arrival that differs.

Only RAM and the CPU registers cross over: Hatari's video, MFP, sound, keyboard and floppy registers are whatever its
own boot of the desktop left, and its frame interrupt is cycle-timed where this emulator's comes every 12,000
instructions. So equality here says the game's tick state does not depend on interrupt timing or on those registers
over the window; a difference says one of them matters, and the first differing range says where to look.

RANGES are Virus's (reversing/virus/README.md "Memory map"): ship position and velocity, fuel/attitude/gravity, the
random generator, score, pool count, wave, and the 128-record actor pool. Output: <outdir>
(default scratchpad/learning/hatari_game/<addr>_<nticks>/): ours.json, hatari.log, the debugger scripts.
--until stops this emulator at its first arrival at that address (a game-over routine) and asks Hatari for the same
number of arrivals, so <nticks> is then only a cap.  --control pokes one pool byte in the RAM handed to Hatari and must report arrival 0 different.
Exit status 0 when every arrival agrees, 1 when one differs, 2 when a run failed.
"""
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hatari_callcap import ROOT, HATARI, DLL, TOS, RAM_OFF, RAM_LEN, NAMES

sys.path.insert(0, os.path.join(ROOT, 'tools'))

RANGES = [('ship', 0x270b0, 12), ('fuel_att_g', 0x32a2e, 14), ('rng', 0x2706e, 8), ('score', 0x2708e, 4),
          ('count', 0x32a3e, 2), ('wave', 0x32a50, 2), ('pool', 0x31d54, 2560)]


SAME = 3000     # steps: a stop this soon after the last is the same arrival (a Virus tick is about 35,000, its frame interrupt under 1,000)


def regs_of(snap, out):
    r = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl'], input='r\nq\n', capture_output=True, text=True, cwd=ROOT)
    log = r.stdout + r.stderr
    open(os.path.join(out, 'regs.log'), 'w').write(log)
    reg = {n.lower(): int(v, 16) for n, v in re.findall(r'\b([DA][0-7]):([0-9a-f]{8})', log)}
    if len(reg) != 16: sys.exit('this emulator: register dump not read (see regs.log)')
    sr = int(re.findall(r'CCR: ([01]{16})', log)[-1], 2)
    usp, ssp = [int(x, 16) for x in re.findall(r'USP:([0-9a-f]{8}) SSP:([0-9a-f]{8})', log)[-1]]
    pc = int(re.findall(r'PC: ([0-9a-f]{8})', log)[-1], 16)
    return reg, sr, usp, ssp, pc


def ours(snap, addr, n, out, until=None):
    from stclient import StServer
    s = StServer(ROOT)
    ticks = []; again = []
    try:
        s('load', snapshot=snap); s('bp_set', addrs=[addr] + ([until] if until else []))
        while len(ticks) < n:
            r = s('run', max_steps=20000000)
            if r['reason'] != 'breakpoint': print('this emulator: arrival %d not reached (%s)' % (len(ticks), r['reason'])); break
            if until and int(str(r['pc']).lstrip('$'), 16) & 0xffffff == until: print('this emulator reached $%x after %d arrivals' % (until, len(ticks))); break
            if ticks and r['steps'] < SAME:             # an interrupt taken at the breakpoint returns to it: the same arrival
                again.append(r['steps']); continue
            ticks.append({nm: s('read', addr=a, len=ln) for nm, a, ln in RANGES})
    finally:
        try: s('shutdown')
        except SystemExit: pass
    json.dump(ticks, open(os.path.join(out, 'ours.json'), 'w'))
    if again: print('this emulator: %d stop(s) were a return to the breakpoint after an interrupt taken there (steps %s), not counted' % (len(again), again))
    return ticks


def hatari(ram, reg, sr, usp, ssp, pc, addr, n, out):
    p = lambda f: os.path.join(out, f)
    open(p('ram8.bin'), 'wb').write(ram[8:])
    if os.path.exists(p('hatari.log')): os.remove(p('hatari.log'))
    if sr & 0x2000: ssp = reg['a7']
    else: usp = reg['a7']
    lines = ['loadbin %s $8' % p('ram8.bin'), 'r sr=$%04x' % sr, 'r usp=$%x' % usp, 'r isp=$%x' % ssp]
    lines += ['r %s=$%x' % (k, reg[k]) for k in NAMES[:15]]
    lines += ['r a7=$%x' % reg['a7'], 'r pc=$%x' % pc,
              'b pc = $%x :trace :quiet :file %s' % (addr, p('tick.dbg')),
              'b pc = $%x :%d :once :trace :file %s' % (addr, n, p('quit.dbg'))]
    open(p('load.dbg'), 'w').write('\n'.join(lines) + '\n')
    open(p('tick.dbg'), 'w').write("echo @T 'VBL'\n" + ''.join('m $%x-$%x\n' % (a, a + ln) for _, a, ln in RANGES))
    open(p('quit.dbg'), 'w').write('quit\n')
    open(p('init.dbg'), 'w').write('b VBL = 200 :once :trace :file %s\n' % p('load.dbg'))
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    cmd = [HATARI, '--configfile', '/dev/null', '--machine', 'st', '--memsize', '1', '--tos', TOS, '--fast-forward', 'on',
           '--sound', 'off', '--confirm-quit', 'off', '--run-vbls', str(2000 + 8 * n), '--parse', p('init.dbg')]
    r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, cwd=out)
    log = r.stdout + r.stderr
    open(p('hatari.log'), 'w').write(log)
    ticks = []; vbls = []
    for blk in log.split('@T ')[1:]:
        body = blk.split('\n')
        c = body[0].index(':')                      # echo ends without a newline: the first dump line follows the VBL
        vbls.append(body[0][:c - 8].strip()); body[0] = body[0][c - 8:]
        mem = {}
        for ln in body:
            m = re.match(r'^\$?([0-9A-Fa-f]{6,8}): ((?:[0-9A-Fa-f]{2} )+)', ln)
            if m:
                a = int(m.group(1), 16)
                for i, b in enumerate(m.group(2).split()): mem[a + i] = b.lower()
        try: ticks.append({nm: ''.join(mem[a + i] for i in range(ln)) for nm, a, ln in RANGES})
        except KeyError: break                      # a block cut short by the quit
    return ticks, vbls


def main():
    a = sys.argv[1:]
    ctl = '--control' in a
    a = [x for x in a if x != '--control']
    until = None
    if '--until' in a: k = a.index('--until'); until = int(a[k + 1], 16); a = a[:k] + a[k + 2:]
    if len(a) < 3: sys.exit(__doc__)
    snap, addr, n = os.path.abspath(a[0]), int(a[1], 16), int(a[2])
    out = os.path.abspath(a[3] if len(a) > 3 else os.path.join(ROOT, 'scratchpad', 'learning', 'hatari_game', '%x_%d' % (addr, n)))
    os.makedirs(out, exist_ok=True)
    reg, sr, usp, ssp, pc = regs_of(snap, out)
    ram = bytearray(open(snap, 'rb').read()[RAM_OFF:RAM_OFF + RAM_LEN])
    if ctl: ram[0x31d54 + 3] ^= 0xff
    o = ours(snap, addr, n, out, until)
    if until: n = len(o)
    h, vbls = hatari(bytes(ram), reg, sr, usp, ssp, pc, addr, n, out)
    print('arrivals at $%x: this emulator %d, Hatari %d (asked %d); Hatari VBL at first %s, at last %s' % (
        addr, len(o), len(h), n, vbls[0] if vbls else '?', vbls[len(h) - 1] if h else '?'))
    if not o or not h: sys.exit(2)
    m = min(len(o), len(h)); first = None; per = {nm: 0 for nm, _, _ in RANGES}
    for k in range(m):
        bad = [nm for nm, _, _ in RANGES if o[k][nm].lower() != h[k][nm]]
        for nm in bad: per[nm] += 1
        if bad and first is None: first = (k, bad)
    eq = sum(1 for k in range(m) if all(o[k][nm].lower() == h[k][nm] for nm, _, _ in RANGES))
    print('arrivals equal on every range: %d/%d' % (eq, m))
    print('arrivals differing, per range: ' + '  '.join('%s %d' % kv for kv in per.items()))
    if first:
        k, bad = first
        print('first difference at arrival %d: %s' % (k, ', '.join(bad)))
        for nm in bad:
            x, y = o[k][nm].lower(), h[k][nm]
            i = next(i for i in range(0, len(x), 2) if x[i:i + 2] != y[i:i + 2])
            ad = dict((n_, a_) for n_, a_, _ in RANGES)[nm] + i // 2
            print('  %s at $%x: this emulator %s  Hatari %s' % (nm, ad, x[i:i + 16], y[i:i + 16]))
    sys.exit(0 if eq == m == n else 1)


if __name__ == '__main__':
    main()
