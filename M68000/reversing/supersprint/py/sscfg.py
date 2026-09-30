"""Shared paths for the Super Sprint reversing scripts.

R    = the emulator directory (M68000/), derived from this file's location (or M68000_ROOT).
WORK = the untracked working directory holding the extracted disk (files/), the relocated program
       image (ss.img), the decompile (ss.c), the whole-image listing (ss.asm) and the snapshots.
       Default M68000/scratchpad/supersprint; override with SS_WORK. See ../README.md.
DLL  = the emulator; SS_DLL points at a scratch build.
"""
import os

R = os.environ.get('M68000_ROOT') or os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
WORK = os.environ.get('SS_WORK', os.path.join(R, 'scratchpad', 'supersprint'))
DLL = os.environ.get('SS_DLL', os.path.join(R, 'bin', 'Debug', 'net8.0', 'M68000.dll'))
DISK = os.path.join(WORK, 'Super Sprint.ST')
FILES = os.path.join(WORK, 'files')
PRG = os.path.join(FILES, 'AUTO', 'SSPRINT.PRG')
IMG = os.path.join(WORK, 'ss.img')          # PRG relocated to its runtime TEXT base
TEXT = 0xA304                               # runtime TEXT start (basepage $a204 + $100)
A4 = 0x1EB44                                # the game's global-state base register in every race snapshot
A5 = 0xA304                                 # thunk table base: `jsr d(A5)` is `jsr $a304+d` (../../scratchpad thunks.txt)

# anchor snapshots (rebuilt by drive.repl, see ../README.md)
SNAP_ATTRACT = os.path.join(WORK, 'ss_attract.snap')   # 40M steps cold boot: attract loop
SNAP_SELECT = os.path.join(WORK, 'ss_select.snap')     # SELECT TRACK screen
SNAP_RACE = os.path.join(WORK, 'ss_prep.snap')         # a live Track-1 race, one player joined (red car)
SNAP_RESULTS = os.path.join(WORK, 'ss_race0.snap')     # the WINNER'S CIRCLE results screen after that race
