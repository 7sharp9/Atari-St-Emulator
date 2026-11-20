"""Shared helpers for the frontend scripts (HUD, sound, game over): the REPL runner, the work directory $VIRUS_WORK/frontend and the
whole-image listing regenerated with tools/disassemble.py (never a stored listing)."""
import os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from vcommon import ROOT, WORK, work   # noqa: E402

OUT = work('frontend')
os.makedirs(OUT, exist_ok=True)
G_GAME2 = work('drive', 'g_game2.snap')       # human game on the wave-1 launch pad (reversing/virus/drive.sh)
CODE_SNAP = G_GAME2

def run(snap, cmds):
    """Run REPL lines against a snapshot (ATARI_NOTRACE=1); returns stdout+stderr."""
    env = dict(os.environ, ATARI_NOTRACE='1')
    p = subprocess.run(['dotnet', 'exec', os.path.join(ROOT, 'bin/Debug/net8.0/M68000.dll'), 'resume', snap, 'repl'],
                       input='\n'.join(cmds) + '\nq\n', capture_output=True, text=True, cwd=ROOT, env=env)
    return p.stdout + p.stderr

def listing():
    """The code listing $c000..$28000 of CODE_SNAP as a list of lines, written to $OUT/code.lst by tools/disassemble.py --all."""
    path = os.path.join(OUT, 'code.lst')
    with open(path, 'w') as f:
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'disassemble.py'), '--snap', CODE_SNAP, '--all', 'c000', '28000'],
                       stdout=f, check=True, cwd=ROOT)
    return open(path).read().splitlines()
