"""anims.py: decode DAMND's animation lists (thunks $3f2bc.. through $3b1c, A1 = list) with their hurt and attack boxes (box table $404ca, set at $3f2aa).
frame record (from $3b1c: move.l 2(frame),42(A6); move.w 6(frame),48(A6)): hurt idx = byte +4, attack idx = byte +5, w48 = word +6.
box table A0 = $404ca: hurt box = A0 + idx*8 (dx dy hw hh words); attack box = A0 + (idx&$7f)*16 + word(A0) (dx dy hw hh, +8 damage row word, +11 bit 7 hard hit, +12 sound)."""
import os, sys, re
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
sw = lambda a: w(a) - 65536 if w(a) & 0x8000 else w(a)
BOX = 0x404ca
# thunk -> list (from the lea in each: `lea n(PC),A1 / jmp $3b1c`)
THUNK = {0x3f2bc: 0x3f41e, 0x3f2c4: 0x3fef2, 0x3f2cc: 0x3fefe, 0x3f2d4: 0x3ff66, 0x3f2dc: 0x3ff1e, 0x3f2e4: 0x3ff3e, 0x3f2ec: 0x3f5de, 0x3f2fc: 0x3f6aa,
         0x3f304: 0x3f7ee, 0x3f30c: 0x3f8aa, 0x3f314: 0x3f93a, 0x3f322: 0x3fbf6, 0x3f32a: 0x3fc1a, 0x3f332: 0x3fc3e, 0x3f33a: 0x3fc5a, 0x3f342: 0x3ff72,
         0x3f34a: 0x40162, 0x3f352: 0x40172, 0x3f35a: 0x4022a, 0x3f372: 0x40232, 0x3f37a: 0x402d6, 0x3f382: 0x402ce, 0x3f38a: 0x3f906}
THUNK[0x3f35a + 0x1000] = 0x4018   # the $3f368 variant (flag 99(A6)): movea.l #$4018,A1 (absolute word address, not a list in this ROM image?)
def decode(lst, maxn=80):
    out = []; a = lst
    for _ in range(maxn):
        off = sw(a); d = rom[a+2]; fl = rom[a+3]
        if d & 0x80: out.append(dict(entry=a, loop=a+off, dur=d, flag=fl)); break
        f = a + off
        out.append(dict(entry=a, frame=f, dur=d, flag=fl, hurt=rom[f+4], atk=rom[f+5], w48=w(f+6)))
        a += 4
    return out
def hurtbox(i): p = BOX + i*8; return (sw(p), sw(p+2), w(p+4), w(p+6))
def atkbox(i):
    p = BOX + (i & 0x7f)*16 + w(BOX)
    return dict(addr=p, dx=sw(p), dy=sw(p+2), hw=w(p+4), hh=w(p+6), row=w(p+8), hard=rom[p+11] >> 7, snd=rom[p+12], b11=rom[p+11], raw=rom[p:p+16].hex())
def describe(lst):
    ents = decode(lst)
    ticks = sum(e['dur'] for e in ents if 'frame' in e)
    atks = []
    for e in ents:
        if 'frame' in e and e['atk']:
            k = atkbox(e['atk']); atks.append((e['atk'], e['dur'], k))
    return ents, ticks, atks
if __name__ == '__main__':
    for t, lst in sorted(THUNK.items()):
        if lst < 0x10000: continue
        ents, ticks, atks = describe(lst)
        loop = [e for e in ents if 'loop' in e]
        print('thunk %x list %x: %d frames, %d ticks%s' % (t, lst, sum(1 for e in ents if 'frame' in e), ticks, (' loops to %x' % loop[0]['loop']) if loop else ''))
        print('   frames (dur/flag hurt atk): ' + ' '.join('%d/%02x:h%d,a%02x' % (e['dur'], e['flag'], e['hurt'], e['atk']) for e in ents if 'frame' in e))
        for aid, dur, k in atks:
            print('   attack box %02x dur %d dx=%d dy=%d hw=%d hh=%d row=%04x hard=%d snd=%02x' % (aid, dur, k['dx'], k['dy'], k['hw'], k['hh'], k['row'], k['hard'], k['snd']))
