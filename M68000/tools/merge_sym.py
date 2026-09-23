"""merge_sym.py - merge subagent sym.txt files into a game's .sym and report name clashes.

  python tools/merge_sym.py <target.sym> <sym.txt>... [addr=name ...] [--write]

Lines are `addr<TAB>name` (hex address, any width; '#' lines are comments and are kept at the
top). Without --write it only reports:
  EXISTING  the target already names the address differently (the target's name is kept)
  CLASH     two input files name a new address differently (the first file's name is kept)
Most are synonyms; a real semantic disagreement has to be settled in the code (skill section 3c).
`addr=name` arguments override both, including existing target names. --write rewrites the
target sorted by address, six-digit lower-case hex, LF line endings.
"""
import sys


def read_sym(path):
    hdr, names = [], {}
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\r\n')
        if not line.strip():
            continue
        if line.startswith('#'):
            hdr.append(line)
            continue
        parts = line.split('\t') if '\t' in line else line.split(None, 1)
        names[int(parts[0], 16)] = parts[1].split()[0]
    return hdr, names


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    target, rest = argv[0], argv[1:]
    write = '--write' in rest
    over = {int(a.split('=')[0], 16): a.split('=', 1)[1] for a in rest if '=' in a}
    inputs = [a for a in rest if '=' not in a and a != '--write']
    hdr, have = read_sym(target)
    new = {}
    for f in inputs:
        for a, n in read_sym(f)[1].items():
            if a in have:
                if have[a] != n and a not in over:
                    print('EXISTING %06x %s vs %s (%s)' % (a, have[a], n, f))
                continue
            if a in new and new[a] != n and a not in over:
                print('CLASH    %06x %s vs %s (%s)' % (a, new[a], n, f))
            new.setdefault(a, n)
    added = [a for a in new if a not in have]
    have.update(new)
    have.update(over)
    print('%d new names, %d overrides, %d total' % (len(added), len(over), len(have)))
    if write:
        body = ['%06x\t%s' % (a, have[a]) for a in sorted(have)]
        open(target, 'w', encoding='utf-8', newline='\n').write('\n'.join(hdr + body) + '\n')


if __name__ == '__main__':
    main(sys.argv[1:])
