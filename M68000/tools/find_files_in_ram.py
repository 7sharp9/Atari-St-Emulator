"""Which disk files (depacked) sit in a snapshot's RAM, and where.

usage: find_files_in_ram.py <snap> <dir> [addr ...]
  no addr:   every file in <dir> (>= 64 bytes) whose first 64 bytes occur in RAM, with each address and how many
             of its bytes match from there (FULL when the whole file is there)
  addr ...:  for each hex address, the file with the longest matching prefix there

A loader call's argument is not the file it opens (Midwinter's loader adds 10 to the number during play,
reversing/midwinter/architecture.md section 5): identify a buffer by its content with this.
"""
import os, sys

root = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, 'tools'))
from gfxview import load_ram  # noqa: E402


def prefix(ram, at, data):
    n = 0
    while n < len(data) and at + n < len(ram) and ram[at + n] == data[n]:
        n += 1
    return n


def main():
    ram = load_ram(sys.argv[1])[0]
    files = {}
    for name in sorted(os.listdir(sys.argv[2])):
        p = os.path.join(sys.argv[2], name)
        if os.path.isfile(p):
            d = open(p, 'rb').read()
            if len(d) >= 64:
                files[name] = d
    if len(sys.argv) > 3:
        for a in sys.argv[3:]:
            at = int(a.lstrip('$'), 16)
            n, name = max((prefix(ram, at, d), name) for name, d in files.items())
            size = len(files[name])
            print(f'${at:06x}: {name} {n}/{size} bytes{" FULL" if n == size else ""}' if n else f'${at:06x}: no file')
        return
    for name, d in files.items():
        at = ram.find(d[:64])
        while at >= 0:
            n = prefix(ram, at, d)
            print(f'{name} ({len(d)} bytes) at ${at:06x}: {n}/{len(d)}{" FULL" if n == len(d) else ""}')
            at = ram.find(d[:64], at + 1)


if __name__ == '__main__':
    main()
