"""pics.py - Black Tiger picture collections (BTCLIPS, BTOBJ), BT5, and Degas BT000/BT001.PI1.

Collection file: table of 16-bit offsets (entry k at word 2k; the table ends where the lowest
offset begins), each pointing at a picture: word w (16 px groups), word h (rows), then h rows of
w groups, each group 4 plane words (ST interleaved, 8 bytes).  Drawn by trap #3 fn8 ($ad7c ->
$ae0c -> $adb0); D5 != 0 selects colour-0-transparent drawing.  Sizes checked: every gap between
consecutive pictures is exactly 4 + w*h*8.
  BTCLIPS: loaded to $4a59e, pointer $1efe4, accessor $f2a4 (index in D0 = stack arg).
  BTOBJ  : loaded to $4f0dc, pointer $1efe8, accessor $f2ce and the static-object drawer $d514.
  BT5    : single picture (header w=6,h=112, 5380 bytes) drawn at the ending ($c72c..$c750).
"""
import os
import sys

import numpy as np

from bt_common import *  # noqa


def pic_rows(d, o):
    w, h = w16(d, o), w16(d, o + 2)
    rows = []
    for y in range(h):
        row = []
        for g in range(w):
            p = [w16(d, o + 4 + (y * w + g) * 8 + 2 * i) for i in range(4)]
            for bit in range(15, -1, -1):
                row.append(((p[0] >> bit) & 1) | (((p[1] >> bit) & 1) << 1)
                           | (((p[2] >> bit) & 1) << 2) | (((p[3] >> bit) & 1) << 3))
        rows.append(row)
    return rows


def collection(name):
    d = read_file(name)
    offs = []
    first = None
    i = 0
    while True:
        o = w16(d, 2 * i)
        if o > 0 and (first is None or o < first):
            first = o
        if first is not None and 2 * i >= first:
            break
        offs.append(o)
        i += 1
    ents = []
    for k, o in enumerate(offs):
        if o == 0 or o >= len(d):
            ents.append(None)
        else:
            ents.append(pic_rows(d, o))
    return d, offs, ents


def degas(name):
    d = read_file(name)
    res = w16(d, 0)
    pal = [w16(d, 2 + 2 * i) for i in range(16)]
    rows = []
    for y in range(200):
        row = []
        for g in range(20):
            o = 34 + y * 160 + g * 8
            p = [w16(d, o + 2 * i) for i in range(4)]
            for bit in range(15, -1, -1):
                row.append(((p[0] >> bit) & 1) | (((p[1] >> bit) & 1) << 1)
                           | (((p[2] >> bit) & 1) << 2) | (((p[3] >> bit) & 1) << 3))
        rows.append(row)
    return res, pal, rows


def best_match(scr, rows, min_px=12):
    """scr: ndarray (H,W) of indices; rows: picture (colour 0 transparent). returns (ok, tot, x, y)."""
    pic = np.array(rows, dtype=np.uint8)
    ph, pw = pic.shape
    H, W = scr.shape
    acc = np.zeros((H - ph + 1, W - pw + 1), dtype=np.int32)
    ys, xs = np.nonzero(pic)
    tot = len(ys)
    if tot < min_px:
        return (0, tot, -1, -1)
    for y, x in zip(ys, xs):
        acc += (scr[y:y + H - ph + 1, x:x + W - pw + 1] == pic[y, x])
    i = np.unravel_index(np.argmax(acc), acc.shape)
    return (int(acc[i]), tot, int(i[1]), int(i[0]))
