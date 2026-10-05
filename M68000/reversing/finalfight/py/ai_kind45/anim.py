"""anim.py: decode the animation lists the fighter handlers install through $3b10/$3b1c.
Format read from $3b10, $3b1c, $3b3c (see k5 notes):
  setter   = `move.b 20(A6),D0 / lea 6(PC),A1 / jmp $3b10` (12 bytes) followed by a word table indexed by the character byte +20
  list     = array of 4-byte entries {offset.w (to the frame record, relative to the entry), duration.b (+40), flags.b (+41)}
  frame    = {w0, b42, b43, hurt box idx (+44), attack box idx (+45), w48 (+48)}   (copied by $3b1c: `move.l 2(frame),42(A6)`, `move.w 6(frame),48(A6)`)
  loop     = an entry whose duration byte has bit 7 set: its offset is the (negative) distance to the entry to continue with
usage: anim.py <setter addr> [sub]   |   anim.py scan <lo> <hi>
"""
import sys, os
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
def w(a): return int.from_bytes(rom[a:a + 2], 'big')
def sw(a):
    v = w(a); return v - 65536 if v & 0x8000 else v
SETTER = bytes.fromhex('102e001443fa00064ef83b10')

def list_addr(table, sub):
    return table + sw(table + 2 * sub)

def decode(lst, maxn=64):
    """returns list of dict(entry, dur, flag, hurt, atk, b42, b43, w48, loop_to)"""
    out = []; a = lst; seen = set()
    while len(out) < maxn:
        off = sw(a); dur = rom[a + 2]; flag = rom[a + 3]
        if dur & 0x80:
            out.append(dict(entry=a, loop_to=a + off, dur=dur, flag=flag)); break
        f = a + off
        out.append(dict(entry=a, frame=f, dur=dur, flag=flag, hurt=rom[f + 4], atk=rom[f + 5], b42=rom[f + 2], b43=rom[f + 3], w48=w(f + 6)))
        a += 4
    return out

def show(setter, sub):
    table = setter + 12
    lst = list_addr(table, sub)
    ents = decode(lst)
    atk = sorted(set(e['atk'] for e in ents if 'atk' in e and e['atk']))
    print('setter $%x sub %d list $%x entries %d frames-ticks %d attack boxes %s' % (setter, sub, lst, len(ents), sum(e['dur'] for e in ents if 'frame' in e), [hex(x) for x in atk]))
    for e in ents:
        if 'frame' in e:
            print('   $%x dur=%2d flag=%02x frame=$%x hurt=%02x atk=%02x b42=%02x b43=%02x w48=%04x' % (e['entry'], e['dur'], e['flag'], e['frame'], e['hurt'], e['atk'], e['b42'], e['b43'], e['w48']))
        else:
            print('   $%x loop -> $%x (dur byte %02x)' % (e['entry'], e['loop_to'], e['dur']))

if __name__ == '__main__':
    if sys.argv[1] == 'scan':
        lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
        a = lo
        while a < hi:
            i = rom.find(SETTER, a, hi)
            if i < 0: break
            print('%x' % i)
            a = i + 2
    else:
        s = int(sys.argv[1], 16)
        subs = [int(sys.argv[2])] if len(sys.argv) > 2 else [0, 1]
        for sub in subs: show(s, sub)
