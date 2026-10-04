"""ram_actors.py - actor sprite matching with banks read from the snapshot's RAM (so a boss bank
loaded over BTSPR by $cfa4 is the one used), same rules as sprites.py.
  python ram_actors.py <snap>...   : per on-screen actor best match over frame/frame-1, both facings, +-R px
"""
import glob
import os
import sys

from sprites import *  # noqa


def bank_of(ram, t):
    if t & 0x80:
        return ram, l32(ram, 0x1ee9e)
    ptr = l32(ram, 0x1eea2)
    off = l32(ram, ptr + 4 * (t - 1))
    if off == 0 or off > 0x20000:
        return None
    return ram, ptr + off


def search(ram, scr, a, rng=24, frames=(0, -1), anim=None):
    """best (ok, tot, frame_delta, dx, dy, mirrored) of the actor's sprite slid +-rng px over the playfield
    (numpy accumulation); anim overrides the actor's state."""
    import numpy as np
    t = ram[a]
    bb = bank_of(ram, t)
    if bb is None:
        return None
    buf, base = bb
    try:
        b = parse_bank(buf, base)
    except Exception:
        return None
    st = ram[a + 1] if anim is None else anim
    if st >= len(b["anims"]):
        return None
    an = b["anims"][st]
    H, code = b["H"], an["code"]
    sx, sy, ww = w16(ram, 0x1efec), w16(ram, 0x1efee), w16(ram, 0x1effe)
    x, y = w16(ram, a + 4), w16(ram, a + 6)
    dx0 = (x - sx) % ww
    if dx0 > ww // 2:
        dx0 -= ww
    px0, py0 = dx0 - code * 8, y - sy - H
    S = np.full((160 + 2 * 200, 256 + 2 * 200), 255, dtype=np.uint8)
    S[200:360, 200:456] = np.array([r[32:288] for r in scr[20:180]], dtype=np.uint8)
    best = (-1, 1, 0, 0, 0, 0)
    for fd in frames:
        f = ram[a + 2] + fd
        if not 0 <= f < len(an["frames"]):
            continue
        rows = decode_frame(buf, base + an["frames"][f], code, H)
        if rows is None:
            continue
        for flip in (0, 1):
            rr = mirror(rows) if flip else rows
            R = np.array(rr, dtype=np.uint8)
            ys, xs = np.nonzero(R)
            if len(ys) < 30:
                continue
            n = 2 * rng + 1
            ok = np.zeros((n, n), dtype=np.int32)
            tot = np.zeros((n, n), dtype=np.int32)
            for yy, xx in zip(ys, xs):
                c = R[yy, xx]
                y0 = 200 + py0 - rng + yy
                x0 = 200 + px0 - rng + xx
                win = S[y0:y0 + n, x0:x0 + n]
                tot += win != 255
                ok += win == c
            ratio = np.where(tot >= 30, ok / np.maximum(tot, 1), -1.0)
            i = np.unravel_index(np.argmax(ratio), ratio.shape)
            if tot[i] >= 30 and (ok[i] / tot[i]) > best[0] / best[1]:
                best = (int(ok[i]), int(tot[i]), fd, int(i[1]) - rng, int(i[0]) - rng, flip)
    return best, dict(type=t, state=st, frame=ram[a + 2], facing=ram[a + 3], H=H, code=code, x=x, y=y, vis=(px0, py0))


def main(names):
    lines = []
    for n in names:
        ram = load_snap(n)
        scr = screen_indices(ram, l32(ram, 0xc31a))
        for i in range(0xb3):
            a = 0x1f010 + i * 16
            if ram[a] == 0:
                continue
            r = search(ram, scr, a)
            if r is None:
                continue
            best, info = r
            line = "%s slot %d type %02x state %d frame %d facing %d code %d H %d: best %d/%d frame%+d d=(%+d,%+d) mirrored=%d" % (
                os.path.basename(n), i, info["type"], info["state"], info["frame"], info["facing"], info["code"], info["H"],
                best[0], best[1], best[2], best[3], best[4], best[5])
            print(line)
            lines.append(line)
    return lines


if __name__ == "__main__":
    main(sys.argv[1:])
