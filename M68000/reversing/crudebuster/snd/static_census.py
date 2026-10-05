#!/usr/bin/env python3
"""Static census of the opcodes in every channel stream of every song (music grammar for flag-1 songs: length < $70, notes $70-$8f/$e0-$ff;
effect grammar for flag-0 songs: duration < $80, note $80-$8f).  Each stream is decoded from its pointer until $a8 (END), a backward jump or a stop
at the repeat/call structure limit; the decode must end cleanly (END or loop) for the grammar and operand lengths (static_streams.OPLEN) to be accepted.
usage: static_census.py"""
import sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import songs as S, static_streams as SS
def music(start, ch, limit=20000):
    pos = start; ops = []; n = 0; stack = []; seen = set(); status = 'limit'
    while n < limit:
        n += 1
        b = S.rb(pos)
        if (pos, tuple(s[2] if s[0] == 'rep' else 0 for s in stack)) in seen and not stack:
            status = 'loop'; break
        seen.add((pos, tuple(s[2] if s[0] == 'rep' else 0 for s in stack)))
        if b < 0x70: pos += 1
        elif b < 0x90 or b >= 0xe0: pos += 1
        else:
            idx = b - 0x90
            if idx >= 72: status = 'bad'; break
            k = SS.OPLEN.get(idx)
            if idx in (19, 20, 21) and ch >= 11: k = 1
            if idx in (19, 20, 21) and ch < 8: k = 0
            if k is None: status = 'unknown-op %02x' % b; break
            args = [S.rb(pos + 1 + j) for j in range(k)]
            ops.append((idx, ch))
            if idx == 24: status = 'END'; break
            if idx == 9:
                tgt = args[0] | args[1] << 8
                if tgt <= pos: status = 'loop'; break
                pos = tgt; continue
            if idx == 10: stack.append(['rep', pos + 2, args[0]]); pos += 2; continue
            if idx == 11:
                if not stack: status = 'bad-endrep'; break
                top = stack[-1]; top[2] -= 1
                if top[2] > 0: pos = top[1]
                else: stack.pop(); pos += 1
                continue
            if idx == 12: stack.append(['call', pos + 3]); pos = args[0] | args[1] << 8; continue
            if idx == 13:
                if not stack: status = 'bad-ret'; break
                pos = stack.pop()[1]; continue
            pos += 1 + k
    return ops, status
cnt = collections.Counter(); status = collections.Counter(); chcnt = collections.defaultdict(collections.Counter)
nstreams = 0
for i in range(1, S.MAXID + 1):
    p, h, chans, q = S.header(i)
    for ch, a in chans:
        nstreams += 1
        if h[2] & 1:
            ops, st = music(a, ch)
        else:
            ev, loops = SS.decode(a, ch)
            ops = [(e0, ch) for e0 in []]
            # effect streams: reuse SS (names) -> count opcodes through a re-decode of raw ops
            ops = []; st = 'END' if ev and ev[-1][0] == 'END' else ('loop' if loops else 'other:%s' % ev[-1][0])
            # raw opcode census for effect streams: walk again quickly
            pos = a; seen = 0
            # use SS.decode events: map names back to idx
            inv = {v: k for k, v in SS.NAME.items()}
            for e in ev:
                if e[0] in inv: ops.append((inv[e[0]], ch))
                elif e[0].startswith('op') and len(e[0]) == 4: ops.append((int(e[0][2:], 16) - 0x90, ch))
        status[st] += 1
        for idx, c in ops: cnt[idx] += 1; chcnt[idx][c] += 1
print('streams decoded: %d; end status: %s' % (nstreams, dict(status)))
unused = [i for i in range(72) if i not in cnt]
print('opcodes never present in any decoded stream (one pass each): %s' % ' '.join('%02x' % (0x90 + i) for i in unused))
