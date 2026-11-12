"""Diff two stserver execution profiles (profile_start / profile_stop JSON): an input run A against a
same-snapshot, same-budget control B.

    python3 tools/profdiff.py A.json B.json [--value 47 --value 85 ...] [--text LUMBAJAK] [--top 20] [--gap 16]

Coverage: the PCs only A executed, grouped into runs whose PCs lie within --gap bytes of each other,
then the PCs only B executed.

Compares (with --value, hex, or --text): every compare in A whose source or destination operand equals
one of the values (masked to the compare's size), or, for --text, whose operand bytes (big-endian, the
compare's size) occur in the text: a name compared four letters at a time (`cmp.l (A0),D1`) matches
"LUMB" in --text LUMBAJAK where no single-byte value would. Ranked by
  1. the operand pair never occurs in B at that PC (input-only) before pairs B also ran;
  2. the compare matched (source = destination) before ones that did not;
  3. fewer distinct pairs at that PC in A first (a compare against a constant beats a loop over a table);
  4. lower PC.
The rank is printed with each line, so a known compare's position can be read off. This is the
input-to-state correspondence of Redqueen: an operand equal to the injected byte marks a compare
that consumes it, and the other operand is what it is tested against. DEVELOPING.md "Execution profile".
"""
import argparse, json, sys


def load(path):
    with open(path) as f:
        d = json.load(f)
    cov = {int(e['pc'][1:], 16): e['count'] for e in d['coverage']}
    cmps = {}
    for c in d['compares']:
        pc = int(c['pc'][1:], 16)
        pairs = {}
        for p in c['pairs']:
            k = (None if p['src'] is None else int(p['src'][1:], 16), None if p['dst'] is None else int(p['dst'][1:], 16))
            pairs[k] = p['count']
        cmps[pc] = dict(kind=c['kind'], size=c['size'], overflow=c['overflow'], pairs=pairs)
    return d, cov, cmps


def runs(pcs, gap):
    out = []
    for pc in sorted(pcs):
        if out and pc - out[-1][-1] <= gap:
            out[-1].append(pc)
        else:
            out.append([pc])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--value', action='append', default=[], help='hex byte/word/long injected in A')
    ap.add_argument('--text', default=None, help='typed text in A: match operands whose bytes occur in it')
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--gap', type=int, default=16)
    args = ap.parse_args()
    da, cova, cmpa = load(args.a)
    db, covb, cmpb = load(args.b)
    for name, d in (('A', da), ('B', db)):
        print(f'{name}: steps {d["steps"]} skipped {d["skipped"]} from step {d["base_step"]} to {d["end_step"]}, '
              f'{len(d["coverage"])} PCs, {len(d["compares"])} compare PCs')
    if da['end_step'] - da['base_step'] != db['end_step'] - db['base_step']:
        print('WARNING: the two profiles cover different step budgets')

    onlya = set(cova) - set(covb)
    onlyb = set(covb) - set(cova)
    print(f'\ncoverage: {len(onlya)} PCs only in A, {len(onlyb)} only in B')
    for label, pcs, cov in (('A only', onlya, cova), ('B only', onlyb, covb)):
        rs = runs(pcs, args.gap)
        print(f'{label}: {len(rs)} runs')
        for r in rs[:args.top]:
            print(f'  ${r[0]:06x}..${r[-1]:06x}  {len(r):4d} PCs  max count {max(cov[p] for p in r)}')
        if len(rs) > args.top:
            print(f'  ... {len(rs) - args.top} more')

    if not args.value and not args.text:
        return
    values = [int(v.replace('$', '').replace('0x', ''), 16) for v in args.value]
    text = args.text.encode('latin-1') if args.text else None
    def in_text(x, size):
        return text is not None and x is not None and size in (1, 2, 4) and x.to_bytes(size, 'big') in text
    cands = []
    for pc, c in cmpa.items():
        m = {1: 0xff, 2: 0xffff, 4: 0xffffffff}.get(c['size'], 0xffffffff)
        bpairs = cmpb.get(pc, {}).get('pairs', {})
        for (src, dst), n in c['pairs'].items():
            hit = [v for v in values if (src is not None and src == v & m) or (dst is not None and dst == v & m)]
            if in_text(src, c['size']) or in_text(dst, c['size']):
                hit.append('text')
            if not hit:
                continue
            only = (src, dst) not in bpairs
            matched = src is not None and src == dst
            cands.append(((0 if only else 1, 0 if matched else 1, len(c['pairs']), pc),
                          pc, c, src, dst, n, hit, only, matched))
    cands.sort(key=lambda x: x[0])
    what = ', '.join(['$%x' % v for v in values] + ([repr(args.text)] if text else []))
    print(f'\ncompares with an operand in {{{what}}}: {len(cands)} pairs')
    fmt = lambda x: '?' if x is None else f'${x:x}'
    for rank, (_, pc, c, src, dst, n, hit, only, matched) in enumerate(cands[:args.top], 1):
        print(f'{rank:3d}  ${pc:06x} {c["kind"]}.{ {1: "b", 2: "w", 4: "l"}.get(c["size"], "?") } '
              f'src {fmt(src)} dst {fmt(dst)} x{n}  {"A-only" if only else "also-B"} '
              f'{"equal" if matched else "unequal"}  pairs-at-pc {len(c["pairs"])}{" +overflow" if c["overflow"] else ""}')
    if len(cands) > args.top:
        print(f'  ... {len(cands) - args.top} more')


if __name__ == '__main__':
    sys.exit(main())
