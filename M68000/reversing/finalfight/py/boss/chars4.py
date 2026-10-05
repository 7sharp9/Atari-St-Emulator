"""chars4.py: per-kind character records of the pool-4 bosses (92(A6) bases set at $40a8c, $42ad0, $45ff0/$46d1c, $4becc/$4caa4, $4eaaa/$4fccc): health words by level (+0..+63), defence class (+64..+95), damage rows (+96..).
$2fa2 reads hp = word[base + 2*lvl], def = byte[base + 64 + lvl], 92 = base + $60 + lvl; DAMND overrides the health with $12c (1 player) / $1c2 (2 players) at $3d462; Sodom does the same at $40cb0."""
import os, sys
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
BASES = {'kind0 DAMND 1P': (0x40572, 0x40632), 'kind1 SODOM 1P': (0x45d8c, 0x45e8c), 'kind2 EDI.E 1P': (0x48956, 0x489d6), 'kind4 ABIGAIL 1P': (0x4e800, 0x4e920), 'kind5 BELGER 1P': (0x510ec, 0x5114c)}
for name, (b1, b2) in BASES.items():
    print(name, 'base %x, 2P base %x, record size %d' % (b1, b2, b2 - b1))
    print('  hp words by level 0,4,8,12,16,20,24,28,31:', [w(b1 + 2*i) for i in (0, 4, 8, 12, 16, 20, 24, 28, 31)])
    print('  defence class by level (same):', [rom[b1 + 64 + i] for i in (0, 4, 8, 12, 16, 20, 24, 28, 31)])
    nrows = (b2 - b1 - 0x60) // 32
    for r in range(nrows):
        row = rom[b1 + 0x60 + 32*r: b1 + 0x60 + 32*r + 32]
        print('  damage row $%02x by level 0,8,13,16,20,31: %s' % (32*r, [row[i] for i in (0, 8, 13, 16, 20, 31)]))
