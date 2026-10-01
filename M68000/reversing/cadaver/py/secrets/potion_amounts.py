"""potion_amounts.py <snap> (run from M68000/, like item_census.py): for every placed potion of id 0 (STAMINA), 7 (WATER), 9 (CURE), 13, 16: room, object id, block bytes +0..+3."""
import struct, sys
sys.path.insert(0, 'tools'); sys.path.insert(0, 'reversing/cadaver/py')
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
snap = sys.argv[1]
ram, base = load_ram(snap); a5 = snapshot_regs(snap)[0]['a5']
u16 = lambda a: struct.unpack_from('>H', ram, a)[0]
room_idx, room_dat, room_cnt = resource_type(ram, base, a5, 3)
obj_idx, obj_dat, _ = resource_type(ram, base, a5, 5)
t6 = resource_type(ram, base, a5, 6); t2 = resource_type(ram, base, a5, 2)
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
        c2 = resolve(ram, base, t2[0], t2[1], u16(t + 6))
        if c2 is None or ram[c2 + 22] != 2: continue
        blk = t + ram[t + 12]
        if ram[blk] in (0, 7, 9, 13, 16, 8, 12):
            print('room %2d obj %3d potion %2d blk %s' % (slot, oid, ram[blk], ram[blk:blk + 4].hex()))
