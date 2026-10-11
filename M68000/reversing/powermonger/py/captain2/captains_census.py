"""Census of the local side's live captain groups over .ram images.

For each RAM image: local side = word $57ffe; group k (0..5) of side s is live when
word 28 of ($51538 + s*$13c + 2k) is non-zero (the captain-box loop $133ee).
Prints images with two or more live local groups first.
Usage: captains_census.py <ram-or-dir>...
"""
import os, struct, sys

def w(b, a):
    return struct.unpack_from('>H', b, a)[0]

def groups(b):
    side = w(b, 0x57ffe)
    base = 0x51538 + side * 0x13c
    live = [k for k in range(6) if w(b, base + 28 + 2 * k)]
    return side, live

def main(args):
    files = []
    for a in args:
        if os.path.isdir(a):
            for r, _, fs in os.walk(a):
                files += [os.path.join(r, f) for f in fs if f.endswith('.ram')]
        else:
            files.append(a)
    rows = []
    for f in sorted(files):
        try:
            b = open(f, 'rb').read()
        except OSError:
            continue
        if len(b) < 0x60000:
            continue
        side, live = groups(b)
        rows.append((len(live), f, side, live))
    for n, f, side, live in sorted(rows, key=lambda r: -r[0]):
        if n >= 2 or '-a' in sys.argv:
            print(n, side, live, f)
    print('images', len(rows), 'with >=2:', sum(1 for r in rows if r[0] >= 2))

if __name__ == '__main__':
    main([a for a in sys.argv[1:] if a != '-a'])
