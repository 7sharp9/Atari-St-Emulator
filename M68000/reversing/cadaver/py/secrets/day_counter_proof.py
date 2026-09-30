"""Day counter ('DAY n' on the status bar): static census + live pokes.  Start snapshot gameplay_empire.snap.

Mechanism (VBL ISR $01528e, transcribed): with A5 = $018152,
  2171(A5) counts VBLs down from 2172(A5) (= 50, set at $0077e4) -> every 50 VBLs:  2169(A5) += 1 (seconds)
  2169 == 60 -> 2169 = 0, 2168(A5) += 1 (minutes);   2168 == 30 -> 2170(A5) = 1 (day-wrap flag), 2166(A5) += 1 (day),
  2168 = 0, 2167(A5) += 1.   => one day = 50*60*30 = 90,000 VBLs (30 min at 50 Hz).  $0077e0 clears 2166..2169 at game start.
Readers: 2166 only at $00ebc8 (status text 'DAY' (name string 29) + 2166 + 1, routine $00ebaa);  2167 never read.
  2170(A5): main loop $006b2a calls $00ebaa (redraw) and clears it when it is 1; TimerQueueService $009006 (every 17th call,
  countdown 2460(A5)) instead queues the name-banner opcode with index $1c (string 28 'A DAY PASSES ...') via $00defa and
  sets 2170 = $ff, which makes the main loop skip its redraw (DAY text then refreshes at the next $00eb4a status refresh).
Checks printed:
  [1] A5-displacement census of 2166..2172 in the loaded image (expect 2166: $0077e2,$00ebca,$0152cc; 2167: $0152d4).
  [2] poke 2168=29,2169=59,2171=1 -> after the next VBL 2166=1,2167=1,2170 flag set then cleared by $00ebaa (hits).
  [3] same plus 2460=1 -> banner path: $009016 and $00defa hit, 2170 ends $ff (render: 'A DAY PASSES ...').
  [4] 2171=50,2169=58,2168=29 -> the wrap arrives after exactly 100 VBL-ISR entries (2 seconds).
Run from M68000/:  uv run python reversing/cadaver/py/secrets/day_counter_proof.py
"""
import os, re, struct, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from ram import ram
M68 = os.path.abspath(os.path.join(here, '..', '..', '..', '..')); REPO = os.path.dirname(M68)
DISK = os.path.join(REPO, 'Cadaver', 'Cadaver (1990)(Image Works)[cr Empire][one disk].st')
SNAP = os.path.join(M68, 'scratchpad/cadaver/gameplay_empire.snap')
env = dict(os.environ, ATARI_NOTRACE='1')
def repl(cmds):
    p = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl', '--disk-a', DISK],
                       input='\n'.join(cmds) + '\nq\n', text=True, capture_output=True, cwd=M68, env=env)
    return p.stdout
r = ram(SNAP)
for nm, d in (('2166', 0x876), ('2167', 0x877), ('2170', 0x87a)):
    print('[1] displacement %s(A5) words in $001000-$019000:' % nm, [hex(i) for i in range(0x1000, 0x19000, 2) if r[i] == d >> 8 and r[i + 1] == d & 255])
o = repl(['w 189ca 1d3b0001', 'hits 400000 ebaa defa 9016 152c4 6b32', 'm 189c4 10'])
print('[2]', ' | '.join(l.strip() for l in o.splitlines() if l.startswith('  $') or re.match(r'^[0-9a-f]{2} ', l)))
o = repl(['w 189ca 1d3b0001', 'w 18aec 00000100', 'hits 400000 ebaa defa 9016 9020 152c4 6b32', 'm 189c4 10'])
print('[3]', ' | '.join(l.strip() for l in o.splitlines() if l.startswith('  $') or re.match(r'^[0-9a-f]{2} ', l)))
o = repl(['w 189ca 1d3a0032', 'hits 3000000 152c4'])
S = int(re.search(r'\$0152c4\s+\d+\s+first (\d+)', o).group(1))
o = repl(['w 189ca 1d3a0032', 'hits %d 1528e 152c4' % (S + 1)])
print('[4] wrap at step', S, '->', ' | '.join(l.strip() for l in o.splitlines() if l.startswith('  $')))
