"""PICTURES.DCH = LSD! -> Huffman -> 64000 bytes = two 32000-byte ST low-res screens (loaded to $53000, $fa00 bytes); SELECT44.DAT = LSD! -> 20480 bytes.
Renders the two screens with palette $21682 (the text-screen palette the game installs with them) and checks the live copy in a Game Over snapshot."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
from huff import expand
from PIL import Image
o, *_ = depack(rd('PICTURES.DCH'))
e, used = expand(o)
print('PICTURES.DCH: LSD unpacked', len(o), 'huffman', len(e), 'stream consumed', used)
r = ram()
pals = {'$21682': r[0x21682:0x21682+32], '$21802': r[0x21802:0x21802+32]}
def render(scr, pal, path):
    img = Image.new('RGB', (320, 200)); px = img.load()
    P = [int.from_bytes(pal[2*i:2*i+2], 'big') for i in range(16)]
    for y in range(200):
        for xw in range(20):
            base = y * 160 + xw * 8
            w = [int.from_bytes(scr[base + 2*p: base + 2*p + 2], 'big') for p in range(4)]
            for b in range(16):
                v = sum(((w[p] >> (15 - b)) & 1) << p for p in range(4))
                c = P[v]; px[xw*16 + b, y] = (((c >> 8) & 7) * 36, ((c >> 4) & 7) * 36, (c & 7) * 36)
    img.save(path)
render(e[0:32000], pals['$21682'], WORK + '/data/pictures_0_worldselect.png')      # $25000, palette $21682 (page 2 of the title loop $17b9e)
render(e[32000:64000], pals['$21802'], WORK + '/data/pictures_1_title.png')          # $2cd00, palette $21802 (page 1 of the title loop $17b6e)
# Is it resident (Game Over snapshot)?  search the RAM of a Game Over state for the first 64 bytes of each half
g = ram(WORK + '/data/name_entry.snap')
for i in range(2):
    ch = e[i*32000 + 8000: i*32000 + 8064]
    print('half', i, 'chunk found in name_entry snapshot RAM at', hex(g.find(ch)) if g.find(ch) >= 0 else None)
s, *_ = depack(rd('SELECT44.DAT'))
print('SELECT44 unpacked', len(s))
w = ram(ROOT + '/scratchpad/impossamole/agents/world12/klondike_select.snap')
m = sum(1 for a, b in zip(s, w[0x4c400:0x4c400+len(s)]) if a == b)
print('SELECT44.DAT vs RAM $4c400 in klondike_select.snap:', m, '/', len(s))
