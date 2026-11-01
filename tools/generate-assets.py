#!/usr/bin/env python3
"""Generate the cyberpunk SVG assets for the josh14max GitHub profile.

Usage :  cd tools && npm i @fontsource/chakra-petch @fontsource/share-tech-mono
         pip install fonttools && python3 generate-assets.py

All text is converted to glyph outlines (<path> defs reused with <use>), so the
SVGs render identically on GitHub, where external/embedded fonts are blocked.
"""
import os
import random

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

HERE = os.path.dirname(os.path.abspath(__file__))
# Polices : cd tools && npm i @fontsource/chakra-petch @fontsource/share-tech-mono
FD = os.environ.get('FONTS_DIR', os.path.join(HERE, 'node_modules/@fontsource/'))
OUT = os.environ.get('OUT_DIR', os.path.join(HERE, '..', 'assets'))
os.makedirs(OUT, exist_ok=True)

# ── palette ──────────────────────────────────────────────────────────────
BG = '#07070d'
PANEL = '#0b0b14'
Y = '#f3e600'   # neon yellow
C = '#00f0ff'   # electric cyan
R = '#ff2a6d'   # hot magenta-red
W = '#ecebf5'
G = '#8b8ba7'
G2 = '#3a3a52'


def f1(v):
    s = f'{v:.1f}'
    return s[:-2] if s.endswith('.0') else s


class Font:
    def __init__(self, path):
        self.f = TTFont(path)
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f['head'].unitsPerEm
        self.hmtx = self.f['hmtx']
        self._p = {}

    def gname(self, ch):
        g = self.cmap.get(ord(ch))
        if g is None:
            raise KeyError(f'missing glyph {ch!r}')
        return g

    def adv(self, ch):
        return self.hmtx[self.gname(ch)][0]

    def path(self, ch):
        if ch not in self._p:
            pen = SVGPathPen(self.gs, ntos=lambda v: str(int(round(v))))
            self.gs[self.gname(ch)].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
            self._p[ch] = pen.getCommands()
        return self._p[ch]

    def width(self, s, size, ls=0):
        return sum(self.adv(c) for c in s) * size / self.upm + ls * max(len(s) - 1, 0)


cp = FD + 'chakra-petch/files/chakra-petch-latin-'
FONTS = {
    'disp': Font(cp + '700-italic.woff'),
    'bold': Font(cp + '700-normal.woff'),
    'semi': Font(cp + '600-normal.woff'),
    'mono': Font(FD + 'share-tech-mono/files/share-tech-mono-latin-400-normal.woff'),
}
MONO_ADV = FONTS['mono'].adv('a') / FONTS['mono'].upm  # em width of one mono char


class SVG:
    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.glyphs = {}
        self.defs, self.css, self.body = [], [], []

    def t(self, s, x, y, font='mono', size=16, fill=None, ls=0, anchor='start', attrs=''):
        """Return (svg_fragment, width, x_start) for text drawn as glyph outlines."""
        F = FONTS[font]
        w = F.width(s, size, ls)
        if anchor == 'middle':
            x -= w / 2
        elif anchor == 'end':
            x -= w
        sc = size / F.upm
        cx = 0.0
        parts = []
        for ch in s:
            if not ch.isspace():
                gid = f'{font}-{ord(ch):x}'
                self.glyphs[gid] = F.path(ch)
                parts.append(f'<use href="#{gid}" x="{cx:.0f}"/>')
            cx += F.adv(ch) + ls / sc
        fill_attr = f' fill="{fill}"' if fill else ''
        frag = (f'<g transform="translate({f1(x)} {f1(y)}) scale({sc:.5f})"{fill_attr}{attrs}>'
                + ''.join(parts) + '</g>')
        return frag, w, x

    def add(self, *frags):
        self.body.extend(frags)

    def text(self, *a, **k):
        frag, w, x = self.t(*a, **k)
        self.body.append(frag)
        return w, x

    def save(self, name):
        css = ''.join(self.css) + '@media (prefers-reduced-motion:reduce){*{animation:none!important}}'
        glyphs = ''.join(f'<path id="{k}" d="{v}"/>' for k, v in self.glyphs.items())
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{self.title}">'
               f'<title>{self.title}</title><style>{css}</style>'
               f'<defs>{glyphs}{"".join(self.defs)}</defs>{"".join(self.body)}</svg>')
        with open(os.path.join(OUT, name), 'w') as fh:
            fh.write(svg)
        print(f'{name:28s} {len(svg)/1024:6.1f} KB')


def notch(x, y, w, h, c=12, corners=('tr', 'bl')):
    pts = []
    pts += [(x, y + c), (x + c, y)] if 'tl' in corners else [(x, y)]
    pts += [(x + w - c, y), (x + w, y + c)] if 'tr' in corners else [(x + w, y)]
    pts += [(x + w, y + h - c), (x + w - c, y + h)] if 'br' in corners else [(x + w, y + h)]
    pts += [(x + c, y + h), (x, y + h - c)] if 'bl' in corners else [(x, y + h)]
    return 'M' + ' L'.join(f'{f1(a)} {f1(b)}' for a, b in pts) + ' Z'


def scan_defs(s, opacity=0.32):
    s.defs.append('<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
                  f'<rect width="4" height="1" fill="#000" opacity="{opacity}"/></pattern>')


def scan_band(s, w, h, dur=6, band=90, color='#ffffff', op=0.05):
    s.defs.append(f'<linearGradient id="band" x1="0" y1="0" x2="0" y2="1">'
                  f'<stop offset="0" stop-color="{color}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{color}" stop-opacity="{op}"/>'
                  f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient>')
    s.css.append(f'.band{{animation:band {dur}s linear infinite}}'
                 f'@keyframes band{{from{{transform:translateY(-{band}px)}}to{{transform:translateY({h}px)}}}}')
    s.add(f'<rect class="band" x="0" y="0" width="{w}" height="{band}" fill="url(#band)"/>')


def chevron(x, y, size, fill):
    """Small right-pointing chevron whose vertical centre is y."""
    h = size
    return (f'<path d="M{f1(x)} {f1(y - h/2)} L{f1(x + h*0.55)} {f1(y)} L{f1(x)} {f1(y + h/2)} '
            f'L{f1(x + h*0.22)} {f1(y)} Z" fill="{fill}"/>')


def skyline(s, base, rng, layers, x0=0, x1=1200, blink_cls='wb'):
    out = []
    for (fill, hmin, hmax, wmin, wmax, wprob, wcolor, wop) in layers:
        x = x0 - rng.randint(0, 30)
        while x < x1:
            bw = rng.randint(wmin, wmax)
            bh = rng.randint(hmin, hmax)
            top = base - bh
            out.append(f'<rect x="{x}" y="{top}" width="{bw}" height="{bh}" fill="{fill}"/>')
            if rng.random() < 0.25:
                ax = x + rng.randint(6, max(7, bw - 6))
                ah = rng.randint(10, 26)
                out.append(f'<line x1="{ax}" y1="{top}" x2="{ax}" y2="{top-ah}" stroke="{fill}" stroke-width="2"/>')
                if rng.random() < 0.6:
                    out.append(f'<circle class="{blink_cls}" style="animation-delay:-{rng.uniform(0,4):.1f}s" '
                               f'cx="{ax}" cy="{top-ah}" r="2" fill="{R}"/>')
            yy = top + 8
            while yy < base - 6:
                xx = x + 5
                while xx < x + bw - 6:
                    if rng.random() < wprob:
                        cls = f' class="{blink_cls}" style="animation-delay:-{rng.uniform(0,6):.1f}s"' if rng.random() < 0.08 else ''
                        out.append(f'<rect{cls} x="{xx}" y="{yy}" width="3" height="4" fill="{wcolor}" opacity="{wop}"/>')
                    xx += 7
                yy += 9
            x += bw + rng.randint(-4, 3)
    return out


# ══════════════════════════════════════════════════════════════════════
# 1. HEADER
# ══════════════════════════════════════════════════════════════════════
def header():
    W_, H_ = 1200, 360
    HZ = 268
    rng = random.Random(2077)
    s = SVG(W_, H_, 'JOSH14MAX — netrunner-class DevOps and vibe-coder')
    scan_defs(s)
    s.defs.append(
        f'<radialGradient id="gR" cx="50%" cy="50%" r="55%"><stop offset="0" stop-color="{R}" stop-opacity=".22"/>'
        f'<stop offset=".6" stop-color="{R}" stop-opacity=".03"/><stop offset="1" stop-color="{R}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="gH" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C}" stop-opacity="0"/>'
        f'<stop offset=".75" stop-color="{C}" stop-opacity=".16"/><stop offset="1" stop-color="{C}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="gF" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d0b1c"/><stop offset="1" stop-color="#040408"/></linearGradient>'
        '<radialGradient id="vig" cx="50%" cy="50%" r="75%"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity=".8"/></radialGradient>'
        '<filter id="blur8" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="9"/></filter>'
        '<filter id="blur3" x="-10%" y="-200%" width="120%" height="500%"><feGaussianBlur stdDeviation="3"/></filter>'
        f'<clipPath id="floor"><rect x="0" y="{HZ}" width="{W_}" height="{H_-HZ}"/></clipPath>'
    )
    s.css.append(
        '.wb{animation:wb 5s steps(1,end) infinite}'
        '@keyframes wb{0%{opacity:.9}48%{opacity:.1}52%{opacity:.9}100%{opacity:.9}}'
        '.hl{animation:hl 3.6s cubic-bezier(.55,0,1,.45) infinite}'
        f'@keyframes hl{{0%{{transform:translateY(0);opacity:0}}25%{{opacity:.45}}100%{{transform:translateY({H_-HZ}px);opacity:.9}}}}'
        '.flk{animation:flk 7s steps(1,end) infinite}'
        '@keyframes flk{0%{opacity:1}41%{opacity:.35}41.8%{opacity:1}43%{opacity:.6}43.6%{opacity:1}100%{opacity:1}}'
        '.gr{mix-blend-mode:screen;animation:gr 6s steps(1,end) infinite}'
        '@keyframes gr{0%{transform:translate(-4px,0)}62%{transform:translate(-16px,2px)}63.5%{transform:translate(9px,-1px)}'
        '65%{transform:translate(-4px,0)}86.6%{transform:translate(-12px,0)}87.4%{transform:translate(-4px,0)}100%{transform:translate(-4px,0)}}'
        '.gc{mix-blend-mode:screen;animation:gc 6s steps(1,end) infinite}'
        '@keyframes gc{0%{transform:translate(4px,0)}62%{transform:translate(14px,-2px)}63.5%{transform:translate(-10px,1px)}'
        '65%{transform:translate(4px,0)}86.6%{transform:translate(11px,0)}87.4%{transform:translate(4px,0)}100%{transform:translate(4px,0)}}'
        '.sl{opacity:0;animation:slo 6s steps(1,end) infinite}'
        '@keyframes slo{0%{opacity:0}62%{opacity:1}65.5%{opacity:0}86.6%{opacity:1}87.6%{opacity:0}100%{opacity:0}}'
        '.s1{animation:s1 6s steps(1,end) infinite}@keyframes s1{0%{transform:translateX(0)}62%{transform:translateX(-26px)}63.5%{transform:translateX(18px)}65%{transform:translateX(-8px)}86.6%{transform:translateX(30px)}100%{transform:translateX(0)}}'
        '.s2{animation:s2 6s steps(1,end) infinite}@keyframes s2{0%{transform:translateX(0)}62%{transform:translateX(22px)}63.5%{transform:translateX(-14px)}65%{transform:translateX(6px)}86.6%{transform:translateX(-20px)}100%{transform:translateX(0)}}'
        '.s3{animation:s3 6s steps(1,end) infinite}@keyframes s3{0%{transform:translateX(0)}62%{transform:translateX(-12px)}63.5%{transform:translateX(30px)}65%{transform:translateX(-18px)}86.6%{transform:translateX(14px)}100%{transform:translateX(0)}}'
        '.blk{opacity:0;animation:blk 7s steps(1,end) infinite}'
        '@keyframes blk{0%{opacity:0}30%{opacity:.85}31%{opacity:0}31.6%{opacity:.6}32.2%{opacity:0}100%{opacity:0}}'
        '.blink{animation:blink 1.1s steps(1,end) infinite}@keyframes blink{0%{opacity:1}50%{opacity:.15}100%{opacity:1}}'
    )

    # background, glows, skyline
    s.add(f'<rect width="{W_}" height="{H_}" fill="{BG}"/>',
          f'<rect width="{W_}" height="{H_}" fill="url(#gR)"/>')
    s.add(*skyline(s, HZ, rng, [
        ('#11112a', 60, 165, 26, 64, 0.10, C, 0.28),
        ('#0a0a17', 26, 105, 40, 110, 0.07, Y, 0.55),
    ]))
    # neon vertical signs on the skyline
    for (x, y0, h, col, d) in [(118, 150, 70, R, 0), (1046, 132, 86, C, 2.1), (884, 176, 48, Y, 4.0)]:
        s.add(f'<rect class="flk" style="animation-delay:-{d}s" x="{x}" y="{y0}" width="5" height="{h}" fill="{col}" filter="url(#blur3)" opacity=".9"/>',
              f'<rect class="flk" style="animation-delay:-{d}s" x="{x+1}" y="{y0}" width="3" height="{h}" fill="{col}"/>')
    s.add(f'<rect x="0" y="{HZ-80}" width="{W_}" height="96" fill="url(#gH)"/>')

    # perspective floor
    s.add(f'<rect x="0" y="{HZ}" width="{W_}" height="{H_-HZ}" fill="url(#gF)"/>')
    vl = []
    for k in range(-16, 17):
        xt = 600 + k * 38
        xb = 600 + k * 260
        vl.append(f'<line x1="{xt}" y1="{HZ}" x2="{xb}" y2="{H_}"/>')
    s.add(f'<g clip-path="url(#floor)" stroke="{C}" stroke-width="1" opacity=".38">' + ''.join(vl) + '</g>')
    hl = []
    n = 7
    for i in range(n):
        hl.append(f'<line class="hl" style="animation-delay:-{i*3.6/n:.2f}s" x1="0" y1="{HZ}" x2="{W_}" y2="{HZ}"/>')
    s.add(f'<g clip-path="url(#floor)" stroke="{C}" stroke-width="1.2">' + ''.join(hl) + '</g>')
    s.add(f'<line x1="0" y1="{HZ}" x2="{W_}" y2="{HZ}" stroke="{C}" stroke-width="4" filter="url(#blur3)" opacity=".8"/>',
          f'<line x1="0" y1="{HZ}" x2="{W_}" y2="{HZ}" stroke="{C}" stroke-width="1.5"/>')

    # title stack
    TS, TB = 136, 206
    frag, tw, tx = s.t('JOSH14MAX', 600, TB, 'disp', TS, ls=4, anchor='middle', attrs=' id="ttl"')
    s.defs.append(frag)
    s.add(f'<use href="#ttl" fill="{Y}" opacity=".55" filter="url(#blur8)" class="flk"/>',
          f'<use href="#ttl" fill="{R}" class="gr"/>',
          f'<use href="#ttl" fill="{C}" class="gc"/>',
          f'<use href="#ttl" fill="{Y}" class="flk"/>')
    bands = [(TB - 98, 16, 's1'), (TB - 62, 11, 's2'), (TB - 30, 18, 's3')]
    for i, (by, bh, cls) in enumerate(bands):
        s.defs.append(f'<clipPath id="b{i}"><rect x="0" y="{by}" width="{W_}" height="{bh}"/></clipPath>')
        s.add(f'<g class="sl" clip-path="url(#b{i})"><rect x="0" y="{by}" width="{W_}" height="{bh}" fill="{BG}"/>'
              f'<use href="#ttl" fill="{Y if i != 1 else C}" class="{cls}"/></g>')

    s.add(f'<rect width="{W_}" height="{H_}" fill="url(#vig)"/>')

    # tag plates under the title
    left_t, right_t = 'DEVOPS // NETRUNNER-CLASS', 'VIBE-CODER'
    PS, PL = 19, 2.6
    wl = FONTS['semi'].width(left_t, PS, PL)
    wr = FONTS['semi'].width(right_t, PS, PL)
    pad, sk, gap, py, ph = 20, 11, 14, 226, 32
    total = wl + wr + 4 * pad + gap + sk
    x0 = 600 - total / 2
    a0, a1 = x0, x0 + wl + 2 * pad
    b0, b1 = a1 + gap, a1 + gap + wr + 2 * pad
    s.add(f'<path d="M{f1(a0+sk)} {py} L{f1(a1+sk)} {py} L{f1(a1)} {py+ph} L{f1(a0)} {py+ph} Z" fill="{Y}"/>',
          f'<path d="M{f1(b0+sk)} {py} L{f1(b1+sk)} {py} L{f1(b1)} {py+ph} L{f1(b0)} {py+ph} Z" fill="{C}"/>')
    s.text(left_t, a0 + pad + sk / 2, py + 23, 'semi', PS, fill=BG, ls=PL)
    s.text(right_t, b0 + pad + sk / 2, py + 23, 'semi', PS, fill=BG, ls=PL)

    # top HUD
    s.add(f'<path d="M40 22 L54 22 L40 36 Z" fill="{Y}"/>')
    s.text('SYS://JOSEPH-MARIE', 62, 36, 'mono', 17, fill=Y, ls=1.5)
    s.text('EPITECH NANTES · PRE-MSC · GAP YEAR 26/27', 62, 55, 'mono', 12.5, fill=G, ls=1)
    s.text('NANTES // FR', 1138, 36, 'mono', 17, fill=W, ls=1.5, anchor='end')
    s.add(f'<circle class="blink" cx="1154" cy="30.5" r="5" fill="{C}"/>')
    s.text('UPLINK STABLE · NODE jojoserver', 1160, 55, 'mono', 12.5, fill=G, ls=1, anchor='end')
    bx = 528
    bars = []
    while bx < 672:
        bw = rng.choice([1, 1, 2, 3, 4])
        if rng.random() < 0.7:
            bars.append(f'<rect x="{bx}" y="22" width="{bw}" height="16"/>')
        bx += bw + rng.choice([1, 2, 2, 3])
    s.add(f'<g fill="{Y}" opacity=".7">' + ''.join(bars) + '</g>')
    s.text('ID 0x14-MAX', 600, 54, 'mono', 11, fill=G, ls=2, anchor='middle')
    ticks = ''.join(f'<line x1="{x}" y1="70" x2="{x}" y2="{74 if x % 100 else 78}"/>' for x in range(40, 1161, 20))
    s.add(f'<g stroke="{G}" opacity=".35"><line x1="40" y1="70" x2="1160" y2="70"/>{ticks}</g>')

    # glitch blocks
    for (x, y, w, h, col, d) in [(212, 118, 46, 7, Y, 0), (930, 96, 24, 5, C, 1.3), (300, 238, 70, 4, R, 2.9),
                                 (868, 214, 38, 9, Y, 4.4), (146, 196, 18, 18, C, 5.6), (1012, 172, 56, 5, R, 3.5)]:
        s.add(f'<rect class="blk" style="animation-delay:-{d}s" x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}"/>')

    # bottom HUD
    s.add(f'<rect x="32" y="328" width="440" height="24" fill="{BG}" opacity=".75"/>',
          f'<rect x="900" y="328" width="268" height="24" fill="{BG}" opacity=".75"/>')
    s.text('BUILD 2026.11 // K3S · DOCKER · TERRAFORM · AWS', 40, 345, 'mono', 13.5, fill=C, ls=1)
    w_, _ = s.t('[ SCROLL TO JACK IN ]', 0, 0, 'mono', 13.5, ls=1.5)[1:]
    frag = s.t('[ SCROLL TO JACK IN ]', 1160, 345, 'mono', 13.5, fill=Y, ls=1.5, anchor='end')[0]
    s.add(f'<g class="blink">{frag}</g>')

    # corner brackets, scanlines, scan band
    s.add(f'<g fill="none" stroke="{Y}" stroke-width="2.5">'
          '<path d="M12 44 V12 H44"/><path d="M1156 12 H1188 V44"/>'
          '<path d="M12 316 V348 H44"/><path d="M1156 348 H1188 V316"/></g>')
    s.add(f'<rect width="{W_}" height="{H_}" fill="url(#scan)"/>')
    scan_band(s, W_, H_, dur=5, band=80, op=0.06)
    s.save('header.svg')


# ══════════════════════════════════════════════════════════════════════
# 2. SECTION HEADERS
# ══════════════════════════════════════════════════════════════════════
def section(num, label, tag):
    W_, H_ = 1200, 72
    s = SVG(W_, H_, f'{num} // {label}')
    s.css.append('.pk{animation:pk 4.5s cubic-bezier(.7,0,.3,1) infinite}'
                 '@keyframes pk{0%{transform:translateX(0);opacity:0}10%{opacity:1}90%{opacity:1}100%{transform:translateX(var(--d));opacity:0}}'
                 '.blink{animation:blink 1.1s steps(1,end) infinite}@keyframes blink{0%{opacity:1}50%{opacity:.15}100%{opacity:1}}')
    s.add(f'<path d="M10 14 L104 14 L92 58 L0 58 Z" fill="{Y}"/>')
    s.text(num, 52, 46, 'disp', 28, fill=BG, anchor='middle')
    lw, _ = s.text(label, 124, 47, 'bold', 31, fill=W, ls=3.5)
    lx = 124 + lw + 26
    s.add(f'<g stroke="{G}"><line x1="{f1(lx)}" y1="36" x2="1150" y2="36" opacity=".45"/>'
          + ''.join(f'<line x1="{x}" y1="32" x2="{x}" y2="40" opacity=".45"/>'
                    for x in range(int(lx) + 30, 1140, 60)) + '</g>')
    d = 1150 - lx - 30
    s.add(f'<rect class="pk" style="--d:{f1(d)}px" x="{f1(lx)}" y="34" width="30" height="4" fill="{C}"/>')
    s.add(f'<rect class="blink" x="1160" y="28" width="16" height="16" fill="{Y}"/>')
    s.text(tag, 1150, 24, 'mono', 12, fill=G, ls=1.5, anchor='end')
    slug = label.lower().replace(' ', '-').replace('/', '')
    s.save(f'sec-{num}-{slug}.svg')


# ══════════════════════════════════════════════════════════════════════
# 3. TERMINAL (whoami) — SMIL typing animation
# ══════════════════════════════════════════════════════════════════════
def terminal():
    rng = random.Random(14)
    W_ = 1200
    FS = 21
    LH = 35
    cw = MONO_ADV * FS
    X0 = 48
    TOP = 96
    PROMPT = 'jm@jojoserver'
    LINES = [
        ('cmd', 'whoami'),
        ('out', [('Joseph-Marie', Y), (' // DevOps apprentice-netrunner · Epitech Nantes (pre-MSc)', W)]),
        ('cmd', 'cat /etc/role'),
        ('out', [('Network DevOps apprentice', W), (' @ ', G), ('Bureau Veritas', Y), ('  ·  Terraform · AWS · network eng.', G)]),
        ('cmd', 'kubectl get nodes'),
        ('out', [('NAME         STATUS   ROLES', G)]),
        ('out', [('jojoserver   ', W), ('Ready', C), ('    control-plane', W)]),
        ('cmd', 'cat mission.txt'),
        ('out', [('Build infra that heals itself. Ship products at AI speed. Own every line.', W)]),
        ('cmd', 'echo $CURRENT_QUEST'),
        ('out', [('gap-year 26/27', R), (' :: ', G), ('DevOps > Cloud', W), (' :: ', G), ('LFCS > CKA > Terraform > AWS SAA', Y)]),
        ('prompt', ''),
    ]
    H_ = TOP + LH * len(LINES) + 34
    s = SVG(W_, H_, 'Terminal: whoami — Joseph-Marie, DevOps apprentice and vibe-coder')
    scan_defs(s, 0.28)
    s.defs.append('<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
                  f'<rect width="1.5" height="1.5" fill="{G}" opacity=".18"/></pattern>')
    s.css.append('.blink{animation:blink 1s steps(1,end) infinite}@keyframes blink{0%{opacity:1}50%{opacity:0}100%{opacity:1}}')

    # frame
    s.add(f'<path d="{notch(8, 8, W_-16, H_-16, 22, ("tl","br"))}" fill="{PANEL}" stroke="{Y}" stroke-width="1.6"/>')
    s.add(f'<path d="{notch(8, 8, W_-16, H_-16, 22, ("tl","br"))}" fill="url(#dots)"/>')
    s.add(f'<path d="M8 30 L30 8 L{W_-8} 8 L{W_-8} 50 L8 50 Z" fill="{Y}"/>')
    s.text('jm@jojoserver: ~  —  zsh  —  120×32', 52, 36, 'mono', 16, fill=BG, ls=1)
    for i, x in enumerate([1112, 1138, 1164]):
        s.add(f'<rect x="{x}" y="21" width="16" height="16" fill="none" stroke="{BG}" stroke-width="2"/>')
    s.add(f'<line x1="{1166}" y1="23" x2="{1178}" y2="35" stroke="{BG}" stroke-width="2"/>'
          f'<line x1="{1178}" y1="23" x2="{1166}" y2="35" stroke="{BG}" stroke-width="2"/>')
    s.text('SECURE SHELL · AES-256 · LATENCY 4ms', W_ - 30, H_ - 22, 'mono', 11.5, fill=G2, ls=1.5, anchor='end')

    pw = FONTS['mono'].width(PROMPT, FS)
    cmd_x = X0 + pw + 30

    # timeline
    # The loop starts on the finished screen (so the first frame / a static
    # render shows everything), then "clears" at CLR and types it all again.
    CLR = 4.0
    events = []  # (time, cursor_x, cursor_y)
    reveals = []  # per line: list of (time, width)
    t = CLR + 0.7
    for i, (kind, content) in enumerate(LINES):
        y = TOP + i * LH
        if kind in ('cmd', 'prompt'):
            steps = [(t, pw + 30)]
            events.append((t, cmd_x, y))
            t += 0.45
            for k in range(1, len(content) + 1):
                steps.append((t, pw + 30 + k * cw))
                events.append((t, cmd_x + k * cw, y))
                t += rng.uniform(0.045, 0.095)
            t += 0.35
            reveals.append(steps)
        else:
            t += 0.12
            total = sum(len(x[0]) for x in content) * cw
            reveals.append([(t, total + 4)])
            nxt_y = TOP + (i + 1) * LH
            events.append((t, X0, nxt_y + 400))  # hide cursor while output prints
        if i + 1 < len(LINES) and LINES[i + 1][0] in ('cmd', 'prompt') and kind == 'out':
            t += 0.55
    T = t + 3.0

    def anim(attr, pairs, start_val, cleared_val):
        vals = [start_val, cleared_val] + [v for _, v in pairs]
        kts = [0.0, CLR / T] + [tm / T for tm, _ in pairs]
        cleaned_v, cleaned_k = [], []
        for v, k in zip(vals, kts):
            if cleaned_k and k <= cleaned_k[-1]:
                k = cleaned_k[-1] + 1e-4
            cleaned_v.append(v)
            cleaned_k.append(k)
        return (f'<animate attributeName="{attr}" dur="{T:.2f}s" repeatCount="indefinite" calcMode="discrete" '
                f'values="{";".join(f1(v) for v in cleaned_v)}" keyTimes="{";".join(f"{k:.4f}" for k in cleaned_k)}"/>')

    for i, (kind, content) in enumerate(LINES):
        y = TOP + i * LH
        full = (pw + 30 + len(content) * cw + 6) if kind != 'out' else sum(len(x[0]) for x in content) * cw + 6
        s.defs.append(f'<clipPath id="cl{i}"><rect x="{X0 - 4}" y="{y - 26}" width="{f1(full)}" height="{LH}">'
                      + anim('width', reveals[i], full, 0) + '</rect></clipPath>')
        parts = []
        if kind in ('cmd', 'prompt'):
            parts.append(s.t(PROMPT, X0, y, 'mono', FS, fill=C)[0])
            parts.append(chevron(X0 + pw + 10, y - 7, 15, Y))
            if content:
                parts.append(s.t(content, cmd_x, y, 'mono', FS, fill=W)[0])
        else:
            x = X0
            for seg, col in content:
                parts.append(s.t(seg, x, y, 'mono', FS, fill=col)[0])
                x += len(seg) * cw
        s.add(f'<g clip-path="url(#cl{i})">' + ''.join(parts) + '</g>')

    # cursor
    last_y = TOP + (len(LINES) - 1) * LH
    xs = [(tm, x + 2) for tm, x, _ in events]
    ys = [(tm, yy - 19) for tm, _, yy in events]
    s.add(f'<rect class="blink" x="{f1(cmd_x + 2)}" y="{last_y - 19}" width="{f1(cw)}" height="23" fill="{Y}">'
          + anim('x', xs, cmd_x + 2, cmd_x + 2)
          + anim('y', ys, last_y - 19, -100) + '</rect>')

    s.add(f'<path d="{notch(8, 8, W_-16, H_-16, 22, ("tl","br"))}" fill="url(#scan)"/>')
    scan_band(s, W_, H_, dur=7, band=70, op=0.045)
    s.save('terminal.svg')


# ══════════════════════════════════════════════════════════════════════
# 4. ARSENAL / LOADOUT
# ══════════════════════════════════════════════════════════════════════
def arsenal():
    W_ = 1200
    ROWS = [
        ('INFRA // CORE', [('Linux', 0), ('Docker', 0), ('K3s', 0), ('Kubernetes', 0), ('Traefik', 0), ('Ansible', 0), ('Terraform', 0)]),
        ('CI / CD', [('GitHub Actions', 0), ('Jenkins', 0), ('Drone CI', 0), ('Gitea', 0), ('Git', 0)]),
        ('OBSERVABILITY', [('Prometheus', 0), ('Grafana', 0), ('cAdvisor', 0)]),
        ('CLOUD', [('AWS', 1), ('Terraform on AWS', 1)]),
        ('VIBE-CODE STACK', [('Cursor', 0), ('Claude', 0), ('React', 0), ('TypeScript', 0), ('Vite', 0), ('Tailwind', 0), ('Supabase', 0), ('Vercel', 0)]),
        ('NETWORK / SEC', [('TCP/IP', 1), ('Subnetting', 0), ('Kali Linux', 0), ('Exegol', 0)]),
        ('MLOPS LAB', [('Python', 0), ('MLflow', 0)]),
    ]
    QUEUE = ['LFCS', 'CKA', 'Terraform Associate', 'AWS SAA']
    LX, CX0, CX1 = 44, 300, 1156
    CH, PADX, GAPX, FS = 38, 16, 10, 17.5
    top = 74
    rowgap = 56
    # layout (with wrapping)
    layout = []
    y = top
    for label, chips in ROWS:
        x = CX0
        row = []
        for name, learning in chips:
            w = FONTS['semi'].width(name, FS, 0.6) + 2 * PADX
            if x + w > CX1:
                x = CX0
                y += CH + 10
            row.append((name, learning, x, y, w))
            x += w + GAPX
        layout.append((label, y if not row else row[0][3], row))
        y += rowgap
    qy = y + 22
    H_ = qy + 110
    s = SVG(W_, H_, 'Loadout: DevOps, cloud, CI/CD, observability and vibe-coding stack')
    scan_defs(s, 0.25)
    s.defs.append(f'<linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{C}" stop-opacity=".12"/><stop offset="1" stop-color="{C}" stop-opacity="0"/></linearGradient>')
    s.css.append('.sw{animation:sw 7s linear infinite}@keyframes sw{0%{transform:translateX(-200px)}60%{transform:translateX(1250px)}100%{transform:translateX(1250px)}}'
                 '.dash{animation:dash 1.2s linear infinite}@keyframes dash{to{stroke-dashoffset:-14}}'
                 '.blink{animation:blink 1.1s steps(1,end) infinite}@keyframes blink{0%{opacity:1}50%{opacity:.15}100%{opacity:1}}')
    frame = notch(8, 18, W_ - 16, H_ - 26, 20, ('tr', 'bl'))
    s.add(f'<path d="{frame}" fill="{PANEL}" stroke="{G2}" stroke-width="1.5"/>')
    s.add(f'<path d="M8 18 L300 18 L288 40 L8 40 Z" fill="{Y}"/>')
    s.text('LOADOUT.CFG // josh14max', 22, 35, 'mono', 14.5, fill=BG, ls=1.5)
    s.text('SLOTS ACTIVE: ' + str(sum(1 for _, ch in ROWS for c in ch if not c[1])), W_ - 34, 36, 'mono', 12.5, fill=G, ls=1.5, anchor='end')

    delay = 0.0
    for idx, (label, ly, row) in enumerate(layout):
        s.text(f'{idx+1:02d}', LX, ly + 25, 'mono', 13, fill=G, ls=1)
        s.text(label, LX + 32, ly + 25, 'mono', 15, fill=Y, ls=1.6)
        for (name, learning, x, y, w) in row:
            stroke = C if learning else Y
            dash = ' stroke-dasharray="5 2" class="dash"' if learning else ''
            fill = W if not learning else C
            chip = (f'<path d="{notch(x, y, w, CH, 9)}" fill="#10101c" stroke="{stroke}" stroke-width="1.3" stroke-opacity=".9"{dash}/>'
                    + s.t(name, x + PADX, y + 25.5, 'semi', FS, fill=fill, ls=0.6)[0])
            s.add(chip)

    # upgrade queue
    s.add(f'<line x1="{LX}" y1="{qy-20}" x2="{W_-44}" y2="{qy-20}" stroke="{G2}" stroke-dasharray="2 6"/>')
    s.text('UPGRADE QUEUE', LX + 32, qy + 25, 'mono', 15, fill=R, ls=1.6)
    s.add(f'<rect class="blink" x="{LX}" y="{qy+13}" width="12" height="12" fill="{R}"/>')
    x = CX0
    for i, name in enumerate(QUEUE):
        w = FONTS['semi'].width(name, FS, 0.6) + 2 * PADX + 74
        s.add(f'<path d="{notch(x, qy, w, CH, 9)}" fill="#14070d" stroke="{R}" stroke-width="1.3" stroke-dasharray="5 2" class="dash"/>')
        s.text(name, x + PADX, qy + 25.5, 'semi', FS, fill=W, ls=0.6)
        s.text('QUEUED', x + w - PADX, qy + 24.5, 'mono', 11, fill=R, ls=1.2, anchor='end')
        x += w
        if i < len(QUEUE) - 1:
            s.add(chevron(x + 9, qy + CH / 2, 16, R))
            x += 32
    # legend
    ly = qy + 76
    s.add(f'<rect x="{LX}" y="{ly-11}" width="22" height="13" fill="none" stroke="{Y}" stroke-width="1.3"/>')
    s.text('IN USE', LX + 32, ly, 'mono', 12.5, fill=G, ls=1.5)
    s.add(f'<rect x="{LX+120}" y="{ly-11}" width="22" height="13" fill="none" stroke="{C}" stroke-width="1.3" stroke-dasharray="4 2"/>')
    s.text('LEARNING', LX + 152, ly, 'mono', 12.5, fill=G, ls=1.5)
    s.add(f'<rect x="{LX+262}" y="{ly-11}" width="22" height="13" fill="none" stroke="{R}" stroke-width="1.3" stroke-dasharray="4 2"/>')
    s.text('CERT TARGET', LX + 294, ly, 'mono', 12.5, fill=G, ls=1.5)

    s.add(f'<rect class="sw" x="0" y="18" width="180" height="{H_-26}" fill="url(#sw)"/>')
    s.add(f'<path d="{frame}" fill="url(#scan)"/>')
    s.save('arsenal.svg')


# ══════════════════════════════════════════════════════════════════════
# 5. VIBE PROTOCOL
# ══════════════════════════════════════════════════════════════════════
def protocol():
    W_, H_ = 1200, 300
    STEPS = [
        ('01', 'SPEC', 'PRD + user stories', 'before the first prompt'),
        ('02', 'GENERATE', 'Cursor + Claude', 'as pair-programmers'),
        ('03', 'AUDIT', 'secrets out of the front', 'RLS · HMAC webhooks'),
        ('04', 'SHIP', 'containers · CI/CD', 'monitored in prod'),
    ]
    xs = [150, 450, 750, 1050]
    LY = 76
    D = 6.0
    s = SVG(W_, H_, 'Vibe protocol: spec, generate, audit, ship')
    scan_defs(s, 0.25)
    s.defs.append('<filter id="gl" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="4"/></filter>')
    css = (f'.pkt{{animation:pkt {D}s linear infinite}}'
           f'@keyframes pkt{{from{{transform:translateX(0)}}to{{transform:translateX({xs[-1]-xs[0]}px)}}}}')
    for i in range(4):
        f = i / 3 * 100
        a, b = max(f - 2.5, 0), min(f + 6, 100)
        if i == 0:
            css += f'.nd{i}{{animation:nd{i} {D}s linear infinite}}@keyframes nd{i}{{0%{{fill:{Y}}}{b:.1f}%{{fill:{BG}}}100%{{fill:{BG}}}}}'
        elif i == 3:
            css += f'.nd{i}{{animation:nd{i} {D}s linear infinite}}@keyframes nd{i}{{0%{{fill:{BG}}}{a:.1f}%{{fill:{BG}}}100%{{fill:{Y}}}}}'
        else:
            css += (f'.nd{i}{{animation:nd{i} {D}s linear infinite}}@keyframes nd{i}{{0%{{fill:{BG}}}{a:.1f}%{{fill:{BG}}}'
                    f'{f:.1f}%{{fill:{Y}}}{b:.1f}%{{fill:{BG}}}100%{{fill:{BG}}}}}')
    s.css.append(css)
    frame = notch(8, 8, W_ - 16, H_ - 16, 20, ('tr', 'bl'))
    s.add(f'<path d="{frame}" fill="{PANEL}" stroke="{G2}" stroke-width="1.5"/>')
    s.add(f'<line x1="{xs[0]}" y1="{LY}" x2="{xs[-1]}" y2="{LY}" stroke="{G}" stroke-width="1.5" stroke-dasharray="3 7" opacity=".7"/>')
    s.add(f'<g class="pkt"><rect x="{xs[0]-22}" y="{LY-3}" width="44" height="6" fill="{C}" filter="url(#gl)"/>'
          f'<rect x="{xs[0]-16}" y="{LY-2}" width="32" height="4" fill="{C}"/></g>')
    for i, (n, title, l1, l2) in enumerate(STEPS):
        x = xs[i]
        s.add(f'<rect class="nd{i}" x="{x-11}" y="{LY-11}" width="22" height="22" transform="rotate(45 {x} {LY})" fill="{BG}" stroke="{Y}" stroke-width="2"/>')
        s.text(n, x, 160, 'disp', 50, fill=Y, anchor='middle')
        s.text(title, x, 198, 'bold', 25, fill=W, ls=3, anchor='middle')
        s.text(l1, x, 232, 'mono', 15.5, fill=G, anchor='middle')
        s.text(l2, x, 256, 'mono', 15.5, fill=G, anchor='middle')
    s.text('AI WRITES FAST. I OWN WHAT SHIPS.', W_ - 36, 34, 'mono', 12, fill=R, ls=1.6, anchor='end')
    s.add(f'<path d="{frame}" fill="url(#scan)"/>')
    s.save('vibe-protocol.svg')


# ══════════════════════════════════════════════════════════════════════
# 6. CONTRACT CARDS
# ══════════════════════════════════════════════════════════════════════
def wrap(text, font, size, maxw):
    words, lines, cur = text.split(), [], ''
    for w in words:
        cand = (cur + ' ' + w).strip()
        if FONTS[font].width(cand, size) <= maxw:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def card(slug, idx, title, status, scol, sub, desc, tags, accent):
    W_, H_ = 600, 310
    s = SVG(W_, H_, f'{title} — {sub}')
    scan_defs(s, 0.25)
    s.defs.append(f'<pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                  f'<rect width="2" height="8" fill="{accent}" opacity=".35"/></pattern>')
    s.css.append('.blink{animation:blink 1.1s steps(1,end) infinite}@keyframes blink{0%{opacity:1}50%{opacity:.15}100%{opacity:1}}'
                 f'.cs{{animation:cs 5s linear infinite}}@keyframes cs{{from{{transform:translateY(0)}}to{{transform:translateY({H_-30}px)}}}}'
                 '.gx{mix-blend-mode:screen;animation:gx 5s steps(1,end) infinite}'
                 '@keyframes gx{0%{transform:translate(-2px,0)}70%{transform:translate(-9px,1px)}71.5%{transform:translate(5px,0)}73%{transform:translate(-2px,0)}100%{transform:translate(-2px,0)}}')
    frame = notch(6, 6, W_ - 12, H_ - 12, 26, ('tr', 'bl'))
    s.add(f'<path d="{frame}" fill="{PANEL}" stroke="{accent}" stroke-width="1.6"/>')
    s.add(f'<path d="M{W_-150} 6 L{W_-32} 6 L{W_-6} 32 L{W_-6} 70 Z" fill="url(#hatch)"/>')
    s.text(f'CONTRACT // {idx}', 30, 42, 'mono', 14, fill=C, ls=1.8)
    # status pill
    sw = FONTS['mono'].width(status, 13, 1.5) + 40
    sx = W_ - 170 - sw
    solid = status in ('LIVE', 'ONLINE')
    s.add(f'<path d="{notch(sx, 24, sw, 26, 7)}" fill="{scol if solid else "none"}" stroke="{scol}" stroke-width="1.3"/>')
    s.add(f'<circle class="blink" cx="{sx+15}" cy="37" r="4" fill="{BG if solid else scol}"/>')
    s.text(status, sx + 27, 42, 'mono', 13, fill=BG if solid else scol, ls=1.5)
    # title with chromatic offset
    frag, tw, tx = s.t(title, 30, 104, 'disp', 44, ls=1.5, attrs=f' id="t-{slug}"')
    s.defs.append(frag)
    s.add(f'<use href="#t-{slug}" fill="{R}" class="gx"/>', f'<use href="#t-{slug}" fill="{W}"/>')
    s.text(sub, 30, 134, 'mono', 15, fill=accent, ls=0.8)
    y = 172
    for line in wrap(desc, 'semi', 18.5, W_ - 70)[:3]:
        s.text(line, 30, y, 'semi', 18.5, fill='#b9b9cc')
        y += 26
    # tags
    x = 30
    for tg in tags:
        w = FONTS['mono'].width(tg, 12.5, 0.8) + 20
        if x + w > W_ - 150:
            break
        s.add(f'<rect x="{f1(x)}" y="250" width="{f1(w)}" height="24" fill="none" stroke="{C}" stroke-opacity=".55"/>')
        s.text(tg, x + 10, 266.5, 'mono', 12.5, fill=C, ls=0.8)
        x += w + 7
    s.text('ACCESS', W_ - 58, 267, 'mono', 14, fill=Y, ls=2, anchor='end')
    s.add(chevron(W_ - 50, 262, 14, Y), chevron(W_ - 40, 262, 14, Y))
    s.defs.append(f'<clipPath id="fr"><path d="{frame}"/></clipPath>')
    s.add(f'<g clip-path="url(#fr)"><rect class="cs" x="0" y="10" width="{W_}" height="2" fill="{accent}" opacity=".18"/></g>')
    s.add(f'<path d="{frame}" fill="url(#scan)"/>')
    s.save(f'card-{slug}.svg')


# ══════════════════════════════════════════════════════════════════════
# 7. UPLINK BUTTONS
# ══════════════════════════════════════════════════════════════════════
def button(slug, label, sub, col):
    W_, H_ = 390, 78
    s = SVG(W_, H_, label)
    s.css.append('.blink{animation:blink 1.1s steps(1,end) infinite}@keyframes blink{0%{opacity:1}50%{opacity:.15}100%{opacity:1}}')
    s.add(f'<path d="{notch(4, 4, W_-8, H_-8, 16, ("tr","bl"))}" fill="{PANEL}" stroke="{col}" stroke-width="1.8"/>')
    s.add(f'<path d="M4 4 L18 4 L18 {H_-4} L4 {H_-20} Z" fill="{col}"/>')
    s.text(label, 38, 41, 'bold', 23, fill=W, ls=2.5)
    s.text(sub, 38, 62, 'mono', 12.5, fill=col, ls=1.2)
    s.add(f'<g class="blink">{chevron(W_-40, H_/2, 18, col)}</g>')
    s.save(f'btn-{slug}.svg')


# ══════════════════════════════════════════════════════════════════════
# 8. FOOTER
# ══════════════════════════════════════════════════════════════════════
def footer():
    W_, H_ = 1200, 190
    rng = random.Random(14)
    s = SVG(W_, H_, 'End of transmission')
    scan_defs(s, 0.3)
    s.defs.append(f'<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG}" stop-opacity="0"/>'
                  f'<stop offset="1" stop-color="{BG}"/></linearGradient>'
                  f'<linearGradient id="hl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{Y}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{Y}"/><stop offset="1" stop-color="{Y}" stop-opacity="0"/></linearGradient>')
    s.css.append('.wb{animation:wb 5s steps(1,end) infinite}@keyframes wb{0%{opacity:.9}48%{opacity:.1}52%{opacity:.9}100%{opacity:.9}}'
                 '.blink{animation:blink 1s steps(1,end) infinite}@keyframes blink{0%{opacity:1}50%{opacity:0}100%{opacity:1}}'
                 '.gx{mix-blend-mode:screen;animation:gx 4s steps(1,end) infinite}'
                 '@keyframes gx{0%{transform:translate(-3px,0)}55%{transform:translate(-12px,1px)}56.5%{transform:translate(8px,0)}58%{transform:translate(-3px,0)}100%{transform:translate(-3px,0)}}')
    s.add(f'<rect width="{W_}" height="{H_}" fill="{BG}"/>')
    s.add(*skyline(s, H_, rng, [('#10102a', 40, 120, 26, 64, 0.08, C, 0.25), ('#0b0b18', 20, 70, 40, 100, 0.05, Y, 0.5)]))
    s.add(f'<rect width="{W_}" height="{H_}" fill="url(#fade)" opacity=".35"/>')
    s.add(f'<rect x="100" y="0" width="1000" height="2" fill="url(#hl)"/>')
    s.add(f'<rect x="330" y="44" width="540" height="96" fill="{BG}" opacity=".82"/>')
    frag, _, _ = s.t('END OF TRANSMISSION', 600, 92, 'disp', 40, ls=3, anchor='middle', attrs=' id="eot"')
    s.defs.append(frag)
    s.add(f'<use href="#eot" fill="{C}" class="gx"/>', f'<use href="#eot" fill="{Y}"/>')
    w, x = s.text('> stay curious · ship clean · jack out', 600, 124, 'mono', 16, fill=G, ls=1, anchor='middle')
    s.add(f'<rect class="blink" x="{f1(x + w + 6)}" y="110" width="10" height="17" fill="{Y}"/>')
    s.add(f'<rect width="{W_}" height="{H_}" fill="url(#scan)"/>')
    s.save('footer.svg')


if __name__ == '__main__':
    header()
    for n, l, t in [('01', 'WHOAMI', '[ 0x01 ] IDENTITY.SYS'), ('02', 'ARSENAL', '[ 0x02 ] LOADOUT.CFG'),
                    ('03', 'VIBE PROTOCOL', '[ 0x03 ] METHOD.EXE'), ('04', 'ACTIVE CONTRACTS', '[ 0x04 ] JOBS.DB'),
                    ('05', 'NEURAL TRACE', '[ 0x05 ] ACTIVITY.LOG'), ('06', 'UPLINK', '[ 0x06 ] COMMS.NET')]:
        section(n, l, t)
    terminal()
    arsenal()
    protocol()
    card('ng-hair', '0x01', 'NG HAIR', 'LIVE', Y, 'vibe-coded e-commerce · in production',
         'Wig store built AI-first. Mobile-money checkout (Wave, Orange Money) with HMAC-verified webhooks and an in-house back-office.',
         ['React', 'TypeScript', 'Supabase', 'Vercel'], Y)
    card('jojoserver', '0x02', 'JOJOSERVER', 'ONLINE', C, 'self-hosted homelab · bare metal',
         'A recycled PC turned cluster: K3s behind Traefik, self-hosted Git and CI, a full metrics stack, provisioned as code.',
         ['K3s', 'Ansible', 'Terraform', 'Grafana'], C)
    card('aspire', '0x03', 'ASPIRE', 'IN DEV', R, 'create-launch · ship-ready web app',
         'Launch pipeline for a web product: transactional emails, legal pages, error tracking and end-to-end tests.',
         ['E2E tests', 'Monitoring', 'Email'], R)
    card('spam-detector', '0x04', 'SPAM DETECTOR', 'R&D', G, 'mlops lab · experiment tracking',
         'Spam classifier with tracked experiments and model versions, plus an experimental Gmail × Gemini automation.',
         ['Python', 'MLflow', 'Gemini API'], Y)
    button('linkedin', 'LINKEDIN', 'professional uplink', C)
    button('mail', 'MAIL', 'direct line · drop a signal', Y)
    button('hire', 'HIRE ME', 'freelance vibe-code gigs', R)
    footer()
