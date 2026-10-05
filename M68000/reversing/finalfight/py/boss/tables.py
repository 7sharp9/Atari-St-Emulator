"""tables.py: DAMND (pool 4 kind 0, $3d3d6) data tables read from the ROM: movement scripts ($3d6c4/$3d6e4), pause tables, attack picks ($3dbda, $3dc1a)."""
import os
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
sw = lambda a: w(a) - 65536 if w(a) & 0x8000 else w(a)
def hexb(a, n): return ' '.join('%02x' % x for x in rom[a:a+n])
print('movement pick  $3d6c4 (32 b)  :', hexb(0x3d6c4, 32))
print('movement script table $3d6e4 words:', [hex(w(0x3d6e4+2*i)) for i in range(14)])
n = 0
base = 0x3d6e4
for i in range(w(base)//2):
    a = base + w(base + 2*i)
    s = []
    while rom[a] < 0x80 and len(s) < 40: s.append(rom[a]); a += 1
    print('  move script %d @%x: %s end=%02x' % (i, base + w(base + 2*i), ' '.join('%02x' % x for x in s), rom[a]))
print('timer $3d974 (32 b)           :', hexb(0x3d974, 32))
print('timer $3d9ce (32 b)           :', hexb(0x3d9ce, 32))
print('walk time $3da1a words (1P/148=0):', [w(0x3da1a+2*i) for i in range(32)])
print('walk time $3da5a words (148=1)   :', [w(0x3da5a+2*i) for i in range(32)])
print('delay $3db58 words (150):', [w(0x3db58+2*i) for i in range(32)])
print('attack pick $3dbda (148=0) 32 b:', hexb(0x3dbda, 32))
print('attack pick (148=1) 32 b       :', hexb(0x3dbda+32, 32))
print('attack script table $3dc1a words:', [hex(w(0x3dc1a+2*i)) for i in range(6)])
for i in range(6):
    a = 0x3dc1a + w(0x3dc1a + 2*i)
    s = []
    while rom[a] < 0x80 and len(s) < 40: s.append(rom[a]); a += 1
    print('  attack script %d @%x: %s end=%02x' % (i, 0x3dc1a + w(0x3dc1a+2*i), ' '.join('%02x' % x for x in s), rom[a]))
print('timer $3def2 (32 b):', hexb(0x3def2, 32))
print('timer $3df72 (32 b):', hexb(0x3df72, 32))
print('timer $3e502 (32 b):', hexb(0x3e502, 32))
print('$40962 heading-step table (32 b):', hexb(0x4098c, 32))
print('$409ec map (160 b):', hexb(0x409ec, 16))
print('retaliate masks $3edea (4 B x 32):', [hex(int.from_bytes(rom[0x3edea+4*i:0x3edea+4*i+4],'big')) for i in range(32)])
print('retaliate masks $3edea+128 (148=1):', [hex(int.from_bytes(rom[0x3edea+128+4*i:0x3edea+128+4*i+4],'big')) for i in range(32)])
print('2P masks $3eeea:', [hex(int.from_bytes(rom[0x3eeea+4*i:0x3eeea+4*i+4],'big')) for i in range(32)])
print('2P masks $3eeea+128:', [hex(int.from_bytes(rom[0x3eeea+128+4*i:0x3eeea+128+4*i+4],'big')) for i in range(32)])
