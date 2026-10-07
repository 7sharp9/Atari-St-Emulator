"""SUPERSEDED (78th pass): this walks the 59-entry table at $010000, which was read from the wrong base; the real verb table has 94
entries at $00ffba (secrets.md, "The script language"; py/secrets/overlay/verb_decode.py).  Kept for the history of §64.

Cadaver object-verb bytecode interpreter ($010000-$011256, mechanics.md section 9,
ai.md #6): dumps the embedded debug-string table with real addresses, decodes the 59-entry
opcode dispatch table at $010000, and for each entry tries to resolve which verb's
"object doesn't exist" error string its code path reaches (LOCK's own entry was found by hand; this
generalizes that technique across all 59 entries instead of one at a time; mechanics.md section 9
explains why those 59 are the tail of the real table).

Verb resolution is a best-effort static walk: follow the entry's own straight-line body
(stopping at rts/rte/jmp/bra, but treating an unconditional bra/jmp as a same-routine
continuation, not a stop), and for any conditional branch found in that body, follow ONE
more level the same way. This is deliberately shallow - a fuller transitive walk wanders
into shared/neighbouring routines and reports unrelated strings (verified by hand against
several entries during the 70th pass; not repeated here to avoid false positives). Some
targets land on a real instruction this disassembler doesn't decode ("(line-F ...)"
etc.) - a known tooling gap, not proof the entry is invalid; check by hand.

Usage: python verb_opcode_map.py <snap>
"""
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools"))
from disassemble import ram_from_snap, Disassembler  # noqa: E402

STRING_TABLE_LO, STRING_TABLE_HI = 0x172c7, 0x17951
DISPATCH_TABLE = 0x010000
DISPATCH_COUNT = 59
BSR_RESOLVER = 0x010738  # shared type-6/9 object-id resolver, mechanics.md section 9

COND_RE = re.compile(r'^b(eq|ne|cc|cs|pl|mi|gt|lt|ge|le|hi|ls|vc|vs)\s+\$([0-9a-f]+)')
UNCOND_RE = re.compile(r'^(bra|jmp)\s+\$([0-9a-f]+)')
LEA_RE = re.compile(r'lea \$([0-9a-f]+)\.l,A0')


def dump_debug_strings(ram):
    strings = {}
    start = STRING_TABLE_LO
    cur = bytearray()
    for i, b in enumerate(ram[STRING_TABLE_LO:STRING_TABLE_HI]):
        addr = STRING_TABLE_LO + i
        if b == 0:
            if cur:
                strings[start] = bytes(cur).decode('ascii', errors='replace')
            cur = bytearray()
            start = addr + 1
        else:
            cur.append(b)
    if cur:
        strings[start] = bytes(cur).decode('ascii', errors='replace')
    return strings


def dispatch_targets(ram):
    targets = {}
    for i in range(DISPATCH_COUNT):
        off = i * 2
        word = (ram[DISPATCH_TABLE + off] << 8) | ram[DISPATCH_TABLE + off + 1]
        targets[i] = DISPATCH_TABLE + word
    return targets


def straight_chain(dis, start_addr, seen, max_hops=6):
    all_lines, cond_targets = [], []
    addr = start_addr
    for _ in range(max_hops):
        if addr in seen:
            break
        seen.add(addr)
        body = dis.disassemble(addr, count=40, stop_at_control_flow=True)
        all_lines.extend(body)
        for pc, txt in body:
            m = COND_RE.match(txt.strip())
            if m:
                cond_targets.append(int(m.group(2), 16))
        if not body:
            break
        m = UNCOND_RE.match(body[-1][1].strip())
        if m:
            addr = int(m.group(2), 16)
            continue
        break
    return all_lines, cond_targets


def find_verb(dis, strings, start_addr):
    seen = set()
    level0, cond_targets = straight_chain(dis, start_addr, seen)
    uses_resolver = any(f'${BSR_RESOLVER:x}' in txt for _, txt in level0)

    def lea_verb(lines):
        for _, txt in lines:
            m = LEA_RE.search(txt)
            if m:
                return strings.get(int(m.group(1), 16))
        return None

    verb = lea_verb(level0)
    source = "direct" if verb else None
    if not verb:
        for t in cond_targets:
            level1, _ = straight_chain(dis, t, seen)
            v = lea_verb(level1)
            if v:
                verb, source = v, f"via branch to ${t:x}"
                break
    first = level0[0][1] if level0 else '?'
    return verb, source, uses_resolver, first


def main():
    snap = sys.argv[1]
    ram = ram_from_snap(snap)
    strings = dump_debug_strings(ram)
    targets = dispatch_targets(ram)
    dis = Disassembler(ram, rom_base=0)

    print("=== debug-string table ($172c7-$17951) ===")
    for addr, s in sorted(strings.items()):
        print(f"  ${addr:06x}: {s!r}")

    print()
    print(f"{'id':>3} {'addr':>8}  {'verb':45s} {'resolver?':10s} {'how':22s} first instr")
    for i in range(DISPATCH_COUNT):
        target = targets[i]
        verb, source, uses_resolver, first = find_verb(dis, strings, target)
        print(f"{i:3d} ${target:06x}  {verb or '(none found)':45s} "
              f"{'yes' if uses_resolver else 'no':10s} {source or '-':22s} {first}")


if __name__ == "__main__":
    main()
