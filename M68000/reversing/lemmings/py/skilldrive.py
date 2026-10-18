"""Drive a skill on lemming 0 of sel.snap and print the terrain bitmap window around it.

Run from M68000/ (ATARI_NOTRACE is set here):
  uv run python reversing/lemmings/py/skilldrive.py <skill index> <count addr hex> <out dir> [--samples N --step S --x0 X0 --y0 Y0]
Skill index/count offset: mechanics.md "Skill assignment" (basher 5 / $26c28, miner 6 / $26c2c, blocker 3 / $26c26).
The script poked into the REPL is the click_blocker.txt recipe: poke index and count, pin the pointer, aim, click.
The terrain plane is the one-plane bitmap at $41806, stride $330 (mechanics.md "Collisions"); the window is 96 px wide
from the 16-px group of X0 and Y0..Y0+rows.
"""
import argparse, os, struct, subprocess, sys
ap = argparse.ArgumentParser()
ap.add_argument('index', type=int); ap.add_argument('count_addr'); ap.add_argument('out')
ap.add_argument('--samples', type=int, default=8); ap.add_argument('--step', type=int, default=30000)
ap.add_argument('--x0', type=int, default=688); ap.add_argument('--y0', type=int, default=56)
ap.add_argument('--rows', type=int, default=40); ap.add_argument('--snap', default='scratchpad/lemmings/sel.snap')
ap.add_argument('--noclick', action='store_true')
ap.add_argument('--cells', default='', help='c0,r0,r1,val: poke object-map cells (8 columns from c0, rows r0..r1) to val (one byte, e.g. 9 steel)')
ap.add_argument('--wall', default='', help='gx0,gx1,y0,y1: fill the 16-px groups gx0..gx1 (plane 0 and 1 words) for rows y0..y1 before the run')
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
g0 = a.x0 // 16
def dump_cmds():
    c = ['m 23484 44']
    for r in range(a.rows):
        c.append('m %x 48' % (0x41806 + (a.y0 + r) * 0x330 + g0 * 8))
    return c
s = []
if a.wall:
    gx0, gx1, wy0, wy1 = map(int, a.wall.split(','))
    for y in range(wy0, wy1 + 1):
        for gx in range(gx0, gx1 + 1):
            s.append('w %x ffffffff' % (0x41806 + y * 0x330 + gx * 8))
if a.cells:
    c0, cr0, cr1, cv = map(lambda t: int(t, 0), a.cells.split(','))
    for r in range(cr0, cr1 + 1):
        for k in (0, 4):
            s.append('w %x %s' % (0x62f80 + r * 0x198 + c0 + k, ('%02x' % cv) * 4))
s += ['w 26c1a %04x0000' % a.index, 'w %s 00050000' % a.count_addr]
s += ['mouse move -127 -127', 's 30000'] * 3
s += ['mouse move 127 65', 's 12000', 'mouse move 22 0', 's 12000']
s += dump_cmds()
if not a.noclick:
    s += ['mouse down l', 's 60000', 'mouse up l', 's 12000']
for i in range(a.samples):
    s += ['m 26c04 48'] + dump_cmds() + ['s %d' % a.step]
s += ['q']
open(os.path.join(a.out, 'drive.txt'), 'w').write('\n'.join(s) + '\n')
env = dict(os.environ, ATARI_NOTRACE='1')
out = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', a.snap, 'repl', '--disk-a',
                      'scratchpad/lemmings/lemmings.st'], input=open(os.path.join(a.out, 'drive.txt')).read(),
                     capture_output=True, text=True, env=env).stdout
open(os.path.join(a.out, 'raw.txt'), 'w').write(out)
lines = [l for l in out.splitlines() if l[:3].strip() and all(len(t) == 2 for t in l.split()[:4]) and len(l.split()) >= 16]
per = 1 + a.rows  # lemming row + terrain rows ; the 48-byte click struct row is longer
frames, cur = [], None
blocks = [l for l in lines]
# group: the click-struct line has 48 bytes and the terrain rows 48 too, so go by order: struct, rec, rows
i = 0; n_first = 1 + a.rows
def rec(l):
    b = bytes(int(t, 16) for t in l.split())
    return struct.unpack('>HH', b[0:4]) + (struct.unpack('>h', b[8:10])[0], struct.unpack('>I', b[14:18])[0])
def art(rows):
    o = []
    for r, l in enumerate(rows):
        b = bytes(int(t, 16) for t in l.split())
        bits = ''
        for g in range(6):
            w = (b[g * 8] << 8) | b[g * 8 + 1]
            bits += format(w, '016b')
        o.append('%3d ' % (a.y0 + r) + bits.replace('0', '.').replace('1', '#'))
    return o
seq = blocks
# first dump (pre-click): rec + rows
pos = 0
def take(k):
    global pos
    r = seq[pos:pos + k]; pos += k; return r
pre = take(n_first)
frames.append(('pre-click', rec(pre[0]), art(pre[1:])))
for i in range(a.samples):
    st = take(1)
    d = take(n_first)
    frames.append(('t+%d' % (i * a.step), rec(d[0]), art(d[1:])))
res = []
for name, r, rows in frames:
    res.append('== %s lemming0 x=%d y=%d dir=%d state=%x   (columns: x %d..%d)' % (name, r[0], r[1], r[2], r[3], g0 * 16, g0 * 16 + 95))
    res += rows
open(os.path.join(a.out, 'frames.txt'), 'w').write('\n'.join(res) + '\n')
print('\n'.join(res[:1 + a.rows + 1]))
print('frames:', len(frames), '->', os.path.join(a.out, 'frames.txt'))
