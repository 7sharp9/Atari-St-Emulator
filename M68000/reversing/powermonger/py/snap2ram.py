import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
from pm_export import ram_from_snap
from pathlib import Path
for p in sys.argv[1:]:
    Path(p[:-5]+'.ram').write_bytes(ram_from_snap(Path(p)))
