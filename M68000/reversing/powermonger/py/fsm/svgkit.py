"""Minimal SVG writer for the hand-laid infographics: boxes, text lines, arrows, evidence colours, legend."""
import os
import subprocess
from xml.sax.saxutils import escape

FONT = 'Helvetica, Arial, sans-serif'
MONO = 'Menlo, Consolas, "DejaVu Sans Mono", monospace'
EVID = {  # fill, stroke
    'proven': ('#d9f0d3', '#2e7d32'),
    'live': ('#dbe9f7', '#1565c0'),
    'code': ('#ffffff', '#757575'),
    'inferred': ('#fff3cd', '#b7791f'),
    'plain': ('#f5f5f5', '#9e9e9e'),
}
EVID_NAME = {'proven': 'proven (gate vs the real 68000)', 'live': 'live (seen running, counted)',
             'code': 'code read', 'inferred': 'inferred'}


class Svg:
    def __init__(self, w, h, title, subtitle=''):
        self.w, self.h = w, h
        self.el = []
        self.el.append('<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (w, h))
        self.text(16, 28, title, size=18, weight='bold')
        if subtitle:
            self.text(16, 47, subtitle, size=12, color='#424242')

    def text(self, x, y, s, size=12, weight='normal', color='#212121', anchor='start', mono=False, italic=False):
        self.el.append('<text x="%.1f" y="%.1f" font-family=\'%s\' font-size="%s" font-weight="%s"%s fill="%s" '
                       'text-anchor="%s">%s</text>' % (x, y, MONO if mono else FONT, size, weight,
                                                     ' font-style="italic"' if italic else '', color, anchor, escape(s)))

    def lines(self, x, y, rows, size=12, lh=None, **kw):
        lh = lh or size * 1.3
        for i, r in enumerate(rows):
            if isinstance(r, tuple):        # (text, overrides)
                self.text(x, y + i * lh, r[0], size=size, **dict(kw, **r[1]))
            else:
                self.text(x, y + i * lh, r, size=size, **kw)
        return y + len(rows) * lh

    def box(self, x, y, w, h, ev='plain', rx=6, dash=False, sw=1.3):
        f, s = EVID[ev]
        self.el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s" stroke="%s" stroke-width="%s"%s/>'
                       % (x, y, w, h, rx, f, s, sw, ' stroke-dasharray="5,3"' if dash else ''))

    def frame(self, x, y, w, h, label=None):
        self.el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="8" fill="none" stroke="#9e9e9e" stroke-width="1"/>'
                       % (x, y, w, h))
        if label:
            self.text(x + 10, y + 18, label, size=13, weight='bold')

    def line(self, x1, y1, x2, y2, color='#424242', dash=False, arrow=True, sw=1.3):
        self.el.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s%s/>' % (
            x1, y1, x2, y2, color, sw, ' stroke-dasharray="5,3"' if dash else '', ' marker-end="url(#ah)"' if arrow else ''))

    def path(self, d, color='#424242', dash=False, arrow=True, sw=1.3):
        self.el.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s"%s%s/>' % (
            d, color, sw, ' stroke-dasharray="5,3"' if dash else '', ' marker-end="url(#ah)"' if arrow else ''))

    def legend(self, x, y, kinds):
        self.text(x, y, 'Evidence:', size=11, weight='bold')
        cx = x + 64
        for k in kinds:
            self.box(cx, y - 11, 14, 14, k, rx=3)
            self.text(cx + 19, y, EVID_NAME[k], size=11)
            cx += 26 + 6.2 * len(EVID_NAME[k])

    def save(self, path):
        head = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">\n'
                '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#424242"/></marker></defs>\n'
                % (self.w, self.h, self.w, self.h))
        open(path, 'w').write(head + '\n'.join(self.el) + '\n</svg>\n')
        png = os.path.splitext(path)[0] + '.png'
        subprocess.run(['rsvg-convert', '-b', 'white', '-w', str(self.w * 2), path, '-o', png], check=True)
        print('wrote', path, png)
