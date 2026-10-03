"""legs.py: A1 (Cadaver 91st pass) leg-wise exact planner.  A leg = (name, goal predicate, goal fact specs for the relaxed closure).
From the exact end state of the previous leg: (1) run the relaxed closure (relax.py) started at that state to get the support DAG of the goal;
(2) seed the relevant-node set with the facts of that plan (its rooms, every door of those rooms, its items, flags, objects, variables) and
close it under 'a block that writes a relevant node is relevant, its guards become relevant' (sim.relevant_blocks, movement off); (3) run the exact
breadth-first search (sim.py) over only the actions of relevant blocks (+ all door walks) to the goal.  Each leg is therefore minimal within its
relevant action set; the concatenation is a valid, replayable script-level sequence, not a proof of global minimality."""
import sys, re, time, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from relax import Relaxed
from sim import Sim, relevant_blocks, make_filter


def plan_nodes(sm, rx, facts, w):
    seeds = set(); rooms = set()
    for f in facts:
        for rnd, label, x in rx.plan(f):
            if rnd == 0 and x[0] != 'room': pass
            if x[0] == 'room': rooms.add(x[1])
            if x[0] == 'flag': seeds.add(('flag', x[1]))
            if x[0] == 'var': seeds.add(('var', x[1]))
            if x[0] == 'item': seeds.add(('item', x[1])); seeds.add(('exist', x[1]))
            if x[0] == 'obj':
                seeds.add(('exist', x[1])); 
                if x[2] == 'b0': seeds.add(('state0', x[1]))
                if x[2] == 'b1': seeds.add(('state1', x[1]))
                if x[2] == 'lock': seeds.add(('lock', x[1]))
                if x[2] == 'acti': seeds.add(('acti', x[1]))
    neigh = set(rooms)
    for r in rooms:
        for d in w.rooms[r]['doors']:
            for o in sm.door_owner[d]: neigh.add(o)
    for r in neigh: seeds.add(('tele', r))
    for r in rooms:
        for d in w.rooms[r]['doors']:
            seeds.add(('flag', d))
            fw = w.flags[d]['word']
            if 0 < fw < 0x8000: seeds.add(('item', fw)); seeds.add(('exist', fw))
    return seeds


def leg(sm, S0, name, goal, specs, spells=False, maxdepth=26, maxstates=1_200_000, extra_nodes=(), verbose=True):
    rx = Relaxed(sm, start=S0, spells=spells)
    rx.run()
    facts = [rx.reached(sp) for sp in specs]
    if not all(facts):
        return None, 'relaxed closure from this state does not reach %s' % [sp for sp, f in zip(specs, facts) if not f]
    seeds = plan_nodes(sm, rx, facts, sm.w) | set(extra_nodes)
    rel, nodes = relevant_blocks(sm.w, seeds, movement=False)
    flt = make_filter(sm, rel, nodes)
    base = flt
    def f(S, act):
        if act[0] == 'cast8': return spells
        return base(S, act)
    if verbose: print('  leg %s: relaxed layer %s, %d relevant blocks' % (name, max(rx.prov[x][1] for x in facts), len(rel)), flush=True)
    r = sm.bfs(S0, goal, maxdepth=maxdepth, maxstates=maxstates, action_filter=f, verbose=False)
    if r is None: return None, 'exact BFS found nothing within depth %d / %d states' % (maxdepth, maxstates)
    return r, None
