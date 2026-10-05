"""names.py: the HUD name of every (tag, kind, +20) from $5b640: A0 = $5b682 + word[$5b682 + tag]; D1 = word[A0 + 2*kind]; + 32*(+20) unless tag $a; 16 tile words after a 6-word header."""
import os, sys
root = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
w = lambda a: int.from_bytes(rom[a:a+2], 'big')
def name(tag, kind, c20):
    a0 = 0x5b682 + w(0x5b682 + tag)
    d1 = w(a0 + 2*kind)
    if tag != 0xa: d1 += 32*c20
    a = a0 + d1
    words = [w(a + 2*i) for i in range(22)]
    return a, ''.join(chr(x & 0xff) if (x & 0xff00) == 0x4400 else '.' for x in words[6:])
if __name__ == '__main__':
    for tag in (4,):
        for kind in range(8):
            for c in range(0, 2):
                a, s = name(tag, kind, c)
                print('tag %d kind %d +20=%d @%x %r' % (tag, kind, c, a, s))
