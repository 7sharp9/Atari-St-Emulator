#!/usr/bin/env python3
"""Extract PowerMonger's entity-mode transitions from the code (code read, not a run).

usage: mode_edges.py [<ram image>]      (default scratchpad/pm123/win/m1_ready.ram)

Every mode $00..$94 of the dispatch table $14bb4 (handler = $14bb4 + s16 word[$14bb4 + mode], ai.md "The behaviour
modes") is walked intra-procedurally from its entry: bra/bcc/dbcc/jmp to absolute targets, the PC-relative word
dispatch idiom (`move.w N(PC,Dn.w),Dn / jmp|jsr M(PC,Dn.w)`, as in tools/rdis.py) and fall-through are followed; the
walk stops at rts and at the iterator epilogues $161c4 / $16202 / $1622c / $16228 / $14b72 (ai.md "The iterator").
Every jsr/bsr callee is walked the same way, transitively over the text segment ($1050..$1d000).

Collected per walk: every write to a mode byte, `move.b|move.w <src>,31(An)` / `,30(An)`, with the register and
whether A1 was reloaded earlier in the same walk (`... ,A1` destination before the site: the write is then on a
different record from the one the iterator handed in).

Output (to $PM_WORK/out, default scratchpad/pm_fig/out): mode_edges.json.
"""
import json, os, re, struct, sys

here = os.path.dirname(os.path.abspath(__file__))
root = here
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    parent = os.path.dirname(root)
    if parent == root:
        sys.exit('repo root (tools/rdis.py) not found')
    root = parent
sys.path.insert(0, os.path.join(root, 'tools'))
from disassemble import Disassembler  # noqa: E402

work = os.environ.get('PM_WORK') or os.path.join(root, 'scratchpad/pm_fig')
outdir = os.path.join(work, 'out')
os.makedirs(outdir, exist_ok=True)
ram_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'scratchpad/pm123/win/m1_ready.ram')
ram = open(ram_path, 'rb').read()
dis = Disassembler(ram, rom_base=0)

TABLE = 0x14bb4
TEXT = (0x1050, 0x1d000)
STOPS = {0x161c4: 'epi161c4', 0x16202: 'epi16202', 0x1622c: 'next', 0x16228: 'epi16228', 0x14b72: 'loop'}
BR = re.compile(r'^(bra|b[a-z]{2}|dbf|db[a-z]{2}|jmp)\b')
CALL = re.compile(r'^(jsr|bsr)\b')
ABS = re.compile(r'\$([0-9a-f]+)(?:\.w|\.l)?$')
MOVEW = re.compile(r'move\.w \S+ == \$([0-9a-f]+)\+D(\d),D(\d)$')
IDXJ = re.compile(r'^(jmp|jsr) \S+ == \$([0-9a-f]+)\+D(\d)$')
JMPIDX = re.compile(r'^jmp 2\(PC,D(\d)\.w\)')
WMODE = re.compile(r'^move\.([bw]) (\S+),(3[01])\(A(\d)\)$')
A1DEST = re.compile(r'^(lea|movea|adda|suba|move)\S* .*,A1$')


def rw(a):
    return struct.unpack_from('>H', ram, a)[0]


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def mode_table():
    return {mode: (TABLE + s16(rw(TABLE + mode))) & 0xffffff for mode in range(0, 0x96, 2)}


def table_entries(base):
    """Word-offset table: entries are read while the table has not yet run into the lowest handler it names
    (rdis.py's first-word rule fails when entry 0 is 0, as in $600a's table $6062). Capped at 64."""
    ents, lowest, i = [], 0xffffff, 0
    while i < 64 and base + 2 * i < lowest:
        e = (base + s16(rw(base + 2 * i))) & 0xffffff
        if e > base + 2 * i:
            lowest = min(lowest, e)
        ents.append(e)
        i += 1
    return [e for e in ents if TEXT[0] <= e < TEXT[1] and not e & 1 and e >= base + 2 * i]


def target(text):
    mm = ABS.search(text.split('==')[-1].strip()) if '==' in text else ABS.search(text)
    return int(mm.group(1), 16) if mm else None


def walk(entry):
    seen, writes, calls, stops, reloads, tables = {}, [], set(), set(), [], {}
    todo = [entry]
    while todo:
        a = todo.pop()
        prev_move = None
        while a not in seen:
            if a in STOPS and a != entry:
                stops.add(STOPS[a])
                break
            if not (TEXT[0] <= a < TEXT[1]) or len(seen) > 20000:
                break
            try:
                text, nxt = dis.decode_one(a)
            except Exception:
                break
            seen[a] = text
            op = text.split()[0]
            m = WMODE.match(text)
            if m:
                writes.append({'site': a, 'size': m.group(1), 'src': m.group(2), 'off': int(m.group(3)),
                               'reg': 'A' + m.group(4)})
            if A1DEST.match(text):
                reloads.append(a)
            mv = MOVEW.match(text)
            if JMPIDX.match(text) and prev_move:          # move.w N(PC,Dn.w),Dn / jmp 2(PC,Dn.w)
                ents = table_entries(prev_move)
                tables[prev_move] = ents
                todo.extend(ents)
                break
            prev_move = int(mv.group(1), 16) if mv else None
            mi = IDXJ.match(text)
            if mi:
                base = int(mi.group(2), 16)
                ents = table_entries(base)
                tables[base] = ents
                if mi.group(1) == 'jsr':
                    calls.update(ents)
                    a = nxt
                    continue
                todo.extend(ents)
                break
            if CALL.match(text):
                t = target(text)
                if t is not None:
                    calls.add(t)
            elif BR.match(text):
                t = target(text)
                if t is not None:
                    todo.append(t)
            if op in ('rts', 'rte', 'bra', 'jmp', 'illegal'):
                break
            a = nxt
    for w in writes:
        w['a1_reloaded'] = w['reg'] == 'A1' and any(r < w['site'] for r in reloads)
    return {'insns': len(seen), 'writes': writes, 'calls': sorted(calls), 'stops': sorted(stops),
            'tables': {'%x' % b: ['%x' % e for e in v] for b, v in tables.items()}}


def main():
    table = mode_table()
    modes, routines = {}, {}
    todo = []
    for mode, h in sorted(table.items()):
        if not (0x14c48 <= h < 0x16260) or h & 1:
            modes['%02x' % mode] = {'handler': '%x' % h, 'dead': True}
            continue
        r = walk(h)
        r['handler'] = '%x' % h
        modes['%02x' % mode] = r
        todo += r['calls']
    while todo:
        c = todo.pop()
        if '%x' % c in routines or not (TEXT[0] <= c < TEXT[1]):
            continue
        r = walk(c)
        routines['%x' % c] = r
        todo += r['calls']
    for d in list(modes.values()) + list(routines.values()):
        if 'calls' in d:
            d['calls'] = ['%x' % c for c in d['calls']]
            for w in d['writes']:
                w['site'] = '%x' % w['site']
    json.dump({'ram': os.path.relpath(ram_path, root), 'modes': modes, 'routines': routines},
              open(os.path.join(outdir, 'mode_edges.json'), 'w'), indent=1)
    nw = sum(len(d['writes']) for d in routines.values() if d['writes'])
    print('modes %d (dead %d), routines walked %d, routine mode-writes %d' % (
        len(modes), sum(1 for d in modes.values() if d.get('dead')), len(routines), nw))


main()
