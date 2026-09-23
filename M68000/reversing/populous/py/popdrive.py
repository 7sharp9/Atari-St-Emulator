"""popdrive.py - drive Populous through its own mouse UI.

Turns "raise corner (x,y)", "click icon NAME" or "scroll the view to (ox,oy)" into exact REPL
`mouse move` / `mouse down` / `mouse up` lines, computed from the game's pointer and view state.

The game (see ../README.md, section "Driving play") keeps the IKBD in absolute mode and
interrogates it every VBL: $24748/$2474a = pointer x/y, $2474c = button byte (bit 2 left,
bit 0 right). The VBL latches a press into $3d528 (left) / $3c4d6 (right) = 0 and copies the
pointer into $3c518/$3c51c; everything below reads that latched position.

UI hit tests, all in the diamond coordinates  u = y + (x>>1) - 32,  v = y - (x>>1) + 32:
  $c3e2  minimap   0 <= u,v < 64        view origin := (u-3, v-3) clamped 0..56
         right     u > $112             icon (col,row) = ((u-$110)/16, (v-$20)/16)
         panel     v >= $92             icon (col,row) = ((u-$60)/16, (v-$90)/16)
  $119e6 land      $3e<=u<=$10a, -$40<=v<=$88, x >= $40, and (own entity in view $3d54e,
                   or not land mode, or paint mode). Column c = (x-$38)>>4 picks 9 corners on a
                   screen column; the last corner whose screen y (sy + 16k - 8*height) <= y+4 wins.

Library use: Game(mem) with mem = snapshot RAM bytes (popmem.ram) or a live Repl; CLI:
  python popdrive.py <snap> raise X Y      print the REPL lines for one raise (scrolls first)
  python popdrive.py <snap> icon NAME      print the REPL lines for one icon click
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MOUSE_X, MOUSE_Y, MOUSE_BTN = 0x24748, 0x2474a, 0x2474c
LATCH_X, LATCH_Y = 0x3c518, 0x3c51c
BTN_L, BTN_R = 0x3d528, 0x3c4d6
VIEW_X, VIEW_Y = 0x37e7a, 0x249ae
UI_MODE = 0x21d50          # 1 query, 2 raise/lower land, |4 place papal magnet, |8 place swamp
OWN_VISIBLE = 0x3d54e      # OR of visible entity flags, bit 0 = one of yours ($145d2)
PAINT = 0x3b276
PAUSE = 0x3b274            # toggled by top-right icon (1,3), sub-command 6
HEIGHTS = 0x34be4          # 65x65 signed words, index y*65+x
HUMAN = 0x3affe
GOD_REC = 0x21e0c

# Command panel (lower left).  (col,row) -> (name, effect).  Read from $c65a..$d05c.
PANEL = {
    (0, 0): ('flood', 'cmd 14/4'),
    (1, 0): ('armageddon', 'cmd 14/3 (not in paint mode)'),
    (1, 1): ('volcano', 'cmd 6 at view origin'),
    (2, 0): ('earthquake', 'cmd 3 at view origin'),
    (2, 1): ('knight', 'cmd 14/5'),
    (2, 2): ('swamp', 'ui_mode |= 8 (next land click places a swamp, cmd 4); needs mana > 5000 and power $10, or paint mode'),
    (3, 0): ('scroll_nw', 'view y-1, x-1'), (4, 0): ('scroll_n', 'view y-1'), (5, 0): ('scroll_ne', 'view x+1, y-1'),
    (3, 1): ('scroll_w', 'view x-1'), (4, 1): ('centre_query', 'view on the query entity'), (5, 1): ('scroll_e', 'view x+1'),
    (3, 2): ('scroll_sw', 'view x-1, y+1'), (4, 2): ('scroll_s', 'view y+1'), (5, 2): ('scroll_se', 'view x+1, y+1'),
    (3, 3): ('mode_magnet', 'cmd 14/1 arg 0: go to papal magnet'),
    (4, 3): ('mode_settle', 'cmd 14/1 arg 1: settle'),
    (5, 3): ('mode_gather', 'cmd 14/1 arg 2: gather'),
    (4, 4): ('mode_fight', 'cmd 14/1 arg 3: fight'),
    (6, 0): ('ui_query', 'ui_mode = 1: click a walker/town to query it'),
    (6, 1): ('ui_land', 'ui_mode = 2: left raise, right lower'),
    (6, 2): ('ui_magnet', 'ui_mode = (ui_mode&3)|4: next land click moves the papal magnet (cmd 5)'),
    (7, 0): ('goto_leader', 'left: view on (and query) the leader, else the magnet; right: the papal magnet'),
    (7, 1): ('goto_battle', 'view on (and query) the next fighting entity (flag bit 3), either side'),
    (8, 0): ('goto_knight', 'left: the next own knight; right: the next own settlement'),
}
# Lower right (u > $112: the icons right of the land view).  Read from $c4a4..$c656.
RIGHT = {
    (0, 0): ('options', 'cmd 14/7 arg=left: OPTIONS FOR EVIL menu (left: own side, right: other)'),
    (0, 3): ('toggle_21ffc', 'toggle $21ffc, $b15a(0,4) on set'),
    (0, 4): ('toggle_21920', 'toggle $21920, $b15a(0,4) on set'),
    (1, 1): ('game_setup', 'cmd 14/8: GAME SETUP menu'),
    (1, 3): ('pause', 'cmd 14/6: toggle $3b274'),
    (2, 2): ('message', 'cmd 14/2: send message (two-player)'),
}
ICONS = {name: ('panel', cr) for cr, (name, _) in PANEL.items()}
ICONS.update({name: ('right', cr) for cr, (name, _) in RIGHT.items()})


def uv(x, y):
    h = x >> 1
    return y + h - 32, y - h + 32


def screen_of_uv(u, v):
    """An integer screen point with diamond coords exactly (u, v); needs u+v even."""
    assert (u + v) % 2 == 0, (u, v)
    y = (u + v) // 2
    h = (u - v) // 2 + 32
    return 2 * h, y


def icon_point(name):
    where, (c, r) = ICONS[name]
    u0, v0 = (0x60, 0x90) if where == 'panel' else (0x110, 0x20)
    x, y = screen_of_uv(u0 + 16 * c + 8, v0 + 16 * r + 8)
    assert classify(x, y) == (where, (c, r)), (name, x, y, classify(x, y))
    return x, y


def classify(x, y):
    """What $c3e2 does with a click at (x,y): ('minimap', (u,v)) / ('top', (c,r)) / ('panel', (c,r))
    / ('land', None).  Integer division truncates toward zero, as `divs` does."""
    u, v = uv(x, y)
    if 0 <= u < 64 and 0 <= v < 64:
        return 'minimap', (u, v)
    if u > 0x112:
        return 'right', (int((u - 0x110) / 16), int((v - 0x20) / 16))
    if v >= 0x92:
        return 'panel', (int((u - 0x60) / 16), int((v - 0x90) / 16))
    return 'land', None


class Mem:
    """Word/long reads from snapshot RAM bytes or a live popdrive-compatible Repl."""
    def __init__(self, src):
        self.src = src
    def rd(self, a, n):
        if isinstance(self.src, (bytes, bytearray)):
            return bytes(self.src[a:a + n])
        return self.src.mem(a, n)
    def sw(self, a): return struct.unpack('>h', self.rd(a, 2))[0]
    def w(self, a): return struct.unpack('>H', self.rd(a, 2))[0]
    def l(self, a): return struct.unpack('>i', self.rd(a, 4))[0]


class Game:
    def __init__(self, src):
        self.m = Mem(src)
        self.refresh()

    def refresh(self):
        m = self.m
        self.px, self.py = m.sw(MOUSE_X), m.sw(MOUSE_Y)
        self.view = (m.sw(VIEW_X), m.sw(VIEW_Y))
        raw = m.rd(HEIGHTS, 65 * 65 * 2)
        self.h = list(struct.unpack('>%dh' % (65 * 65), raw))
        self.ui_mode = m.w(UI_MODE)
        self.own_visible = m.w(OWN_VISIBLE)
        self.paint = m.w(PAINT)
        self.pause = m.w(PAUSE)
        self.human = m.w(HUMAN)

    # ---- $119e6: which corner the land input acts on for a latched (x, y) ----
    def land_ok(self, x, y):
        u, v = uv(x, y)
        return 0x3e <= u <= 0x10a and -0x40 <= v <= 0x88 and x >= 0x40

    def corner_at(self, x, y, view=None):
        """Corner (cx, cy) and the highlight's y, or None, exactly as $11a7c..$11bf2."""
        ox, oy = view or self.view
        col = (x - 0x38) >> 4
        c0 = oy * 65 + ox
        n, sy = 9, 0x48
        if col > 8:
            n = 17 - col; c0 += col - 8; sy += (col - 8) * 8
        if col < 8:
            n = col + 1; c0 += 65 * (8 - col); sy += 8 * (8 - col)
        best = None
        for k in range(n):
            c = c0 + 66 * k
            ys = sy + 16 * k - 8 * self.h[c]
            if ys <= y + 4:
                best = (c, ys - 3)
        if best is None:
            return None
        c, hy = best
        return (c % 65, c // 65), hy

    def points_for_corner(self, cx, cy, view=None):
        """All screen points whose latched click lands on corner (cx, cy)."""
        out = []
        for x in range(0x40, 320, 2):
            for y in range(0, 200):
                if not self.land_ok(x, y) or classify(x, y)[0] != 'land':
                    continue
                r = self.corner_at(x, y, view)
                if r and r[0] == (cx, cy):
                    out.append((x, y))
        return out

    def best_point_for_corner(self, cx, cy, view=None):
        pts = self.points_for_corner(cx, cy, view)
        if not pts:
            return None
        # the middle of the band that maps to this corner: robust to a one-pixel slip
        xs = sorted({p[0] for p in pts})
        x = xs[len(xs) // 2]
        ys = sorted(p[1] for p in pts if p[0] == x)
        return x, ys[len(ys) // 2]

    def view_for_corner(self, cx, cy):
        """A reachable view origin (minimap click) with the corner well inside the 9x9 window."""
        best = None
        for u in range(0, 64):
            for v in range(0, 64):
                if (u + v) % 2:
                    continue
                x, y = screen_of_uv(u, v)
                if not (0 <= x < 320 and 0 <= y < 200) or classify(x, y) != ('minimap', (u, v)):
                    continue
                ox, oy = min(max(u - 3, 0), 56), min(max(v - 3, 0), 56)
                lx, ly = cx - ox, cy - oy
                if 0 <= lx <= 8 and 0 <= ly <= 8:
                    score = abs(lx - 4) + abs(ly - 4)
                    if best is None or score < best[0]:
                        best = (score, (ox, oy), (x, y))
        return best and (best[1], best[2])


def move_lines(fx, fy, tx, ty):
    """`mouse move` lines taking the pointer from (fx,fy) to (tx,ty), |d| <= 127 each."""
    out = []
    dx, dy = tx - fx, ty - fy
    while dx or dy:
        sx, sy = max(-127, min(127, dx)), max(-127, min(127, dy))
        out.append('mouse move %d %d' % (sx, sy))
        dx -= sx; dy -= sy
    return out


FRAME = 120000   # REPL steps comfortably above one game frame (~105k steps at 1 frame/VBL)


def click_lines(fx, fy, tx, ty, button='l', settle=2, hold=2, after=2):
    """Move, let the VBL read the new position, press, hold across a latch, release."""
    L = move_lines(fx, fy, tx, ty)
    L.append('s %d' % (FRAME * settle))
    L.append('mouse down %s' % button)
    L.append('s %d' % (FRAME * hold))
    L.append('mouse up %s' % button)
    L.append('s %d' % (FRAME * after))
    return L


def plan_raise(g, cx, cy, button='l'):
    """REPL lines for one raise (button l) or lower (r) of corner (cx,cy): scroll via the
    minimap if the corner is off the view, then click on the corner. Returns (lines, info)."""
    lines, px, py, view = [], g.px, g.py, g.view
    if g.best_point_for_corner(cx, cy) is None:
        v = g.view_for_corner(cx, cy)
        if v is None:
            raise ValueError('no minimap click shows corner %r' % ((cx, cy),))
        view, (mx, my) = v
        lines += click_lines(px, py, mx, my)
        px, py = mx, my
    pt = g.best_point_for_corner(cx, cy, view)
    if pt is None:
        raise ValueError('corner %r not clickable from view %r' % ((cx, cy), view))
    lines += click_lines(px, py, pt[0], pt[1], button)
    return lines, {'view': view, 'point': pt}


def plan_icon(g, name, button='l'):
    x, y = icon_point(name)
    return click_lines(g.px, g.py, x, y, button), {'point': (x, y)}


def run(snap_in, lines, snap_out, extra=()):
    """Resume snap_in in a REPL, feed lines (+extra), write snap_out; returns stdout text."""
    import subprocess
    from popcfg import DLL, R, DISK
    env = dict(os.environ, ATARI_NOTRACE='1')
    script = '\n'.join(list(lines) + list(extra) + ['snap %s' % snap_out, 'q']) + '\n'
    if os.path.exists(snap_out):
        os.remove(snap_out)
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap_in, 'repl', '--disk-a', DISK],
                       input=script, capture_output=True, text=True, cwd=R, env=env)
    if not os.path.exists(snap_out):
        raise RuntimeError(p.stdout[-2000:] + p.stderr[-2000:])
    return p.stdout


if __name__ == '__main__':
    from popmem import ram
    snap, what = sys.argv[1], sys.argv[2]
    g = Game(ram(snap))
    if what == 'raise' or what == 'lower':
        L, info = plan_raise(g, int(sys.argv[3]), int(sys.argv[4]), 'l' if what == 'raise' else 'r')
    elif what == 'icon':
        L, info = plan_icon(g, sys.argv[3])
    elif what == 'icons':
        for n in ICONS:
            print(n, icon_point(n))
        sys.exit(0)
    else:
        raise SystemExit(__doc__)
    print('#', info)
    print('\n'.join(L))
