#!/usr/bin/env python3
"""lst.py lo hi : linear sweep listing of the Final Fight program ROM with word-offset dispatch tables printed as data.
A table is recognised after `move.w K(PC,Dm.w) == $base+Dm,Dn` (or `... jmp/jsr 2(PC,Dn.w)`): its words are printed as `.w` lines with their targets, the table
ends at the smallest target found so far (code normally follows), so a table that is followed by data is cut short at the first code target.
Handler entry points from `$5872` (pool 8) are labelled. Root from M68000_ROOT or derived from __file__ (this directory must stay four levels below M68000/)."""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(here, '../../../..'))
sys.path.insert(0, os.path.join(root, 'tools'))
from disassemble import Disassembler
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
dis = Disassembler(rom, rom_base=0)
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
handlers = {int.from_bytes(rom[0x5872 + 4 * i:0x5872 + 4 * i + 4], 'big'): i for i in range(60)}
MOVEW = re.compile(r'move\.w \S+ == \$([0-9a-f]+)\+D(\d),D(\d)$')
JUNK = re.compile(r'^(ori|bchg|bclr|bset|movep|\(line|\?\?\?|subi\?|ori\?|andi\?|eori\?|cmpi\?|btst D\d,|negx|subx|addx|abcd|sbcd|nbcd)')
pending = []
def flush():
    global pending
    if len(pending) >= 3:
        print('  ; ... %d data-like lines elided ($%06x..$%06x)' % (len(pending), pending[0][0], pending[-1][0]))
    else:
        for (pa, pt) in pending: print('  $%06x: %s' % (pa, pt))
    pending = []
def emit(a, text):
    if JUNK.match(text):
        pending.append((a, text))
    else:
        flush()
        print('  $%06x: %s' % (a, text))
a = lo
prev_base = None
skip = {}
while a < hi:
    if a in handlers:
        flush()
        print('; ===== pool 8 kind %02x handler %06x =====' % (handlers[a], a))
    if a in skip:
        flush()
        b, end = skip[a]
        n = (end - b) // 2
        for i in range(n):
            w = dis.rw(b + 2 * i)
            sw = (w ^ 0x8000) - 0x8000
            print('  $%06x: .w $%04x  -> $%06x' % (b + 2 * i, w, (b + sw) & 0xffffff))
        a = end
        continue
    try:
        text, nxt = dis.decode_one(a)
    except Exception:
        print('  $%06x: (decode error)' % a); a += 2; continue
    emit(a, text)
    m = MOVEW.match(text)
    if m:
        prev_base = int(m.group(1), 16)
    elif text.startswith('jmp 2(PC,') or text.startswith('jsr 2(PC,') or ' == $' in text and text.split()[0] in ('jmp', 'jsr'):
        if prev_base is not None:
            b = prev_base
            limit = 0x10000
            i = 0
            while 2 * i < limit:
                w = dis.rw(b + 2 * i)
                sw = (w ^ 0x8000) - 0x8000
                if sw > 0 and 2 * i < sw:
                    limit = min(limit, sw)
                i += 1
                if i > 40: break
            end = b + 2 * i if 2 * i >= limit else b + limit
            skip[nxt] = (b, b + min(limit, 2 * i))
            # the table follows the jmp directly in all handlers here
            if b != nxt:
                skip.pop(nxt, None)
                if b >= nxt:
                    skip[b] = (b, b + min(limit, 2 * i))
        prev_base = None
    elif not m:
        prev_base = None if not text.startswith('move.w') else prev_base
    a = nxt

flush()
