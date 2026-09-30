"""level_verb_live.py: object id 84 (LEVER, slot 60) carries the script block `33 00`: verb 51 = $010410 (LOAD LEVEL operand+1).
Inject its touch event (opcode 5) from gameplay_empire.snap and follow: $010410 -> (A5)+2524 = 1, (A5)+2518 = $ff, $00e53c (save
carry-over list, overlay list 4) -> $006890 restart -> $0068ca header read (sector $190) -> $0b5a8 -> $0154b0 FDC calls.
The restart shows the old 'place levels disk' prompt and waits for a key (the one-disk image has all levels), so a key is sent.  Expected: hits $fe24=1 $10410=1 $e53c=1 $6890=1 $68ca=1, 2524/2518 = 01/ff, then $154b0 reads of 661.. (level 1 overlay) into $4d65e.  Prints each $0154b0 call's D0 (linear sector) / D1 (count) / A0.  Expected: 400/1 (header), then the level-1 record's pairs from
the one-disk table: 661/4 (overlay), 665/132, 797/73, 870/55, 925/12."""
import sys, re
sys.path.insert(0, 'reversing/cadaver/py/secrets/overlay'); sys.path.insert(0, 'reversing/cadaver/py'); sys.path.insert(0, 'tools')
from ov import *
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
oid = 84
ram, base = load_ram('scratchpad/cadaver/gameplay_empire.snap'); regs, _ = snapshot_regs('scratchpad/cadaver/gameplay_empire.snap')
t6i, t6d, _ = resource_type(ram, base, regs['a5'], 6)
rec = resolve(ram, base, t6i, t6d, oid)
print('object id %d record $%06x script %s' % (oid, rec, bytes(ram[rec + 0x10:rec + 0x18]).hex()))
r = Repl()
q = int.from_bytes(r.mem(a5(152), 4), 'big')
wl(r, q, 0x00050000 | (rec >> 16)); wl(r, q + 4, ((rec & 0xffff) << 16)); ww(r, a5(1154), 1)
print('2524/2518 before', r.mem(a5(2524), 1).hex(), r.mem(a5(2518), 1).hex())
h = r.hits(200000, 0xfe24, 0x10410, 0xe53c, 0x6890, 0x68ca, 0xb5a8)
print({hex(k): v for k, v in h.items()}, '2524/2518 after', r.mem(a5(2524), 1).hex(), r.mem(a5(2518), 1).hex())
print('now at PC', hex(r.pc()), '(the level-change prompt wait: any key)')
r.cmd('kbd 39', 's 200000', 'kbd b9')
for n in range(12):
    o = '\n'.join(r.cmd('bp 154b0 30000000'))
    if 'breakpoint' not in o: print('no further $154b0 call:', o.splitlines()[0][:100]); break
    g = lambda reg: int(re.search(reg + r':([0-9a-f]{8})', o).group(1), 16)
    print('  $154b0 call %d: D0=%d D1=%d A0=$%06x' % (n, g('D0'), g('D1'), g('A0')), flush=True)
    r.cmd('s 1')
r.cmd('s 60000000')
print('after 60M more steps PC =', hex(r.pc()), '(main loop $6b7e region = level running)')
live = r.mem(0x4c65e, 2892)
want = open('scratchpad/cadaver/secrets_out/overlay/overlay_level1.bin', 'rb').read()[4:]
print('overlay RAM $04c65e after level 1 load: %d/%d bytes equal depacked level-1 overlay (overlay_level1.bin)' % (sum(a == b for a, b in zip(live, want)), len(want)))
print('(A5)+2534 =', r.mem(a5(2534), 4).hex(), ' header words at $4c65e:', r.mem(0x4c65e, 12).hex())
r.close()
