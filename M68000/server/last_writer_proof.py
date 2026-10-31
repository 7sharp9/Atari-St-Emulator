"""last_writer proof (DEVELOPING.md, "Record and replay"): the recording's answer equals an independent REPL watch.

    python3 server/last_writer_proof.py <stserver.dll> <M68000.dll> <pre_pick.snap> <powermonger.st> <outdir>

The `goto ctl` arm of PowerMonger's `commander/leadkill/gate_leadkill.sh` (2,607,722 steps from `pre_pick.snap`, no
pokes) is run twice: in the REPL under `watch 53006 2`, which lists every write to the captain's lead word, and in
`stserver` as a recording with a checkpoint every 500,000. Then `last_writer 53006 53007 S` for 20 steps S: the base
and one before the first write (expect none), at a write's step and one before it, and spread over the run up to its end. Each must
equal the last REPL watch line at or before S (step, PC, address, value). Falsifier: any of 20 differs.
Exit status 0 = all pass.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from stclient import StServer  # noqa: E402

srv, core, snap, disk, out = sys.argv[1:6]
os.makedirs(out, exist_ok=True)
N = 2_607_722

repl = subprocess.run(['dotnet', 'exec', core, 'resume', snap, 'repl'], cwd=os.getcwd(), capture_output=True,
                      text=True, env=dict(os.environ, ATARI_NOTRACE='1'),
                      input=f'disk {disk}\nwatch 53006 2\ns {N}\nq\n')
open(f'{out}/repl.err', 'w').write(repl.stderr)
W = [(int(m[1]), int(m[2], 16), int(m[3], 16), int(m[4], 16)) for m in
     re.finditer(r'^WATCH: step=(\d+) pc=\$([0-9a-f]+) \S+ \$([0-9a-f]+) <- \$([0-9a-f]+)', repl.stderr, re.M)]
print(f'REPL watch: {len(W)} writes, steps {W[0][0]}..{W[-1][0]}' if W else 'REPL watch: no writes')
if not W:
    sys.exit('no REPL watch lines: nothing to compare against')

s = StServer(os.getcwd(), dll=srv)
B = s('load', snapshot=snap, disk=disk)['step']
s('record_start', every=500_000)
s('step', n=N)
r = s('record_stop')
print(f"recorded {r['base']}..{r['end']}: {r['checkpoints']} checkpoints")

first, mid = W[0][0], W[len(W) // 2][0]
S = [B, first - 1, first, mid - 1, mid, B + N] + [B + (N * k) // 15 for k in range(1, 16)]
S = sorted(set(t for t in S if B <= t <= B + N))
match = 0
for t in S:
    want = next((w for w in reversed(W) if w[0] <= t), None)
    got = s('last_writer', lo=0x53006, hi=0x53007, step=t)
    e = got['event']
    have = (e['step'], int(e['pc'][1:], 16), int(e['addr'][1:], 16), int(e['value'][1:], 16)) if e else None
    ok = have == want
    match += ok
    print(f"{'ok  ' if ok else 'DIFF'} S={t}: last_writer {have} ({got['intervals']} interval(s)), watch {want}")
s.close()
print(f'last_writer {match}/{len(S)}')
sys.exit(0 if match == len(S) == 20 else 1)
