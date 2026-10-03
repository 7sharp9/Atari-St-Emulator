"""refs.py: list every instruction in a whole-image listing that addresses displacement D off an address register (An or (An,Dn)).  usage: refs.py D [listing]
Used to enumerate all readers/writers of object-record bytes."""
import sys, os, re
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
d = sys.argv[1]
f = sys.argv[2] if len(sys.argv) > 2 else ROOT + '/scratchpad/cadaver/secrets_out/cad_all.asm'
pat = re.compile(r'(?<![\w$#.-])' + d + r'\(A[0-6](,D[0-7]\.[wl])?\)')
for l in open(f):
    if re.match(r'\s*\$[0-9a-f]+( \(\+[0-9a-f]+\))?:', l) and pat.search(l.split(':',1)[1]): print(l, end='')
