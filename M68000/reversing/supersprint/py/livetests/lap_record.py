"""lap_record.py <arm> - does a human's best lap ever reach the session lap records -8066(A4)[T]?

The only writer is $1aa2a in the winner's circle, behind `cmp.w -8066(A4)[T],best / bge skip` (signed): with the shipped
SSPRINT.HSC every record is 0, so no positive best can be stored. Same snapshot (data/lead_base.snap), the bot (bot.py) drives
the human to a race-1 win (frame 1276 in bot_ab.py), then the winner's circle runs under `hits`. One variable:

  ship  records as loaded (all 0)
  max   all eight record words poked to $7fff before the race ends
"""
from lt import *
import bot
F['q38'] = -3738; F['q46'] = -3746
arm = sys.argv[1]
r = Repl2(os.path.join(DATA, 'lead_base.snap'))
b = bot.Bot(r)
if arm == 'max':
    setwords(r, {A4 - 8066 + 2 * t: 0x7fff for t in range(8)})
print(arm, 'records before', r.a4w(-8066, 8))
for f in range(1300):
    r.cmd('bp df18 400000')
    row = sample(r)
    if row['lap'][1] >= 4: break
    r.cmd('kbd fe %02x' % b.step(row))
r.cmd('kbd fe 00')
print('  human lap 4 at frame', f, 'laps', row['lap'])
out, _ = r.cmd('hits 25000000 1aa0a 1aa2a 1a4ca be40')
print('  ', ' '.join('%s=%s' % (l.split()[0], l.split()[1]) for l in out if l.startswith('  $')))
print('  records after', r.a4w(-8066, 8))
r.close()
