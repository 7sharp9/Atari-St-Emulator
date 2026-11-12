"""Execution profile (profile_start / profile_stop, tools/profdiff.py) proof on Black Tiger's built-in
level skip (reversing/black_tiger/secrets.md, row 1): joystick 1 = $85 (up + left + fire) held while
ClrHome ($47) is pressed sets $17826 through the main loop's key compare and the joystick compare.

    python3 server/profile_proof.py [--dll <stserver.dll>] [--out <dir>]

From play_start.snap ($BT_WORK, default scratchpad/black_tiger; disk bt_auto.st), one fork:
  A  profiled input drive (the run_all.py `levelskip` key timeline up to the joystick release), 500,000 steps
  B  profiled control, the same 500,000 steps with no input
  A' the input drive again without a profile
Checks:
  1. word $17826 = 1 after A, 0 after B (the input did what the doc says; the control did not)
  2. A and A' end with byte-identical snapshots (profiling does not perturb the machine)
  3. every compare whose operands were both read left the flags those operands give (flag_mismatches 0)
  4. B profiled twice from the fork writes identical JSON (the profile is deterministic)
  5. blind rank (profdiff --value 47 --value 85): the main loop's compares in $c6ac..$c706 are named,
     and their rank is printed
Outputs: <out>/A.json, B.json, B2.json, A.snap, A_noprof.snap, rank.txt (default scratchpad/profile_proof).
"""
import argparse, filecmp, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer

ap = argparse.ArgumentParser()
ap.add_argument('--dll', default=None)
ap.add_argument('--out', default=os.path.join(ROOT, 'scratchpad', 'profile_proof'))
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
WORK = os.environ.get('BT_WORK', os.path.join(ROOT, 'scratchpad', 'black_tiger'))
SNAP, DISK = os.path.join(WORK, 'play_start.snap'), os.path.join(WORK, 'bt_auto.st')
O = lambda f: os.path.join(args.out, f)
BUDGET = 500000
# run_all.py "levelskip": kbd ff 85, s 100000, kbd 47, s 200000, kbd c7, s 100000, kbd ff 00, then 100000 more
DRIVE = [([0xff, 0x85], 100000), ([0x47], 200000), ([0xc7], 100000), ([0xff, 0x00], 100000)]
assert sum(n for _, n in DRIVE) == BUDGET

results = []
def check(name, ok, detail=''):
    results.append(ok)
    print(f'{"PASS" if ok else "FAIL"}  {name}  {detail}')

s = StServer(ROOT, dll=args.dll)
s('load', snapshot=SNAP, disk=DISK)
base = s('fork')['id']

def drive(profile_path=None, inputs=True):
    s('restore', id=base)
    if profile_path: s('profile_start')
    for keys, n in DRIVE:
        if inputs: s('kbd', bytes=keys)
        s('step', n=n)
    stats = s('profile_stop', path=profile_path) if profile_path else None
    return stats, int.from_bytes(s.read(0x17826, 2), 'big')   # a word flag (secrets.md: m 17826 2)

a, flag_a = drive(O('A.json'))
s('save', path=O('A.snap'))
b, flag_b = drive(O('B.json'), inputs=False)
b2, _ = drive(O('B2.json'), inputs=False)
_, flag_a2 = drive(None)
s('save', path=O('A_noprof.snap'))
s.close()
print('A', a); print('B', b)

check('1 input sets $17826, control does not', flag_a == 1 and flag_b == 0 and flag_a2 == 1, f'A {flag_a} B {flag_b} A\' {flag_a2}')
check('2 profiled and unprofiled input runs end identical', filecmp.cmp(O('A.snap'), O('A_noprof.snap'), shallow=False))
check('3 flags agree with the recorded operands',
      a['flag_mismatches'] == 0 and b['flag_mismatches'] == 0 and a['flag_checks'] > 0,
      f'A {a["flag_checks"]} checks {a["flag_mismatches"]} mismatches {a["mismatch_pcs"]}; B {b["flag_checks"]}/{b["flag_mismatches"]}')
check('4 control profile deterministic', filecmp.cmp(O('B.json'), O('B2.json'), shallow=False))

rank = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'profdiff.py'), O('A.json'), O('B.json'),
                       '--value', '47', '--value', '85', '--top', '40'], capture_output=True, text=True, check=True).stdout
open(O('rank.txt'), 'w').write(rank)
lines = rank.splitlines()
start = next(i for i, l in enumerate(lines) if l.startswith('compares with'))
hits = [l for l in lines[start + 1:] if l[:3].strip().isdigit() and 0xc6ac <= int(l.split()[1][1:], 16) <= 0xc706]
print(rank[rank.index('compares with'):])
check('5 the main loop compares in $c6ac..$c706 are named', len(hits) > 0, '; '.join(h.strip() for h in hits))
print(f'{sum(results)}/{len(results)} PASS')
sys.exit(0 if all(results) else 1)
