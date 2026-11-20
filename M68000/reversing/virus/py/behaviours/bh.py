"""Shared setup for the behaviours scripts: repo root, work directory W/behaviours (W = $VIRUS_WORK or scratchpad/virus, as vcommon),
and the mpc modules (shot, shot_capture, replay) imported by path. Their own work directory is pointed at W/behaviours/mpc."""
import os, sys
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))
import vcommon
ROOT = vcommon.ROOT
BW = vcommon.work('behaviours')
os.makedirs(BW, exist_ok=True)
os.environ.setdefault('VIRUS_MPC_WORK', os.path.join(BW, 'mpc'))
sys.path.insert(0, os.path.join(os.path.dirname(_here), 'mpc'))
sys.path.insert(0, _here)
STARTS = os.path.join(vcommon.work('chain', 'long100', 'starts'))
