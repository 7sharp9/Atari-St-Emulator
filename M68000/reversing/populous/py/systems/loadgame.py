"""loadgame.py - load LOLO1.GAM through GAME SETUP -> LOAD A GAME and compare RAM with the file.

Needs systems/loadsel.snap (the LOAD GAME dialog with LOLO1 selected; made from game_start by
clicking game_setup (304,176), LOAD A GAME (140,134), the LOLO1 list entry (104,40)); rebuilt here
if missing. Clicks LOAD (110,183), stops when load_game $1e146 returns (bp $192b8) and compares:
the regions the file holds must equal the file, every region past its end must be untouched.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg_local import WORK, OUT
from popdrive import Game, click_lines, move_lines, FRAME, run
from popmem import ram
from lolo import LAYOUT


def build_dialog():
    snap = os.path.join(WORK, 'game_start.snap')
    for i, (x, y) in enumerate([(304, 176), (140, 134), (104, 40)]):
        g = Game(ram(snap))
        nxt = os.path.join(OUT, 'dlg%d.snap' % i)
        run(snap, click_lines(g.px, g.py, x, y) + ['s 3000000'], nxt)
        snap = nxt
    os.replace(snap, os.path.join(OUT, 'loadsel.snap'))


def main():
    sel = os.path.join(OUT, 'loadsel.snap')
    if not os.path.exists(sel):
        build_dialog()
    g = Game(ram(sel))
    L = move_lines(g.px, g.py, 110, 183) + ['s %d' % (2 * FRAME), 'mouse down l', 's %d' % (2 * FRAME),
                                            'mouse up l', 'bp 192b8 30000000']
    after = os.path.join(OUT, 'loaded_ret.snap')
    run(sel, L, after)
    a, b = ram(sel), ram(after)
    f = open(os.path.join(WORK, 'files', 'LOLO1.GAM'), 'rb').read()
    off = 4
    tot_file = tot_keep = n_file = n_keep = 0
    for addr, n, name in LAYOUT[1:]:
        got = max(0, min(n, len(f) - off))
        if got:
            m = sum(1 for i in range(got) if b[addr + i] == f[off + i]); tot_file += m; n_file += got
            print('%-18s from file  %d/%d' % (name, m, got))
        if got < n:
            k = sum(1 for i in range(got, n) if b[addr + i] == a[addr + i]); tot_keep += k; n_keep += n - got
            print('%-18s unchanged  %d/%d' % (name, k, n - got))
        off += n
    print('TOTAL bytes equal to the file: %d/%d; bytes past the file end left as before: %d/%d'
          % (tot_file, n_file, tot_keep, n_keep))


if __name__ == '__main__':
    main()
