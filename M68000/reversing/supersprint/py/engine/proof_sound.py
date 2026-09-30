"""Validate sound_model.py against the real ISR: for each trigger routine, capture every YM2149 write of N real ISR ticks
(psg_capture.py) and compare with the Python model tick by tick.  usage: proof_sound.py [ticks] [name...]"""
import sys, os, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import psg_capture as PC
from sound_model import Driver

dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
tail = dat[198966:]
INS = tail[1584:1584 + 2100]; SCR = tail[3684:3684 + 10000]
ram = Ram(sscfg.SNAP_RACE)

# trigger table: name -> (addr, arg, [(logical ch, script off)], prio threshold or None, extra)
def T(ch_offs, prio=None): return (ch_offs, prio)
TRIGS = {
    'A12522': (0x12522, 0, lambda d, a: [(a, 0), ((a + 1) % 3, 0)], None),
    'B125e6': (0x125e6, 0, lambda d, a: [(a, 316), ((a + 1) % 3, 316)], None),
    'C126ae': (0x126ae, 0, lambda d, a: [(a, 28)], 4),
    'D1271c': (0x1271c, 0, lambda d, a: [(a, 166)], 3),
    'E1278a': (0x1278a, 0, lambda d, a: [(a, 88)], 4),
    'F127f8': (0x127f8, 0, lambda d, a: [(a, 180)], 1),
    'G12866': (0x12866, 0, lambda d, a: [(a, 302)], 1),
    'H128e0': (0x128e0, 0, lambda d, a: [(a, 14)], 2),
    'I1294e': (0x1294e, 0, lambda d, a: [(a, 74)], 1),
    'J129bc': (0x129bc, 0, lambda d, a: [(0, 194), (1, 208), (2, 222)], None),
    'K12a56': (0x12a56, 0, lambda d, a: [(0, 242)], None),
    'L12a8c': (0x12a8c, 0, lambda d, a: [(0, 272)], None),
    'M12ac2': (0x12ac2, 0, lambda d, a: [(1, 322)], None),
    'N12b00': (0x12b00, 0, lambda d, a: [(0, 336)], None),
    'O12b32': (0x12b32, 0, lambda d, a: [(a, 236)], None),
    'P12c10_0': (0x12c10, 0, lambda d, a: [(0, 3398)], None),
    'P12c10_1': (0x12c10, 1, lambda d, a: [(0, 4488)], None),
    'P12c10_2': (0x12c10, 2, lambda d, a: [(0, 5302)], None),
    'P12c10_3': (0x12c10, 3, lambda d, a: [(0, 5916)], None),
    'P12c10_4': (0x12c10, 4, lambda d, a: [(0, 6794)], None),
    'Q12d64': (0x12d64, 0, lambda d, a: [(0, 906)], None),
    'R12da8': (0x12da8, 0, lambda d, a: [(0, 7780)], None),
    'S12dec': (0x12dec, 0, lambda d, a: [(0, 2580)], None),
    'T12e30': (0x12e30, 0, lambda d, a: [(a, 316)], None),
}


def init_model():
    d = Driver(INS, SCR, master=ram.gsw(-50))
    base = ram.g(-70)
    st = ram.g(-66)
    for hw in range(3):
        d.state[hw] = [ram.sw(st + 30 * hw + 2 * i) for i in range(15)]
        ip = ram.l(0x137f8 + 4 * hw)
        d.cur[hw] = d.I[(ip - base) // 60]
    d.level = [ram.sw(ram.g(-58) + 2 * i) for i in range(3)]
    d.mirror7 = ram.w(0x13810)
    d.div = ram.gsw(-12)
    d.status = [-1, -1, -1]
    return d


def compare(name, ticks, arg=None):
    trig, a0, fn, prio = TRIGS[name]
    arg = a0 if arg is None else arg
    steps = 6000 + ticks * 1200
    psg = PC.run(trig, arg, ticks, 'ff8800 4', steps)
    marks = PC.run(trig, arg, ticks, '%x 2' % (A4 - 12), steps)
    tick_steps = [m[0] for m in marks if m[4] != 8]
    # model
    d = init_model()
    d.master = 16
    for ch, off in fn(d, arg):
        if prio is None or d.level[ch] < prio:
            d.status[ch] = 0; d.ptr[ch] = off; d.delay[ch] = 0
    model = [d.tick() for _ in range(len(tick_steps))]
    # real per tick
    real = [[] for _ in tick_steps]
    pre = []
    regsel = None
    for step, pc, kind, addr, val in psg:
        if addr == 0xFF8800: regsel = val
        elif addr == 0xFF8802:
            if regsel is not None and regsel >= 14: continue      # floppy side/drive select (port A) written by the game/TOS
            if step < tick_steps[0]: pre.append((regsel, val)); continue
            i = max(k for k, s in enumerate(tick_steps) if s <= step)
            real[i].append((regsel, val))
    ok = sum(1 for m, r in zip(model, real) if m == r)
    nw = sum(len(r) for r in real)
    print('%-9s ticks %4d (real ISR invocations %d): ticks whose PSG writes equal the model: %d / %d   (%d real writes, pre-tick writes %s)'
          % (name, ticks, len(tick_steps), ok, len(tick_steps), nw, pre))
    bad = [(i, m, r) for i, (m, r) in enumerate(zip(model, real)) if m != r][:3]
    for i, m, r in bad: print('    first diffs tick %d model %s real %s' % (i, m, r))
    return ok, len(tick_steps), real, model


if __name__ == '__main__':
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    names = sys.argv[2:] or list(TRIGS)
    tot_ok = tot = 0
    for n in names:
        a = b = 0
        ok, n_t, _, _ = compare(n, ticks, 1 if n[0] in 'ABCDEFGHIOT' else None)
        tot_ok += ok; tot += n_t
    print('TOTAL ticks equal %d / %d' % (tot_ok, tot))
