"""prize_score.py - does the winner's circle prize (1000/500/250/0 by rank) add to the persistent 6-digit score -4846+6*car?
From ai_econ/pre_winner.snap (entry of $1a4ca) poke slot 1 (the human) to rank `rank` (labelled poke of the rank keys), watch the 6 score digits
of slot 1, run to $13b16 and print each write (pc, byte) and the score before/after."""
from lt import *
def val(d):
    s = 0
    for x in d: s = s * 10 + (x & 0x7f)
    return s
for rank in (0, 1, 2, 3):
    r = Repl2(os.path.join(AI, 'pre_winner.snap'))
    pk = {}
    for c in range(4):
        pk[A4 - 3906 + 2 * c] = 3 - (c if c != 1 else rank) if False else 0
    # keys: laps for rank positions: human gets the lap count placing it at `rank`
    order = [c for c in (0, 2, 3)]
    keys = {}
    slots = [c for c in (0, 2, 3)]
    ranking = slots[:rank] + [1] + slots[rank:]
    for pos, c in enumerate(ranking):
        pk[A4 - 3906 + 2 * c] = 4 - pos
        pk[A4 - 3850 + 2 * c] = 5
        pk[A4 - 3842 + 2 * c] = 0
    for c in range(3): pk[A4 - 3954 + 2 * c] = 0
    pk[A4 - 3914 + 2] = 0
    setwords(r, pk)
    sc0 = list(r.mem(A4 - 4840, 6))
    r.cmd('watch %x 6' % (A4 - 4840))
    out, regs = r.cmd('bp 13b16 40000000')
    w = [re.search(r'pc=\$([0-9a-f]+) .*<- \$([0-9a-f]+)', l).groups() for l in out if l.startswith('WATCH')]
    sc1 = list(r.mem(A4 - 4840, 6))
    print('human finishes rank %d: score %d -> %d; writes %d (pcs %s); drone flags %s' % (rank, val(sc0), val(sc1), len(w), sorted(set(p for p, v in w)), r.a4w(-3914, 4)), flush=True)
    r.close()
