"""r_inc.py - the race counter R (-1748(A4)) across one winner's circle: does a human win increment it?

Start data ai_econ/pre_winner.snap (entry of $1a4ca after a real race; human slot 1).  Poke (labelled): R0, the rank keys so that
the human (slot 1) or a drone (slot 3) is first, wrenches 0 (no shop).  `watch` the word R and run until the session loop's
clamp at $13b16: every write to R is printed with its pc.  Arms: {human wins, drone wins} x R0 in {5, 49, 50, 0}.
Expected from the code: $1a7d2 R-1 if rank 0 is a drone; $13b00 R+1 unconditionally, clamp 50 ($13b04..$13b10).
Note $13b00 runs after every race, so the net is +1 (human win) and 0 (drone win)."""
from lt import *
rows = []
for who in ('human', 'drone'):
    for R0 in (5, 49, 50, 0):
        r = Repl2(os.path.join(AI, 'pre_winner.snap'))
        pk = {A4 - 1748: R0}
        for c in range(4):
            pk[A4 - 3906 + 2 * c] = 0; pk[A4 - 3850 + 2 * c] = 0; pk[A4 - 3842 + 2 * c] = 0
        win = 1 if who == 'human' else 3
        pk[A4 - 3906 + 2 * win] = 4; pk[A4 - 3850 + 2 * win] = 5
        for c in range(3): pk[A4 - 3954 + 2 * c] = 0
        pk[A4 - 3914 + 2 * 1] = 0           # slot 1 is the human
        setwords(r, pk)
        r.cmd('watch %x 2' % (A4 - 1748))
        w = []
        out, _ = r.cmd('bp 13b16 40000000')
        hit = any('hit' in l for l in out)
        # watch lines printed while running
        w = [l for l in out if l.startswith('WATCH')]
        Rend = r.a4w(-1748, 1)[0]
        flags = r.a4w(-3914, 4)
        rows.append((who, R0, Rend, [re.search(r'pc=\$([0-9a-f]+).*<- \$([0-9a-f]+)', l).groups() for l in w], hit, flags))
        print('%s wins, R0=%2d: R at $13b16 = %d (hit %s); writes (pc, value): %s; drone flags after %s' % (who, R0, Rend, hit, rows[-1][3], flags), flush=True)
        r.close()
