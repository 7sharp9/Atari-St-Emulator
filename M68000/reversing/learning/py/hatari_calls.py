"""hatari_calls.py <snap> <ticks.log> [outdir] [--calls N] [--control]: a whole callcap corpus checked on real Hatari in one process.

hatari_callcap.py starts one Hatari per call (about 3 s each).  This script uses what hatari_game.py showed: from the
same snapshot the game flies the same flight on Hatari, tick for tick, so Hatari's own run passes through every call of
the corpus.  It lets Hatari fly from <snap> with interrupts live and logs, with two trace breakpoints, the registers
and the routine's inputs at every entry of Input_Autopilot ($2538c) and the registers and its outputs at every return
($255d4: the routine has one caller, the bsr.w at $255d0).  Each call is then compared with this emulator's `callcap`
of the same natural entry, read from the pilot corpus <ticks.log> (reversing/virus/py/pilot/capture_pilot.py: `bp`,
the input dumps, then `callcap 2538c`, 3,496 calls from demo/S1b.snap):

  entry    D0-A7, the five condition codes and the seven input ranges (INPUTS: pilot words, ship, matrix, pool count, tick, countdown, pool)
  return   D0-A6 against callcap's register delta, A7 = entry A7 + 4, and the OUTPUTS ranges (pilot words, matrix,
           countdown) against the entry dump with callcap's memory delta applied

callcap's delta is also checked to write nothing outside OUTPUTS and the stack below the entry A7, so the three ranges
are all the memory the routine changes.  Unlike hatari_callcap.py the call runs unmasked on Hatari, inside the game,
with its real return address; all of RAM is not compared, only the routine's inputs and outputs.
--control has Hatari's debugger add 1 to the countdown byte $62a60 at the first entry and must report call 0 different
(changed in the RAM handed over instead, the game's own start-up overwrites it and the control passes 20/20).
Output: <outdir> (default scratchpad/learning/hatari_calls/run/): hatari.log and the debugger scripts.
Exit status 0 when every call agrees, 1 when one differs, 2 when a run failed.
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hatari_callcap import ROOT, HATARI, TOS, RAM_OFF, RAM_LEN, NAMES
from hatari_game import regs_of

ENTRY, RETURN = 0x2538c, 0x255d4
INPUTS = [(0x270a2, 14), (0x270b0, 12), (0x270d4, 18), (0x32a3e, 2), (0x32a44, 2), (0x62a60, 1), (0x31d54, 3292)]   # capture_pilot.py's dumps, in its order
OUTPUTS = [(0x270a2, 14), (0x270d4, 18), (0x62a60, 1)]


def corpus(path):
    """this emulator's side: one dict per callcap that returned (reg0, mem at entry, regN, delta)"""
    calls = []; gave = 0
    for blk in open(path).read().split('--- breakpoint ')[1:]:
        head, cc = blk.split('--- callcap ')[:2]         # a `bp` that ran out of budget leaves its callcap on the previous block: not an entry
        gave += blk.count('--- callcap ') - 1
        if not cc.startswith('$%06x: returned' % ENTRY): sys.exit('corpus record %d: callcap did not return' % len(calls))
        reg0 = [0] * 16
        for nm, v in re.findall(r'\b([DA][0-7]):([0-9a-f]{8})', head): reg0[NAMES.index(nm.lower())] = int(v, 16)
        dumps = [ln.split() for ln in head.split('PC: ')[1].split('\n')[2:] if ln.strip()]
        if len(dumps) != len(INPUTS) or any(len(d) != ln for d, (_, ln) in zip(dumps, INPUTS)):
            sys.exit('corpus record %d: input dumps not as capture_pilot.py writes them' % len(calls))
        mem = {a + i: int(b, 16) for d, (a, _) in zip(dumps, INPUTS) for i, b in enumerate(d)}
        regn = list(reg0)
        for nm, v in re.findall(r'\b([DA][0-7]) \$[0-9a-f]{8}->\$([0-9a-f]{8})', cc): regn[NAMES.index(nm.lower())] = int(v, 16)
        delta = {int(a, 16): int(n, 16) for a, n in re.findall(r'^mem \$([0-9a-f]{6}) \$[0-9a-f]{2}->\$([0-9a-f]{2})', cc, re.M)}
        ccr = int(re.findall(r'CCR: ([01]{16})', head)[-1], 2) & 0x1f
        calls.append({'reg0': reg0, 'mem': mem, 'regn': regn, 'delta': delta, 'ccr': ccr})
    return calls, gave


def hatari(snap, n, out, ctl):
    p = lambda f: os.path.join(out, f)
    reg, sr, usp, ssp, pc = regs_of(snap, out)
    ram = bytearray(open(snap, 'rb').read()[RAM_OFF:RAM_OFF + RAM_LEN])
    open(p('ram8.bin'), 'wb').write(ram[8:])
    if os.path.exists(p('hatari.log')): os.remove(p('hatari.log'))
    if sr & 0x2000: ssp = reg['a7']
    else: usp = reg['a7']
    lines = ['loadbin %s $8' % p('ram8.bin'), 'r sr=$%04x' % sr, 'r usp=$%x' % usp, 'r isp=$%x' % ssp]
    lines += ['r %s=$%x' % (k, reg[k]) for k in NAMES[:15]]
    lines += ['r a7=$%x' % reg['a7'], 'r pc=$%x' % pc]
    if ctl is not None:
        open(p('poke.dbg'), 'w').write('w $62a60 $%02x\n' % ctl)
        lines += ['b pc = $%x :once :trace :file %s' % (ENTRY, p('poke.dbg'))]
    lines += ['b pc = $%x :trace :quiet :file %s' % (ENTRY, p('entry.dbg')),
              'b pc = $%x :trace :quiet :file %s' % (RETURN, p('return.dbg')),
              'b pc = $%x :%d :once :trace :file %s' % (RETURN, n, p('quit.dbg'))]
    open(p('load.dbg'), 'w').write('\n'.join(lines) + '\n')
    dump = lambda rs: ''.join('m $%x-$%x\n' % (a, a + ln) for a, ln in rs)
    open(p('entry.dbg'), 'w').write("echo \\n@E 'VBL'\\n\nr\n" + dump(INPUTS))     # the marker on a line of its own: a dump's ASCII column can hold any text
    open(p('return.dbg'), 'w').write("echo \\n@X 'VBL'\\n\nr\n" + dump(OUTPUTS))
    open(p('quit.dbg'), 'w').write('quit\n')
    open(p('init.dbg'), 'w').write('b VBL = 200 :once :trace :file %s\n' % p('load.dbg'))
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    cmd = [HATARI, '--configfile', '/dev/null', '--machine', 'st', '--memsize', '1', '--tos', TOS, '--fast-forward', 'on',
           '--sound', 'off', '--confirm-quit', 'off', '--run-vbls', str(2000 + 8 * n), '--parse', p('init.dbg')]
    r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, cwd=out)
    log = r.stdout + r.stderr
    open(p('hatari.log'), 'w').write(log)
    recs = []
    for m in re.finditer(r'^@([EX]) \$[0-9a-f]+$(.*?)(?=^@[EX] \$[0-9a-f]+$|\Z)', log, re.M | re.S):
        regs = {}
        for nm, v in re.findall(r'\b([DA][0-7]) ([0-9A-F]{8})\b', m.group(2)): regs.setdefault(nm.lower(), int(v, 16))
        mem = {}
        for a, bs in re.findall(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', m.group(2), re.M):
            for i, b in enumerate(bs.split()): mem[int(a, 16) + i] = int(b, 16)
        sr = re.search(r'SR=([0-9A-Fa-f]{4})', m.group(2))
        if sr: regs['ccr'] = int(sr.group(1), 16) & 0x1f
        recs.append((m.group(1), regs, mem))
    calls = []; i = 0
    while i + 1 < len(recs):                    # an entry and the return that follows it
        if recs[i][0] == 'E' and recs[i + 1][0] == 'X': calls.append((recs[i], recs[i + 1])); i += 2
        else: i += 1
    return calls, len(recs)


def main():
    a = sys.argv[1:]
    ctl = '--control' in a
    a = [x for x in a if x != '--control']
    lim = None
    if '--calls' in a: k = a.index('--calls'); lim = int(a[k + 1]); a = a[:k] + a[k + 2:]
    if len(a) < 2: sys.exit(__doc__)
    snap = os.path.abspath(a[0])
    out = os.path.abspath(a[2] if len(a) > 2 else os.path.join(ROOT, 'scratchpad', 'learning', 'hatari_calls', 'run'))
    os.makedirs(out, exist_ok=True)
    o, gave = corpus(a[1])
    if lim: o = o[:lim]
    n = len(o)
    stray = sum(1 for c in o for ad in c['delta']
                if not any(x <= ad < x + ln for x, ln in OUTPUTS) and not c['reg0'][15] - 256 <= ad < c['reg0'][15])
    steps = sum(len(c['delta']) for c in o)
    print('corpus: %d callcaps of $%x that returned (%d capture stops without one); %d changed bytes, %d outside OUTPUTS and the stack'
          % (n, ENTRY, gave, steps, stray))
    h, nrec = hatari(snap, n, out, (o[0]['mem'][0x62a60] + 1) & 0xff if ctl else None)
    print('Hatari: %d entry/return records, %d paired calls (asked %d)' % (nrec, len(h), n))
    if not h: sys.exit(2)
    m = min(n, len(h)); bad_in = bad_out = 0; first = None
    for k in range(m):
        c, ((_, er, em), (_, xr, xm)) = o[k], h[k]
        why = []
        if len(er) != 17 or len(xr) != 17 or any(ad not in em for x, ln in INPUTS for ad in range(x, x + ln)) \
           or any(ad not in xm for x, ln in OUTPUTS for ad in range(x, x + ln)):
            why.append('record incomplete'); bad_in += 1; bad_out += 1
        else:
            rin = [nm for i, nm in enumerate(NAMES) if er[nm] != c['reg0'][i]] + (['ccr'] if er['ccr'] != c['ccr'] else [])
            min_ = [ad for ad in sorted(c['mem']) if em[ad] != c['mem'][ad]]
            want = dict(c['mem']); want.update(c['delta'])
            rout = [nm for i, nm in enumerate(NAMES[:15]) if xr[nm] != c['regn'][i]]
            if xr['a7'] != er['a7'] + 4: rout.append('a7')
            mout = [ad for x, ln in OUTPUTS for ad in range(x, x + ln) if xm[ad] != want[ad]]
            if rin or min_:
                bad_in += 1
                why.append('entry: ' + ' '.join(rin + ['$%x here %02x Hatari %02x' % (ad, c['mem'][ad], em[ad]) for ad in min_[:4]]))
            if rout or mout:
                bad_out += 1
                why.append('return: ' + ' '.join(['%s here %08x Hatari %08x' % (nm, c['regn'][NAMES.index(nm)], xr[nm]) for nm in rout[:4]] +
                                                 ['$%x here %02x Hatari %02x' % (ad, want[ad], xm[ad]) for ad in mout[:4]]))
        if why and first is None: first = (k, why)
    print('calls equal at entry (16 registers, the condition codes, %d input bytes): %d/%d' % (sum(ln for _, ln in INPUTS), m - bad_in, m))
    print('calls equal at return (16 registers, %d output bytes): %d/%d' % (sum(ln for _, ln in OUTPUTS), m - bad_out, m))
    if first: print('first difference at call %d: %s' % (first[0], '; '.join(first[1])))
    sys.exit(0 if not first and m == n == len(h) and not stray else 1)


if __name__ == '__main__':
    main()
