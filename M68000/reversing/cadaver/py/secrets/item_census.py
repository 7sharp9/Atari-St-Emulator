"""item_census.py <snap>: which spells and potions the 72-room world actually places.
The object description routine $011066 (run for the "what is this" action) reads the template class byte at template+22 and a
type-specific block at template + template[12]:  class 1 = spell scroll: (blk+0) spell id (name via the (A5)+108 table, 8-byte
records, word 0 = string index), (blk+1) power, (blk+2) charges, blk+3 bit0 = "UNKNOWN" name; class 2 = potion: (blk+0) potion id
(name via (A5)+112); class bit7 = weapon/ammo; 4 = container (open/closed, locked); 8 = other use item.  Walks every room's
type-5 object id list (room_object_census.py's resolver), reads each type-6 template, and prints the spell/potion placements plus
which ids of the two name tables are never placed anywhere.
    uv run python reversing/cadaver/py/secrets/item_census.py [snap]          (default gameplay_empire.snap)"""
import struct, sys, collections
sys.path.insert(0, 'tools'); sys.path.insert(0, 'reversing/cadaver/py')
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
from name_strings import decode_index
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
ram, base = load_ram(snap); a5 = snapshot_regs(snap)[0]['a5']
u16 = lambda a: struct.unpack_from('>H', ram, a)[0]
u32 = lambda a: struct.unpack_from('>I', ram, a)[0]
t168, t172 = u32(a5 + 168), u32(a5 + 172)
name = lambda i: decode_index(ram, 0, t168, t172, i).split(b'\0')[0].decode('latin1')
room_idx, room_dat, room_cnt = resource_type(ram, base, a5, 3)
obj_idx, obj_dat, _ = resource_type(ram, base, a5, 5)
t6 = resource_type(ram, base, a5, 6)
spells, potions, classes = collections.defaultdict(list), collections.defaultdict(list), collections.Counter()
for slot in range(room_cnt):
    rec = resolve(ram, base, room_idx, room_dat, slot)
    if rec is None: continue
    stream = resolve(ram, base, obj_idx, obj_dat, slot)
    if stream is None: continue
    for i in range(ram[rec + 29] + 1):
        oid = u16(stream + 2 * i)
        if oid == 0 or oid >= t6[2]: continue
        t = resolve(ram, base, t6[0], t6[1], oid)
        if t is None: continue
        cls = ram[t + 22]; classes[cls] += 1
        blk = t + ram[t + 12]
        if cls == 1: spells[ram[blk]].append((slot, oid, ram[blk + 1], ram[blk + 2], ram[blk + 3] & 1))
        if cls == 2: potions[ram[blk]].append((slot, oid))
print('placed-object class histogram (class byte at template+22):', dict(sorted(classes.items())))
sp = resolve.__globals__  # noqa
stab, ptab = u32(a5 + 108), u32(a5 + 112)
print('\nSPELLS  id name  -> placements (room slot, object id, power, charges, unknown-name flag)')
for sid in range(27):
    print('  %2d %-16s %s' % (sid, name(u16(stab + 8 * sid)), spells.get(sid, 'NEVER PLACED')))
print('  ids placed outside 0..26:', {k: v for k, v in spells.items() if k > 26})
print('\nPOTIONS id name -> placements (room slot, object id)')
for pid in range(18):
    print('  %2d %-16s %s' % (pid, name(u16(ptab + 8 * pid)), potions.get(pid, 'NEVER PLACED')))
print('  ids placed outside 0..17:', {k: v for k, v in potions.items() if k > 17})
