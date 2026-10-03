"""a3: dump the gate table $00fe84 (29 word offsets from the table base, dispatcher $011728 = add.w D0,D0 / adda.w 0(A2,D0.w),A2 / jmp (A2)) and the routine each event reaches. argv1 = snapshot (default gameplay_empire.snap)."""
import sys, os, struct
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from disassemble import ram_from_snap
snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'scratchpad/cadaver/gameplay_empire.snap')
ram = ram_from_snap(snap)
for ev in range(29):
    w = struct.unpack_from('>h', ram, 0xfe84 + 2 * ev)[0]
    print('event %2d: word %04x -> $%06x' % (ev, w & 0xffff, 0xfe84 + w))
