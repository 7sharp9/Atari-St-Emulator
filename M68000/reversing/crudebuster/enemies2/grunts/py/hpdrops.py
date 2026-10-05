"""hpdrops.py <probe.txt>: list every change of an enemy's health (+5) with frame, state before/after, and the amount (first frame of a life excluded)."""
import sys, collections
prev = {}
cnt = collections.Counter()
for line in open(sys.argv[1]):
    p = line.split()
    if p[0] != "A": continue
    f, slot, b = int(p[1]), int(p[2]), bytes.fromhex(p[3])
    k = prev.get(slot)
    if k and k[0] == f - 1 and k[1][2] == b[2] and k[1][5] != b[5] and k[1][5] != 0 and b[5] < k[1][5]:
        d = k[1][5] - b[5]; cnt[(b[2], d)] += 1
        print(f"frame {f} slot {slot} type {b[2]:02x} hp {k[1][5]} -> {b[5]} (-{d}) state {k[1][3]:x} -> {b[3]:x} flags6={k[1][6]:02x} f17={k[1][17]:02x}")
    prev[slot] = (f, b)
print({(hex(t), d): n for (t, d), n in cnt.items()})
