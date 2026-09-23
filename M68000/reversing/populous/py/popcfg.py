"""Shared paths for the Populous reversing scripts.

R    = the emulator directory (M68000/), derived from this file's location.
WORK = the untracked working directory holding the extracted disk files (files/), the
       relocated program image (pop_ad58.img), the headless disk (pop_auto.st) and the
       snapshots. Default M68000/scratchpad/pop; override with POP_WORK. See ../README.md.
"""
import os
R = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
WORK = os.environ.get('POP_WORK', os.path.join(R, 'scratchpad', 'pop'))
DLL = os.environ.get('POP_DLL', os.path.join(R, 'bin', 'Debug', 'net8.0', 'M68000.dll'))  # POP_DLL: test a scratch build
DISK = os.path.join(WORK, 'pop_auto.st')
