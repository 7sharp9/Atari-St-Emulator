# recursive-descent listing of the ROM from given roots; jump tables expanded; embedded data shown as .dw.
# usage: rdl.py <lo> <hi> <root> [root ...]   (hex). follows jsr/bsr/bcc/jmp/jump tables inside [lo,hi).
# output: address-sorted; "L" labels at branch targets, "F" labels at call targets.
import sys, os, re
root_dir = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, os.path.join(root_dir, 'tools'))
import disassemble as D
rom = open(os.path.join(root_dir, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
dis = D.Disassembler(rom, rom_base=0)
OVR = {0x27012: 4, 0x21d0e: 2}
def run(lo, hi, roots, out=sys.stdout):
    ins = {}; tabs = {}; calls = set(); labs = set(); extset = set()
    work = list(roots)
    seen = set()
    while work:
        a = work.pop()
        pend = None
        while lo <= a < hi and a not in seen:
            seen.add(a)
            if pend is not None:
                pa, pdest, pbase = pend
                op = dis.rw(a)
                if (op & 0xffc0) in (0x4ec0, 0x4e80) and ((op >> 3) & 7) == 7 and (op & 7) == 3:
                    ext = dis.rw(a + 2)
                    if not (ext >> 15) & 1 and ((ext >> 12) & 7) == pdest:
                        base = a + 2 + D.sext8(ext & 0xff)
                        if base == pbase:
                            tab = base
                            isjsr = (op & 0xffc0) == 0x4e80
                            ins[a] = '%s %d(PC,D%d.w)   ; table %x' % ('jsr' if isjsr else 'jmp', D.sext8(ext & 0xff), pdest, tab)
                            tg = []
                            end = dis.rw(tab)
                            i = 0
                            if tab in OVR: end = OVR[tab] * 2
                            while 2 * i < end:
                                w = dis.rw(tab + 2 * i)
                                w = w - 65536 if w >= 32768 else w
                                if tab not in OVR and 0 <= w < end and w >= 2 * (i + 1): end = w
                                tg.append(tab + w if (w >= 2 * (i + 1) or w < 0) else None)
                                i += 1
                            tabs[tab] = tg
                            for t in tg:
                                if t is not None:
                                    labs.add(t); work.append(t)
                                    if isjsr: calls.add(t)
                            if isjsr:
                                nxt = a + 4
                                a = nxt; pend = None
                                continue
                            break
                pend = None
            try:
                text, nxt = dis.decode_one(a)
            except Exception:
                ins[a] = '<error>'; break
            ins[a] = text
            pend = None
            md = dis.jumptable_move_dest(a)
            if md is not None:
                ext = dis.rw(a + 2)
                pend = (a, md, a + 2 + D.sext8(ext & 0xff))
            m = re.match(r'(bsr|jsr)\s+\$([0-9a-f]+)', text)
            if m:
                t = int(m.group(2), 16); calls.add(t)
                if lo <= t < hi: work.append(t)
                else: extset.add(t)
            m = re.match(r'(b[a-z]{1,2}|db[a-z]{1,2}|jmp)\s+(?:D\d,)?\$([0-9a-f]+)\s*$', text)
            if m:
                t = int(m.group(2), 16); labs.add(t)
                if lo <= t < hi: work.append(t)
                else: extset.add(t)
            if re.match(r'(rts|rte|bra|jmp|illegal)', text) or text.startswith('trap #1 ') or text == 'trap #1':
                break
            a = nxt
    # emit
    addrs = sorted(set(ins) | set(tabs))
    prev_end = None
    for a in addrs:
        if a in tabs:
            lab = ''
            out.write('%-8s $%06x: .table %s\n' % ('', a, ' '.join('%d:%s' % (i, ('%x' % t) if t is not None else '-') for i, t in enumerate(tabs[a]))))
            prev_end = a + 2 * len(tabs[a]); continue
        if prev_end is not None and a > prev_end:
            # data gap: dump words
            g = prev_end
            while g < a:
                n = min(16, a - g)
                out.write('         $%06x: .data %s\n' % (g, rom[g:g+n].hex(' ', 2)))
                g += n
        lab = 'F%x:' % a if a in calls else ('L%x:' % a if a in labs else '')
        out.write('%-8s $%06x: %s\n' % (lab, a, ins[a]))
        # estimate end: next addr from decode
        try: prev_end = dis.decode_one(a)[1]
        except Exception: prev_end = a + 2
    out.write('; external targets: %s\n' % ' '.join('%x' % t for t in sorted(extset)))
if __name__ == '__main__':
    lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
    run(lo, hi, [int(x, 16) for x in sys.argv[3:]])
