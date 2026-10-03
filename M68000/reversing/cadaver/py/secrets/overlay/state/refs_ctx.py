"""refs_ctx.py: like refs.py but prints N preceding and M following instructions around every hit.  usage: refs_ctx.py D [before] [after] [listing]"""
import sys, os, re
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
d = sys.argv[1]; nb = int(sys.argv[2]) if len(sys.argv) > 2 else 8; na = int(sys.argv[3]) if len(sys.argv) > 3 else 4
f = sys.argv[4] if len(sys.argv) > 4 else ROOT + '/scratchpad/cadaver/secrets_out/cad_all.asm'
pat = re.compile(r'(?<![\w$#.-])' + d + r'\(A[0-6](,D[0-7]\.[wl])?\)')
L = [l for l in open(f) if re.match(r'\s*\$[0-9a-f]+( \(\+[0-9a-f]+\))?:', l)]
for i, l in enumerate(L):
    if pat.search(l.split(':', 1)[1]):
        print('-----'); print(''.join(L[max(0, i - nb):i]), end=''); print('>>' + l[2:], end=''); print(''.join(L[i + 1:i + 1 + na]), end='')
