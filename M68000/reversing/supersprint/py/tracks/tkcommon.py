"""Shared helpers for the `tracks` agent scripts (repo root derived via sscfg)."""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.environ.get('M68000_ROOT') or os.path.normpath(os.path.join(_HERE, '..', '..', '..', '..'))
os.environ.setdefault('M68000_ROOT', _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'reversing', 'supersprint', 'py'))
import sscfg
from repl import Repl
OUT = os.path.join(sscfg.WORK, 'agents', 'tracks')          # untracked: snaps/, data/, png/
def out(*p): 
    d = os.path.join(OUT, *p[:-1]) if len(p) > 1 else OUT
    os.makedirs(d, exist_ok=True); return os.path.join(d, p[-1])
def datfile(n): return open(os.path.join(sscfg.FILES, n), 'rb').read()
A4 = sscfg.A4

import struct
from PIL import Image
sys.path.insert(0, os.path.join(_ROOT, 'tools'))
def load_snap(path): 
    from gfxview import load_ram, load_video_regs
    ram, _ = load_ram(path); return ram
def st_rgb(w): return (((w>>8)&7)*36, ((w>>4)&7)*36, (w&7)*36)
def planar_to_idx(buf, w=320, h=200):
    """ST low-res 4-plane interleaved -> list of rows of colour indexes (numpy uint8 h x w)"""
    import numpy as np
    a = np.frombuffer(bytes(buf[:h*w//2]), dtype='>u2').reshape(h, w//16, 4)
    bits = ((a[:, :, :, None] >> (15 - np.arange(16))) & 1)        # h, grp, plane, bit
    idx = (bits[:, :, 0, :] | (bits[:, :, 1, :] << 1) | (bits[:, :, 2, :] << 2) | (bits[:, :, 3, :] << 3))
    return idx.reshape(h, w).astype('uint8')
def idx_to_img(idx, pal_words):
    import numpy as np
    pal = np.array([st_rgb(w) for w in pal_words], dtype='uint8')
    return Image.fromarray(pal[idx])
def snap_palette(ram, base=0xffff8240):
    return None

def render_snap(snap, png):
    import subprocess
    py = os.path.join(_ROOT, '.venv', 'bin', 'python')
    subprocess.run([py, os.path.join(_ROOT, 'tools', 'snap_render.py'), snap, png], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Repl2(Repl):
    """Repl whose cmd() reads a chosen number of 'PC:' register dumps (breakpoint/hits commands print their own
    register dump before the trailing `r`, which desynchronises the base class)."""
    def cmd2(s, c, npc=2):
        import re
        s.p.stdin.write(c.rstrip('\n') + '\nr\n'); s.p.stdin.flush()
        outl = []; seen = 0
        while True:
            line = s.p.stdout.readline()
            if not line: raise EOFError('\n'.join(outl[-20:]))
            line = line.rstrip('\n'); outl.append(line)
            if line.startswith('PC: '):
                s.p.stdout.readline(); seen += 1
                if seen >= npc: break
        regs = {}
        for l in outl:
            for m in re.finditer(r'\b([DA][0-7]|PC|USP|SSP):\s*([0-9a-f]{8})', l):
                regs[m.group(1)] = int(m.group(2), 16)
        return outl, regs
