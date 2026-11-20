"""sound_sites.py: every call of the sound trigger $17924 (Sound_Trigger) and $1790c (Sound_TriggerAttenuated) in the
whole-image listing, the effect id loaded into D0 just before it, and the enclosing symbol from virus.sym.
Usage: sound_sites.py  (regenerates $VIRUS_WORK/frontend/code.lst with tools/disassemble.py, reads reversing/virus/virus.sym)"""
import os, re, sys, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fcommon import ROOT as d, listing
lst = listing()
syms = sorted((int(l.split()[0].lstrip("$"), 16), l.split()[1]) for l in open(os.path.join(d, "reversing/virus/virus.sym")) if l.strip())
keys = [s[0] for s in syms]
def encl(a):
    i = bisect.bisect_right(keys, a) - 1
    return f"{syms[i][1]}+{a-syms[i][0]:x}" if i >= 0 else "?"
for i, l in enumerate(lst):
    m = re.match(r"\s+\$([0-9a-f]+): jsr \$(17924|1790c)\.l", l)
    if not m: continue
    d0 = "?"
    for j in range(i - 1, max(i - 14, 0), -1):
        mm = re.search(r": (?:move\.w #\$([0-9a-f]+)|moveq #(-?\d+)),D0$", lst[j])
        if mm:
            d0 = int(mm.group(1), 16) if mm.group(1) else int(mm.group(2)); break
    print(f"${m.group(1)}\t{'Atten' if m.group(2)=='1790c' else 'Plain'}\tD0={d0}\t{encl(int(m.group(1),16))}")
