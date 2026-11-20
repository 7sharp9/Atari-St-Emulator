"""Dump the model chain $aa72..$ce9a and the live palette from a Virus snapshot.
Usage: dump_data.py <snap> <outdir>   writes <outdir>/models.bin and <outdir>/palette.txt (16 words, hex 0RGB)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon, gfxview
ram, base = gfxview.load_ram(sys.argv[1])
out = sys.argv[2]; os.makedirs(out, exist_ok=True)
open(os.path.join(out, 'models.bin'), 'wb').write(bytes(ram[0xaa72:0xce9a]))
v = gfxview.load_video_regs(sys.argv[1])
open(os.path.join(out, 'palette.txt'), 'w').write(' '.join('%03x' % w for w in v['palette_words']) + '\n')
print('dumped models.bin (%d bytes) and palette.txt' % (0xce9a - 0xaa72))
