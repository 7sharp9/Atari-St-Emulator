"""Blind rediscovery of the cheat-name compare with an execution profile (DEVELOPING.md "Execution profile").
usage: cheat_profile.py [--dll <stserver.dll>] [NAME CONTROL]     (default LUMBAJAK QWERTYXZ)

1. With the REPL name-entry driver (cheat_entry.py), from data/name_entry.snap: type the first 7 letters of
   NAME, move the cursor to its 8th, snapshot (data/profile/pre8_<NAME>.snap); the same for CONTROL.
2. In stserver, from each snapshot: profile_start, the 8th fire pick (joystick 1 $80, then released), then
   1,800,000 steps (cheat_entry.run gives the entry 1.5M after the pick to compare the name and store the code).
3. tools/profdiff.py NAME-run vs CONTROL-run with --text NAME (an operand whose bytes occur in NAME).
Prints $bb7d after each run (1 for LUMBAJAK, 0 for the control; secrets.md row 1) and the ranked compares;
the cheat-name compare is the one reading the names at $1837e (README "Cheat names").
"""
import argparse, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cheat_entry import Repl, move_to, fire_letter, CELL, ROOT, DISK
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from stclient import StServer

ap = argparse.ArgumentParser()
ap.add_argument('--dll', default=None)
ap.add_argument('names', nargs='*', default=['LUMBAJAK', 'QWERTYXZ'])
args = ap.parse_args()
OUT = os.path.join(ROOT, 'scratchpad/impossamole/agents/secrets/data/profile')
os.makedirs(OUT, exist_ok=True)

def prep(name):
    path = os.path.join(OUT, f'pre8_{name}.snap')
    if os.path.exists(path):
        return path
    r = Repl('scratchpad/impossamole/agents/secrets/data/name_entry.snap')
    r.cmd('s 30000')
    for ch in name[:7]:
        move_to(r, CELL[ch]); fire_letter(r)
    move_to(r, CELL[name[7]])
    print(f'  {name}: buffer {r.mem(0x1a07a, 8)!r} cell {r.b(0x19c1e)}')
    r.snap(path); r.close()
    return path

def profile(s, snap, name):
    s('load', snapshot=snap, disk=os.path.join(ROOT, DISK))
    s('profile_start')
    s('kbd', bytes=[0xff]); s('step', n=300); s('kbd', bytes=[0x80])
    s('step', n=200000)
    s('kbd', bytes=[0xff]); s('step', n=300); s('kbd', bytes=[0x00])
    s('step', n=1800000 - 600)
    st = s('profile_stop', path=os.path.join(OUT, f'{name}.json'))
    print(f'  {name}: $bb7d = {s.read(0xbb7d, 1)[0]}  {st}')

name, control = args.names
snaps = {n: prep(n) for n in (name, control)}
s = StServer(ROOT, dll=args.dll)
for n in (name, control):
    profile(s, snaps[n], n)
s.close()
vals = ['--text', name]
print(subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'profdiff.py'), os.path.join(OUT, f'{name}.json'),
                      os.path.join(OUT, f'{control}.json'), '--top', '25', *vals], capture_output=True, text=True, check=True).stdout)
