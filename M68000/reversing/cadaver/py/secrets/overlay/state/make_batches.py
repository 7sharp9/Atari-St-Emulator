"""make_batches.py [OUTDIR]: from OUTDIR/scan_snaps.tsv (scan_snaps.py) pick one snapshot per distinct (level, room, object set) with animated objects (batch_snaps.txt, 60) and with movers
(batch_mover.txt, 74): the samples the free-run gates run over.  Disk-2 and 'replicants' snapshots are skipped."""
import re, os, sys
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('OUTDIR', os.path.join(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *['..'] * 6))), 'scratchpad/cadaver/s91_state')))
def pick(col, pat, extra, limit, name):
    seen = {}
    for l in open(OUT + '/scan_snaps.tsv'):
        p, lv, rm, M, A = l.rstrip('\n').split('\t')
        src = A if col == 'A' else M
        ids = tuple(sorted(set(int(x) for x in re.findall(pat, src) if int(x) != 0)))
        if not ids or 'disk2' in p or 'replicants' in p: continue
        key = (lv, rm, ids) + extra(src)
        if key not in seen: seen[key] = p
    open(OUT + '/' + name, 'w').write(''.join(p + '\n' for p in list(seen.values())[:limit]))
pick('A', r'(\d+):[0-9a-f]+/[0-9a-f]+/f[0-9a-f]+', lambda s: (), 60, 'batch_snaps.txt')
pick('M', r'(\d+):s\d+,c\d+', lambda s: (tuple(sorted(set(re.findall(r':s(\d+),', s)))),), 74, 'batch_mover.txt')
