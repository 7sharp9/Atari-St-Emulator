"""mkland.py <land> [extra repl cmds...]: print REPL pokes that turn scratchpad/pm122/end/land1_pick_end.snap (stopped at $11414
at the end of the conquest-map pick, resource $b resident) into a pick of campaign land <land>: $580a4 and the 332-byte
parameter entry at $580a6 (from $3f428 + land*$14c, read from the snapshot's own RAM)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap
land = int(sys.argv[1])
ram = ram_from_snap(str(ROOT / 'scratchpad/pm122/end/land1_pick_end.snap'))
ent = ram[0x3f428 + land * 0x14c: 0x3f428 + (land + 1) * 0x14c]
out = ['w 580a4 %04x%04x' % (land, ram[0x580a6] << 8 | ram[0x580a7])]  # keeps word 580a6 for now
out = []
out.append('w 580a4 %04x' % land + '0000') if False else None
# $580a4 is a word at an even address followed by $580a6 (entry bytes 0,1): write them together as one longword
out.append('w 580a4 %04x%02x%02x' % (land, ent[0], ent[1]))
for i in range(2, 0x14c, 4):
    chunk = ent[i:i + 4]
    if len(chunk) < 4:
        chunk = chunk + ram[0x580a6 + i + len(chunk):0x580a6 + i + 4]
    out.append('w %x %s' % (0x580a6 + i, chunk.hex()))
print('\n'.join(out))
