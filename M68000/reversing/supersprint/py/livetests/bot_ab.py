"""bot_ab.py <arm> [frames] [look] [lift] - the drone A/B with a human that actually drives (bot.py) instead of poked counters.

Same snapshot (data/lead_base.snap, see lead_ab.py), same frame budget, one joystick packet `fe <byte>` sent every frame in
both arms, so the only variable is the packet's value:

  ctl   fe 00 every frame (the human idles at the start line)
  bot   the byte bot.Bot chooses from this frame's state

Samples the whole per-car state (lt.sample plus the Q words) at the entry of $df18 every frame, before the packet, and watches
-3882..-3867(A4) (divisors, caps) for any write. Output data/bot_<arm>.json; compare with bot_cmp.py.
"""
from lt import *
import bot
F['q38'] = -3738; F['q46'] = -3746; F['bump'] = -3818; F['spin'] = -3866
arm = sys.argv[1]
frames = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
look = int(sys.argv[3]) if len(sys.argv) > 3 else 480
lift = int(sys.argv[4]) if len(sys.argv) > 4 else 70
r = Repl2(os.path.join(DATA, 'lead_base.snap'))
b = bot.Bot(r, look=look, lift=lift)
r.cmd('watch %x 16' % (A4 - 3882))
rows, pk, wl = [], [], []
for f in range(frames):
    out, _ = r.cmd('bp df18 400000')
    assert any('hit' in l for l in out), out[-3:]
    wl += ['f%d %s' % (f, l) for l in out if l.startswith('WATCH')]
    row = sample(r)
    p = b.step(row) if arm == 'bot' else 0
    row['pkt'] = p
    rows.append(row)
    wl += ['f%d %s' % (f, l) for l in r.cmd('kbd fe %02x' % p)[0] if l.startswith('WATCH')]
    if f % 100 == 0:
        print(f, 'lap', row['lap'], 'chk', row['chk'], 'tiles', row['tiles'][1], 'spd', row['spd'][1], 'stun', row['stun'][1],
              'off-line', round(b.last[0]) if arm == 'bot' else '-', flush=True)
r.cmd('snap %s' % os.path.join(DATA, 'bot_%s_end.snap' % arm))
out, _ = r.cmd('w %x 00370000' % (A4 - 3874 + 2))          # positive control: poke slot 1's cap word
poke = [l for l in out if l.startswith('WATCH')] or [l for l in r.cmd('s 20')[0] if l.startswith('WATCH')]
json.dump({'arm': arm, 'frames': frames, 'look': look, 'lift': lift, 'rows': rows, 'watch': wl, 'poke_watch': poke},
          open(os.path.join(DATA, 'bot_%s.json' % arm), 'w'))
print(arm, 'frames', len(rows), 'watch lines in run', len(wl), 'positive control lines', len(poke), poke[:1])
r.close()
