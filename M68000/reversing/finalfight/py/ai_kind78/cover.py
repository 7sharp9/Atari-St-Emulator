#!/usr/bin/env python3
"""cover.py <hits files...>: sum execution counts over runs and list handler entries never executed."""
import sys, collections
tot = collections.Counter(); order = []
for f in sys.argv[1:]:
    for l in open(f):
        a, c = l.split(); 
        if a not in order: order.append(a)
        tot[a] += int(c)
zero = [a for a in order if tot[a] == 0]
print('entries', len(order), 'executed', len(order) - len(zero), 'never', len(zero))
print('never:', ' '.join(zero))
