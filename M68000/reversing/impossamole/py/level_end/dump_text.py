"""Print printable ASCII runs of a snapshot's RAM in a range: dump_text.py <snap> <lo hex> <hi hex>"""
import os, sys
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, ROOT + '/tools')
from pm_export import ram_from_snap
ram = ram_from_snap(Path(sys.argv[1]))
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
print(''.join(chr(b) if 32 <= b < 127 else '.' for b in ram[lo:hi]))
