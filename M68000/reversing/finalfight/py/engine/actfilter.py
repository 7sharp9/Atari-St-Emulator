#!/usr/bin/env python3
"""actfilter.py <pd.log> [lo hi] : print ACT lines (propdrive.lua PD_ACT=1) only where the scene state fields change (flags, actor state bytes, player state, handshake bytes) or every 100 frames."""
import re, sys
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
prev = None
for l in open(sys.argv[1]):
    if not l.startswith('ACT'): continue
    m = re.match(r'ACT r=(\d+)', l)
    r = int(m.group(1))
    if r < lo or r > hi: continue
    key = re.sub(r' (cam|1116|918|x|y|P1 x|30|128)=\S+', '', re.sub(r'f=\d+ ', '', re.sub(r'ACT r=\d+', '', l)))
    key = re.sub(r'cam=\S+|1116=\S+|918=\S+|P1 x=\S+ y=\S+', '', key)
    key = re.sub(r'x=\S+ y=\S+ 30=\S+ 128=\S+', '', key)
    if key != prev or r % 100 == 0:
        print(l.rstrip()[:330])
    prev = key
