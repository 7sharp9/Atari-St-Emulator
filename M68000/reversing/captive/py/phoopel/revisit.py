"""Can a finished target be entered and finished again? (ai.md "Finishing a base", world.md "Targets and landing seeds")

revisit.py exit     from phoopel/finish_base1_blast_state2.snap: labelled pokes put the party on the entrance facing N,
                    then the leave click (as leave.py). Prints target 1's entry 14170(A6)+0 and the count 14794(A6)
                    before and after: $87ee sets bit 1 of byte 2, $87f4 adds 1 to the count.
revisit.py land     from base1/site.snap (target 1 of mission 1 selected on the map, by play), twice: a control, and with
                    the one labelled poke byte 2 |= 2 on target 1's entry (what `exit` shows $87ee writing). Each run
                    clicks ORBIT and LAND as natural_base.repl does, stops at the fed_MapGen call $b5c2 (D2), runs on
                    30M steps, then pokes the party onto the entrance cell 13556(A6) (labelled) and counts the base-entry
                    test's hit $bd84 over 3M steps. Request 1 (written at $2f61a) gives mode 1, request 2 ($2f630) mode 2.
revisit.py blast    from exit's exited.snap, 4M steps on (rebuild done, party on the entrance (22,22) in its walled box):
                    20M steps with the party left there, against: turn to face N, the compound door's code 8 (TL, BL, TR,
                    BR) clicked from inside, four steps N. Counts the state-4 explosion $107cc, the droid-damage entry
                    $9a9a and the droid death $e6dc; reads the live-droid count 410(A6) and 14800(A6).
Outputs under scratchpad/captive/phoopel/revisit/.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../ai'))
from cap import *

F = [('mode', 13564), ('13410', 13410), ('target14782', 14782), ('visited14794', 14794), ('14880', 14880)]
sv = lambda s: {n: w16(s, o) for n, o in F}
ent = lambda s: s.read(A6 + 14170, 4).hex()
OUTD = os.path.join(W, 'phoopel', 'revisit')


def click(s, dx, dy, settle):
    s('mouse', action='move', dx=dx, dy=dy); s('step', n=30000)
    s('mouse', action='down', button='l'); s('step', n=60000)
    s('mouse', action='up', button='l'); s('step', n=settle)


def run_until(s, pc, n):
    r = s('run', max_steps=n, until_pc=[pc, pc | 0x80000000])
    return r['reason']


def exit_run():
    s = srv('phoopel/finish_base1_blast_state2.snap')
    for off, v in ((26, w16(s, 22)), (28, w16(s, 24)), (30, 0)):
        s('poke', addr=A6 + off, width=2, value=v)
    s('step', n=180000)
    print('labelled pokes: party onto the entrance, facing 0')
    print('before', sv(s), 'entry', ent(s))
    s('watch_add', lo=A6 + 13410, hi=A6 + 13411, kind='w')
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
    s('mouse', action='move', dx=100, dy=105); s('step', n=30000)
    s('mouse', action='down', button='l')
    h = s('hits', steps=60000, addrs=['$87d6', '$87ee', '$87f4', '$8836'])
    s('mouse', action='up', button='l')
    h2 = s('hits', steps=3_000_000, addrs=['$87d6', '$87ee', '$87f4', '$8836'])
    print('hits', ' '.join(f"{a['addr']}:{a['count'] + b['count']}" for a, b in zip(h['hits'], h2['hits'])))
    print('after ', sv(s), 'entry', ent(s))
    ex, party = l32(s, 13556), l32(s, 26)
    print(f'entrance 13556 = ({ex >> 16},{ex & 0xffff}), party ({party >> 16},{party & 0xffff})')
    print('writes to 13410:', s('watch_events'))
    os.makedirs(OUTD, exist_ok=True)
    s('save', path=os.path.join(OUTD, 'exited.snap'))
    s('render', path=os.path.join(OUTD, 'exited.png'))
    s('step', n=30_000_000)
    party = l32(s, 26)
    print(f'30M later: {sv(s)}, party ({party >> 16},{party & 0xffff})')
    s('render', path=os.path.join(OUTD, 'exited_30m.png'))
    s.close()


def land_run():
    s = srv('base1/site.snap')
    base = s('fork')['id']
    for tag in ('control', 'visited'):
        s('restore', id=base)
        e = bytearray(s.read(A6 + 14170, 4))
        if tag == 'visited':
            s('poke', addr=A6 + 14170 + 2, width=1, value=e[2] | 2)
        print(f'{tag}: entry {ent(s)}', sv(s))
        click(s, 100, -34, 30_000_000)                                      # ORBIT
        s('mouse', action='move', dx=49, dy=-2); s('step', n=30000)         # LAND
        s('mouse', action='down', button='l'); s('step', n=60000)
        s('mouse', action='up', button='l')
        reason = run_until(s, 0xb5c2, 20_000_000)
        print(f'{tag}: to $b5c2: {reason}, D2 = {s.reg("d2") & 0xffff}, mode {w16(s, 13564)}')
        run_until(s, 0xb5c6, 5_000_000)
        s('step', n=30_000_000)
        ex, party = l32(s, 13556), l32(s, 26)
        print(f'{tag}: after 30M: mode {w16(s, 13564)}, entrance 13556 = ({ex >> 16},{ex & 0xffff}), '
              f'party ({party >> 16},{party & 0xffff})')
        s('poke', addr=A6 + 26, width=4, value=ex)
        h = s('hits', steps=3_000_000, addrs=['$bd6a', '$bd84', '$b5c2'])
        print(f'{tag}: party poked onto the entrance; hits', ' '.join(f"{a['addr']}:{a['count']}" for a in h['hits']),
              '; after', sv(s))
    s.close()


def blast_run():
    s = srv(os.path.join(OUTD, 'exited.snap'))
    s('step', n=4_000_000)
    print('settled: party', hex(l32(s, 26)), 'facing', w16(s, 30), 'mode', w16(s, 13564), '13410', w16(s, 13410),
          'door (22,21) tile', s.read(A6 + 9242 + 64 * 21 + 22, 1).hex())
    base = s('fork')['id']

    def key(k):
        s('kbd', bytes=[k]); s('step', n=60000); s('kbd', bytes=[k | 0x80]); s('step', n=600000)

    for tag, keys in (('stand', []), ('turn only', ['L', 'L', 'F', 'F']), ('walk out', ['L', 'L', 'CODE', 'F', 'F', 'F', 'F'])):
        s('restore', id=base)
        for k in keys:
            if k == 'CODE':
                for _ in range(3):
                    s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
                for dx, dy in ((70, 80), (0, 65), (64, -65), (0, 65)):
                    click(s, dx, dy, 600000)
            else:
                key({'F': 0x68, 'L': 0x67, 'R': 0x69}[k])
        p = l32(s, 26)
        print(f'{tag}: inputs {keys}, party ({p >> 16},{p & 0xffff}) facing {w16(s, 30)}, door tile',
              s.read(A6 + 9242 + 64 * 21 + 22, 1).hex())
        h = s('hits', steps=20_000_000, addrs=['$107cc', '$9a9a', '$e6dc'])
        print(f'{tag}: 20M steps: hits', ' '.join(f"{a['addr']}:{a['count']}" for a in h['hits']),
              f'; live droids 410 = {w16(s, 410)}, 14800 = {w16(s, 14800)}')
    s.close()


{'exit': exit_run, 'land': land_run, 'blast': blast_run}[sys.argv[1]]()
