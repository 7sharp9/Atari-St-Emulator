"""Print every live object slot of a snapshot: uv run python objs.py <snap> [slots lo hi]"""
import os, sys
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, os.path.dirname(__file__))
from live_census import live_objects, ram_from_snap
ram = ram_from_snap(Path(sys.argv[1]))
for o in live_objects(ram):
    print({k: (hex(v) if k in ('addr', 'anim') else v) for k, v in o.items()})
print('hero', ram[0x1a572:0x1a572+8].hex(), 'camera', int.from_bytes(ram[0x227b6:0x227b8],'big'), 'hp', ram[0xbb74], 'weapon', ram[0xbb72])
