"""Dump SoundEffectTable $177d2's 54 records (18 bytes each) from a snapshot to <W>/sound/records.bin and .json.
Usage: dump.py <snap>"""
import os, sys, struct, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
ram = vcommon.load_ram(sys.argv[1])
ptrs = [struct.unpack_from('>I', ram, 0x177d2 + 4 * i)[0] for i in range(54)]
recs = [{'id': i, 'addr': p, 'words': list(struct.unpack_from('>9h', ram, p))} for i, p in enumerate(ptrs)]
out = vcommon.work('sound'); os.makedirs(out, exist_ok=True)
json.dump(recs, open(os.path.join(out, 'records.json'), 'w'))
open(os.path.join(out, 'records.bin'), 'wb').write(b''.join(ram[p:p + 18] for p in ptrs))
print(f'dumped {len(recs)} records from {hex(min(ptrs))} to {hex(max(ptrs))}')
