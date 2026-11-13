"""Does the game over after state 3 restart the current mission or the game? From phoopel/state3/pre3.snap, one labelled
poke 14776(A6) (mission number, 0 = mission 1) = 4, then as state3.py after's click run: run to $134b8, 3M steps, click,
then 30M steps; read 14776 and render. Control: state3.py after (no poke) shows CAPTIVE MISSION 0001."""
import os, sys
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'reversing', 'captive', 'py', 'ai'))
from cap import *  # noqa: E402
OUTD = os.path.join(W, 'phoopel', 'state3')
s = srv(os.path.join(OUTD, 'pre3.snap'))
s('poke', addr=A6 + 14776, width=2, value=4)
print('labelled poke: 14776 = 4; read back', w16(s, 14776))
r = s('run', max_steps=1_000_000, until_pc=[0x134b8])
print('to $134b8:', r['reason'], r['steps'], '14776', w16(s, 14776), '14800', w16(s, 14800))
s('step', n=3_000_000)
s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l')
h = s('hits', steps=30_000_000, addrs=['$13624', '$5608', '$8570'])
print('hits', ' '.join(f"{a['addr']}:{a['count']}" for a in h['hits']))
print('after 30M: 14776', w16(s, 14776), 'mode', w16(s, 13564), '410', w16(s, 410), '14800', w16(s, 14800))
s('render', path=os.path.join(OUTD, 'mission_poke4_end.png'))
s.close()
