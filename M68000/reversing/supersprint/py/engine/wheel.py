"""SELECT-TRACK steering wheel: SUPER.DAT B2 = 150-byte header + 5 frames of 64x44 px (1408 B each: 44 rows x 4 groups x 4 plane words).  $19164
copies the 7040 bytes to -94(A4) and builds the other 11 of the 16 rotation frames: $16926(buf, a, b) = frame b := vertical flip of frame a
(frames 5..8 from 3..0), $16962(buf, a, b) = frame b := horizontal mirror of frame a (frames 9..15 from 7..1; each 16-bit word bit-reversed,
the four groups of a row in reverse order)."""
import struct


def vflip(frame):
    return b''.join(frame[r * 32:(r + 1) * 32] for r in range(43, -1, -1))


def rev16(w):
    return int('{:016b}'.format(w)[::-1], 2)


def hmirror(frame):
    out = bytearray()
    for r in range(44):
        row = frame[r * 32:(r + 1) * 32]
        groups = [struct.unpack_from('>4H', row, g * 8) for g in range(4)]
        for g in range(3, -1, -1):
            out += struct.pack('>4H', *[rev16(w) for w in groups[g]])
    return bytes(out)


def all_frames(b2):
    f = [b2[0x96 + i * 1408:0x96 + (i + 1) * 1408] for i in range(5)] + [None] * 11
    for j in range(5, 9): f[j] = vflip(f[8 - j])
    for j in range(9, 16): f[j] = hmirror(f[16 - j])
    return f
