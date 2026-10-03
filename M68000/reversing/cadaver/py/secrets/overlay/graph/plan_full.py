"""plan_full.py [outdir]: A1 (Cadaver 91st pass) the answer chains, from room 90 (lineage snapshot), as exact leg-wise plans.

Part 1: the delete-relaxed closure (relax.py) without and with the native UNLOCK DOOR scroll: which goals are reachable at all (dead ends).
Part 2: leg-wise exact search (legs.py / sim.py): each leg is a breadth-first search from the exact end state of the previous leg, over the actions of
the blocks that regress from the leg's goal (the support facts of the relaxed plan, closed under 'writes a relevant node'); the hand-built legs of part C
(the six captain objects, room 88) use mfilter.py action lists.  Each leg is minimal within its action set; the concatenation is replayable in
sim.py, not a proof of global minimality.  A player action = a door crossing, TAKE, OPERATE, APPLY, a hero step into a room region, a THROW, a wait or a spell cast.
Writes <outdir>/chains.txt.  Numbers are decimal.
Run from M68000/:  .venv/bin/python reversing/cadaver/py/secrets/overlay/graph/plan_full.py [outdir]"""
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from legs import *
from relax import setup
from mfilter import mfilter
from model import OUTDIR

GOALS = [('a1 key 690', 'ruck:690'), ('a2 door $79 (keyhole 720 + key 690)', 'flag:121'), ('b1 emerald 731 or 730', 'ruck:731'),
         ('b2 door $74 (17 -> 87)', 'flag:116'), ('c  START LEVEL 2', 'level:2')]


def part1(out):
    for spells in (False, True):
        sm, rx = setup(spells=spells); rx.run()
        rooms = sorted(f[1] for f in rx.prov if f[0] == 'room')
        out.append('RELAXED CLOSURE from the lineage state, %s: %d rooms reachable; never reached: %s' % (
            'scripts + UNLOCK DOOR scroll 407' if spells else 'scripts only', len(rooms), sorted(set(sm.w.rooms) - set(rooms))))
        for t, sp in GOALS:
            f = rx.reached(sp)
            out.append('   %-44s %s' % (t, ('reached at layer %d' % rx.prov[f][1]) if f else 'NOT REACHED (dead end of the model)'))
    out.append('   note: the relaxed closure lets the verb-42 countdown of room 88 fire freely, so its "level 2" layer is a lower bound only; part 2 runs the exact countdown (operate 736 needs state bit 0 of 736, set by the sixth captain object in room 87).')
    out.append('')


def run_legs(out):
    sm = Sim(); sm.spells = True
    S = sm.initial()
    H = lambda *ids: (lambda S: all(sm.in_ruck(S, i) for i in ids))
    LEGS = [('gems 716, 717, 718 in the rucksack', H(716, 717, 718), ['ruck:716', 'ruck:717', 'ruck:718'], True),
            ('door $2b open (gem lock 719: 716, 717, 718 in that order)', lambda S: sm.flag(S, 43) == 0, ['flag:43'], True),
            ('door $42 open (keyhole 539 + key 538)', lambda S: sm.flag(S, 66) == 0, ['flag:66'], True),
            ('door $73 open (object 275, room 48)', lambda S: sm.flag(S, 115) == 0, ['flag:115'], True),
            ('hero in room 93 (levers)', lambda S: S['room'] == 93, ['room:93'], True),
            ('GOAL a1: key 690 in the rucksack (room 82)', H(690), ['ruck:690'], True),
            ('UNLOCK DOOR scroll 407 (room 52)', H(407), ['ruck:407'], True),
            ('GOAL a2: door $79 open (keyhole 720, room 53, key 690)', lambda S: sm.flag(S, 121) == 0, ['flag:121'], True),
            ('GOAL b1: emerald 731 in the rucksack (room 90)', H(731), ['ruck:731'], True),
            ('GOAL b2: door $74 open, scripts only (region 1 of room 17 with 731)', lambda S: sm.flag(S, 116) == 0, ['flag:116'], False),
            ('urn 611 warm (ashes 227 applied)', lambda S: sm.ost(S, 611)[2] == 1, ['b0:611'], True)]
    total = []; marks = {}
    def emit(name, path, S):
        n_script = sum(1 for a, t in path if a[0] != 'walk')
        out.append('  LEG %s: %d actions (%d walks, %d script actions)' % (name, len(path), len(path) - n_script, n_script))
        for a, tr in path: out.append('      %-76s %s' % (sm.describe(a), ('fires ' + ' '.join(tr)) if tr else ''))
    for name, goal, specs, spl in LEGS:
        r, err = leg(sm, S, name, goal, specs, spells=spl, maxdepth=28, verbose=False)
        if not r: out.append('  LEG %s: FAILED (%s)' % (name, err)); return total, S
        path, S = r; total += path; emit(name, path, S)
        out.append('      [cumulative %d actions; room %d, health ledger %d, gold %d]' % (len(total), S['room'], S['health'], S['gold']))
        if name.startswith('GOAL'): marks[name[:7]] = len(total)
    # ---- part C: six captain objects into room 96 through region 1 of room 87
    def hand(name, goal, flt, maxdepth=30):
        nonlocal S, total
        r = sm.bfs(S, goal, maxdepth=maxdepth, maxstates=1500000, action_filter=flt, verbose=False)
        if not r:
            import pickle; pickle.dump(S, open('/tmp/plan_state.pkl', 'wb')); out.append('  LEG %s: FAILED' % name); return False
        path, S2 = r; S = S2; total += path; emit(name, path, S)
        out.append('      [cumulative %d actions; room %d, health ledger %d, gold %d]' % (len(total), S['room'], S['health'], S['gold']))
        return True
    inr = lambda o: (lambda S: sm.ost(S, o)[0] == 96)
    # room 87's entry block deletes every rucksack entry of template 51, 52, 53, 93, 115, 140 (verb 82): the scroll 407 (template 93) is gone after the first
    # entry, so everything that needs the spell (room 24 for object 507) is done BEFORE the first entry; the urn 611 and the three hidden captain objects are carried in.
    if not hand('pick up urn 611 and the captain objects 302 (operate 230, room 16), 703 (operate 602, room 41), 507 (operate 492, room 24; door $24 needs the spell; TAKE 507 teleports into room 86, door $72 needs the spell)',
                lambda S: all(sm.in_ruck(S, o) for o in (611, 302, 703, 507)),
                mfilter(ops=(230, 602, 492), takes=(611, 302, 703, 507), cast=True), maxdepth=40): return total, S
    if not hand('room 87: urn 611 then emerald 731 thrown at object 413 (event 4): state0(419) set', lambda S: sm.ost(S, 419)[2] == 1, mfilter(cast=True), maxdepth=30): return total, S
    if not hand('six captain objects 341, 493, 681, 302, 703, 507 thrown into region 1 of room 87 (each PLACEd in room 96 by r87.0@17)',
                lambda S: all(sm.ost(S, o)[0] == 96 for o in (341, 493, 681, 302, 703, 507)), mfilter(throws=(341, 493, 681, 302, 703, 507))): return total, S
    if not hand('room 88: operate 736, wait the countdown, hero into region 1 -> START LEVEL 2', lambda S: S['level'] == 2,
                mfilter(ops=(736,)), maxdepth=30): return total, S
    marks['c'] = len(total)
    out.append('')
    out.append('CUMULATIVE ACTION COUNTS: %s; total %d' % (marks, len(total)))
    return total, S


def main():
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTDIR
    outdir.mkdir(exist_ok=True)
    out = ['CHAINS from room 90 (lineage snapshot: health 60, gold 0, rucksack [(680, 93)], VAR 6 = 1, 7 = 2, 13 = 1, lever 225 armed, 3 non-keep blocks spent)', '']
    part1(out)
    t = time.time()
    run_legs(out)
    out.append('(search time %.0fs)' % (time.time() - t))
    (outdir / 'chains.txt').write_text('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
