#!/usr/bin/env python3
"""Summarise a sweep log (lua/sweep.lua) per latch command: what the HuC6280 did in the window after the latch write.
usage: analyze_sweep.py out/sw_all.log [out.tsv]
Per command: latch reads (should be 1), YM2151 key-ons per channel, YM2151 write count, YM2203 FM key-ons / SSG volume writes, OKI phrase starts
(chip, phrase, voice mask, attenuation) and stops, first-effect delay in frames, total chip writes, IRQ2 ticks."""
import re, sys, collections, json

def parse(path):
    blocks = {}
    cur = None
    for l in open(path):
        p = l.split()
        if not p: continue
        if p[0] == 'CMD':
            cur = dict(cmd=int(p[1], 16), ev=[], lrd=[], lat=[], pre=[], base=None, send=None, ticks=0); blocks[cur['cmd']] = cur
        elif cur is None: continue
        elif p[0] == 'BASE': cur['base'] = int(p[1])
        elif p[0] == 'SEND': cur['send'] = int(p[1])
        elif p[0] == 'PRE': cur['pre'].append(int(p[1], 16))
        elif p[0] == 'LRD': cur['lrd'].append((int(p[1]), int(p[2], 16), int(p[3], 16)))
        elif p[0] == 'LAT': cur['lat'].append((int(p[1]), int(p[2], 16)))
        elif p[0] == 'EV': cur['ev'].append((int(p[1]), p[2], p[3], int(p[4], 16), int(p[5], 16)))
        elif p[0] == 'TICKS': cur['ticks'] = int(p[1])
    return blocks

def decode(ev):
    """Turn raw address/data writes into register writes per chip."""
    out = []           # (frame, chip, reg, data)  for ym chips; ('oki', frame, chip, byte)
    last = {}
    for f, chip, kind, val, pc in ev:
        if chip.startswith('ym'):
            if kind == 'a': last[chip] = val
            else: out.append((f, chip, last.get(chip, -1), val))
        else:
            out.append((f, chip, 'w', val))
    return out

def oki_events(w, chip):
    """Phrase starts and stops from raw OKI data bytes (first byte bit7 set = phrase, next byte = voice mask/att)."""
    starts, stops = [], []
    st = None
    for f, c, r, v in w:
        if c != chip: continue
        if st is not None:
            starts.append((f, st & 0x7f, (v >> 4) & 0xf, v & 0xf)); st = None
        elif v & 0x80: st = v
        else: stops.append((f, (v >> 3) & 0xf))
    return starts, stops

def summarise(b):
    w = decode(b['ev'])
    base = b['send']
    r = {}
    r['cmd'] = b['cmd']
    r['lrd'] = len(b['lrd'])
    r['lat'] = len(b['lat'])
    ym2151 = [x for x in w if x[1] == 'ym2151']
    r['ym2151_writes'] = len(ym2151)
    ko = collections.Counter()
    koff = 0
    first = None
    for f, c, reg, v in ym2151:
        if reg == 0x08:
            if v & 0x78: ko[v & 7] += 1
            else: koff += 1
    r['ym2151_keyon'] = dict(sorted(ko.items()))
    r['ym2151_keyoff'] = koff
    ym2203 = [x for x in w if x[1] == 'ym2203']
    r['ym2203_writes'] = len(ym2203)
    fk = collections.Counter(); ssgvol = 0; ssgper = 0
    for f, c, reg, v in ym2203:
        if reg == 0x28 and v & 0xf0: fk[v & 7] += 1
        if reg in (8, 9, 10) and (v & 0xf): ssgvol += 1
        if reg in range(0, 6): ssgper += 1
    r['ym2203_fm_keyon'] = dict(sorted(fk.items()))
    r['ym2203_ssg_vol_on'] = ssgvol
    r['ym2203_ssg_per'] = ssgper
    for chip in ('oki1', 'oki2'):
        s, t = oki_events(w, chip)
        r[chip + '_start'] = [(x[1], x[2], x[3]) for x in s]
        r[chip + '_stops'] = len(t)
    r['ticks'] = b['ticks']
    first = None
    for f, c, reg, v in w:
        if c == 'ym2151' and reg in (0x14,): continue
        first = f - base if first is None else first
    r['first_write'] = first
    r['total_writes'] = len(w)
    return r

def classify(r):
    tags = []
    if r['ym2151_keyon'] or r['ym2203_fm_keyon'] or r['ym2203_ssg_vol_on']: tags.append('music/notes')
    if r['oki1_start'] or r['oki2_start']: tags.append('oki')
    if not tags and r['total_writes'] > 0: tags.append('regs only')
    if not tags: tags.append('none')
    return '+'.join(tags)

if __name__ == '__main__':
    blocks = parse(sys.argv[1])
    rows = [summarise(blocks[c]) for c in sorted(blocks)]
    out = open(sys.argv[2], 'w') if len(sys.argv) > 2 else sys.stdout
    out.write('cmd\tclass\tlatch_reads\t68k_lat\tym2151_wr\tym2151_keyon(ch:n)\tym2151_keyoff\tym2203_wr\tfm_keyon\tssg_vol_on\tssg_per\toki1_starts(phrase/mask/att)\toki1_stops\toki2_starts\toki2_stops\ttotal\tticks\tfirst\n')
    for r in rows:
        out.write('%02x\t%s\t%d\t%d\t%d\t%s\t%d\t%d\t%s\t%d\t%d\t%s\t%d\t%s\t%d\t%d\t%d\t%s\n' % (
            r['cmd'], classify(r), r['lrd'], r['lat'], r['ym2151_writes'],
            ','.join('%d:%d' % kv for kv in r['ym2151_keyon'].items()) or '-', r['ym2151_keyoff'], r['ym2203_writes'],
            ','.join('%d:%d' % kv for kv in r['ym2203_fm_keyon'].items()) or '-', r['ym2203_ssg_vol_on'], r['ym2203_ssg_per'],
            ' '.join('%d/%x/%d' % x for x in r['oki1_start']) or '-', r['oki1_stops'],
            ' '.join('%d/%x/%d' % x for x in r['oki2_start']) or '-', r['oki2_stops'], r['total_writes'], r['ticks'], r['first_write']))
