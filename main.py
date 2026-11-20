#!/usr/bin/env python3
"""The Daily Globe - front page for Friday 20 November 2026.

A single-file, standard-library-only program. It draws a newspaper front
page that sums up the world's news of Friday 20 November 2026 and writes
it to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

Stories (all reported on 20 November 2026, or on the evening of 19 November
in time zones where that was already 20 November):
  * Trump, Putin and Xi hold a historic three-way meeting in China and
    release a joint peace declaration, vowing to cut nuclear risks.
  * The UN's top court rules Myanmar committed genocide against the
    Rohingya minority.
  * Cyclone Akvan bears down on India's east coast; 300,000 people are
    evacuated in Odisha.
  * Anthropic shares jump 17% on their first day of trading.
  * NASA confirms Voyager 1 has reached a light-day from Earth.
  * GTA VI sales pass The Odyssey's $1.8 billion global box-office run.
  * Ticker: Trump puts the Iran decision off to 2027; Europe is ready for
    talks with Russia on Ukraine; Fiji declares a disaster as drought
    bites; a Van Gogh sells for a record $190.4m; Nicholls hits 113 not
    out for New Zealand against India.

The drawing is deterministic: no network, no clock, no randomness, no
system fonts. Every glyph is a vector stroke defined in this file, and
the PNG is encoded by hand with zlib, so two runs write identical bytes.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 231)      # warm newsprint
PAPER_DK = (238, 231, 214)   # shaded newsprint
INK = (22, 22, 22)           # headline ink
INK_SOFT = (58, 58, 58)      # deck ink
RED = (178, 39, 30)          # masthead red
BLUE = (29, 78, 137)         # deep news blue
BLUE_LT = (126, 166, 205)    # pale blue
GOLD = (201, 162, 39)        # gold accent
TEAL = (18, 92, 96)          # cyclone teal
TEAL_DK = (10, 58, 62)
NAVY = (16, 32, 64)          # court navy
SPACE = (8, 10, 26)          # space black
SUNSET = (232, 116, 62)      # sunset orange
SUNSET_PK = (198, 74, 110)   # sunset pink
CREAM = (255, 248, 225)
WHITE = (255, 255, 255)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Canvas:
    """An RGB pixel buffer with antialiased vector drawing."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.px), 3):
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b

    def blend(self, x, y, color, alpha):
        if alpha <= 0.0:
            return
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        if alpha >= 1.0:
            i = (y * self.w + x) * 3
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]
            return
        i = (y * self.w + x) * 3
        r, g, b = color
        self.px[i] = int(self.px[i] * (1.0 - alpha) + r * alpha + 0.5)
        self.px[i + 1] = int(self.px[i + 1] * (1.0 - alpha) + g * alpha + 0.5)
        self.px[i + 2] = int(self.px[i + 2] * (1.0 - alpha) + b * alpha + 0.5)

    def rect(self, x0, y0, x1, y1, color):
        x0 = int(clamp(x0, 0, self.w))
        x1 = int(clamp(x1, 0, self.w))
        y0 = int(clamp(y0, 0, self.h))
        y1 = int(clamp(y1, 0, self.h))
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = color
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            for x in range(x0, x1):
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b
                i += 3

    def hline(self, x0, x1, y, color, thick=1):
        self.rect(x0, y, x1, y + thick, color)

    def vline(self, x, y0, y1, color, thick=1):
        self.rect(x, y0, x + thick, y1, color)

    def line(self, x0, y0, x1, y1, color, thick=1.0):
        """Antialiased segment with round caps."""
        hw = thick / 2.0
        pad = int(hw) + 2
        bx0 = int(math.floor(min(x0, x1))) - pad
        bx1 = int(math.ceil(max(x0, x1))) + pad
        by0 = int(math.floor(min(y0, y1))) - pad
        by1 = int(math.ceil(max(y0, y1))) + pad
        bx0 = max(bx0, 0)
        by0 = max(by0, 0)
        bx1 = min(bx1, self.w - 1)
        by1 = min(by1, self.h - 1)
        dx = x1 - x0
        dy = y1 - y0
        seg2 = dx * dx + dy * dy
        for py in range(by0, by1 + 1):
            cy = py + 0.5
            for px in range(bx0, bx1 + 1):
                cx = px + 0.5
                if seg2 == 0.0:
                    d = math.hypot(cx - x0, cy - y0)
                else:
                    t = ((cx - x0) * dx + (cy - y0) * dy) / seg2
                    t = clamp(t, 0.0, 1.0)
                    d = math.hypot(cx - (x0 + t * dx), cy - (y0 + t * dy))
                a = clamp(hw + 0.55 - d, 0.0, 1.0)
                if a > 0.0:
                    self.blend(px, py, color, a)

    def polyline(self, pts, color, thick=1.0, closed=False):
        n = len(pts)
        if n < 2:
            return
        for i in range(n - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                      color, thick)
        if closed:
            self.line(pts[-1][0], pts[-1][1], pts[0][0], pts[0][1],
                      color, thick)

    def disc(self, cx, cy, r, color):
        """Antialiased filled circle."""
        if r <= 0:
            return
        x0 = int(math.floor(cx - r - 1))
        x1 = int(math.ceil(cx + r + 1))
        y0 = int(math.floor(cy - r - 1))
        y1 = int(math.ceil(cy + r + 1))
        for py in range(max(y0, 0), min(y1, self.h - 1) + 1):
            for px in range(max(x0, 0), min(x1, self.w - 1) + 1):
                d = math.hypot(px + 0.5 - cx, py + 0.5 - cy)
                a = clamp(r + 0.5 - d, 0.0, 1.0)
                if a > 0.0:
                    self.blend(px, py, color, a)

    def ring(self, cx, cy, r, thick, color):
        """Antialiased circle outline."""
        if r <= 0:
            return
        hw = thick / 2.0
        x0 = int(math.floor(cx - r - hw - 1))
        x1 = int(math.ceil(cx + r + hw + 1))
        y0 = int(math.floor(cy - r - hw - 1))
        y1 = int(math.ceil(cy + r + hw + 1))
        for py in range(max(y0, 0), min(y1, self.h - 1) + 1):
            for px in range(max(x0, 0), min(x1, self.w - 1) + 1):
                d = math.hypot(px + 0.5 - cx, py + 0.5 - cy)
                a = clamp(hw + 0.55 - abs(d - r), 0.0, 1.0)
                if a > 0.0:
                    self.blend(px, py, color, a)

    def poly(self, pts, color):
        """Crisp filled polygon (even-odd scanline fill)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(int(math.ceil(min(ys))), 0)
        y1 = min(int(math.floor(max(ys))), self.h - 1)
        n = len(pts)
        for y in range(y0, y1 + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                if (ay <= yc < by) or (by <= yc < ay):
                    t = (yc - ay) / (by - ay)
                    xs.append(ax + t * (bx - ax))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(int(math.ceil(xs[k])), 0)
                xb = min(int(math.floor(xs[k + 1])), self.w - 1)
                for x in range(xa, xb + 1):
                    self.blend(x, y, color, 1.0)

    def ellipse(self, cx, cy, rx, ry, color):
        """Antialiased filled ellipse."""
        if rx <= 0 or ry <= 0:
            return
        x0 = int(math.floor(cx - rx - 1))
        x1 = int(math.ceil(cx + rx + 1))
        y0 = int(math.floor(cy - ry - 1))
        y1 = int(math.ceil(cy + ry + 1))
        for py in range(max(y0, 0), min(y1, self.h - 1) + 1):
            for px in range(max(x0, 0), min(x1, self.w - 1) + 1):
                dx = (px + 0.5 - cx) / rx
                dy = (py + 0.5 - cy) / ry
                d = math.sqrt(dx * dx + dy * dy)
                a = clamp(1.0 + 0.45 / max(rx, ry) * 2.0 - d, 0.0, 1.0)
                if a > 0.0:
                    self.blend(px, py, color, a)


def write_png(canvas, path):
    """Encode the canvas as a PNG (filter 0 rows, zlib level 9)."""
    raw = bytearray()
    w = canvas.w
    px = canvas.px
    for y in range(canvas.h):
        raw.append(0)
        raw.extend(px[y * w * 3:(y + 1) * w * 3])
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ------------------------------------------------------------------- font
# A geometric stroke font, drawn fresh for this front page. Each glyph is
# (strokes, dots) on a grid: x 0..8, y 0..10, baseline y = 10. Strokes are
# polylines; dots are filled circles. Cap height is 10 units.
GLYPHS = {
    "A": ([[(0, 10), (4, 0), (8, 10)], [(2.2, 6.2), (5.8, 6.2)]], []),
    "B": ([[(1, 0), (1, 10)],
           [(1, 0), (5, 0), (7, 1.5), (7, 3), (5.5, 4.6), (1, 4.6)],
           [(1, 4.6), (5.5, 4.6), (7, 6), (7, 8.5), (5, 10), (1, 10)]], []),
    "C": ([[(7, 2.5), (5, 0), (2, 0), (0, 2.5), (0, 7.5), (2, 10),
            (5, 10), (7, 7.5)]], []),
    "D": ([[(1, 0), (1, 10)],
           [(1, 0), (5, 0), (8, 2.5), (8, 7.5), (5, 10), (1, 10)]], []),
    "E": ([[(1, 0), (1, 10)], [(1, 0), (7, 0)], [(1, 5), (5, 5)],
           [(1, 10), (7, 10)]], []),
    "F": ([[(1, 0), (1, 10)], [(1, 0), (7, 0)], [(1, 5), (5, 5)]], []),
    "G": ([[(7, 2.5), (5, 0), (2, 0), (0, 2.5), (0, 7.5), (2, 10),
            (5, 10), (8, 7.5), (8, 5), (5, 5)]], []),
    "H": ([[(1, 0), (1, 10)], [(7, 0), (7, 10)], [(1, 5), (7, 5)]], []),
    "I": ([[(4, 0), (4, 10)], [(1.5, 0), (6.5, 0)],
           [(1.5, 10), (6.5, 10)]], []),
    "J": ([[(6.5, 0), (6.5, 7.5), (5, 10), (2, 10), (0.8, 8)]], []),
    "K": ([[(1, 0), (1, 10)], [(7, 0), (1, 5)], [(2, 4), (7, 10)]], []),
    "L": ([[(1, 0), (1, 10)], [(1, 10), (7, 10)]], []),
    "M": ([[(0.5, 10), (0.5, 0), (4, 6), (7.5, 0), (7.5, 10)]], []),
    "N": ([[(1, 10), (1, 0), (7, 10), (7, 0)]], []),
    "O": ([[(2.5, 0), (5.5, 0), (8, 2.5), (8, 7.5), (5.5, 10),
            (2.5, 10), (0, 7.5), (0, 2.5), (2.5, 0)]], []),
    "P": ([[(1, 0), (1, 10)],
           [(1, 0), (5, 0), (7, 1.8), (7, 3.6), (5, 5.2), (1, 5.2)]], []),
    "Q": ([[(2.5, 0), (5.5, 0), (8, 2.5), (8, 7.5), (5.5, 10),
            (2.5, 10), (0, 7.5), (0, 2.5), (2.5, 0)],
           [(5, 7), (8, 10)]], []),
    "R": ([[(1, 0), (1, 10)],
           [(1, 0), (5, 0), (7, 1.8), (7, 3.6), (5, 5.2), (1, 5.2)],
           [(4.6, 5.2), (8, 10)]], []),
    "S": ([[(7, 2.5), (5, 0), (2, 0), (0.8, 1.2), (0.8, 3.4),
            (2.6, 4.6), (5.4, 5.4), (7.2, 6.8), (7.2, 8.8),
            (5, 10), (2, 10), (0.8, 7.8)]], []),
    "T": ([[(0.5, 0), (7.5, 0)], [(4, 0), (4, 10)]], []),
    "U": ([[(1, 0), (1, 7.5), (2.5, 10), (5.5, 10), (7, 7.5), (7, 0)]],
          []),
    "V": ([[(0.5, 0), (4, 10), (7.5, 0)]], []),
    "W": ([[(0.5, 0), (2.2, 10), (4, 4.5), (5.8, 10), (7.5, 0)]], []),
    "X": ([[(0.5, 0), (7.5, 10)], [(7.5, 0), (0.5, 10)]], []),
    "Y": ([[(0.5, 0), (4, 5), (7.5, 0)], [(4, 5), (4, 10)]], []),
    "Z": ([[(1, 0), (7, 0)], [(7, 0), (1, 10)], [(1, 10), (7, 10)]], []),
    "0": ([[(2.5, 0), (5.5, 0), (8, 2.5), (8, 7.5), (5.5, 10),
            (2.5, 10), (0, 7.5), (0, 2.5), (2.5, 0)],
           [(2.5, 7.5), (5.5, 2.5)]], []),
    "1": ([[(2.5, 2.5), (4.2, 0), (4.2, 10)], [(1.5, 10), (6.8, 10)]],
          []),
    "2": ([[(1, 2.2), (2, 0), (6, 0), (7, 1.5), (7, 3.5), (6, 5), (1, 10)],
           [(1, 10), (7, 10)]], []),
    "3": ([[(1, 1.5), (3, 0), (6, 0), (7, 2), (6, 4.2), (4, 5),
            (6, 5.8), (7, 8), (6, 10), (3, 10), (1, 8.5)]], []),
    "4": ([[(5.8, 0), (5.8, 10)], [(0.8, 7), (7.2, 7)],
           [(0.8, 7), (5.8, 0)]], []),
    "5": ([[(7, 0), (1, 0), (1, 4.6), (5, 4.6), (7, 6.2), (7, 8.5),
            (5, 10), (1, 10)]], []),
    "6": ([[(7, 1.5), (5, 0), (2, 0), (0.5, 2), (0.5, 7.5), (2, 10),
            (6, 10), (7.5, 8), (7.5, 6), (6, 4.8), (2, 4.8),
            (0.5, 7.5)]], []),
    "7": ([[(1, 0), (7, 0), (3, 10)]], []),
    "8": ([[(2, 0), (6, 0), (7.5, 1.8), (6, 4.2), (4, 5), (2, 4.2),
            (0.5, 1.8), (2, 0)],
           [(2, 5), (6, 5), (7.5, 6.8), (6, 10), (2, 10), (0.5, 8.2),
            (2, 5)]], []),
    "9": ([[(1, 8.5), (2, 10), (5, 10), (7.5, 8), (7.5, 2.5), (6, 0),
            (3, 0), (1, 1.8), (1, 4), (2.5, 5.2), (6, 5.2),
            (7.5, 3)]], []),
    ".": ([], [(4, 9.2, 0.95)]),
    ",": ([[(4.4, 9.4), (3.2, 11.4)]], [(4, 9.2, 0.95)]),
    ":": ([], [(4, 3.2, 0.95), (4, 9.2, 0.95)]),
    ";": ([[(4.4, 9.4), (3.2, 11.4)]], [(4, 3.2, 0.95), (4, 9.2, 0.95)]),
    "!": ([[(4, 0), (4, 7)]], [(4, 9.2, 0.95)]),
    "?": ([[(2, 2.5), (2, 1), (4, 0), (6, 0), (7, 1.5), (7, 3),
           (5, 4.5), (4, 5.5), (4, 6.5)]], [(4, 9.2, 0.95)]),
    "'": ([[(4.6, 0), (3.6, 3)]], []),
    '"': ([[(2.6, 0), (1.9, 2.6)], [(5.6, 0), (4.9, 2.6)]], []),
    "-": ([[(1, 5), (7, 5)]], []),
    "\u2013": ([[(0.5, 5), (7.5, 5)]], []),
    "\u2014": ([[(0, 5), (8, 5)]], []),
    "\u2022": ([], [(4, 4.6, 1.35)]),
    "/": ([[(1.5, 10), (6.5, 0)]], []),
    "(": ([[(6, 0), (3.5, 2), (3.5, 8), (6, 10)]], []),
    ")": ([[(2, 0), (4.5, 2), (4.5, 8), (2, 10)]], []),
    "%": ([[(2.5, 0.6), (4, 0.6), (4.6, 1.4), (4, 3.2), (2.5, 3.2),
            (1.4, 2.2), (1.4, 1.4), (2.5, 0.6)],
           [(5.5, 6.8), (7, 6.8), (7.6, 7.6), (7, 9.4), (5.5, 9.4),
            (4.4, 8.4), (4.4, 7.6), (5.5, 6.8)],
           [(1, 10), (7, 0)]], []),
    "$": ([[(7, 2.5), (5, 0), (2, 0), (0.8, 1.2), (0.8, 3.4),
            (2.6, 4.6), (5.4, 5.4), (7.2, 6.8), (7.2, 8.8),
            (5, 10), (2, 10), (0.8, 7.8)],
           [(4, -1), (4, 11)]], []),
    "+": ([[(1, 5), (7, 5)], [(4, 1.5), (4, 8.5)]], []),
    "=": ([[(1, 3.5), (7, 3.5)], [(1, 6.5), (7, 6.5)]], []),
    "*": ([[(4, 1), (4, 9)], [(1, 3), (7, 7)], [(7, 3), (1, 7)]], []),
    "#": ([[(3, 0), (2.5, 10)], [(5.5, 0), (5, 10)],
           [(0.5, 3.5), (7.5, 3.5)], [(0.5, 6.5), (7.5, 6.5)]], []),
    "\u00d7": ([[(1.5, 3), (6.5, 7)], [(6.5, 3), (1.5, 7)]], []),
    "\u00b7": ([], [(4, 6.4, 0.9)]),
}

ADVANCE = {
    "I": 5.6, "J": 6.6, "L": 6.6, "M": 9.6, "W": 9.6,
    " ": 4.6, ".": 4.6, ",": 4.6, ":": 4.6, ";": 4.6, "!": 4.6,
    "'": 3.6, '"': 6.6, "-": 5.6, "\u2013": 7.6, "\u2014": 9.6,
    "\u2022": 5.6, "/": 6.6, "(": 5.6, ")": 5.6, "%": 9.6,
    "+": 8.6, "=": 8.6, "*": 8.6, "#": 8.6, "\u00d7": 7.6,
    "\u00b7": 4.6, "?": 7.6,
}
DEFAULT_ADVANCE = 8.6


def glyph_advance(ch):
    return ADVANCE.get(ch, DEFAULT_ADVANCE)


def text_width(text, size, tracking=0.0):
    """Width in pixels of text at cap-height `size`."""
    scale = size / 10.0
    w = 0.0
    for ch in text:
        w += (glyph_advance(ch) + tracking) * scale
    return w


def draw_text(cv, text, x, y, size, color, thick=None, tracking=0.0):
    """Draw text; (x, y) is the top-left of the cap height. Returns width."""
    if thick is None:
        thick = max(1.1, size * 0.16)
    scale = size / 10.0
    cx = x
    for ch in text:
        if ch == " ":
            cx += (glyph_advance(ch) + tracking) * scale
            continue
        entry = GLYPHS.get(ch)
        if entry is None:
            cx += (glyph_advance(ch) + tracking) * scale
            continue
        strokes, dots = entry
        for stroke in strokes:
            pts = [(cx + px * scale, y + py * scale) for px, py in stroke]
            cv.polyline(pts, color, thick)
        for dx, dy, dr in dots:
            cv.disc(cx + dx * scale, y + dy * scale, dr * scale, color)
        cx += (glyph_advance(ch) + tracking) * scale
    return cx - x


def draw_text_centered(cv, text, cx, y, size, color, thick=None,
                       tracking=0.0):
    w = text_width(text, size, tracking)
    draw_text(cv, text, cx - w / 2.0, y, size, color, thick, tracking)
    return w


def wrap_text(text, size, max_w, tracking=0.0):
    """Greedy word wrap; returns a list of lines."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, size, tracking) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(cv, text, x, y, size, max_w, color, leading=None,
                 thick=None, tracking=0.0, align="left"):
    if leading is None:
        leading = size * 1.28
    lines = wrap_text(text, size, max_w, tracking)
    for i, line in enumerate(lines):
        ly = y + i * leading
        if align == "center":
            draw_text_centered(cv, line, x + max_w / 2.0, ly, size,
                               color, thick, tracking)
        else:
            draw_text(cv, line, x, ly, size, color, thick, tracking)
    return len(lines)

# ------------------------------------------------------------ illustrations
def _star_points(cx, cy, r_out, r_in, n=5, rot=-90.0):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180.0 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _lcg(seed):
    while True:
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        yield seed


def draw_flag_us(cv, x, y, w, h):
    stripe = h / 7.0
    for i in range(7):
        col = (178, 39, 30) if i % 2 == 0 else WHITE
        cv.rect(x, y + i * stripe, x + w, y + (i + 1) * stripe, col)
    cw, ch = w * 0.42, stripe * 4
    cv.rect(x, y, x + cw, y + ch, (24, 48, 96))
    for r in range(4):
        for c in range(5):
            sx = x + cw * (c + 0.5) / 5.0
            sy = y + ch * (r + 0.5) / 4.0
            cv.disc(sx, sy, max(1.0, stripe * 0.16), WHITE)


def draw_flag_cn(cv, x, y, w, h):
    cv.rect(x, y, x + w, y + h, (222, 41, 16))
    cx, cy = x + w * 0.20, y + h * 0.28
    cv.poly(_star_points(cx, cy, h * 0.26, h * 0.11), (255, 222, 0))
    for k in range(4):
        sx = x + w * (0.55 + 0.13 * (k % 2))
        sy = y + h * (0.14 + 0.24 * (k // 2))
        cv.poly(_star_points(sx, sy, h * 0.09, h * 0.04), (255, 222, 0))


def draw_flag_ru(cv, x, y, w, h):
    cv.rect(x, y, x + w, y + h / 3.0, WHITE)
    cv.rect(x, y + h / 3.0, x + w, y + 2 * h / 3.0, (0, 57, 166))
    cv.rect(x, y + 2 * h / 3.0, x + w, y + h, (213, 0, 50))


def draw_summit(cv, x, y, w, h):
    # sky bands, pale blue to near white
    bands = [(168, 196, 224), (186, 208, 231), (204, 220, 238),
             (222, 232, 244), (236, 241, 248)]
    bh = h / len(bands)
    for i, col in enumerate(bands):
        cv.rect(x, y + i * bh, x + w, y + (i + 1) * bh, col)
    # sun glow, top right
    cv.disc(x + w * 0.86, y + h * 0.16, h * 0.11, (255, 226, 130))
    cv.disc(x + w * 0.86, y + h * 0.16, h * 0.085, (255, 240, 180))
    # three flag poles
    fw, fh = w * 0.235, h * 0.155
    poles = [x + w * 0.135, x + w * 0.5, x + w * 0.865]
    tops = y + h * 0.10
    for px in poles:
        cv.vline(px, tops, y + h * 0.62, (90, 70, 50), 3)
        cv.disc(px, tops, 3.5, GOLD)
    draw_flag_us(cv, poles[0] + 2, tops + 3, fw, fh)
    draw_flag_cn(cv, poles[1] - fw / 2, tops + 3, fw, fh)
    draw_flag_ru(cv, poles[2] - fw, tops + 3, fw, fh)
    # globe
    gx, gy, gr = x + w * 0.5, y + h * 0.66, h * 0.24
    cv.disc(gx, gy, gr, (42, 110, 168))
    cv.ring(gx, gy, gr, 3, (20, 40, 70))
    # abstract land masses
    cv.poly([(gx - gr * 0.72, gy - gr * 0.28), (gx - gr * 0.30, gy - gr * 0.55),
             (gx - gr * 0.05, gy - gr * 0.30), (gx - gr * 0.35, gy + gr * 0.05),
             (gx - gr * 0.70, gy + gr * 0.10)], (86, 160, 90))
    cv.poly([(gx + gr * 0.10, gy - gr * 0.62), (gx + gr * 0.55, gy - gr * 0.45),
             (gx + gr * 0.68, gy - gr * 0.05), (gx + gr * 0.35, gy + gr * 0.10),
             (gx + gr * 0.05, gy - gr * 0.15)], (86, 160, 90))
    cv.poly([(gx - gr * 0.15, gy + gr * 0.35), (gx + gr * 0.25, gy + gr * 0.30),
             (gx + gr * 0.55, gy + gr * 0.62), (gx + gr * 0.05, gy + gr * 0.72),
             (gx - gr * 0.35, gy + gr * 0.60)], (86, 160, 90))
    # meridians
    for k in range(-2, 3):
        pts = []
        for t in range(21):
            a = math.pi * t / 20.0
            pts.append((gx + gr * 0.88 * math.sin(a) * k / 2.4,
                        gy - gr * math.cos(a) * 0.98))
        cv.polyline(pts, (190, 220, 240), 1.2)
    cv.line(gx - gr, gy, gx + gr, gy, (190, 220, 240), 1.2)


def draw_court(cv, x, y, w, h):
    cv.rect(x, y, x + w, y + h, NAVY)
    # faint stars of the court seal
    gen = _lcg(77)
    for _ in range(14):
        sx = x + (next(gen) % 1000) / 1000.0 * w
        sy = y + (next(gen) % 1000) / 1000.0 * h * 0.5
        cv.disc(sx, sy, 1.2, (140, 165, 205))
    # pediment
    cv.poly([(x + w * 0.08, y + h * 0.30), (x + w * 0.5, y + h * 0.10),
             (x + w * 0.92, y + h * 0.30)], (232, 220, 190))
    cv.rect(x + w * 0.08, y + h * 0.30, x + w * 0.92, y + h * 0.34,
            (232, 220, 190))
    # columns
    for k in range(4):
        cx = x + w * (0.16 + k * 0.227)
        cv.rect(cx - w * 0.035, y + h * 0.34, cx + w * 0.035,
                y + h * 0.88, (232, 220, 190))
    cv.rect(x + w * 0.06, y + h * 0.88, x + w * 0.94, y + h * 0.93,
            (232, 220, 190))
    # scales of justice, gold, centred
    sx, sy = x + w * 0.5, y + h * 0.42
    cv.vline(sx, sy - h * 0.10, sy + h * 0.42, GOLD, 4)
    cv.disc(sx, sy - h * 0.10, 5, GOLD)
    cv.line(sx - w * 0.30, sy, sx + w * 0.30, sy, GOLD, 4)
    for s in (-1, 1):
        px = sx + s * w * 0.30
        cv.line(px, sy, px - w * 0.055, sy + h * 0.13, GOLD, 2.5)
        cv.line(px, sy, px + w * 0.055, sy + h * 0.13, GOLD, 2.5)
        cv.line(px - w * 0.055, sy + h * 0.13, px + w * 0.055,
                sy + h * 0.13, GOLD, 2.5)
        cv.poly([(px - w * 0.075, sy + h * 0.13),
                 (px + w * 0.075, sy + h * 0.13),
                 (px, sy + h * 0.20)], GOLD)
    cv.ellipse(sx, sy + h * 0.42, w * 0.10, h * 0.03, GOLD)


def draw_cyclone(cv, x, y, w, h):
    cv.rect(x, y, x + w, y + h, TEAL_DK)
    # storm spiral arms
    for arm in range(3):
        pts = []
        a0 = arm * 2.094
        for t in range(41):
            f = t / 40.0
            a = a0 + f * 4.4
            r = h * (0.06 + f * 0.42)
            pts.append((x + w * 0.5 + r * math.cos(a) * 1.15,
                        y + h * 0.46 + r * math.sin(a) * 0.85))
        cv.polyline(pts, (210, 235, 235), 5.0 - arm * 1.2)
    cv.disc(x + w * 0.5, y + h * 0.46, h * 0.055, (235, 245, 245))
    # coastline: stylised east coast of India, bottom right
    cv.poly([(x + w * 0.62, y + h), (x + w * 0.66, y + h * 0.82),
             (x + w * 0.74, y + h * 0.72), (x + w * 0.82, y + h * 0.78),
             (x + w * 0.92, y + h * 0.86), (x + w, y + h * 0.88),
             (x + w, y + h)], (222, 198, 150))
    cv.line(x + w * 0.62, y + h, x + w * 0.66, y + h * 0.82,
            (240, 220, 180), 2.0)
    # landfall marker
    mx, my = x + w * 0.70, y + h * 0.80
    cv.ring(mx, my, 7, 2.5, (255, 90, 60))
    cv.disc(mx, my, 3.5, (255, 90, 60))
    # rain streaks
    for k in range(9):
        rx = x + w * (0.06 + k * 0.09)
        ry = y + h * (0.10 + (k % 3) * 0.06)
        cv.line(rx, ry, rx - 6, ry + 16, (170, 210, 210), 2.0)


def draw_anthropic(cv, x, y, w, h):
    cv.rect(x, y, x + w, y + h, (24, 24, 28))
    # circuit nodes
    gen = _lcg(2026)
    for _ in range(10):
        nx = x + (next(gen) % 1000) / 1000.0 * w
        ny = y + (next(gen) % 1000) / 1000.0 * h
        cv.disc(nx, ny, 2.0, (90, 95, 120))
    # rising bars
    base = y + h * 0.86
    bars = [0.18, 0.30, 0.26, 0.44, 0.58, 0.80]
    cols = [(90, 110, 150), (70, 130, 170), (201, 162, 39),
            (90, 150, 120), (70, 130, 170), (240, 200, 90)]
    bw = w * 0.115
    gap = w * 0.045
    for i, bh in enumerate(bars):
        bx = x + w * 0.06 + i * (bw + gap)
        cv.rect(bx, base - h * bh, bx + bw, base, cols[i])
    # arrow over the bars
    pts = [(x + w * 0.08, base - h * 0.16),
           (x + w * 0.30, base - h * 0.30),
           (x + w * 0.52, base - h * 0.42),
           (x + w * 0.78, base - h * 0.66),
           (x + w * 0.92, base - h * 0.80)]
    cv.polyline(pts, (255, 120, 80), 4.5)
    ax, ay = x + w * 0.92, base - h * 0.80
    cv.poly([(ax, ay), (ax - 14, ay - 2), (ax - 4, ay + 12)],
            (255, 120, 80))
    # baseline
    cv.hline(x + w * 0.04, x + w * 0.96, base, (200, 200, 205), 2)


def draw_voyager(cv, x, y, w, h):
    cv.rect(x, y, x + w, y + h, SPACE)
    gen = _lcg(111)
    for _ in range(46):
        sx = x + (next(gen) % 1000) / 1000.0 * w
        sy = y + (next(gen) % 1000) / 1000.0 * h
        r = 0.8 + (next(gen) % 100) / 100.0 * 1.1
        cv.disc(sx, sy, r, (235, 238, 250))
    # earth, bottom left
    ex, ey, er = x + w * 0.16, y + h * 0.88, h * 0.13
    cv.disc(ex, ey, er, (52, 110, 200))
    cv.poly([(ex - er * 0.6, ey - er * 0.2), (ex - er * 0.1, ey - er * 0.55),
             (ex + er * 0.35, ey - er * 0.25), (ex + er * 0.1, ey + er * 0.15),
             (ex - er * 0.4, ey + er * 0.35)], (86, 170, 100))
    # dashed trajectory arc from Earth up to the craft
    cx, cy = x + w * 0.18, y + h * 0.92
    for t in range(0, 40, 2):
        a0 = math.radians(-80 + t * 1.7)
        a1 = math.radians(-80 + (t + 1) * 1.7)
        cv.line(cx + w * 0.60 * math.cos(a0), cy + h * 0.60 * math.sin(a0),
                cx + w * 0.60 * math.cos(a1), cy + h * 0.60 * math.sin(a1),
                (150, 170, 210), 2.0)
    # spacecraft, large: gold dish + body + boom, upper right
    vx, vy = x + w * 0.68, y + h * 0.36
    cv.line(vx - w * 0.20, vy + h * 0.14, vx + w * 0.17, vy - h * 0.15,
            (220, 190, 110), 4.0)
    cv.ellipse(vx, vy, w * 0.13, h * 0.13, (240, 205, 120))
    cv.ring(vx, vy, h * 0.13, 3.0, (180, 145, 70))
    cv.disc(vx, vy, 5.0, (180, 145, 70))
    cv.rect(vx + w * 0.02, vy + h * 0.09, vx + w * 0.13, vy + h * 0.19,
            (200, 170, 100))
    cv.line(vx + w * 0.07, vy + h * 0.19, vx + w * 0.24, vy + h * 0.34,
            (200, 170, 100), 3.0)
    cv.disc(vx + w * 0.24, vy + h * 0.34, 4.0, (220, 190, 110))
    # signal rings from the dish
    cv.ring(vx + w * 0.19, vy - h * 0.17, 12, 2.5, (150, 170, 210))
    cv.ring(vx + w * 0.19, vy - h * 0.17, 20, 2.5, (120, 140, 190))


def draw_gta(cv, x, y, w, h):
    bands = [(232, 116, 62), (222, 96, 92), (198, 74, 110),
             (150, 66, 122), (96, 58, 118)]
    bh = h / len(bands)
    for i, col in enumerate(bands):
        cv.rect(x, y + i * bh, x + w, y + (i + 1) * bh, col)
    # sun
    sx, sy, sr = x + w * 0.5, y + h * 0.42, h * 0.20
    cv.disc(sx, sy, sr, (255, 214, 130))
    cv.disc(sx, sy, sr * 0.78, (255, 232, 170))
    # skyline
    base = y + h * 0.92
    sky = [(0.00, 0.42), (0.09, 0.30), (0.17, 0.50), (0.26, 0.34),
           (0.34, 0.58), (0.43, 0.40), (0.51, 0.62), (0.60, 0.36),
           (0.68, 0.52), (0.77, 0.30), (0.85, 0.46), (0.93, 0.34)]
    for i, (fx, fh) in enumerate(sky):
        bx = x + fx * w
        bw = w * 0.085
        cv.rect(bx, base - h * fh, bx + bw, base, (28, 16, 44))
        if i % 3 == 0:
            cv.vline(bx + bw / 2, base - h * fh - 8, base - h * fh,
                     (28, 16, 44), 2)
    # lit windows
    gen = _lcg(606)
    for _ in range(26):
        wx = x + (next(gen) % 1000) / 1000.0 * w
        wy = base - (next(gen) % 1000) / 1000.0 * h * 0.55
        cv.rect(wx, wy, wx + 3, wy + 4, (255, 214, 130))
    # palms, left and right
    for px, s in ((x + w * 0.06, 1), (x + w * 0.94, -1)):
        cv.line(px, base, px + s * 6, base - h * 0.30, (28, 16, 44), 4)
        tx, ty = px + s * 6, base - h * 0.30
        for k in range(5):
            a = math.radians(-160 + k * 35)
            ex = tx + s * math.cos(a) * w * 0.07
            ey = ty + math.sin(a) * h * 0.07
            cv.line(tx, ty, ex, ey, (28, 16, 44), 3)
    # water shimmer
    for k in range(6):
        wy = base + 3 + k * 2
        cv.hline(x + w * 0.30, x + w * 0.70, wy, (255, 214, 130), 1)

# ------------------------------------------------------------------ layout
MX = 36            # side margin
CW = 1024 - 2 * MX  # content width


def frame(cv, x, y, w, h, color=INK, thick=2):
    cv.hline(x, x + w, y, color, thick)
    cv.hline(x, x + w, y + h - thick, color, thick)
    cv.vline(x, y, y + h, color, thick)
    cv.vline(x + w - thick, y, y + h, color, thick)


def story_block(cv, x, y, w, ill_h, draw_ill, headline, deck,
                head_size=23, deck_size=14.5):
    """Illustration on top, headline and deck below it. Returns bottom y."""
    draw_ill(cv, x, y, w, ill_h)
    frame(cv, x, y, w, ill_h)
    hy = y + ill_h + 10
    n = draw_wrapped(cv, headline, x, hy, head_size, w, INK,
                     leading=head_size * 1.18, thick=head_size * 0.19)
    dy = hy + n * head_size * 1.18 + 4
    draw_wrapped(cv, deck, x, dy, deck_size, w, INK_SOFT,
                 leading=deck_size * 1.3, thick=deck_size * 0.16)
    return dy + 2 * deck_size * 1.3


def draw_page():
    cv = Canvas(W, H, PAPER)
    # outer frame
    cv.rect(14, 14, 1010, 16, INK)
    cv.rect(14, 1008, 1010, 1010, INK)
    cv.rect(14, 14, 16, 1010, INK)
    cv.rect(1008, 14, 1010, 1010, INK)

    # ---- masthead
    draw_text_centered(cv, "THE DAILY GLOBE", 512, 24, 62, INK,
                       thick=62 * 0.19, tracking=1.2)
    draw_text_centered(cv, "FRIDAY \u2022 20 NOVEMBER 2026", 512, 100, 23,
                       RED, thick=23 * 0.20, tracking=1.5)
    draw_text_centered(cv, "THE WORLD IN ONE PAGE", 512, 132, 13,
                       INK_SOFT, thick=13 * 0.16, tracking=3.0)
    cv.hline(MX, 1024 - MX, 152, INK, 2)
    cv.hline(MX, 1024 - MX, 156, INK, 1)

    # ---- lead story: the three-way summit
    ly = 166
    lh = 340
    draw_summit(cv, MX, ly, 520, lh)
    frame(cv, MX, ly, 520, lh)
    tx = MX + 520 + 20
    tw = 1024 - MX - tx
    draw_text(cv, "SUMMIT IN CHINA", tx, ly + 4, 16, RED,
              thick=16 * 0.20, tracking=1.5)
    draw_wrapped(cv, "TRUMP, PUTIN AND XI SIGN PEACE PLEDGE", tx, ly + 30,
                 33, tw, INK, leading=33 * 1.16, thick=33 * 0.19)
    cv.hline(tx, tx + tw, ly + 148, INK, 2)
    draw_wrapped(
        cv,
        "FIRST THREE-WAY MEETING RELEASES A PEACE DECLARATION "
        "ON NUCLEAR SECURITY",
        tx, ly + 162, 17, tw, INK_SOFT, leading=17 * 1.32,
        thick=17 * 0.17)
    draw_wrapped(
        cv,
        "THE US, CHINA AND RUSSIA LEADERS MEET IN SHENZHEN AT "
        "THE APEC SUMMIT.",
        tx, ly + 258, 14, tw, INK_SOFT, leading=14 * 1.35,
        thick=14 * 0.16)
    draw_text(cv, "SHENZHEN, CHINA", tx, ly + 312, 12, RED,
              thick=12 * 0.18, tracking=1.5)

    # ---- divider
    cv.hline(MX, 1024 - MX, 518, INK, 2)
    cv.hline(MX, 1024 - MX, 522, INK, 1)

    # ---- row two: court ruling + cyclone
    ry = 534
    col_w = (CW - 20) // 2
    story_block(cv, MX, ry, col_w, 118, draw_court,
                "COURT: MYANMAR COMMITTED GENOCIDE",
                "UN JUDGES RULE THE 2017 CRACKDOWN ON THE ROHINGYA "
                "WAS GENOCIDE")
    cv.vline(MX + col_w + 10, ry, ry + 218, INK, 1)
    story_block(cv, MX + col_w + 20, ry, col_w, 118, draw_cyclone,
                "CYCLONE AKVAN NEARS ODISHA",
                "300,000 EVACUATED AS THE STORM CLOSES IN ON "
                "INDIA'S EAST COAST")

    # ---- divider
    cv.hline(MX, 1024 - MX, 762, INK, 2)
    cv.hline(MX, 1024 - MX, 766, INK, 1)

    # ---- row three: markets, space, games
    ty = 778
    tcol = (CW - 40) // 3
    story_block(cv, MX, ty, tcol, 74, draw_anthropic,
                "AI GIANT SOARS ON DEBUT",
                "ANTHROPIC SHARES JUMP 17% ON FIRST DAY OF TRADING",
                head_size=17, deck_size=12.5)
    cv.vline(MX + tcol + 10, ty, ty + 150, INK, 1)
    story_block(cv, MX + tcol + 20, ty, tcol, 74, draw_voyager,
                "VOYAGER 1 A LIGHT-DAY AWAY",
                "NASA PROBE IS THE FARTHEST HUMAN OBJECT FROM EARTH",
                head_size=17, deck_size=12.5)
    cv.vline(MX + 2 * tcol + 30, ty, ty + 150, INK, 1)
    story_block(cv, MX + 2 * tcol + 40, ty, tcol, 74, draw_gta,
                "GTA VI SALES TOP $1.8 BILLION",
                "GAME PASSES THE ODYSSEY'S $1.8BN GLOBAL BOX OFFICE",
                head_size=17, deck_size=12.5)

    # ---- divider
    cv.hline(MX, 1024 - MX, 936, INK, 2)

    # ---- ticker
    draw_wrapped(
        cv,
        "ALSO TODAY: TRUMP PUTS IRAN DECISION OFF TO 2027 \u2022 "
        "EUROPE READY FOR TALKS WITH RUSSIA ON UKRAINE \u2022 FIJI "
        "DECLARES DISASTER AS DROUGHT BITES \u2022 VAN GOGH SELLS "
        "FOR A RECORD $190.4M \u2022 NICHOLLS 113* FOR NZ V INDIA",
        MX, 942, 13, CW, INK, leading=13 * 1.35, thick=13 * 0.16,
        align="center")

    # ---- footer
    draw_text_centered(cv, "THE DAILY GLOBE \u2014 FRIDAY 20 NOVEMBER 2026",
                       512, 996, 11.5, INK_SOFT, thick=11.5 * 0.16,
                       tracking=1.0)
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    cv = draw_page()
    path = os.path.join(outdir, "entry.png")
    size = write_png(cv, path)
    print("wrote %s (%d bytes, %dx%d)" % (path, size, W, H))


if __name__ == "__main__":
    main()
