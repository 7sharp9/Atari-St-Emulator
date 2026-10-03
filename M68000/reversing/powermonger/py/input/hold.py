"""hold.py <name>: real-mouse hold tests (pointer homed to 0,0 then moved 1:1; button held across hits runs).
Needed because the IKBD interrogation answer rewrites $2df92/$2df94 every frame, so poking the live pointer does not stick.
Run from M68000: uv run python reversing/powermonger/py/input/hold.py H1"""
import os, subprocess, sys
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
SNAP = 'scratchpad/pm142/rand1.snap'
ADDRS = '1310e 13154 13178 131f8 13212 13288 13362 13342 132da 132f4 1330e 13328 107d6 13f60 1338e 133a0 13386 1338a'
M = ['m 4bb3a 4', 'm ff9a 2', 'm 12f56 2', 'm 57ffc 2', 'm 58098 2', 'm 2df96 8']
HOME = ['mouse move -400 -400', 's 300000', 'mouse move 0 0', 's 300000']
def go(x, y): return ['mouse move %d %d' % (x, y), 's 300000', 'mouse move 0 0', 's 300000']
H = lambda n: ['hits %d %s' % (n, ADDRS)]
T = {
 'H1_right_hold_rotL': go(28, 158) + M + ['mouse down r'] + H(1000000) + M + ['mouse up r'],
 'H2_left_hold_rotL': go(28, 158) + M + ['mouse down l'] + H(1000000) + M + ['mouse up l'],
 'H3_right_hold_roseN': go(18, 172) + M + ['mouse down r'] + H(1000000) + M + ['mouse up r'],
 'H3b_left_hold_roseN': go(18, 172) + M + ['mouse down l'] + H(1000000) + M + ['mouse up l'],
 'H4_left_drag_minimap': go(20, 40) + M + ['mouse down l'] + H(600000) + M + ['mouse move 10 0', 's 300000', 'mouse move 0 0'] + H(600000) + M + ['mouse up l'],
 'H5_right_hold_zoom_in': go(50, 165) + M + ['mouse down r'] + H(1000000) + M + ['mouse up r'],
 'H6_strip_click_x50': go(50, 3) + M + ['mouse down l'] + H(600000) + M + ['mouse up l'],
}
n = sys.argv[1]
script = HOME + T[n] + ['q']
r = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl'], input='\n'.join(script) + '\n',
                   capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, ATARI_NOTRACE='1'))
out = [l for l in r.stdout.splitlines() if (l.startswith('  $') and l.split()[1] != '0') or l[:2].strip().isalnum() and ' ' in l and not l.startswith('mouse')]
print('=== ' + n); print('\n'.join(out))
