"""move.py: A* movement for the commander's orders (commander README "Design", movement tool).

The game has no pathfinding: a lead walks straight at its target and sticks at a shore. An order's target cell
becomes the lead's target point, the cell centre (cx*256+128, cy*256+128) (README "The target cell is the cell
centre", gate_cellpt.py 16/16), so a movement plan is a list of cells, each sent as a go to `$02` order (camps on
arrival, README order table / gate_ungated.sh), and the real order (attack, get men, ...) goes at the goal cell
from the last leg's centre.

    plan_legs(mp, start, goal, speed) -> (legs, ok, why)
        legs: the intermediate cells (the goal not included); every leg's centre samples land and the straight
        leg (astar.Map.leg, the mode $10/$12 walker's own probe) from the previous point (start, then each
        leg's centre: the walker snaps onto its target at arrival, $14fdc) to it passes, as does the last
        centre -> the goal centre.
    Mover(mp, side, k, goal, final_type)        per-group movement state machine (loop.py --move, ab.py)
        .tick(obs, clock) -> [action dict] | []  issue leg 1, detect arrival (lead in the leg cell, or the group
        camped there), issue the next leg, finally the real order; re-plan from the lead's position when the
        lead makes no progress for STALL steps.

Candidates: the cells of the A* triangle path (astar.Map.astar) in path order, with a land centre (triangle B
under the $1648e rule). Greedy string-pull: from the current point take the farthest candidate whose leg passes.
When no path cell works (a narrow land bridge whose cells have a wet triangle B), cells within Chebyshev radius
SNAP of a path cell are tried, scored by the path index of the nearest path cell. A snapped leg is still checked
with Map.leg; a plan whose legs all fail is reported (ok False) rather than issued.
CLI: move.py <snap> <side> <k> <gx> <gy>   prints the plan from that group's lead to cell (gx, gy).
"""
import math, os, struct, sys
from pathlib import Path

ROOT = Path(os.environ['M68000_ROOT']) if os.environ.get('M68000_ROOT') else \
    next(d for d in Path(__file__).resolve().parents if (d / 'tools' / 'rdis.py').exists())
CMD = ROOT / 'reversing' / 'powermonger' / 'commander'
sys.path.insert(0, str(CMD))
from astar import Map        # noqa: E402

OBJ = 0x51b66                # ai.md object records; byte 16 the speed $164bc reads (astar._step)
GOTO = 0x02
SNAP = 2


def centre(c):
    return (c[0] * 256 + 128, c[1] * 256 + 128)


def land_centre(mp, c):
    return 0 <= c[0] < 64 and 0 <= c[1] < 128 and mp.sample(*centre(c)) != 0


def lead_speed(R, lead):
    return R[OBJ + lead + 16]


def lead_boat(R, lead):
    return R[OBJ + lead + 33] == 0x0a


def plan_legs(mp, start, goal, speed=32, boat=False):
    """(legs, ok, why). start: world point; goal: cell. boat: the lead holds a Boat (byte 33 == $0a): the walker
    skips its water probe (astar.py header) and the group crosses water, so the order goes straight (ab.py p4 on
    rand1: 12 boats, the direct go to crossed the water the model blocks; inferred for boat carriers in general)."""
    g = centre(goal)
    if not land_centre(mp, goal):
        return [], False, 'goal centre is water'
    if boat:
        return [], True, 'boat'
    if mp.leg(start, g, speed)[0]:
        return [], True, 'straight'
    if not mp.reachable(start, g):
        return [], False, 'unreachable'
    tri = mp.astar(start, g)
    pcells = []
    for n in tri:
        cx, cy, _h = mp.centroid(n)
        if not pcells or pcells[-1] != (cx, cy):
            pcells.append((cx, cy))
    idx = {}
    for i, c in enumerate(pcells):
        idx.setdefault(c, i)
    # candidates: (score, cell); path cells first, snapped neighbours as a fallback
    path_c = [(i, c) for i, c in enumerate(pcells) if land_centre(mp, c)]
    snap_c = {}
    for i, (cx, cy) in enumerate(pcells):
        for dx in range(-SNAP, SNAP + 1):
            for dy in range(-SNAP, SNAP + 1):
                c = (cx + dx, cy + dy)
                if c in idx or not land_centre(mp, c):
                    continue
                if c not in snap_c or snap_c[c] < i:
                    snap_c[c] = i
    snap_l = sorted(((i, c) for c, i in snap_c.items()), key=lambda t: (t[0], t[1]))
    legs, cur, pos = [], tuple(start), -1
    start_cell = (start[0] >> 8, start[1] >> 8)
    for _ in range(len(pcells) + 8):
        if mp.leg(cur, g, speed)[0]:
            return legs, True, 'path'
        best = None
        for i, c in reversed(path_c):              # farthest path cell first
            if i <= pos or c == goal or (not legs and c == start_cell and i == 0):
                continue
            if mp.leg(cur, centre(c), speed)[0]:
                best = (i, c)
                break
        if best is None:                           # snap: a nearby land-centred cell, farthest along the path
            for i, c in sorted(snap_l, key=lambda t: (-t[0], t[1])):
                if i <= pos:
                    continue
                if mp.leg(cur, centre(c), speed)[0]:
                    best = (i, c)
                    break
        if best is None:
            return legs, False, 'no walkable leg from %s (path index %d)' % (cur, pos)
        pos, c = best
        legs.append(c)
        cur = centre(c)
    return legs, False, 'leg cap'


class Mover:
    """One group's movement to a goal cell, ending in the real order there."""
    STALL = 12_000_000           # steps without a cell of progress towards the current leg before re-planning
    PIGEON = 12_000_000          # grace for a non-first group: the order travels by pigeon (~9M steps, README)
    MAX_REPLAN = 6

    def __init__(self, mp, side, k, goal, final_type=GOTO, final_xy=None):
        self.mp, self.side, self.k, self.goal = mp, side, k, tuple(goal)
        self.final_type = final_type
        self.final_xy = tuple(final_xy) if final_xy else self.goal
        self.legs, self.i = None, 0          # planned legs, index of the leg in flight
        self.issued = None                   # step of the last order
        self.best = None                     # (best distance to the leg target, step it was reached)
        self.replans = 0
        self.done = False                    # the final order is out
        self.failed = None
        self.events = []                     # (step, what, detail) for the log

    def _group(self, obs):
        S = obs['sides'][self.side] if self.side in obs['sides'] else obs['sides'][str(self.side)]
        return S['groups'][self.k]

    def _order(self, typ, cell, clock, what):
        self.issued, self.best = clock, None
        self.events.append((clock, what, list(cell)))
        return [dict(side=self.side, type=typ, x=cell[0], y=cell[1], group=self.k)]

    def _plan(self, pos, speed, clock, boat=False):
        legs, ok, why = plan_legs(self.mp, pos, self.goal, speed, boat)
        self.events.append((clock, 'plan', dict(frm=list(pos), legs=[list(c) for c in legs], ok=ok, why=why)))
        if not ok:
            self.failed = why
            return False
        self.legs, self.i = legs, 0
        return True

    def target(self):
        return self.goal if self.legs is None or self.i >= len(self.legs) else self.legs[self.i]

    def tick(self, obs, R, clock):
        if self.done or self.failed:
            return []
        g = self._group(obs)
        if not g['alive'] or 'lead_obj' not in g:
            self.failed = 'group gone'
            return []
        lo = g['lead_obj']
        pos, here = (lo['x'], lo['y']), tuple(lo['cell'])
        speed, boat = lead_speed(R, g['lead']), lead_boat(R, g['lead'])
        if self.legs is None:                                  # first call: plan and send leg 1
            if not self._plan(pos, speed, clock, boat):
                return []
            return self._next(clock)
        tgt = self.legs[self.i]
        if here == tgt:                                        # arrival: the lead stands in the leg cell
            self.events.append((clock, 'arrive', dict(cell=list(tgt), state=g['state'])))
            self.i += 1
            return self._next(clock)
        # progress towards the leg target
        c = centre(tgt)
        d = max(abs(pos[0] - c[0]), abs(pos[1] - c[1]))
        if self.best is None or d < self.best[0] - 256:
            self.best = (d, clock)
        grace = self.PIGEON if self.k else 0
        if clock - self.best[1] >= self.STALL and clock - self.issued >= self.STALL + grace:
            self.replans += 1
            self.events.append((clock, 'stall', dict(pos=list(pos), leg=list(tgt), d=d)))
            if self.replans > self.MAX_REPLAN or not self._plan(pos, speed, clock, boat):
                self.failed = self.failed or 'replan cap'
                return []
            return self._next(clock)
        return []

    def _next(self, clock):
        if self.i < len(self.legs):
            return self._order(GOTO, self.legs[self.i], clock, 'leg %d/%d' % (self.i + 1, len(self.legs)))
        self.done = True
        return self._order(self.final_type, self.final_xy, clock, 'final %02x' % self.final_type)


if __name__ == '__main__':
    from observe import load, observe
    snap, side, k, gx, gy = sys.argv[1], *map(int, sys.argv[2:6])
    R = load(ROOT / snap if not os.path.isabs(snap) else snap)
    mp = Map(R)
    g = observe(R)['sides'][side]['groups'][k]
    pos = (g['lead_obj']['x'], g['lead_obj']['y'])
    sp = lead_speed(R, g['lead'])
    print('lead', pos, 'cell', g['lead_obj']['cell'], 'speed', sp)
    print('straight leg:', mp.leg(pos, centre((gx, gy)), sp)[::2])
    print('tick model straight:', mp.simulate_walk(pos, centre((gx, gy)), sp, 3000)[:3])
    print(plan_legs(mp, pos, (gx, gy), sp))
