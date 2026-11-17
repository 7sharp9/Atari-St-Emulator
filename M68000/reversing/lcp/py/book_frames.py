"""Frames after Ctrl-B (README, "Control keys and house events"): presses Ctrl-B in `house.snap`, runs 8M steps, then
renders a frame every 3M steps (12 frames) to $LCP_WORK/keys/Bseq_NN.png, printing the book flag `$2c9be` and the
animation code `$512ee` at each.

usage: book_frames.py
Needs $LCP_WORK (default <root>/scratchpad/lcp) holding house.snap and disk/tmbird03_even.st.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('LCP_WORK') or os.path.join(root, 'scratchpad', 'lcp')
sys.path.insert(0, os.path.join(root, 'tools'))
from stclient import StServer  # noqa: E402

os.makedirs(os.path.join(WORK, 'keys'), exist_ok=True)
s = StServer(root)
s('load', snapshot=os.path.join(WORK, 'house.snap'), disk=os.path.join(WORK, 'disk', 'tmbird03_even.st'))
for b in (0x1d, 0x30):
    s('kbd', bytes=[b]); s('run', max_steps=15000)
for b in (0xb0, 0x9d):
    s('kbd', bytes=[b]); s('run', max_steps=2000)
s('run', max_steps=8_000_000)
for i in range(12):
    s('run', max_steps=3_000_000)
    s('render', path=os.path.join(WORK, 'keys', f'Bseq_{i:02d}.png'))
    print(i, s.read(0x2c9be, 2).hex(), s.read(0x512ee, 2).hex(), flush=True)
s.close()
