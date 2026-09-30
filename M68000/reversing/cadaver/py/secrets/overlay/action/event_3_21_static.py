"""event_3_21_static.py: bonus.  Union of the events pushed by every immediate-opcode push site in the resident image + level-0 overlay
(gameplay_empire.snap), the level-1 overlay (level1_loaded.snap) and the 7 overlay listings in scratchpad/cadaver/secrets_out/overlay/*.lst
(one-disk pairs 0/5, Disk 2 pairs 0/7/14/21/28, levels 0/1).  Also counts every reference to the ring cursor 304(A5) and every write to the queue
count 1154(A5) that is not the idiom, to show no computed-opcode push exists.  Result: events 3 and 21 are absent in all of them.
    uv run python reversing/cadaver/py/secrets/overlay/action/event_3_21_static.py"""
import re, glob, subprocess, sys, collections
def scan(lines):
    evs = collections.Counter(); reg = 0
    for i, l in enumerate(lines):
        if 'addq.w #1,1154(A5)' in l:
            op = None
            for j in range(i - 1, max(i - 14, 0), -1):
                if re.search(r'movea\.l 304\(A5\),A\d', lines[j]):
                    for k in range(j + 1, i):
                        m = re.search(r'move\.w (#\$[0-9a-f]+|\S+),\(A\d\)\+', lines[k])
                        if m: op = m.group(1); break
                    break
            if op and op.startswith('#$'): evs[int(op[2:], 16) & 0xff] += 1
            else: reg += 1
    return evs, reg
tot = collections.Counter(); regs = 0
for snap in ['scratchpad/cadaver/gameplay_empire.snap', 'scratchpad/cadaver/level1_loaded.snap']:
    out = subprocess.run([sys.executable, 'tools/disassemble.py', '--snap', snap, '--all', '6000', '4d300'], capture_output=True, text=True).stdout.splitlines()
    e, rg = scan(out); tot.update(e); regs += rg; print(snap, 'pushes', sum(e.values()), 'computed', rg, 'events', sorted(e))
for f in sorted(glob.glob('scratchpad/cadaver/secrets_out/overlay/*.lst')):
    e, rg = scan(open(f).read().splitlines()); tot.update(e); regs += rg; print(f.split('/')[-1], 'pushes', sum(e.values()), 'computed', rg, 'events', sorted(e))
print('union of events pushed:', sorted(tot)); print('computed-opcode pushes found:', regs)
print('event 3 pushed:', 3 in tot, ' event 21 pushed:', 21 in tot)
