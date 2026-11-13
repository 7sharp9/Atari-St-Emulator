"""Wrapped prose for the infographic SVGs.

para(a, text, x, y, width, ...) appends <text> lines to the list-appender `a`, wrapping `text` to `width` pixels as
Helvetica measures it (PIL, the font rsvg-convert uses on the Mac; a per-character estimate elsewhere), and returns
the y of the next line. `**word**` marks bold spans; a blank line ("\n\n") starts a new paragraph.
"""
import html as _html
import re as _re

_FONTS = {}


def _font(size, bold):
    key = (round(size * 4), bold)
    if key not in _FONTS:
        try:
            from PIL import ImageFont
            _FONTS[key] = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', size, index=1 if bold else 0)
        except Exception:
            _FONTS[key] = None
    return _FONTS[key]


def textlen(s, size=12, bold=False):
    f = _font(size, bold)
    if f is not None:
        return f.getlength(s)
    return len(s) * size * (0.60 if bold else 0.55)


def _tokens(text):
    """Split into words; each word is a list of (segment, bold) runs, ** toggling bold."""
    out = []
    bold = False
    for w in text.split():
        runs = []
        for part in _re.split(r'(\*\*)', w):
            if part == '**':
                bold = not bold
            elif part:
                runs.append((part, bold))
        if runs:
            out.append(runs)
    return out


def _wlen(runs, size):
    return sum(textlen(t, size, b) for t, b in runs)


def lines(text, width, size=12):
    """Wrap to lists of words (lists of runs) per line; None marks a paragraph break."""
    res = []
    for par in text.split('\n\n'):
        cur, curw = [], 0.0
        for runs in _tokens(par):
            ww = _wlen(runs, size)
            sp = textlen(' ', size) if cur else 0
            if cur and curw + sp + ww > width:
                res.append(cur)
                cur, curw = [], 0.0
                sp = 0
            cur.append(runs)
            curw += sp + ww
        res.append(cur)
        res.append(None)
    return res[:-1]


def para(a, text, x, y, width, size=12, lh=None, color=None, anchor=None, parskip=None):
    """Emit wrapped text starting with its first baseline at y; return the next baseline."""
    lh = lh or round(size * 1.38, 1)
    parskip = lh * 0.5 if parskip is None else parskip
    style = f'font-size:{size}px' + (f';fill:{color}' if color else '')
    anc = f' text-anchor="{anchor}"' if anchor else ''
    for ln in lines(text, width, size):
        if ln is None:
            y += parskip
            continue
        out = []
        for i, runs in enumerate(ln):
            for t, b in runs:
                t = _html.escape(t, quote=False)
                out.append(f'<tspan style="font-weight:bold">{t}</tspan>' if b else t)
            if i < len(ln) - 1:
                out.append(' ')
        a(f'<text x="{x}" y="{y:.1f}" style="{style}"{anc} xml:space="preserve">{"".join(out)}</text>')
        y += lh
    return y


def height(text, width, size=12, lh=None, parskip=None):
    lh = lh or round(size * 1.38, 1)
    parskip = lh * 0.5 if parskip is None else parskip
    h = 0.0
    for ln in lines(text, width, size):
        h += parskip if ln is None else lh
    return h
