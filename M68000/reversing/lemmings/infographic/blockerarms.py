"""The two blocker arms behind the infographic's trajectory plot (mechanics.md "Collisions", click_blocker.txt's recipe):
sel.snap, skill 3 and count 5 poked, pointer aimed at lemming 0, click or no click, then 30 samples of the whole 10-record
array, 60,000 steps apart. Writes <out>/outB.txt (blocker) and <out>/outC.txt (control): one line of 440 hex bytes a sample.
Run from M68000/:  python3 reversing/lemmings/infographic/blockerarms.py <out dir>"""
import os, subprocess, sys
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
pre = ['w 26c1a 00030000', 'w 26c26 00050000'] + ['mouse move -127 -127', 's 30000'] * 3 + ['mouse move 127 65', 's 12000', 'mouse move 22 0', 's 12000']
def arm(name, click):
    s = pre + (['mouse down l', 's 60000', 'mouse up l', 's 12000'] if click else ['s 72000'])
    for i in range(30): s += ['s 60000', 'm 23484 440']
    s.append('q')
    o = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', 'scratchpad/lemmings/sel.snap', 'repl', '--disk-a',
                        'scratchpad/lemmings/lemmings.st'], input='\n'.join(s) + '\n', capture_output=True, text=True,
                       env=dict(os.environ, ATARI_NOTRACE='1')).stdout
    L = [l for l in o.splitlines() if len(l.split()) >= 16 and all(len(t) == 2 for t in l.split())]
    # `m` prints 48 bytes a line: join the 10 lines (440 bytes) of each sample
    flat = [t for l in L for t in l.split()]
    assert len(flat) % 440 == 0, len(flat)
    open(os.path.join(out, name), 'w').write('\n'.join(' '.join(flat[i:i + 440]) for i in range(0, len(flat), 440)) + '\n')
arm('outB.txt', True); arm('outC.txt', False)
