"""campaign.py - march the human's people from their north-west start to the evil towns through the
game's own UI (popdrive clicks only), so that gather/fight decisions happen next to enemies.

From late4.snap (frame 2161, side 0 has no leader, magnet (8,20)):
  1. click mode_magnet (go to papal magnet): the first walker on the magnet becomes the leader;
  2. repeatedly: scroll (minimap click) to a view holding the leader and the next hop, click
     ui_magnet, click the land corner (hop.x+1, hop.y+1) -> cmd 5 at hop; run until the leader is
     within 1 cell of the magnet;
  3. near the target, save snaps/near.snap, then click mode_gather / mode_fight into
     snaps/gather1.snap / snaps/fight1.snap.
Writes a log of every step to stdout.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
import popdrive as D
from repl import Repl
from popcfg import WORK

WD = os.path.join(WORK, 'walker')
TARGET = (22, 47)
FR = D.FRAME


class Live:
    def __init__(self, snap):
        self.r = Repl(os.path.abspath(snap))
        self.g = D.Game(self.r)

    def feed(self, lines):
        for ln in lines: self.r.cmd(ln)
        self.g.refresh()

    def frames(self, n): self.r.cmd('s %d' % (FR * n)); self.g.refresh()
    def w(self, a): return D.Mem(self.r).w(a)
    def l(self, a): return D.Mem(self.r).l(a)

    def side(self, s=0):
        b = 0x3b226 + 16 * s
        return dict(leader=self.w(b), magnet=self.w(b + 2), mode=self.w(b + 4), mana=self.l(b + 12))

    def leader_cell(self):
        ld = self.side()['leader']
        return None if ld == 0 else self.w(0x3b278 + 0x16 * (ld - 1) + 8)

    def click(self, x, y, button='l'):
        self.feed(D.click_lines(self.g.px, self.g.py, x, y, button))

    def icon(self, name):
        x, y = D.icon_point(name); self.click(x, y)

    def scroll_to(self, view):
        """minimap click giving view origin `view` exactly (origin = (u-3, v-3), u+v even)."""
        ox, oy = view
        for u, v in ((ox + 3, oy + 3), (ox + 4, oy + 4)):
            if (u + v) % 2: continue
            x, y = D.screen_of_uv(u, v)
            if D.classify(x, y) == ('minimap', (u, v)):
                self.click(x, y); return True
        return False

    def snap(self, path): self.r.cmd('snap %s' % os.path.abspath(path))


def views_for(cell, corner):
    """view origins (even u+v reachable) with the entity cell and the corner well inside."""
    cx, cy = cell & 63, cell >> 6
    out = []
    for ox in range(0, 57):
        for oy in range(0, 57):
            if (ox + oy) % 2: continue
            if ox <= cx <= ox + 7 and oy <= cy <= oy + 7 and \
               ox + 1 <= corner[0] <= ox + 8 and oy + 1 <= corner[1] <= oy + 8:
                out.append((abs(ox + 4 - corner[0]) + abs(oy + 4 - corner[1]), (ox, oy)))
    return [v for _, v in sorted(out)]


def main():
    L = Live(os.path.join(WORK, 'late4.snap'))
    print('start', L.side(), 'frame', L.w(0x3c4c8))
    L.icon('mode_magnet')
    for _ in range(40):
        if L.side()['leader']: break
        L.frames(20)
    print('leader', L.side(), 'cell', L.leader_cell(), 'frame', L.w(0x3c4c8))
    for hop in range(12):
        lc = L.leader_cell()
        if lc is None:
            print('no leader'); L.frames(40); continue
        lx, ly = lc & 63, lc >> 6
        if abs(lx - TARGET[0]) + abs(ly - TARGET[1]) <= 2: break
        hx = lx + max(-4, min(4, TARGET[0] - lx))
        hy = ly + max(-4, min(4, TARGET[1] - ly))
        corner = (hx + 1, hy + 1)
        done = False
        for view in views_for(lc, corner)[:6]:
            if not L.scroll_to(view): continue
            L.frames(2)
            if L.g.own_visible == 0 or L.g.view != view:
                continue
            pt = L.g.best_point_for_corner(*corner)
            if pt is None: continue
            L.icon('ui_magnet')
            L.click(*pt)
            L.frames(2)
            mg = L.side()['magnet']
            print('hop', hop, 'leader', (lx, ly), 'view', view, 'corner', corner, '->magnet',
                  (mg & 63, mg >> 6), 'mana', L.side()['mana'], 'frame', L.w(0x3c4c8))
            done = (mg == hy * 64 + hx)
            break
        if not done:
            print('hop', hop, 'failed at leader', (lx, ly)); break
        for _ in range(30):
            lc = L.leader_cell()
            if lc is None: break
            if abs((lc & 63) - hx) <= 1 and abs((lc >> 6) - hy) <= 1: break
            L.frames(8)
    L.snap(os.path.join(WD, 'snaps', 'near.snap'))
    print('near', L.side(), L.side(1), 'leader cell', L.leader_cell(), 'frame', L.w(0x3c4c8))
    L.r.close()


if __name__ == '__main__':
    main()
