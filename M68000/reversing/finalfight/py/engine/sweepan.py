#!/usr/bin/env python3
"""sweepan.py <sweep.txt> : per injected sound id (z80sweep.lua markers) the sound CPU response in its observation window:
 - OKI6295 bytes written to $f002 (a byte with bit 7 set starts phrase (b&0x7f), the next byte is the channel mask in bits 4..7 and attenuation in bits 0..3; a byte below 0x80 stops the channels in bits 3..6)
 - YM2151 key-on events (register $08: channel = d&7, operator mask = d>>3&15) and key-offs, plus the number of register writes
Summary line per id: oki phrases started, ym channels keyed on, ym write count in the first 150 frames and in the last 30 frames of the window."""
import re, sys, collections
lines = open(sys.argv[1]).read().splitlines()
marks = []
evs = []
for l in lines:
    m = re.match(r'f=(\d+) S id=([0-9a-f]+)', l)
    if m: marks.append((int(m.group(1)), int(m.group(2), 16))); continue
    m = re.match(r'f=(\d+) Z (ym|w) a=([0-9a-f]+) d=([0-9a-f]+)', l)
    if m: evs.append((int(m.group(1)), m.group(2), int(m.group(3), 16), int(m.group(4), 16)))
res = {}
for i, (f, d) in enumerate(marks):
    end = marks[i + 1][0] - 40 - 1 if i + 1 < len(marks) else f + 150   # next window starts with $f0 + 40 frames
    end = min(end, f + 150)
    window = [e for e in evs if f <= e[0] < end]
    oki = []
    pend = None
    reg = None
    keyon = collections.Counter(); keyoff = 0; nym = 0; late = 0
    for (ff, k, a, dd) in window:
        if k == 'ym':
            if a == 0xf000: reg = dd
            else:
                nym += 1
                if ff >= end - 30: late += 1
                if reg == 0x08:
                    if (dd >> 3) & 15: keyon[dd & 7] += 1
                    else: keyoff += 1
        elif a == 0xf002:
            if pend is not None:
                oki.append('P%02x/ch%x/att%x' % (pend, dd >> 4, dd & 15)); pend = None
            elif dd & 0x80: pend = dd & 0x7f
            else: oki.append('stop%x' % (dd >> 3))
    res[d] = (len(window), oki, dict(keyon), keyoff, nym, late)
    print('id %02x: oki %-34s ym keyon %-28s keyoff %3d  ym writes %5d (last30f %4d)' % (d, ' '.join(oki[:6]) or '-', ','.join('%d:%d' % kv for kv in sorted(keyon.items())) or '-', keyoff, nym, late))
