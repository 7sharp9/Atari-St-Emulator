"""savegame.py - SAVE A GAME over LOLO1 on the (full) game disk and log the Fwrite results.

From game_start.snap: game_setup icon (304,176), SAVE A GAME (140,124), the LOLO1 list entry
(104,40), SAVE button (110,183). ATARI_TRACE_OS logs every Fcreate/Fwrite with its return value.
Disk writes stay in the emulator's in-memory image (MMU.tryWriteSector); pop_auto.st on the host
is not modified. Prints each Fwrite's requested and written byte counts and the file total.
"""
import os, sys, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popcfg_local import WORK, OUT, R, DLL, DISK
from popdrive import Game, click_lines, run
from popmem import ram


def main():
    snap = os.path.join(WORK, 'game_start.snap')
    for i, (x, y) in enumerate([(304, 176), (140, 124), (104, 40)]):
        g = Game(ram(snap))
        nxt = os.path.join(OUT, 'sdlg%d.snap' % i)
        run(snap, click_lines(g.px, g.py, x, y) + ['s 3000000'], nxt)
        snap = nxt
    g = Game(ram(snap))
    L = click_lines(g.px, g.py, 110, 183) + ['s 20000000', 'snap ' + os.path.join(OUT, 'saved.snap'), 'q']
    env = dict(os.environ, ATARI_NOTRACE='1', ATARI_TRACE_OS='1')
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl', '--disk-a', DISK],
                       input='\n'.join(L) + '\n', capture_output=True, text=True, cwd=R, env=env)
    open(os.path.join(OUT, 'save_os.txt'), 'w').write(p.stdout + '\n----\n' + p.stderr)
    top = [l for l in (p.stdout + p.stderr).splitlines() if re.match(r'OS +\d+ (\S)', l)]
    pend, total = None, 0
    for l in top:
        m = re.match(r'OS +\d+ (F\w+)\((.*)\)', l)
        if m and m.group(1) in ('Fcreate', 'Fwrite', 'Fclose', 'Fopen', 'Fdelete'):
            pend = (m.group(1), m.group(2)); continue
        m = re.match(r'OS +\d+ = \$([0-9a-f]+)', l)
        if m and pend:
            v = int(m.group(1), 16)
            if pend[0] == 'Fwrite':
                req = int(re.search(r'count=\$([0-9a-f]+)', pend[1]).group(1), 16)
                total += v if v < 0x80000000 else 0
                print('Fwrite %6d -> %6d  %s' % (req, v, pend[1]))
            else:
                print(pend[0], pend[1], '->', hex(v))
            pend = None
    print('bytes written to the file:', total)


if __name__ == '__main__':
    main()
