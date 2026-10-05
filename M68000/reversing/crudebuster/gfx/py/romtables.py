"""Decode the graphics tables of the program ROM into data/*.txt:
  messages.txt     the $28fa big-text messages ($2962 table, 80 entries): attribute, destination, glyph codes and the decoded text
  level_tables.txt per-level room map ($8908), layer A/B/C screen tables ($8c94 $98fe $9d20), event tables ($8f52)
  anim_index.txt   the actor animation database at $30000 (type -> state -> animation: ticks, last frame, sound, frame pointers, part counts)"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import palsets as P
import levelmaps as M
ROOT = P.ROOT
W, L = P.W, P.L
ROM = P.ROM


def glyph_char(c):
    k = (c - 0x8c)
    if k % 4 or k < 0: return "<%x>" % c
    k //= 4
    if k < 10: return str(k)
    if k < 36: return chr(ord("A") + k - 10)
    return {36: "<-", 37: "?"}.get(k, "[%x]" % c)


def messages():
    out = ["# $28fa message table $2962: index, then sub-records (attribute word ORed into every tile word, destination in chip0 pf1 RAM, glyph codes)",
           "# a glyph code g writes 4 tiles: (dest) = g, (dest+0x80) = g+1, (dest-2) = g+2, (dest-2+0x80) = g+3 ; dest += 4 per glyph; 0xfffe = new sub-record, 0xffff = end",
           "# glyph g = 0x8c + 4*k : k 0-9 digits, 10-35 A-Z, 36 left arrow, 37 '?'; chars are char-ROM codes 0x4000 + (g & 0xfff)"]
    n = (L(0x2962) - 0x2962) // 4
    for i in range(n):
        p = L(0x2962 + 4 * i)
        subs = []
        while True:
            att = W(p); dst = L(p + 2); p += 6; codes = []
            while True:
                c = W(p); p += 2
                if c in (0xffff, 0xfffe): end = c; break
                codes.append(c)
            subs.append((att, dst, codes))
            if end == 0xffff: break
        txt = " | ".join("".join(glyph_char(c) for c in cs) for _, _, cs in subs)
        out.append("%2d  %s   %s" % (i, "  ".join("[att %04x dst %06x: %s]" % (a, d, " ".join("%x" % c for c in cs)) for a, d, cs in subs), txt))
    open(os.path.join(ROOT, "data", "messages.txt"), "w").write("\n".join(out) + "\n")


def level_tables():
    out = []
    for name, base, n in (("room map $8908 (word per [row=$80406 hi-1][col=$8040a hi-1], 16 columns; bit meanings: see doc)", 0x8908, None),
                          ("layer A screen table $8c94 (chip0 pf2, blocks $41000+0x200*i, lo=top hi=bottom, ff=none)", M.TBL_A, None),
                          ("layer B screen table $98fe (chip1 pf1, blocks $4ba00+0x200*i)", M.TBL_B, None),
                          ("layer C screen table $9d20 (chip1 pf2, blocks $4da00+0x200*i)", M.TBL_C, None),
                          ("event table $8f52 (word per screen -> function index into $8ff2, ffff none)", 0x8f52, None)):
        out.append("# " + name)
        for lv in range(6):
            out.append("level %d @%05x: %s" % (lv, L(base + 4 * lv), " ".join("%04x" % w for w in M.level_table(base, lv))))
    open(os.path.join(ROOT, "data", "level_tables.txt"), "w").write("\n".join(out) + "\n")


def anim_index():
    out = ["# actor animation database: $30000 type table -> state table -> animation {ticks/frame, last frame index, sound word, frame pointers} -> frame {parts.w, 8-byte parts}",
           "# read by the generic actor draw routine $22540 (type = obj+2, state = obj+3, frame = obj+20)"]
    ntypes = (L(0x30000) - 0x30000) // 4
    for t in range(ntypes):
        sp = L(0x30000 + 4 * t)
        nst = None
        out.append("type %d state table $%05x" % (t, sp))
        # state count: up to the first animation pointer region; use pointer ordering
        nst = 1; lo = L(sp)                                # the table ends where the lowest animation pointer starts
        while sp + 4 * nst < lo:
            lo = min(lo, L(sp + 4 * nst)); nst += 1
        for s in range(nst):
            ap = L(sp + 4 * s)
            if not (0x30000 <= ap < 0x7fff0):
                out.append("  state %2d pointer %08x (not an animation)" % (s, ap)); continue
            tick, last, snd = ROM[ap], ROM[ap + 1], W(ap + 2)
            fr = [L(ap + 4 + 4 * k) for k in range(last + 1)]
            parts = [W(f) if 0 <= f < 0x7fff0 else None for f in fr]
            out.append("  state %2d anim $%05x ticks %d last %d sound %04x frames %s parts %s" % (s, ap, tick, last, snd, " ".join("%05x" % f for f in fr), parts))
    open(os.path.join(ROOT, "data", "anim_index.txt"), "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    messages(); level_tables(); anim_index()
    print("written")
