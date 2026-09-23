"""strategy.py LOGDIR [every] - summarize a cmdlog.py natural run: commands per side by type with
first/last frame, magnet moves, mode switches, and a state table (settlements, castles, population,
mana, leader, mode, magnet) every `every` frames."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from join import dedup

NAMES = {1: 'raise', 2: 'lower', 3: 'quake', 4: 'swamp', 5: 'magnet', 6: 'volcano'}
SUB = {1: 'mode', 3: 'armageddon', 4: 'flood', 5: 'knight'}


def cname(c):
    if c[0] == 14: return '14/' + SUB.get(c[2], str(c[2])) + ('=%d' % c[1] if c[2] == 1 else '')
    return NAMES.get(c[0], str(c[0]))


def main():
    d = sys.argv[1]; every = int(sys.argv[2]) if len(sys.argv) > 2 else 250
    L = dedup([json.loads(l) for l in open(os.path.join(d, 'log.jsonl'))], 'step')
    print('frames %d..%d (%d entries)' % (L[0]['frame'], L[-1]['frame'], len(L)))
    for s in (0, 1):
        cnt = collections.Counter(); first = {}; lastf = {}
        events = []
        for e in L:
            c = e['s%d' % s]['cmd']
            if not c[0]: continue
            n = cname(c); cnt[n] += 1; first.setdefault(n, e['frame']); lastf[n] = e['frame']
            if c[0] not in (1, 2): events.append((e['frame'], n, c[1], c[2]))
        print('side %d (ctrl %d): %d commands' % (s, L[-1]['s%d' % s]['ctrl'], sum(cnt.values())))
        for n, k in sorted(cnt.items(), key=lambda x: -x[1]):
            print('   %-16s %5d  first %5d last %5d' % (n, k, first[n], lastf[n]))
        print('   non-land events:', events[:60], '...' if len(events) > 60 else '')
    print('frame | side0 towns/castles pop mana lead mode magnet | side1 ...')
    for e in L:
        if (e['frame'] - L[0]['frame']) % every == 0 or e is L[-1]:
            row = [str(e['frame'])]
            for s in (0, 1):
                x = e['s%d' % s]
                row.append('%3d/%2d %6d %6d L%-3d m%d (%2d,%2d)' % (x['towns'], x['castles'], x['pop'], x['mana'],
                                                                   x['leader'], x['mode'], x['magnet'] & 63, x['magnet'] >> 6))
            print(' | '.join(row))


if __name__ == '__main__':
    main()
