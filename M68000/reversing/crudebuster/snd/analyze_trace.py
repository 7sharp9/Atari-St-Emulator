#!/usr/bin/env python3
"""Analyse rtrace logs (lua/rtrace.lua): sequencer stream bytes, opcode dispatch, chip writes in execution order.
usage: analyze_trace.py ops out/rt_*.log     operand byte counts per opcode index (observed), per channel
       analyze_trace.py chans out/rt_*.log   which chip registers each channel writes after a note
"""
import sys, re, collections, glob

def events(path):
    for l in open(path):
        p = l.split()
        if p: yield p

def ops(paths):
    # (idx) -> Counter of operand counts ; (idx) -> set of channels
    cnt = collections.defaultdict(collections.Counter)
    chs = collections.defaultdict(collections.Counter)
    jumps = collections.defaultdict(int)
    for path in paths:
        pend = {}   # ch -> (pos, byte, idx)
        last = {}   # ch -> (pos, byte) last fetch
        for p in events(path):
            k = p[0]
            if k in ('F', 'G'):
                ch = int(p[1]); pos = int(p[2], 16) + int(p[3]); b = int(p[4], 16)
                if ch in pend:
                    ppos, pb, idx = pend.pop(ch)
                    n = pos - ppos - 1
                    if 0 <= n <= 8:
                        cnt[idx][n] += 1
                    else:
                        jumps[idx] += 1
                last[ch] = (pos, b)
            elif k == 'D':
                ch = int(p[1]); idx = int(p[2])
                if ch in last:
                    pend[ch] = (last[ch][0], last[ch][1], idx)
                chs[idx][ch] += 1
    return cnt, chs, jumps

if __name__ == '__main__':
    mode = sys.argv[1]
    paths = sorted(sum((glob.glob(a) for a in sys.argv[2:]), []))
    if mode == 'ops':
        cnt, chs, jumps = ops(paths)
        for idx in range(72):
            c = cnt.get(idx, {})
            print('%02x (idx %2d) operand counts %s  channels %s  nonlinear %d' % (0x90 + idx, idx, dict(c), dict(sorted(chs[idx].items())), jumps.get(idx, 0)))

def chan_writes(paths):
    """For each channel, which (chip, reg) are written between one of its note fetches and the next stream fetch of any channel."""
    res = collections.defaultdict(collections.Counter)
    for path in paths:
        cur = None            # channel whose note was just fetched
        reg = {}
        for p in events(path):
            k = p[0]
            if k in ('F', 'G'):
                ch = int(p[1]); b = int(p[4], 16)
                note = (0x70 <= b < 0x90) or b >= 0xe0
                cur = ch if note else None
            elif k == 'D':
                cur = None
            elif k == 'E' and cur is not None:
                chip, kind, v = p[1], p[2], int(p[3], 16)
                if kind == 'a': reg[chip] = v
                else:
                    r = reg.get(chip, -1)
                    if chip == 'ym2151':
                        cls = 'kon' if r == 0x08 else ('KC' if 0x28 <= r < 0x30 else ('KF' if 0x30 <= r < 0x38 else ('TL' if 0x60 <= r < 0x80 else 'r%02x' % r)))
                    elif chip == 'ym2203':
                        cls = 'kon' if r == 0x28 else ('FNUM' if 0xa0 <= r <= 0xa6 else ('SSGper' if r < 6 else ('SSGvol' if 8 <= r <= 10 else ('TL' if 0x40 <= r < 0x50 else 'r%02x' % r))))
                    else:
                        cls = 'byte'
                    res[cur][(chip, cls)] += 1
    return res
if __name__ == '__main__' and mode == 'chans':
    res = chan_writes(paths)
    for ch in sorted(res):
        print(ch, ', '.join('%s:%s=%d' % (k[0], k[1], v) for k, v in sorted(res[ch].items())))

def op_regs(paths):
    """For every opcode index: the chip registers written between its dispatch and the next stream fetch / dispatch (register = last address write)."""
    res = collections.defaultdict(collections.Counter)
    for path in paths:
        cur = None
        reg = {}
        for p in events(path):
            k = p[0]
            if k in ('F', 'G'): cur = None
            elif k == 'D': cur = int(p[2])
            elif k == 'E' and cur is not None:
                chip, kind, v = p[1], p[2], int(p[3], 16)
                if chip.startswith('ym'):
                    if kind == 'a': reg[chip] = v
                    else:
                        r = reg.get(chip, -1)
                        # normalise per-channel register groups
                        if chip == 'ym2151' and r >= 0x20: r = (r & 0xf8) | 0 if r < 0x28 else r & 0xf8
                        res[cur][(chip, '%02x' % r)] += 1
                else:
                    res[cur][(chip, 'byte')] += 1
    return res
if __name__ == '__main__' and mode == 'opregs':
    res = op_regs(paths)
    for idx in range(72):
        c = res.get(idx)
        if c: print('%02x idx%2d  %s' % (0x90 + idx, idx, ', '.join('%s:%s=%d' % (k[0][2:], k[1], v) for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:10])))
