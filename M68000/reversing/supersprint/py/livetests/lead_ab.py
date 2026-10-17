"""lead_ab.py <arm> [steps] - rubber-band test with the human LEADING.  Same snapshot (data/lead_base.snap = ai_econ/prerace_k.snap
+ 1,000,000 steps, race live, human slot 1 idle, drones 0,2,3), same step budget, one variable per arm:

  ctl   nothing poked (human idle at the start line, last by every measure)
  lap   human lap/sector/tile counters (-3906/-3850/-3842 [1]) set to those of drone 3 at base+LEAD steps in the ctl arm
        (the human is ahead on the game's own ranking key; it stays at the start line)
  pos   as lap, and the human car is also moved (Q and screen X/Y of slot 1) to where drone 3 (the pack leader) will be at base+LEAD
  fire  as pos, plus joystick fire held (human accelerates, crashes about)

Samples every `stride` steps (default 5000) the whole per-car state, and watches the 16 bytes -3882..-3867 (divisors and caps)
for any write.  Output data/lead_<arm>.json.  Run `ctl` first (it also records the lead target), then the others.
Positive control: at the end a labelled `w` poke of a cap word must appear as a WATCH line.
"""
from lt import *
arm = sys.argv[1]
steps = int(sys.argv[2]) if len(sys.argv) > 2 else 5_000_000
stride = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
LEAD = int(sys.argv[4]) if len(sys.argv) > 4 else 9_000_000
TSLOT = 3                       # the pack leader (cap 72) defines the lead target
base = os.path.join(DATA, 'lead_base.snap')
if not os.path.exists(base):
    r = Repl2(os.path.join(AI, 'prerace_k.snap'))
    r.cmd('s 1000000'); r.cmd('snap %s' % base); r.close()
r = Repl2(base)
if arm != 'ctl':
    tgt = json.load(open(os.path.join(DATA, 'lead_target.json')))
    pk = {A4 - 3906 + 2: tgt['lap'], A4 - 3850 + 2: tgt['chk'], A4 - 3842 + 2: tgt['tiles']}
    if arm in ('pos', 'fire'):
        pk.update({A4 - 3746 + 2: tgt['qx'], A4 - 3738 + 2: tgt['qy'], A4 - 3698 + 2: tgt['sy'], A4 - 3690 + 2: tgt['sx']})
    setwords(r, pk)
r.cmd('kbd fe 80' if arm == 'fire' else 'kbd fe 00')   # every arm sends one joystick packet, so IKBD interrupt timing is the same
r.cmd('watch %x 16' % (A4 - 3882))
rows, wlines, done = [], [], 0
FRAME = stride == 0              # stride 0: sample once per frame at the entry of $df18 (frame-aligned; a fixed step grid
                                 # drifts against the frame when the human's work per frame differs)
if FRAME:
    steps = steps // 12000       # `steps` is then a frame count
    LEAD //= 12000
    stride = 1
while done < steps:
    if FRAME:
        out, _ = r.cmd('bp df18 400000')
        assert any('hit' in l for l in out), out[-3:]
    else:
        out, _ = r.cmd('s %d' % stride)
    done += stride
    wlines += [l for l in out if l.startswith('WATCH')]
    row = sample(r)
    row['t'] = done
    rows.append(row)
if arm == 'ctl':
    # run on to base+LEAD to record where drone 3 (the pack leader) will be (the lead target)
    while done < LEAD:
        if FRAME:
            r.cmd('bp df18 400000'); done += 1
        else:
            r.cmd('s %d' % stride); done += stride
    s = sample(r)
    json.dump({'lap': s['lap'][TSLOT], 'chk': s['chk'][TSLOT], 'tiles': s['tiles'][TSLOT], 'qx': s['qx'][TSLOT], 'qy': s['qy'][TSLOT],
               'sx': s['sx'][TSLOT], 'sy': s['sy'][TSLOT], 'at': done}, open(os.path.join(DATA, 'lead_target.json'), 'w'))
    wlines += [l for l in r.cmd('s 1')[0] if l.startswith('WATCH')]
    # (watch lines after `steps` are still collected below)
pre = len(wlines)
out, _ = r.cmd('w %x 00370000' % (A4 - 3874 + 2))      # positive control: poke slot 1's cap word
poke_seen = [l for l in out if l.startswith('WATCH')]
if not poke_seen:
    out, _ = r.cmd('s 20'); poke_seen = [l for l in out if l.startswith('WATCH')]
json.dump({'arm': arm, 'steps': steps, 'stride': stride, 'rows': rows, 'watch': wlines, 'poke_watch': poke_seen}, open(os.path.join(DATA, 'lead_%s.json' % arm), 'w'))
print(arm, 'samples', len(rows), 'watch lines in run', pre, 'positive control lines', len(poke_seen), poke_seen[:1])
f = rows[-1]
print(' final lap', f['lap'], 'chk', f['chk'], 'tiles', f['tiles'], 'cap', f['cap'], 'div', f['div'], 'spd', f['spd'])
r.close()
