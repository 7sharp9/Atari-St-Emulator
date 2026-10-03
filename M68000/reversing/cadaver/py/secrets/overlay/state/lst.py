"""lst.py: print cad_all.asm ($001000-$019100 whole-image listing) lines for addresses LO..HI (hex).  usage: lst.py LO HI [file]"""
import sys, os, re
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
f = sys.argv[3] if len(sys.argv) > 3 else ROOT + '/scratchpad/cadaver/secrets_out/cad_all.asm'
for l in open(f):
    m = re.match(r'\s*\$([0-9a-f]+)(?: \(\+[0-9a-f]+\))?:', l)
    if m and lo <= int(m.group(1), 16) <= hi: print(l, end='')
