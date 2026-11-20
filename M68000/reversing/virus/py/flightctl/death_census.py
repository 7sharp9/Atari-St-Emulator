"""Which exit of the ship tick ends each life, over one attract game (REPL `hits`, no pokes).

  python death_census.py <start_snap> <steps> [out.txt]       e.g. scratchpad/virus/chain/long100/starts/main_g001.snap 640000000

A `hits` count is of instruction starts, so a taken branch is the count at the branch minus the count at its fall-through:
  enemy exit      $257fa (tst.b $62a5d / bne $25ad8)   taken = n($257fa) - n($257fe)
  vertex exit     $25804 (tst.b $62a62 / bne $25ad2)   taken = n($257fe) - n($25808)
  ground contact  $25870 (c < 0, ground above the ship)        n($25870)
    hard          $25874 bgt (vy > $28) -> $25ad2              n($25874) - n($25878)
    soft          $25878 -> $25c28 landing test                n($25c28); lands at $25c52, otherwise the test crashes: n($25c28) - n($25c52)
  object cell     $25846 (object map byte, low five bits set, bit 4 clear)   n($25846)
  lives lost      $25ba0 (subi.w #1,$32a54)
The census is bounded by <steps> and by the run having no input: a game's own deaths only.
"""
import os, re, subprocess, sys
_p = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_p))
import vcommon as V
ROOT = V.ROOT
WORK = V.work('flightctl')
os.makedirs(WORK, exist_ok=True)
A = [0x255d4, 0x255de, 0x25a6e, 0x25aae, 0x257fa, 0x257fe, 0x25808, 0x25870, 0x25874, 0x25878, 0x25c28, 0x25c52, 0x25846, 0x25ad2, 0x25ad8, 0x25ba0]

def main(snap, steps, out=None):
    env = dict(os.environ, ATARI_NOTRACE='1')
    cmd = f'hits {steps} ' + ' '.join(f'{a:x}' for a in A) + '\nq\n'
    p = subprocess.run(['dotnet', 'exec', os.path.join(ROOT, 'bin/Debug/net8.0/M68000.dll'), 'resume', snap, 'repl'], input=cmd,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT, env=env)
    if out: open(out, 'w').write(p.stdout)
    n = {int(m.group(1), 16): int(m.group(2)) for m in re.finditer(r'^\s+\$([0-9a-f]+)\s+(\d+)\s+first', p.stdout, re.M)}
    if 0x255d4 not in n: raise SystemExit('no hits table in the REPL output')
    enemy = n[0x257fa] - n[0x257fe]; vertex = n[0x257fe] - n[0x25808]
    hard = n[0x25874] - n[0x25878]; softcrash = n[0x25c28] - n[0x25c52]
    print(f'{n[0x255d4]} ticks; ceiling-cut ticks {n[0x255de]}; pad ticks {n[0x25a6e]} (refuel stores {n[0x25aae]}); object-cell hits {n[0x25846]}')
    print(f'lives lost {n[0x25ba0]} = enemy {enemy} + vertex {vertex} + ground hard {hard} + ground soft-test crash {softcrash} (sum {enemy + vertex + hard + softcrash}); '
          f'soft landings {n[0x25c52]}; object kills {n[0x25846]}')

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
