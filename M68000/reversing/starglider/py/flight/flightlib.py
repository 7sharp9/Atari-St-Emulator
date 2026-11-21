"""Shared helpers for the Starglider flight scripts: the named globals ($5bf00 + offset), a Drive on g_game1, and the
input encodings. Import with the walk-up used by every script in this directory."""
import os, sys

def _find_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            raise SystemExit('repo root (the directory holding tools/rdis.py) not found')
        d = p
    return d

ROOT = _find_root()
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'reversing', 'starglider', 'py'))
import sgcommon as sg
import stdrive as sd
from stclient import StServer

G = sg.GLOBALS
POLL = 44000          # one main-loop iteration is about 44,000 steps (BRIEF)

# name -> (A6 offset, signed); every word unless 'b' in the name table below
WORDS = dict(x=302, y=304, z=306, pitch=314, yaw=316, roll=318, spd=542, climb=570, bankadd=640,
             energy=606, shield=608, over=300, missiles=632, silo_t=658, ang640=640)
BYTES = dict(mode_dock=714, refuel=707, missile_cam=712, hit=703, cheat=717, xhair_lock=705, sound=715)
# absolute (non-A6) words: the mouse/keyboard stick accumulators the ISR and the key routine write
ACC = dict(stick_x=0xc3ce, stick_y=0xc3d0, stick_t=0xc3d4)
KEYMAP = dict(left=0x4b, right=0x4d, up=0x48, down=0x50, space=0x39, slash=0x35, x=0x2d, c=0x2e, semi=0x27,
              dot=0x34)

def state(dr):
    s = {k: dr.s16(G + o) for k, o in WORDS.items()}
    s.update({k: dr.u8(G + o) for k, o in BYTES.items()})
    s.update({k: dr.s16(a) for k, a in ACC.items()})
    return s

def new_drive(journal, snap=None):
    os.makedirs(os.path.dirname(journal), exist_ok=True)
    dr = sd.Drive(ROOT, journal=journal, period=POLL)
    dr.load(snap or sg.SNAP_GAME1, sg.DISK)
    return dr
