"""SELECT44.DAT (LSD!, 20480 bytes) loaded to $4c400 = bank-2 frame 100 on (384-byte 32x24 frames, 16 bytes per row: planes 0..3 as longwords).
Contact sheet of its 53 whole frames with the world-select palette $21682 (colour 0 drawn magenta)."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
from PIL import Image
s, *_ = depack(rd('SELECT44.DAT'))
r = ram(ROOT + '/scratchpad/impossamole/agents/world12/klondike_select.snap')
pal = [int.from_bytes(r[0x21682 + 2*i:0x21682 + 2*i + 2], 'big') for i in range(16)]
n = len(s) // 384
img = Image.new('RGB', (10 * 34, ((n + 9) // 10) * 26), (40, 40, 40)); px = img.load()
for f in range(n):
    ox, oy = (f % 10) * 34, (f // 10) * 26
    for y in range(24):
        pl = [int.from_bytes(s[f*384 + y*16 + 4*p: f*384 + y*16 + 4*p + 4], 'big') for p in range(4)]
        for x in range(32):
            v = sum(((pl[p] >> (31 - x)) & 1) << p for p in range(4))
            c = pal[v]
            px[ox + x, oy + y] = (255, 0, 255) if v == 0 else (((c >> 8) & 7) * 36, ((c >> 4) & 7) * 36, (c & 7) * 36)
img = img.resize((img.width * 3, img.height * 3), Image.NEAREST)
img.save(WORK + '/data/select44_frames.png')
print(n, 'frames of 384 bytes,', len(s) - n * 384, 'bytes left over')
