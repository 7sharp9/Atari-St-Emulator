#!/usr/bin/env python3
"""Build the command table (cmd_table.tsv / cmd_table.md): for every latch id the static song header (channels, flag), the MAME sweep effect
(chips, key-ons, OKI phrases), the 68000 call sites (callers68k.tsv, whole-image raw scan) and the play-through observations (auto/play logs: caller
return address and count).
usage: build_table.py [--play out/play1.log --play out/auto1.log ...]"""
import os, sys, re, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import analyze_sweep as A, songs as S

import static_streams as SS
def music_has_notes(start, ch, limit=400):
    """True when the music-mode stream plays a note/rest or an OKI note before its END (False = parameter-reset / END-only stream)."""
    pos = start
    for _ in range(limit):
        b = S.rb(pos)
        if b < 0x70: pos += 1; continue
        if b < 0x90 or b >= 0xe0: return True
        idx = b - 0x90
        if idx == 0: return True
        if idx == 24: return False
        n = SS.OPLEN.get(idx)
        if idx in (19, 20, 21): n = 0 if ch < 8 else (1 if ch >= 11 else 2)
        if n is None or idx in (9, 10, 12): return True
        pos += 1 + n
    return True
def kind_of(i, h, chans, summ):
    if i == 0: return 'reset (jump to $E000: whole sound program restarts)'
    if i > S.MAXID: return 'ignored' if i < 0x7c else None
    if h[2] == 0 and len(chans) >= 4 and i in (1, 2, 0x12): return 'control: take over channels and end them (silence)'
    if h[2]:
        if i == 3: return 'control: end all music channels (stop music, silence all)'
        if not any(music_has_notes(a, c) for c, a in chans): return 'control: reset channel parameters to defaults, then END on every channel'
        return 'music'
    chs = [c for c, _ in chans]
    if 11 in chs: return 'voice effect on OKI1 (opcode $CC) via channel 11'
    if any(c in (8, 9, 10) for c in chs): return 'sound effect on YM2203 FM channel %s' % '/'.join(str(c - 8) for c in chs if c in (8, 9, 10))
    return 'effect'

HIGH = [
 ('71-7b', 'ignored (id > $70, `cmp $4000`)', '-', 'no chip write (11 ids x 300 frames)', '-', '-', '-'),
 ('7c', 'service tone: next command byte -> YM2203 reg 1 (SSG A period hi) [$56 = 1]', '-', 'none until the following byte', '-', '-', '-'),
 ('7d', 'service tone: next command byte -> reg 0 (period lo), then reg 3/2 = period-1 (SSG B), vols 8/8/0 [$56 = 2]', '-', 'none until the following byte', '-', '-', '-'),
 ('7e', 'service tone on: YM2203 reg 7 = $fc, vol A/B = 8, C = 0', '-', '4 YM2203 writes (2 non-zero SSG volumes)', '-', '-', '-'),
 ('7f', 'service tone off: reg 7 = $ff, vols 0', '-', '4 YM2203 writes', '-', '-', '-'),
 ('80-9f', 'YM2151 master volume: $28 = ~((id-$80)*4) (bit 7 = refresh flag); attenuation 127-4n added to carrier TL', '-', 'no chip write at the latch; TL of later key-ons + att (3 values x 64 writes exact)', '-', '-', '-'),
 ('a0-bf', 'YM2203 FM/SSG master volume: $29 = ~((id-$a0)*4) (bit 7 never cleared)', '-', 'none observable (no YM2203/SSG stream is refreshed)', '-', '-', '-'),
 ('c0-c7', 'OKI2 master attenuation: $2a = (id-$c0) ^ $87', '-', 'phrase start attenuation nibble = table att + (7-n), clamped 8', '-', '-', '-'),
 ('c8-cf', 'OKI1 master attenuation: $2b = (id-$c8) ^ $87', '-', 'as above for OKI1', '-', '-', '-'),
 ('d0-ff', 'tempo offset: $27 = (id-$e0)*4 (signed byte), T = $08/$09 + $27', '-', 'music tempo changes (exact: T 150 -> 86 / 150 -> 274)', '-', '-', '-'),
]
def main():
    plays = []
    a = sys.argv[1:]
    while a:
        if a[0] == '--play': plays.append(a[1]); a = a[2:]
        else: a = a[1:]
    blocks = A.parse(os.path.join(HERE, 'out', 'sw_all.log'))
    summ = {c: A.summarise(b) for c, b in blocks.items()}
    # 68000 call sites
    sites = collections.defaultdict(list)
    for l in list(open(os.path.join(HERE, 'callers68k.tsv')))[1:]:
        f = l.rstrip('\n').split('\t')
        for tok in f[2].split(','):
            if tok != '?': sites[int(tok[1:], 16)].append(f[0])
    dyn = collections.defaultdict(collections.Counter)    # id -> Counter(call-site return address)
    for pth in plays:
        for l in open(pth):
            p = l.split()
            if p and p[0] == 'LAT' and len(p) >= 5:
                dyn[int(p[2], 16)][int(p[3], 16)] += 1
    rows = []
    for i in range(0, 256):
        r = summ.get(i)
        h = chans = None
        if 1 <= i <= S.MAXID:
            p, h, chans, q = S.header(i)
        k = kind_of(i, h, chans, r) if h else ('reset' if i == 0 else None)
        rows.append((i, h, chans, r, k))
    out = open(os.path.join(HERE, 'cmd_table.tsv'), 'w')
    out.write('id\tkind\tchannels\tsweep_effect\toki_phrases\t68000_static_sites\tobserved_in_play(retaddr:n)\n')
    for i, h, chans, r, k in rows:
        if r is None or i > S.MAXID: continue
        if k is None and r['total_writes'] == 0 and i not in sites and i not in dyn: continue
        eff = []
        if r['ym2151_keyon']: eff.append('YM2151 key-ons %s' % ','.join('ch%d:%d' % kv for kv in r['ym2151_keyon'].items()))
        if r['ym2203_fm_keyon']: eff.append('YM2203 FM key-ons %s' % ','.join('fm%d:%d' % kv for kv in r['ym2203_fm_keyon'].items()))
        if r['ym2203_ssg_vol_on']: eff.append('SSG volume writes %d' % r['ym2203_ssg_vol_on'])
        if not eff and r['total_writes']: eff.append('%d register writes, no key-on' % r['total_writes'])
        if not r['total_writes']: eff.append('no chip write')
        oki = []
        for chip in ('oki1', 'oki2'):
            st = r[chip + '_start']
            if st: oki.append('%s phrases %s' % (chip, ' '.join('%d' % x[0] for x in st)))
        chtxt = ' '.join('%d' % c for c, _ in chans) if chans else '-'
        out.write('%02x\t%s\t%s\t%s\t%s\t%s\t%s\n' % (i, k or '-', chtxt, '; '.join(eff), '; '.join(oki) or '-', ' '.join(sites.get(i, [])) or '-',
                                                   ' '.join('%06x:%d' % kv for kv in sorted(dyn[i].items())) or '-'))
    # ids with no song: the latch byte classes handled in the FIFO push ($E248..$E2B3) and the service tone commands
    for r in HIGH:
        out.write('\t'.join(r) + '\n')
    out.close()

if __name__ == '__main__':
    main()
