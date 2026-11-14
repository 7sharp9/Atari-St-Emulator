"""gate.py - drive a planned causeway through Populous's own mouse UI and compare with the model.

usage (from M68000/):  uv run python reversing/populous/py/causeway/gate.py <tag> <snapshot-name> "x,y;x,y;..." [startcell x,y]
Two chains from the same prepared snapshot: ACT (every click) and CTL (identical frames, the raise clicks'
mouse down/up removed).  Per click: corner raised 0 -> 1, $37f8a == 1, mana(ACT) - mana(CTL) delta == -14.
At the end: 4225 corners ACT vs model(H0, clicks), vs model(H_CTL, clicks), mana, shape map walkability vs model.
POKES (labelled): own walker idx 7 is teleported to a land cell inside the view (entity +8 cell, +10, +18 zeroed,
+4 str 3000, occupancy map moved) because a land click needs an own entity in view ($3d54e) and the islands'
settlements are out of reach of the gaps."""
import os, sys, json, struct
from causelib import *
from planner import replay, connected
from popdrive import Game, run, click_lines, classify
WALKER = 7
def lmana(m): return struct.unpack_from('>i', m, 0x3b232)[0]

def teleport(m, cell):
    a = ENT + 0x16*WALKER
    old = w(m, a+8)
    return ['ww %x %04x' % (a+8, cell), 'ww %x %04x' % (a+10, 0), 'ww %x %04x' % (a+12, 0), 'ww %x %04x' % (a+18, 0), 'ww %x %04x' % (a+4, 3000),
            'wb %x 00' % (0x37fd4+old), 'wb %x %02x' % (0x37fd4+cell, WALKER+1)]

def pick_cell(m, view, near):
    h = heights(m); ox, oy = view; best = None
    for x in range(ox, ox+8):
        for y in range(oy, oy+8):
            if cell_walkable(h, x, y, shapes(m)):
                d = (x-near[0])**2 + (y-near[1])**2
                if best is None or d < best[0]: best = (d, y*64+x)
    return best[1]

def strip_raise(lines):
    """drop the last 'mouse down l' / 'mouse up l' pair (the raise click); keep the steps"""
    out = list(lines); i = max(k for k, s in enumerate(out) if s == 'mouse down l'); j = max(k for k, s in enumerate(out) if s == 'mouse up l')
    del out[j]; del out[i]; return out

def main():
    tag, snap, cl = sys.argv[1], sys.argv[2], sys.argv[3]
    clicks = [tuple(map(int, s.split(','))) for s in cl.split(';')]
    D = os.path.join(DATA, 'snaps', tag); os.makedirs(D, exist_ok=True)
    S0 = os.path.join(WORK, snap + '.snap')
    m0 = ram(S0); H0 = heights(m0); shp0 = shapes(m0)
    start = tuple(map(int, sys.argv[4].split(','))) if len(sys.argv) > 4 else clicks[0]
    # prep both chains identically: poke walker next to the first click, 2 frames to draw
    near = (clicks[0][0], clicks[0][1])
    g0 = Game(m0); v0 = g0.view_for_corner(*clicks[0])
    Hm, mana_model, costs = replay(H0, clicks)
    log = dict(tag=tag, snap=snap, clicks=clicks, costs=costs, pokes=[])
    act = os.path.join(D, 'act0.snap'); ctl = os.path.join(D, 'ctl0.snap')
    # first: scroll (both chains) so the view is known, then place the walker inside it
    cur_a = cur_c = S0; n = 0; pokes = 0
    per = []
    for idx, (cx, cy) in enumerate(clicks):
        ma = ram(cur_a); g = Game(ma)
        if g.best_point_for_corner(cx, cy) is None:
            view, (mx, my) = g.view_for_corner(cx, cy)
            sl = click_lines(g.px, g.py, mx, my)
            for which in ('a', 'c'):
                cur = cur_a if which == 'a' else cur_c
                out = os.path.join(D, 'k%d_scroll_%s.snap' % (idx, which)); run(cur, sl, out)
                if which == 'a': cur_a = out
                else: cur_c = out
            ma = ram(cur_a); g = Game(ma)
        # own entity in view?  The walker must be inside the view window and alive; re-place it if not (labelled poke)
        e = [x for x in entities(ma) if x['i'] == WALKER]
        ox, oy = g.view
        inwin = e and ox <= (e[0]['cell'] & 63) < ox+8 and oy <= (e[0]['cell'] >> 6) < oy+8
        if not inwin or idx == 0:
            cell = pick_cell(ma, g.view, (cx, cy)); pl = teleport(ma, cell) + ['s 240000']; pokes += 1
            log['pokes'].append(dict(before_click=idx, view=g.view, walker_cell=(cell & 63, cell >> 6)))
            for which in ('a', 'c'):
                cur = cur_a if which == 'a' else cur_c
                out = os.path.join(D, 'k%d_poke_%s.snap' % (idx, which)); run(cur, pl, out)
                if which == 'a': cur_a = out
                else: cur_c = out
            ma = ram(cur_a); g = Game(ma)
        mc = ram(cur_c)
        pt = g.best_point_for_corner(cx, cy)
        lines = click_lines(g.px, g.py, pt[0], pt[1], 'l')
        out_a = os.path.join(D, 'k%d_a.snap' % idx); out_c = os.path.join(D, 'k%d_c.snap' % idx)
        run(cur_a, lines, out_a); run(cur_c, strip_raise(lines), out_c)
        ma2, mc2 = ram(out_a), ram(out_c)
        Ha, Ha2 = heights(ma), heights(ma2)
        dm = (lmana(ma2) - lmana(ma)) - (lmana(mc2) - lmana(mc))
        per.append(dict(click=(cx, cy), h_before=Ha[cy*65+cx], h_after=Ha2[cy*65+cx], f8a=w(ma2, 0x37f8a), dmana=dm, pred=-costs[idx],
                        own_visible=w(ma2, 0x3d54e), ok=(Ha[cy*65+cx] == 0 and Ha2[cy*65+cx] == 1 and dm == -costs[idx])))
        print('click', idx, per[-1], flush=True)
        cur_a, cur_c = out_a, out_c
    ma, mc = ram(cur_a), ram(cur_c)
    Ha, Hc = heights(ma), heights(mc)
    # models
    exact = sum(Ha[i] == Hm[i] for i in range(N*N))
    Hmc, _, _ = replay(Hc, clicks)
    exact_ctl = sum(Ha[i] == Hmc[i] for i in range(N*N))
    noise = sum(Hc[i] != H0[i] for i in range(N*N))
    dmana = lmana(ma) - lmana(mc)
    # broken-model control: one click moved by one corner
    bad = list(clicks); bad[len(bad)//2] = (bad[len(bad)//2][0]+1, bad[len(bad)//2][1])
    Hb, mb, _ = replay(H0, bad); Hbc, _, _ = replay(Hc, bad)
    # extra-click model: mana prediction for k+1 clicks
    # walkability of the real shape map vs the height model
    sha = shapes(ma)
    walk_real = [sha[i] != 0 for i in range(4096)]
    walk_model = [any(Ha[y*N+x] > 0 for x, y in corners_of(i & 63, i >> 6)) for i in range(4096)]
    wmatch = sum(a == b for a, b in zip(walk_real, walk_model))
    comps_ok = None
    g = Gen(0)
    goal = None
    res = dict(tag=tag, snap=snap, clicks=clicks, costs=costs, model_mana=mana_model,
               per_click_ok=sum(p['ok'] for p in per), n_clicks=len(per),
               corners_exact_vs_model_H0=exact, corners_exact_vs_model_CTL=exact_ctl, total_corners=N*N,
               ctl_noise_corners_vs_H0=noise, mana_delta_act_minus_ctl=dmana, mana_predicted=-mana_model,
               broken_model_corners_exact=sum(Ha[i] == Hb[i] for i in range(N*N)), broken_model_corners_exact_ctl=sum(Ha[i] == Hbc[i] for i in range(N*N)),
               broken_click=bad, broken_mana_pred=-mb, walk_cells_match=wmatch, walk_cells_total=4096, pokes=log['pokes'], per=per)
    json.dump(res, open(os.path.join(DATA, 'gate_%s.json' % tag), 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per'}, indent=1))
    # also save the final ACT snapshot copy for rendering
    os.replace(cur_a, os.path.join(D, 'final_act.snap')); os.replace(cur_c, os.path.join(D, 'final_ctl.snap'))
main()
