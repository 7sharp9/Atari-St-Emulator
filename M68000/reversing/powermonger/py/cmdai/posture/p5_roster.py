"""p5_roster.py <snap>: the REPL lines that dismiss object 6's whole group (p5_roster.sh dismiss). Prints a '#' summary
line, then the pokes: the group's posture := 2 (all men go), its side's group word $58042 + 2*side := the group, the
side's slot $58016 + 6*side := {side, $14, 0, 0} in state 2 (commander/README.md "the command buffer"). Each longword
write keeps the neighbouring bytes read from the snapshot. Exit 1 when the man is not in a roster (bit 6 of byte 7)."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap
b = ram_from_snap(sys.argv[1]); m = 0x51c92
w = lambda a: int.from_bytes(b[a:a + 2], 'big')
side, bit6 = b[m + 5], b[m + 7] >> 6 & 1
lead = 0x51b66 + w(m + 28) if w(m + 28) else m       # word 28: the lead, 0 when the man leads ($539a)
grp = w(lead + 42)                                   # the group in the group-offset frame
gb = 0x51538 + grp
print(f'# man side {side} bit6 {bit6} lead ${lead:x} group ${grp:x} (k {(grp - side * 0x13c - 0x4c) // 2}) '
      f'men {w(gb - 24)} posture {w(gb + 60)}')
if not bit6 or not 1 <= side <= 4:
    sys.exit(1)
slot, gw = 0x58016 + 6 * side, 0x58042 + 2 * side
print(f'w {gb + 60:x} 0002{w(gb + 62):04x}')
print(f'w {gw:x} {grp:04x}{w(gw + 2):04x}')
print(f'w {slot:x} {side:02x}140000')
print(f'w {slot + 4:x} 0200{w(slot + 6):04x}')
