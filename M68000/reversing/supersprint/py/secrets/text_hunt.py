"""text_hunt.py - hunt for hidden text in the PRG image and the 4 data files under many byte->letter encodings:
   (a) plain ASCII (letters, case-insensitive), (b) 'glyph index' encodings byte = k + (letter index) for every k 0..255
   (upper and lower contiguous runs), (c) ASCII with high bit set, (d) byte-swapped word pairs (2 chars per big-endian word).
   A hit needs >=5 consecutive letters AND the run must contain an English dictionary word of >=5 letters (or >=4 for rarer
   encodings), using /usr/share/dict/words.  Prints offset, encoding and the recovered run."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import sscfg
words = set(w.strip().lower() for w in open('/usr/share/dict/words') if w.strip().isalpha() and len(w.strip()) >= 5)
maxw = 12
def has_word(s, minlen):
    s = s.lower(); n = len(s)
    for i in range(n):
        for j in range(i + minlen, min(n, i + maxw) + 1):
            if s[i:j] in words:
                return s[i:j]
    return None
files = {'PRG(img)': open(sscfg.IMG, 'rb').read()}
for f in ('INIT.DAT', 'SUPER1.DAT', 'SUPER.DAT', 'SSPRINT.HSC'):
    files[f] = open(os.path.join(sscfg.FILES, f), 'rb').read()
def runs(d, mapper, minrun):
    cur = []
    start = 0
    for i, b in enumerate(d):
        c = mapper(b)
        if c is None:
            if len(cur) >= minrun: yield start, ''.join(cur)
            cur = []
        else:
            if not cur: start = i
            cur.append(c)
    if len(cur) >= minrun: yield start, ''.join(cur)
hits = []
for name, d in files.items():
    # (a) ascii
    enc = {'ascii': lambda b: chr(b) if (65 <= b <= 90 or 97 <= b <= 122 or b == 32) else None,
           'ascii|80': lambda b: chr(b & 0x7f) if b >= 0x80 and (65 <= (b & 0x7f) <= 90 or 97 <= (b & 0x7f) <= 122) else None}
    for k in range(0, 230):
        enc['glyph+%d' % k] = (lambda k: (lambda b: chr(65 + b - k) if k <= b <= k + 25 else None))(k)
    for en, mp in enc.items():
        for off, s in runs(d, mp, 6):
            w = has_word(s.replace(' ', ''), 5 if en.startswith('ascii') else 5)
            if w and len(set(s)) >= 4:
                hits.append((name, en, off, s[:60], w))
seen = set()
for h in hits:
    key = (h[0], h[2] // 1, h[3])
    if key in seen: continue
    seen.add(key)
    print('%-9s %-10s @%06x %r  (word %r)' % h)
print('total hits', len(seen))
