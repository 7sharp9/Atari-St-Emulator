"""seg.py <name>: run one pointer/key poke segment against a snapshot, print hits + state deltas.
Root derived from __file__ (reversing/powermonger/py/input/seg.py -> M68000). Usage: uv run python reversing/powermonger/py/input/seg.py S1 [snap]"""
import os, subprocess, sys
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
SNAP = sys.argv[2] if len(sys.argv) > 2 else 'scratchpad/pm142/rand1.snap'
ADDRS = '12fd8 1310e 13178 13154 131be 131e6 131f8 13212 13288 133ba 1343a 13444 134f4 13506 135c4 13736 1373c 13762 13824 13864 13892 1394c 13b84 13b94 9036 1898e 189f8 107d6 13f60 13362 13374 1338e 133a0 13342 13352 13386 1338a 132da 132e4 132f4 132fe 1330e 13318 13328 13332 13838 13846 1383a 13854'
def pos(x, y): return '%04x%04x' % (x, y)
def click(x, y, left=True, right_level=False):
    c = ['w 2df8e ' + pos(x, y), 'w 2df92 ' + pos(x, y)]
    if left: c.append('w 2df96 00010000')
    if right_level: c.append('w 2df9c 00000001')
    return c
SEG = {
 'S0': [],
 'S1_minimap_click': click(30, 70),
 'S2_minimap_armed_nocaptain': ['w 57fd4 000c0000'] + click(30, 70),
 'S3_strip_click': click(40, 3),
 'S4_rot_left_click': click(28, 158),
 'S5_rot_right_level': click(28, 158, left=False, right_level=True),
 'S6_zoom_in_click': click(50, 165),
 'S6b_zoom_out_click': click(50, 185),
 'S7_zoom_in_right': click(50, 165, left=False, right_level=True),
 'S8_rose_N_click': click(18, 172),
 'S8b_rose_E_click': click(30, 181),
 'S8c_rose_S_click': click(18, 195),
 'S8d_rose_W_click': click(6, 181),
 'S8e_rose_right_level': click(18, 172, left=False, right_level=True),
 'S9_sword_icon': click(243, 190),
 'S10_arrow_left': ['w 2deb4 000000ff'],
 'S11_minimap_hold_left': ['w 2df8e %s' % pos(20, 40), 'w 2df92 %s' % pos(20, 40), 'w 2df9c 00010000'],
}
name = sys.argv[1]
steps = os.environ.get('STEPS', '1500000')
extra = os.environ.get('PRE', '')
script = ['m 4bb3a 4', 'm ff9a 2', 'm 12f56 2', 'm 57ffc 2', 'm 57fd4 2', 'm 58098 2', 'm 2df96 8']
script += [l for l in extra.split(';') if l]
script += SEG[name]
script += ['hits %s %s' % (steps, ADDRS)]
script += ['m 4bb3a 4', 'm ff9a 2', 'm 12f56 2', 'm 57ffc 2', 'm 57fd4 2', 'm 58098 2', 'm 2df96 8', 'q']
env = dict(os.environ, ATARI_NOTRACE='1')
r = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl'], input='\n'.join(script) + '\n',
                   capture_output=True, text=True, cwd=ROOT, env=env)
print('=== ' + name); print(r.stdout[-3000:]); print(r.stderr[-500:])
