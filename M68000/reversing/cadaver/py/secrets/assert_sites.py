"""assert_sites.py [snap]: every `jsr $11788.l` (the fatal-error screen, see fatal_screen.py) in the main code $006e00-$011800 with the
`lea <string>.l,A0` a few instructions before it and the string ($0172c8-$017951): the 67 conditions the programmers checked.
    uv run python reversing/cadaver/py/secrets/assert_sites.py [snap]"""
import re, subprocess, sys
sys.path.insert(0, 'tools')
from gfxview import load_ram
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
ram, _ = load_ram(snap)
out = subprocess.run(['uv', 'run', 'python', 'tools/disassemble.py', '--snap', snap, '--all', '6e00', '11800'], capture_output=True, text=True).stdout
lines = [l for l in out.splitlines() if re.match(r'\s+\$[0-9a-f]+:', l)]
n = 0
for i, l in enumerate(lines):
    if 'jsr $11788.l' in l:
        s = None
        for j in range(i - 1, max(i - 6, 0), -1):
            m = re.search(r'lea \$([0-9a-f]+)\.l,A0', lines[j])
            if m:
                a = int(m.group(1), 16); s = ram[a:ram.index(b'\0', a)].decode('latin1'); break
        print(l.split(':')[0].strip(), s); n += 1
print(n, 'sites')
