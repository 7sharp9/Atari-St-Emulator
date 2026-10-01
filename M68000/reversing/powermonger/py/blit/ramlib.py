"""Helpers: read RAM of a snapshot (cached .ram next to the snapshot copy)."""
import os, sys
from pathlib import Path
ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
from pm_export import ram_from_snap

def ram(snap):
    return ram_from_snap(ROOT / snap)

def words(r, a, n):
    return [(r[a+2*i]<<8)|r[a+2*i+1] for i in range(n)]
