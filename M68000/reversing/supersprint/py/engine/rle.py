"""The game's word-RLE screen format (decoder is the routine at $10236, used for the reset-time picture).

stream: word T (the escape token) then a sequence of words: a literal word W != T is copied; the triple
(T, value, count) writes `value` `count` times. The output is 4 planes x 4000 words; word i of plane p is stored
at interleaved position (i*4 + p) -- i.e. ordinary ST low-res screen memory. j (the read index) runs on across planes.
"""
import struct


def unrle_plane_major(words, planes=4, per_plane=4000):
    T = words[0]
    j = 1
    out = [0] * (planes * per_plane)
    for p in range(planes):
        i = 0
        while i < per_plane:
            w = words[j]
            if w == T:
                v, n = words[j + 1], words[j + 2]
                j += 3
                for _ in range(n):
                    out[i * 4 + p] = v     # NOTE: stores never checked against per_plane in the asm (bcs on count only)
                    i += 1
            else:
                out[i * 4 + p] = w
                j += 1
                i += 1
    return out, j


def to_words(b):
    return list(struct.unpack('>%dH' % (len(b) // 2), b))
