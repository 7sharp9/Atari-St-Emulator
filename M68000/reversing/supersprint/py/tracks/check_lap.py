"""Check a recorded drone lap (data/drone_T.csv) against the racing line decoded from SUPER.DAT.
For each drone car: (1) its waypoint-index sequence vs trackpath.walk() for that car's lane (transition match count),
(2) distance of its screen position from the nearest point of the decoded lane polyline, (3) laps completed (wp wraps)."""
import sys, csv, math; sys.path.insert(0,'.')
from tkcommon import *
import trackdata as TD, trackpath as TP

def load(T):
    rows = {}
    with open(out('data', 'drone_%d.csv' % T)) as fh:
        for r in csv.DictReader(fh):
            rows.setdefault(int(r['car']), []).append({k: int(v) for k, v in r.items()})
    return rows

def dist_to_poly(p, segs):
    best = 1e9
    for (x0, y0), (x1, y1) in segs:
        vx, vy = x1 - x0, y1 - y0; L = vx*vx + vy*vy
        t = 0 if L == 0 else max(0, min(1, ((p[0]-x0)*vx + (p[1]-y0)*vy) / L))
        d = math.hypot(p[0] - (x0 + t*vx), p[1] - (y0 + t*vy)); best = min(best, d)
    return best

def check(T, verbose=True):
    rows = load(T); n = len(TD.waypoints(T)); res = {}
    for car, rs in rows.items():
        if rs[0]['droneflag'] == 0: continue
        allsucc = TP.successors(T, car)
        lane = set(TP.walk(T, car))
        # reachable set over all gate phases, starting from wp 0
        reach = {0}; todo = [0]
        while todo:
            a = todo.pop()
            for b in allsucc[a]:
                if b not in reach: reach.add(b); todo.append(b)
        succ = {a: allsucc[a] for a in reach}
        obs = []
        for r in rs:
            if not obs or obs[-1] != r['wp']: obs.append(r['wp'])
        ok = sum(1 for a, b in zip(obs, obs[1:]) if b in succ.get(a, ()))
        off_lane = sum(1 for a in obs if a not in succ)
        recs = TD.waypoints(T)
        segs = []
        for a in reach:
            if recs[a][3] <= 15:                       # control records carry no geometry
                p0, p1 = TP.segment(recs[a]); segs.append(((p0[0]/8, p0[1]/8), (p1[0]/8, p1[1]/8)))
        # only frames where the car is actually moving along the line (edge flag 0, not stunned)
        ds = [dist_to_poly((r['x'], r['y']), segs) for r in rs if r['edge'] == 0 and r['stun'] <= 0]
        laps = sum(1 for a, b in zip(obs, obs[1:]) if b < a and a > n - 10)
        res[car] = dict(transitions=len(obs)-1, matched=ok, off_lane=off_lane, frames=len(ds),
                        mean_px=sum(ds)/len(ds), max_px=max(ds), laps=laps, first=obs[:6], hit_edge=sum(1 for r in rs if r['edge']), )
        if verbose:
            print('track %d car %d: wp transitions %d, equal to decoded lane successor %d, wp outside lane %d; '
                  'pos-to-line mean %.2f px max %.2f px over %d frames; lap wraps %d; edge-flag frames %d' %
                  (T+1, car, res[car]['transitions'], ok, off_lane, res[car]['mean_px'], res[car]['max_px'], len(ds), laps, res[car]['hit_edge']))
    return res

if __name__ == '__main__':
    for T in map(int, sys.argv[1:] or range(8)): check(T)
