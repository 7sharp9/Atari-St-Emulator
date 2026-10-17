"""scan.py TAG SNAP 'SCRIPT' : poison all 28 candidate 1 KB blocks at once; if anything outside changes, poison each 1 KB block
alone and list the consumed ones.  Appends a line to data/scan_<TAG>.json.  Budget = the steps in SCRIPT."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flow import *

KB = []
for b in BLOCKS:
    for k in range(4): KB.append((b + k * 0x400, b + (k + 1) * 0x400))

def scan(tag, snap, script, procs=int(os.environ.get('SCAN_PROCS', 3))):
    t = time.time()
    snap = snapath(snap)
    cpc, res = consumed(snap, script, [KB], procs=procs)
    allv = res[0]
    out = {'tag': tag, 'snap': os.path.basename(snap), 'script': script, 'all_diff': allv[1], 'consumed_kb': []}
    if allv[1]:
        cpc, res = consumed(snap, script, [[k] for k in KB], procs=procs)
        out['consumed_kb'] = ['%x' % r[0][0][0] for r in res if r[1]]
        out['per_kb'] = {'%x' % r[0][0][0]: r[1] for r in res if r[1]}
    out['secs'] = int(time.time() - t)
    json.dump(out, open(os.path.join(DATA, 'scan_%s.json' % tag), 'w'), indent=1)
    print(tag, 'all-diff', out['all_diff'], 'consumed 1KB blocks', out['consumed_kb'], '(%ds)' % out['secs'], flush=True)
    return out

if __name__ == '__main__':
    scan(sys.argv[1], sys.argv[2], parse_script(sys.argv[3]))
