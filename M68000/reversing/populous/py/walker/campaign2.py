"""campaign2.py - UI-only march of the human's people across the sea to the south-west evil towns.

The human starts on an island (x 4..16, y 2..21 of GENESIS). Five single-corner raises
(0 -> 1 turns the four cells round the corner into walkable shore) join it to the chain of islets
leading to the evil settlement at (29,51):
    corners (17,23) (18,25) (18,27)   island -> islet x18..29 y26..35
    corners (23,42) (26,47)           islets y36..46 -> evil land y48..
Magnet mode (0) + papal-magnet hops along the path move the leader and its followers. Everything is
a popdrive click: minimap scrolls, ui_land + land corner (raise), ui_magnet + land corner (magnet).
A raise click needs one of your entities in the view ($11a5a: $3d54e != 0 when ui_mode == 2); a
magnet click does not (ui_mode is 5/6 then).

Start snaps/near.snap (made by campaign.py: late4 + mode_magnet, leader 12 at (8,20)); writes
snaps/front.snap.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import campaign as C
import popdrive as D

WD = C.WD
PATH = [(None, (15, 20)), ((17, 23), (17, 24)), ((18, 25), None), ((18, 27), (19, 29)),
        (None, (20, 34)), (None, (20, 38)), ((23, 42), (22, 40)), ((26, 47), (24, 44)),
        (None, (26, 47)), (None, (27, 49))]


def height(L, cx, cy): return D.Mem(L.r).sw(D.HEIGHTS + 2 * (cy * 65 + cx))


def own_cells(L):
    n = L.w(0x3c4e2); out = []
    raw = D.Mem(L.r).rd(0x3b278, n * 0x16)
    for i in range(n):
        p = raw[i * 0x16:(i + 1) * 0x16]
        if p[1] == 0 and (p[4] << 8 | p[5]) > 0 and p[0] in (1, 2):
            out.append((p[8] << 8 | p[9]))
    return out


def raise_corner(L, corner):
    for oc in sorted(own_cells(L), key=lambda c: abs((c & 63) - corner[0]) + abs((c >> 6) - corner[1])):
        for view in C.views_for(oc, corner)[:4]:
            if not L.scroll_to(view): continue
            L.frames(2)
            if L.g.own_visible == 0 or L.g.view != view: continue
            pt = L.g.best_point_for_corner(*corner)
            if pt is None: continue
            h0 = height(L, *corner)
            L.icon('ui_land'); L.click(*pt); L.frames(2)
            h1 = height(L, *corner)
            print('raise', corner, 'view', view, 'height', h0, '->', h1, 'mana', L.side()['mana'],
                  'frame', L.w(0x3c4c8))
            if h1 > h0: return True
    return False


def magnet_to(L, cell):
    cx, cy = cell
    v = L.g.view_for_corner(cx + 1, cy + 1)
    if v is None: return False
    view, (mx, my) = v
    L.click(mx, my); L.frames(2)
    pt = L.g.best_point_for_corner(cx + 1, cy + 1)
    if pt is None: return False
    L.icon('ui_magnet'); L.click(*pt); L.frames(2)
    mg = L.side()['magnet']
    print('magnet ->', (mg & 63, mg >> 6), 'want', cell, 'mana', L.side()['mana'], 'frame', L.w(0x3c4c8))
    return mg == cy * 64 + cx


def wait_leader(L, cell, maxf=400):
    for _ in range(maxf // 8):
        lc = L.leader_cell()
        if lc is not None and abs((lc & 63) - cell[0]) <= 1 and abs((lc >> 6) - cell[1]) <= 1:
            break
        L.frames(8)
    lc = L.leader_cell()
    print('  leader at', None if lc is None else (lc & 63, lc >> 6), 'frame', L.w(0x3c4c8))


def main():
    L = C.Live(os.path.join(WD, 'snaps', 'near.snap'))
    print('start', L.side(), 'leader', L.leader_cell(), 'frame', L.w(0x3c4c8))
    for corner, hop in PATH:
        if corner and not raise_corner(L, corner):
            print('raise failed', corner); break
        if hop:
            if not magnet_to(L, hop):
                print('magnet failed', hop); break
            wait_leader(L, hop)
        L.snap(os.path.join(WD, 'snaps', 'front.snap'))
    L.snap(os.path.join(WD, 'snaps', 'front.snap'))
    print('end', L.side(), L.side(1), 'frame', L.w(0x3c4c8))
    L.r.close()


if __name__ == '__main__':
    main()
