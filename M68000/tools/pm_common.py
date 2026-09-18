"""Shared PowerMonger memory-map constants used by more than one tool
(pm_fsm_ref.py, pm_export.py, ...). Only constants that were independently
redefined with the same value in more than one file live here - most
per-tool addresses (grid/sprite layout, herd/garrison/group tables, etc.)
are only ever used by one tool and stay local to it.
"""

OBJ = 0x51b66          # entity object array (stride OBJ_STRIDE)
OBJ_STRIDE = 50
TERRAIN = 0x438ee      # terrain plane base
