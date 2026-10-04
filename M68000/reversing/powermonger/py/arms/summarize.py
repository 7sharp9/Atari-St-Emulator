"""summarize.py <prefix> [<prefix>...]: per-land and total `hits` over all chunks of <ARMS_WORK>/long/<prefix>_*.txt (run_arms.sh / run_arms2.sh); ARMS_WORK env, default scratchpad/pm148/arms.
Prints the table (steps run, $6522 calls = ticks, counts of the arm addresses) and for every address with a nonzero count the lands that have it."""
import collections, glob, os, re, sys
from pathlib import Path
def _root():
    if os.environ.get('M68000_ROOT'): return Path(os.environ['M68000_ROOT'])
    for p in Path(__file__).resolve().parents:
        if (p / 'tools' / 'pm_fsm_ref.py').exists(): return p
ROOT = _root()
WORK = ROOT / os.environ.get('ARMS_WORK', 'scratchpad/pm148/arms')
cols = ['6522', '65b4', '65c8', '65e0', '65f4', '661a', '6638', '664c', '666c', '6680', '6686', '668c', '66a4', '66b0', '6884', '2776', 'd2c8', '25d6', '550e', '5100', '153cc', '1547e', '4220', '4562']
tot = collections.Counter(); lands = 0; steps = 0; alive_steps = 0
per = {}
for pre in sys.argv[1:]:
    for f in sorted(glob.glob(str(WORK / 'long' / (pre + '_*.txt')))):
        txt = open(f).read()
        chunks = txt.split('--- hits over')[1:]
        if not chunks: continue
        c = collections.Counter(); st = 0
        for blk in chunks:
            st += int(re.match(r'\s+(\d+) step', blk).group(1))
            for a, n in re.findall(r'\$0*([0-9a-f]+)\s+(\d+)\s+first', blk):
                c[a] += int(n)
        name = os.path.basename(f)[:-4]
        per[name] = (st, c, len(chunks))
print('land'.ljust(14), 'chunks Msteps', ' '.join(x.rjust(5) for x in cols))
for name, (st, c, n) in per.items():
    print(name.ljust(14), str(n).rjust(6), str(st // 1000000).rjust(6), ' '.join(str(c[x]).rjust(5) for x in cols))
    tot.update(c); steps += st; lands += 1
    # steps the land was running: $6522 runs ~ every 182k steps while the land lives
print('lands', lands, 'steps run %.1fG' % (steps / 1e9), ' totals:', {x: tot[x] for x in cols if tot[x]})
ended = sum(1 for n, (st, c, k) in per.items() if c['d2c8'])
print('lands that ended ($d2c8) inside the run:', ended)
print('estimated land-steps alive (6522 calls * 182000): %.1fG' % (tot['6522'] * 182000 / 1e9))
