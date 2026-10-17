"""Live differential of the sound model against the game's own Timer-D ISR ($13254, driven by engine/psg_capture.py: fake interrupts from the
race snapshot's page-flip routine) over the WHOLE length of the unreferenced entries, for both the model with the missing-rts bug and without.
usage: liveproof.py [Q12d64 J129bc M12ac2] [--ticks N]   (default ticks: model length + 60)
Counts ticks whose PSG register writes equal the model's; a failing model prints its first differing tick."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
import proof_sound as PS, psg_capture as PC
from tune import Driver, FixedDriver, make, run

ENT = {'Q12d64': (0x12d64, [(0, 906)]), 'J129bc': (0x129bc, [(0, 194), (1, 208), (2, 222)]), 'M12ac2': (0x12ac2, [(1, 322)])}
args = [a for a in sys.argv[1:] if not a.startswith('--')]
names = args or list(ENT)
for name in names:
    trig, ents = ENT[name]
    _, _, n_model = run(Driver, ents)
    ticks = n_model + 60
    if '--ticks' in sys.argv: ticks = int(sys.argv[sys.argv.index('--ticks') + 1])
    steps = 6000 + ticks * 1200
    psg = PC.run(trig, 0, ticks, 'ff8800 4', steps)
    marks = PC.run(trig, 0, ticks, '%x 2' % (sscfg.A4 - 12), steps)
    tick_steps = [m[0] for m in marks if m[4] != 8]
    real = [[] for _ in tick_steps]; pre = []; regsel = None
    for step, pc, kind, addr, val in psg:
        if addr == 0xFF8800: regsel = val
        elif addr == 0xFF8802:
            if regsel is not None and regsel >= 14: continue
            if step < tick_steps[0]: pre.append((regsel, val)); continue
            i = max(k for k, s in enumerate(tick_steps) if s <= step)
            real[i].append((regsel, val))
    nw = sum(len(r) for r in real)
    for label, cls in (('model with the $13308 fall-through', Driver), ('model without it', FixedDriver)):
        d = make(cls, ents)
        model = [d.tick() for _ in range(len(tick_steps))]
        ok = sum(1 for m, r in zip(model, real) if m == r)
        bad = [(i, m, r) for i, (m, r) in enumerate(zip(model, real)) if m != r][:2]
        print('%-8s %-36s ticks %5d (real ISR invocations %d, real PSG writes %d): equal %d / %d' % (name, label, ticks, len(tick_steps), nw, ok, len(tick_steps)))
        for i, m, r in bad: print('     first diff tick %d model %s real %s' % (i, m, r))
