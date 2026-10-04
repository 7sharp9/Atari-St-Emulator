"""Black Tiger (Atari ST) sound decoder / renderer.

The game has no sequencer and no PSG tone/noise/envelope music.  Every sound is a
digitised 8-bit signed sample that COMMAND.PRG's Timer A handler ($106c2) plays through the
three YM2149 volume registers (R8,R9,R10) via a 256-entry table (see notes.md):

    per tick:  byte = *ptr++ ;  i = (byte + $80) & $ff ;  PSG R8,R9,R10 <- TAB[i].{A,B,C}
    TAB = 256 x 8 bytes at $17ce0:  08 A 09 B 0a C 00 00     (movep.l + movep.w to $ff8800)

Samples are UNSIGNED 8-bit; the table index is (byte + $80) & $ff, i.e. byte ^ $80, and
the table is decreasing in the raw byte (byte 0 -> loudest triple, byte 255 -> silent).

Sound ids (the word given to $105e8 / $105d8):
    0       BT4 file ($da5c bytes at $201cc), Timer A rate index 1  (title / attract tune)
    1..8    BTSND entries: header = 32 x (offset.l,len.l) at 8*id, data at $100.., rate index 0
    9..31   header slots that alias id 8
The last byte of every stream is never played (handler decrements the count before the fetch).

Usage:
    python btsnd.py tables            # print the volume table + rate table + header
    python btsnd.py wav [outdir]      # render ids 0..8 to WAV
    python btsnd.py regs <id>         # print predicted (R8,R9,R10) per tick
"""
import os
import struct
import sys
import wave

from btsnd_common import FILES, OUT, ROOT, BT_WORK, Snap

TIMER_A_CLK = 2457600
PRESCALE = {1: 4, 2: 10, 3: 16, 4: 50, 5: 64, 6: 100, 7: 200}
# Rendering level table.  Preferred: Hatari's measured 16x16x16 three-voice YM2149 DAC table
# (src/includes/ym2149_fixed_vol.h, "volume_table[C][B][A]", data measured on a real ST by Paulo
# Simoes 2012; included by Hatari's sound.c as `volumetable_original`).  Located through
# $HATARI_YM_TABLE (path to that header) or $HATARI_SRC/src/includes/ym2149_fixed_vol.h; not copied
# into this repo.  Fallback (INFERRED, a recollection of StSound's 16-entry ymVolumeTable, summed over
# the three channels, not checked against a source): YM_VOL.  Neither is used by the PSG-write gates.
YM_VOL = [62, 161, 265, 377, 580, 774, 1155, 1575, 2260, 3088, 4570, 6233, 9330, 13187, 21220, 32767]


def _hatari_table():
    import re
    p = os.environ.get("HATARI_YM_TABLE") or os.path.join(
        os.environ.get("HATARI_SRC") or os.path.expanduser("~/GitHub/hatari"), "src", "includes", "ym2149_fixed_vol.h")
    if not os.path.exists(p):
        return None
    t = open(p).read()
    nums = [int(x) for x in re.findall(r"\b\d+\b", re.sub(r"/\*.*?\*/", "", t, flags=re.S))]
    return nums if len(nums) == 4096 else None


HATARI = _hatari_table()


def ym_level(a, b, c):
    """Output level of the three YM2149 volume nibbles: Hatari's measured table (0..65119) or,
    without it, the summed fallback model."""
    if HATARI is not None:
        return HATARI[c * 256 + b * 16 + a]
    return (YM_VOL[a] + YM_VOL[b] + YM_VOL[c]) * 65119 // (3 * 32767)


def level_source():
    return "Hatari measured table (Paulo Simoes)" if HATARI is not None else "fallback StSound-style sum (INFERRED)"

# runtime address -> offset in the on-disk COMMAND.PRG (found by searching the table bytes;
# the game's image is moved/unpacked, so this is not a constant base shift for the whole file)
FILE_OFF_VOLTAB = 47800        # runtime $17ce0
FILE_OFF_RATETAB = 0x184e0 - 0xc228   # runtime $184e0


def read(name):
    return open(os.path.join(FILES, name), "rb").read()


def load_tables(snap=None):
    """(voltab[256] of (A,B,C), rates[8] of (ctrl, data, hz)).  From COMMAND.PRG; if a Snap is
    given the RAM copy is compared and an assertion raised on mismatch."""
    c = read("COMMAND.PRG")
    raw = c[FILE_OFF_VOLTAB:FILE_OFF_VOLTAB + 2048]
    rraw = c[FILE_OFF_RATETAB:FILE_OFF_RATETAB + 16]
    if snap is not None:
        assert snap.ram[0x17ce0:0x17ce0 + 2048] == raw, "volume table differs from RAM"
        assert snap.ram[0x184e0:0x184e0 + 16] == rraw, "rate table differs from RAM"
    vt = []
    for i in range(256):
        e = raw[8 * i:8 * i + 8]
        assert e[0] == 8 and e[2] == 9 and e[4] == 10 and e[6:8] == b"\0\0", (i, e.hex())
        vt.append((e[1], e[3], e[5]))
    rates = []
    for i in range(8):
        w = struct.unpack_from(">H", rraw, 2 * i)[0]
        data, ctrl = w >> 8, w & 0xff
        hz = TIMER_A_CLK / PRESCALE[ctrl] / data if ctrl in PRESCALE and data else 0.0
        rates.append((ctrl, data, hz))
    return vt, rates


def header(btsnd=None):
    d = btsnd if btsnd is not None else read("BTSND")
    return [struct.unpack_from(">II", d, 8 * i) for i in range(32)]


def stream(sid, btsnd=None):
    """Bytes the Timer A handler fetches for sound id `sid` (one per tick), and the rate index."""
    if sid == 0:
        bt4 = read("BT4")
        assert len(bt4) == 0xda5c
        return bt4[:0xda5c - 1], 1
    d = btsnd if btsnd is not None else read("BTSND")
    off, ln = header(d)[sid]
    return d[off:off + ln - 1], 0


def music_as_played():
    """Id 0 as the game really plays it: BT4 is at $201cc..$2dc28 and the level loader's
    `t0` Fread to $25f8c ($201cc + 24000) overwrites its tail while it plays, so ticks 24000..
    play the first bytes of the T0 file (tile data), not BT4 (verified in verify_natural.py)."""
    bt4 = read("BT4")[:0xda5c - 1]
    return bt4[:24000] + read("T0")[:len(bt4) - 24000]


def predict_regs(sid, vt, music_overlay=False):
    s, _ = stream(sid)
    if sid == 0 and music_overlay:
        s = music_as_played()
    return [vt[(b + 0x80) & 0xff] for b in s]


def render(sid, vt, rates):
    s, ri = stream(sid)
    hz = rates[ri][2]
    return centre([ym_level(*vt[(b + 0x80) & 0xff]) for b in s]), hz


def centre(levels):
    """Levels (0..65119 unsigned DAC output) -> 16-bit signed PCM, mean removed, scale 1/2 so a
    full-scale excursion cannot clip (max level 65119 -> +-32560)."""
    mean = sum(levels) / len(levels)
    return [int(round((v - mean) / 2.0)) for v in levels]


def write_wav(path, pcm, hz):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(round(hz)))
        w.writeframes(b"".join(struct.pack("<h", max(-32768, min(32767, x))) for x in pcm))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tables"
    vt, rates = load_tables()
    if cmd == "tables":
        for i, r in enumerate(rates):
            print("rate", i, "ctrl=%d data=%d hz=%.1f" % r)
        for i, (o, n) in enumerate(header()):
            print("hdr", i, hex(o), hex(n))
        print("level source:", level_source())
        lv = [ym_level(*vt[(b + 0x80) & 0xff]) for b in range(256)]
        print("levels by raw byte 0,32,..,224:", [lv[b] for b in range(0, 256, 32)])
        print("inversions (level rises with raw byte):", sum(1 for b in range(255) if lv[b] < lv[b + 1]))
    elif cmd == "wav":
        outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, "wav")
        os.makedirs(outdir, exist_ok=True)
        for sid in range(9):
            pcm, hz = render(sid, vt, rates)
            p = os.path.join(outdir, "snd%d.wav" % sid)
            write_wav(p, pcm, hz)
            print(p, len(pcm), "ticks", "%.1f Hz" % hz, "%.2f s" % (len(pcm) / hz))
        # id 0 as played in the attract demo (tail overwritten by the t0 load)
        lv = [ym_level(*vt[(b + 0x80) & 0xff]) for b in music_as_played()]
        p = os.path.join(outdir, "snd0_as_played_t0_overwrite.wav")
        write_wav(p, centre(lv), rates[1][2])
        print(p)
    elif cmd == "regs":
        for t in predict_regs(int(sys.argv[2]), vt):
            print(*t)


if __name__ == "__main__":
    main()
