"""What happens in a base once the fire has reached the end of its path (13410(A6) = 3)? (ai.md "Finishing a base")

state3.py reach   from phoopel/finish_base1_blast_state2.snap (state 2, no further pokes) run to the first arrival at
                  $bfa4 (the write of 13410 = 3); save pre3.snap there (one instruction before the write). Then run on
                  to the end screen $134b8 and census what runs in between and after.
state3.py after   from pre3.snap (party where play left it, (18,8)): run to $134b8, 3M steps, then a left click against
                  no click; census $134b8 $13624 (screen exit) $5608 $8570 (globals clear) $562e $90be $b5c2 over 30.06M
                  steps; renders at 2.06M, 5.06M and the end; saves after_click_30m.snap.
state3.py leave   from pre3.snap: labelled pokes party onto the base entrance 22/24(A6), facing 0, then the leave click
                  (leave.py's), against the same pokes and no click. Census $dd90 $87c0 $87d6 $87f4 $8836 $134b8 over
                  the run; 14794 and mode read after 30M steps.
Outputs under scratchpad/captive/phoopel/state3/.
"""
import os, sys, json
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'reversing', 'captive', 'py', 'ai'))
from cap import *  # noqa: E402

OUTD = os.path.join(W, 'phoopel', 'state3')
F = [('13410', 13410), ('13408', 13408), ('mode', 13564), ('410', 410), ('14800', 14800), ('14794', 14794),
     ('14776', 14776), ('14782', 14782), ('face', 30)]


def sv(s):
    p = l32(s, 26)
    r = {n: w16(s, o) for n, o in F}
    r['party'] = (p >> 16, p & 0xffff)
    return r


def steps(s):
    return int(str(s('regs').get('steps', s('regs').get('step', 0))).lstrip('$') or 0)


def reach():
    s = srv('phoopel/finish_base1_blast_state2.snap')
    print('start', sv(s), 'entrance 22/24 =', w16(s, 22), w16(s, 24))
    r = s('run', max_steps=60_000_000, until_pc=[0xbfa4, 0x8000bfa4])
    print('run to $bfa4:', r['reason'], r['steps'], 'steps;', sv(s))
    s('save', path=os.path.join(OUTD, 'pre3.snap'))
    s('render', path=os.path.join(OUTD, 'pre3.png'))
    A = ['$bfaa', '$56b4', '$134b8', '$13f4a', '$5608', '$562e', '$8836', '$87d6', '$90be', '$107cc', '$9a9a', '$e6dc']
    h = s('hits', steps=3_000_000, addrs=A)
    print('3M after:', ' '.join(f"{a['addr']}:{a['count']}@{a['first']}" for a in h['hits']))
    print('state', sv(s))
    s('render', path=os.path.join(OUTD, 'pre3_plus3m.png'))
    s.close()


def after():
    """End screen: a click 3M steps in, against no click; then 30M steps."""
    for tag in ('noclick', 'click'):
        s = srv(os.path.join(OUTD, 'pre3.snap'))
        A = ['$134b8', '$13624', '$5608', '$8570', '$562e', '$90be', '$b5c2', '$134b8']
        r = s('run', max_steps=1_000_000, until_pc=[0x134b8])
        print(f'{tag}: to $134b8: {r["reason"]} after {r["steps"]} steps;', sv(s))
        s('step', n=3_000_000)
        tot = {a: 0 for a in A[:-1]}
        first = {}
        def acc(h, base):
            for a, b in zip(A[:-1], h['hits']):
                tot[a] += b['count']
                if b['count'] and a not in first:
                    first[a] = base + b['first']
        if tag == 'click':
            s('mouse', action='down', button='l'); acc(s('hits', steps=60000, addrs=A[:-1]), 0)
            s('mouse', action='up', button='l')
        else:
            acc(s('hits', steps=60000, addrs=A[:-1]), 0)
        done = 60000
        for i in range(60):
            acc(s('hits', steps=500_000, addrs=A[:-1]), done)
            done += 500_000
            if i in (3, 9):
                s('render', path=os.path.join(OUTD, f'after_{tag}_{done // 1000}k.png'))
                print(f'{tag}: {done} steps after the input:', sv(s))
        print(f'{tag}: {done} steps after the input: hits', tot, 'first', first)
        print(f'{tag}: end', sv(s))
        s('render', path=os.path.join(OUTD, f'after_{tag}_end.png'))
        if tag == 'click':
            s('save', path=os.path.join(OUTD, 'after_click_30m.snap'))
        s.close()


def leave():
    for tag in ('noclick', 'click'):
        s = srv(os.path.join(OUTD, 'pre3.snap'))
        for off, v in ((26, w16(s, 22)), (28, w16(s, 24)), (30, 0)):
            s('poke', addr=A6 + off, width=2, value=v)
        print(f'{tag}: labelled pokes: party onto the entrance ({w16(s, 22)},{w16(s, 24)}), facing 0;', sv(s))
        A = ['$dd90', '$87c0', '$87d6', '$87f4', '$8836', '$8840', '$134b8', '$5608', '$bfaa']
        tot = {a: 0 for a in A}

        def acc(h):
            for a, b in zip(A, h['hits']):
                tot[a] += b['count']
        if tag == 'click':
            for _ in range(3):
                s('mouse', action='move', dx=-127, dy=-127); acc(s('hits', steps=30000, addrs=A))
            s('mouse', action='move', dx=100, dy=105); acc(s('hits', steps=30000, addrs=A))
            s('mouse', action='down', button='l'); acc(s('hits', steps=60000, addrs=A))
            s('mouse', action='up', button='l')
        else:
            acc(s('hits', steps=180000, addrs=A))
        for i in range(60):
            acc(s('hits', steps=500_000, addrs=A))
        print(f'{tag}: 30.18M steps hits', tot)
        print(f'{tag}: after', sv(s))
        s('render', path=os.path.join(OUTD, f'leave_{tag}.png'))
        s.close()


{'reach': reach, 'after': after, 'leave': leave}[sys.argv[1]]()
