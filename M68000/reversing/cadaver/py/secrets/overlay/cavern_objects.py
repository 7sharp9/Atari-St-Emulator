"""cavern_objects.py [snap]: list the loaded room's objects with their type-6 template record (A0 after resolve(6,id)),
class byte 22(tmpl), instance offset 12(tmpl), instance bytes, display name; and the spell table (A5)+108 / potion table
(A5)+112 names.  Start snapshot default scratchpad/cadaver/gameplay_empire.snap.  Used to pick real target records for
callcap-ing overlay spell/use routines.  Expected: CAVERN's 22 objects (mechanics.md section 8), 27 spell names, 18 potions."""
import sys, struct
from pathlib import Path
sys.path.insert(0, 'reversing/cadaver/py'); sys.path.insert(0, 'tools')
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
from name_strings import decode_index
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
ram, base = load_ram(snap); regs, _ = snapshot_regs(snap); a5 = regs['a5']
U32 = lambda a: struct.unpack('>I', ram[a - base:a - base + 4])[0]
U16 = lambda a: struct.unpack('>H', ram[a - base:a - base + 2])[0]
t168, t172 = U32(a5 + 168), U32(a5 + 172)
room_idx, room_dat, _ = resource_type(ram, base, a5, 3); obj_idx, obj_dat, _ = resource_type(ram, base, a5, 5)
t6i, t6d, _ = resource_type(ram, base, a5, 6)
slot = U16(a5 + 1166); rec = resolve(ram, base, room_idx, room_dat, slot); n = ram[rec - base + 29]
stream = resolve(ram, base, obj_idx, obj_dat, slot); ids = [U16(stream + 2 * i) for i in range(n + 1)]
array_base = U32(a5 + 56)
def nm(i):
    if i in (None, 0xffff): return '<none>'
    b = decode_index(ram, base, t168, t172, i)
    for k, c in enumerate(b):
        if c < 0x20: b = b[:k]; break
    return b.decode('latin1')
print('room slot', slot, 'objects', len(ids))
for oid in ids:
    t = resolve(ram, base, t6i, t6d, oid)
    if t is None: continue
    slot_off = U16(t + 8); live = U32(array_base + slot_off + 6); inst = t + ram[t - base + 12]
    ni = U16(live + 10) if live else None
    lr = ram[live - base:live - base + 32].hex() if live else ''
    print('   live_rec $%06x cls22=%s %s' % (live, ram[live - base + 22] if live else None, lr))
    print('id %4d tmpl $%06x class %3d inst+%2d @ $%06x name %-16s inst %s' % (oid, t, ram[t - base + 22], ram[t - base + 12], inst, nm(ni), ram[inst - base:inst - base + 12].hex()))
print('spell table (A5)+108:')
for i in range(27):
    ent = U32(a5 + 108) if False else None
sp = U32(a5 + 108); po = U32(a5 + 112)
print(' ptrs spell $%06x potion $%06x' % (sp, po))
for i in range(27):
    a = sp + 8 * i; print('  spell %2d rec %s name %s' % (i, ram[a - base:a - base + 8].hex(), nm(U16(a))))
for i in range(18):
    a = po + 8 * i; print('  potion %2d rec %s name %s' % (i, ram[a - base:a - base + 8].hex(), nm(U16(a))))
