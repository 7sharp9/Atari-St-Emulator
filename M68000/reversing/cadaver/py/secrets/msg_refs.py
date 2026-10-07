"""msg_refs.py <snap>: which of the UI messages (string indices 0-127) a literal in the code names.  Scans the whole loaded image
($006e00-$011800 main code and the level overlay $04c6a8-$04e200) for (a) `move.w #N,2142(A5)` (the message-index register the
banner routine $00defa reads, mechanics.md section 7) and (b) an immediate index loaded into D0 (`moveq #N,D0` / `move.w #N,D0`) within 8
instructions before a `bsr`/`jsr` of a text routine: $00fd2c (decode), $011770 (decode + append), $00a82c (show at line D7), $0111fe-
style table lookups are data-driven and not seen.  Prints the indices with no such literal: candidates for dead text, or text chosen
from data (object records, the $6xxx/$a5 tables) -- not proof either way.
    uv run python reversing/cadaver/py/secrets/msg_refs.py [snap]"""
import re, subprocess, sys
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
def listing(lo, hi):
    out = subprocess.run(['uv', 'run', 'python', 'tools/disassemble.py', '--snap', snap, '--all', lo, hi], capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if re.match(r'\s+\$[0-9a-f]+:', l)]
lines = listing('6e00', '11800') + listing('4c6a8', '4e200')
TEXT = {'$fd2c', '$11770', '$a82c', '$11750', '$1175c', '$a842'}
refs = {}
def num(s): return int(s[1:], 16) if s.startswith('$') else int(s)
for i, l in enumerate(lines):
    m = re.search(r'move\.w #(\$?[0-9a-f]+),2142\(A5\)', l)
    if m: refs.setdefault(num(m.group(1)), []).append(l.split(':')[0].strip() + ' (2142)')
    m = re.search(r'(?:bsr|jsr) (\$[0-9a-f]+)', l)
    if m and m.group(1) in TEXT:
        for j in range(i - 1, max(i - 9, 0), -1):
            mm = re.search(r'(?:moveq|move\.w|move\.l) #(\$?[0-9a-f]+),D0$', lines[j].split(':', 1)[1].strip())
            if mm:
                refs.setdefault(num(mm.group(1)), []).append(l.split(':')[0].strip() + ' (' + m.group(1) + ')'); break
for n in sorted(refs):
    if n < 128: print(n, refs[n])
print('\nindices 0-127 with no code literal:', [n for n in range(128) if n not in refs])
