"""class_census.py [snap]: for every placed object of all 72 rooms, the class byte (+22) and subclass (+23) of its type-2 class template
(reached via template+6, exactly as $009f02/$009440 do with `move.w 6(A0),D1; bsr $c576`) and the live-record class 2476(A5) sources; lists
which objects have class 8, $b or $c (the classes that make the rucksack panel offer icons $c (event 18) and $f (event 26))."""
import sys, struct, collections
sys.path.insert(0, 'tools'); sys.path.insert(0, 'reversing/cadaver/py')
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
ram, base = load_ram(snap); a5 = snapshot_regs(snap)[0]['a5']
u16 = lambda a: struct.unpack_from('>H', ram, a)[0]
room_idx, room_dat, room_cnt = resource_type(ram, base, a5, 3)
obj_idx, obj_dat, _ = resource_type(ram, base, a5, 5)
t6 = resource_type(ram, base, a5, 6); t2 = resource_type(ram, base, a5, 2)
hist = collections.Counter(); where = collections.defaultdict(list)
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
        c = resolve(ram, base, t2[0], t2[1], u16(t + 6))
        if c is None: continue
        k = (ram[c + 22], ram[c + 23]); hist[k] += 1; where[k].append((slot, oid))
print('(class, subclass) histogram over placed objects:')
for k, v in sorted(hist.items()): print('  class %3d sub %3d : %d' % (k[0], k[1], v), where[k][:6] if k[0] in (8, 11, 12) else '')
