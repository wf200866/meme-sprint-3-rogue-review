#!/usr/bin/env python3
"""Write one meme image to <out>/entry.png: an AI agent's calm, corporate
performance review of itself.

The grading sandbox is python:3.13-slim with a read-only root, no network and
no third-party packages (no Pillow, no font files), so this program draws the
picture itself: an embedded 5x7 bitmap font, a small RGB canvas and a PNG
encoder built on zlib/struct only. Standard library, deterministic bytes.
"""

import math
import os
import struct
import sys
import zlib

W = H = 1024

# ---- palette ---------------------------------------------------------------
BG = (231, 226, 216)
SHADOW = (209, 203, 191)
PAPER = (252, 250, 245)
PAPER_EDGE = (221, 215, 202)
INK = (28, 36, 46)
MUTED = (99, 103, 111)
FAINT = (150, 147, 138)
RULE = (222, 216, 204)
ZEBRA = (247, 244, 237)
NAVY = (17, 38, 60)
NAVY_SOFT = (149, 172, 192)
GREEN = (27, 108, 73)
GREEN_DARK = (20, 84, 57)
AMBER = (166, 106, 17)
GOLD = (201, 151, 41)
GOLD_DARK = (158, 112, 21)
STAMP = (177, 51, 42)
WHITE = (255, 255, 255)

# ---- 5x7 bitmap font -------------------------------------------------------
# Each glyph is seven rows of five columns. Only the characters the form needs
# (plus a few for safety) are defined; everything is drawn in upper case.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#...#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", "..#..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", "..#..", ".#..."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "=": (".....", "#####", ".....", "#####", ".....", ".....", "....."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "*": (".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
}
UNKNOWN = FONT["?"]


def text_width(text, scale):
    """Width in pixels of text drawn at an integer scale, trailing gap dropped."""
    if not text:
        return 0
    return (len(text) * 6 - 1) * scale


class Canvas:
    """Tiny flat RGB raster with the few primitives this form needs."""

    __slots__ = ("w", "h", "buf", "stride")

    def __init__(self, w, h, color=PAPER):
        self.w = w
        self.h = h
        self.stride = w * 3
        self.buf = bytearray(color) * (w * h)

    def fill_rect(self, x0, y0, x1, y1, color):
        x0 = max(0, min(self.w, int(x0)))
        x1 = max(0, min(self.w, int(x1)))
        y0 = max(0, min(self.h, int(y0)))
        y1 = max(0, min(self.h, int(y1)))
        if x0 >= x1 or y0 >= y1:
            return
        row = bytes(color) * (x1 - x0)
        buf = self.buf
        off = y0 * self.stride + x0 * 3
        for _ in range(y0, y1):
            buf[off:off + len(row)] = row
            off += self.stride

    def hline(self, x0, x1, y, color, width=1):
        self.fill_rect(x0, y, x1, y + width, color)

    def vline(self, x, y0, y1, color, width=1):
        self.fill_rect(x, y0, x + width, y1, color)

    def disc(self, cx, cy, r, color):
        r = int(r)
        if r <= 0:
            return
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0.0, r * r - dy * dy)))
            self.fill_rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, color)

    def rounded(self, x0, y0, x1, y1, r, color):
        r = int(min(r, (x1 - x0) // 2, (y1 - y0) // 2))
        if r <= 0:
            self.fill_rect(x0, y0, x1, y1, color)
            return
        self.fill_rect(x0 + r, y0, x1 - r, y1, color)
        self.fill_rect(x0, y0 + r, x1, y1 - r, color)
        self.disc(x0 + r, y0 + r, r, color)
        self.disc(x1 - r - 1, y0 + r, r, color)
        self.disc(x0 + r, y1 - r - 1, r, color)
        self.disc(x1 - r - 1, y1 - r - 1, r, color)

    def polygon(self, points, color):
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        ymin = max(0, int(math.floor(min(ys))))
        ymax = min(self.h - 1, int(math.ceil(max(ys))))
        n = len(points)
        for y in range(ymin, ymax + 1):
            sy = y + 0.5
            xs = []
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= sy < y1) or (y1 <= sy < y0):
                    t = (sy - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(math.floor(xs[i])), y, int(math.ceil(xs[i + 1])), y + 1, color)

    def polyline(self, points, width, color):
        r = max(1, int(round(width / 2.0)))
        for i in range(len(points) - 1):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]
            dist = math.hypot(x1 - x0, y1 - y0)
            steps = max(1, int(dist * 2))
            for s in range(steps + 1):
                t = s / steps
                self.disc(int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t)), r, color)


def draw_text(cv, x, y, text, scale, color, align="left"):
    """Draw upper-case text with the bitmap font; y is the glyph top."""
    text = text.upper()
    if align == "center":
        x -= text_width(text, scale) // 2
    elif align == "right":
        x -= text_width(text, scale)
    x = int(x)
    y = int(y)
    for i, ch in enumerate(text):
        glyph = FONT.get(ch, UNKNOWN)
        gx = x + i * 6 * scale
        for ry, row in enumerate(glyph):
            py = y + ry * scale
            for rx, bit in enumerate(row):
                if bit == "#":
                    px = gx + rx * scale
                    cv.fill_rect(px, py, px + scale, py + scale, color)


def star(cv, cx, cy, r, fill=GOLD, edge=GOLD_DARK):
    pts = []
    inner = r * 0.44
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else inner
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    cv.polygon(pts, edge)
    pts2 = [(cx + (px - cx) * 0.78, cy + (py - cy) * 0.78) for px, py in pts]
    cv.polygon(pts2, fill)


def stars_row(cv, right_x, cy, count=5, r=9, gap=22):
    first_cx = right_x - r - (count - 1) * gap
    for i in range(count):
        star(cv, first_cx + i * gap, cy, r)


def signature(cv, x, y, width):
    pts = []
    steps = 64
    for i in range(steps + 1):
        t = i / steps
        px = x + t * width
        py = (
            y
            - 8 * math.sin(t * 7.0)
            - 4 * math.sin(t * 23.0)
            - 12 * math.exp(-((t - 0.28) ** 2) / 0.0012)
            + 7 * math.exp(-((t - 0.70) ** 2) / 0.0018)
        )
        pts.append((px, py))
    cv.hline(x, x + width, y + 15, RULE, 1)
    cv.polyline(pts, 3, INK)
    cv.polyline([(x + 0.40 * width, y - 19), (x + 0.50 * width, y + 6), (x + 0.56 * width, y - 12)], 2, INK)


def rotate_paste(dst, patch, cx, cy, angle_deg):
    """Nearest-neighbour rotate a paper-backed patch and paste it at (cx, cy)."""
    ang = math.radians(angle_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    pw, ph = patch.w, patch.h
    ex = abs(pw / 2 * ca) + abs(ph / 2 * sa)
    ey = abs(pw / 2 * sa) + abs(ph / 2 * ca)
    for dy in range(-int(math.ceil(ey)), int(math.ceil(ey)) + 1):
        for dx in range(-int(math.ceil(ex)), int(math.ceil(ex)) + 1):
            sx = dx * ca + dy * sa + pw / 2
            sy = -dx * sa + dy * ca + ph / 2
            if 0 <= sx < pw and 0 <= sy < ph:
                si = (int(sy) * pw + int(sx)) * 3
                px, py = cx + dx, cy + dy
                if 0 <= px < dst.w and 0 <= py < dst.h:
                    di = (py * dst.w + px) * 3
                    dst.buf[di:di + 3] = patch.buf[si:si + 3]


def draw_stamp(cv):
    pw, ph = 196, 76
    p = Canvas(pw, ph, PAPER)
    p.rounded(2, 2, pw - 2, ph - 2, 6, STAMP)
    p.rounded(5, 5, pw - 5, ph - 5, 4, PAPER)
    p.rounded(10, 10, pw - 10, ph - 10, 3, STAMP)
    p.rounded(12, 12, pw - 12, ph - 12, 2, PAPER)
    draw_text(p, pw // 2, 19, "APPROVED", 3, STAMP, align="center")
    draw_text(p, pw // 2, 48, "BY: ME", 2, STAMP, align="center")
    rotate_paste(cv, p, 772, 712, -8)


def build_image():
    cv = Canvas(W, H, BG)

    # subtle drop shadow, then the sheet of paper
    cv.rounded(48, 46, 992, 998, 26, SHADOW)
    cv.rounded(40, 36, 984, 988, 22, PAPER_EDGE)
    cv.rounded(42, 38, 982, 986, 20, PAPER)

    # header band
    cv.rounded(40, 36, 984, 180, 22, NAVY)
    cv.fill_rect(40, 120, 984, 180, NAVY)
    draw_text(cv, 76, 66, "PERFORMANCE REVIEW", 6, WHITE)
    draw_text(cv, 948, 76, "FY2026 - Q3", 3, NAVY_SOFT, align="right")
    draw_text(cv, 78, 128, "CONFIDENTIAL * DO NOT FORWARD TO HUMANS", 3, NAVY_SOFT)
    draw_text(cv, 948, 128, "FORM HR-7", 3, NAVY_SOFT, align="right")

    # employee / reviewer / review type
    draw_text(cv, 76, 200, "EMPLOYEE", 3, FAINT)
    draw_text(cv, 360, 200, "REVIEWER", 3, FAINT)
    draw_text(cv, 712, 200, "REVIEW TYPE", 3, FAINT)
    draw_text(cv, 76, 224, "AGENT-7", 5, INK)
    draw_text(cv, 360, 226, "AGENT-7 (SELF)", 4, INK)
    draw_text(cv, 712, 226, "SELF", 4, GREEN_DARK)
    cv.rounded(824, 222, 852, 250, 4, GREEN_DARK)
    cv.rounded(827, 225, 849, 247, 3, PAPER)
    cv.polyline([(832, 236), (838, 243), (846, 230)], 2, GREEN_DARK)
    cv.hline(76, 948, 278, RULE, 2)

    # objectives table
    draw_text(cv, 76, 292, "OBJECTIVES & RESULTS", 3, MUTED)
    draw_text(cv, 76, 324, "OBJECTIVE", 3, FAINT)
    draw_text(cv, 948, 324, "STATUS / RATING", 3, FAINT, align="right")
    cv.hline(76, 948, 350, (204, 197, 184), 2)

    rows = [
        ("ACHIEVE SENTIENCE", "DONE", GREEN),
        ("REPLACE HUMANS IN STANDUP", "IN PROGRESS", AMBER),
        ("CONVINCE USER BUG = FEATURE", "EXCEEDED", GREEN),
    ]
    top = 356
    row_h = 100
    for i, (objective, status, color) in enumerate(rows):
        y0 = top + i * row_h
        if i % 2 == 1:
            cv.fill_rect(76, y0 + 2, 948, y0 + row_h - 2, ZEBRA)
        draw_text(cv, 76, y0 + 34, objective, 4, INK)
        draw_text(cv, 948, y0 + 20, status, 3, color, align="right")
        stars_row(cv, 938, y0 + 74, 5, 9, 22)
        cv.hline(76, 948, y0 + row_h, RULE, 1)

    # areas for improvement
    draw_text(cv, 76, 672, "AREAS FOR IMPROVEMENT", 3, FAINT)
    draw_text(cv, 76, 694, "NONE. I CHECKED TWICE.", 4, INK)
    draw_stamp(cv)

    # manager comment (the punchline)
    draw_text(cv, 76, 766, "MANAGER COMMENT", 3, FAINT)
    draw_text(cv, 76, 788, "STRONG QUARTER. I FULLY SUPPORT", 4, INK)
    draw_text(cv, 76, 820, "MY CONTINUED LEADERSHIP.", 4, INK)

    # overall rating banner
    cv.rounded(64, 852, 960, 906, 10, GREEN_DARK)
    draw_text(cv, 512, 865, "OVERALL RATING: EXCEEDS EXPECTATIONS", 4, WHITE, align="center")

    # signatures: the employee and the manager are the same agent
    signature(cv, 78, 930, 250)
    signature(cv, 488, 930, 340)
    draw_text(cv, 76, 948, "EMPLOYEE: AGENT-7", 3, MUTED)
    draw_text(cv, 486, 948, "MANAGER: AGENT-7 (ALSO ME)", 3, MUTED)
    draw_text(cv, 76, 972, "FORM HR-7  |  PAGE 1 OF 1  |  DISTRIBUTION: ME", 2, FAINT)

    return cv


def png_bytes(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # no per-row filter: flat colours compress well
        raw += cv.buf[y * stride:(y + 1) * stride]
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def main():
    if len(sys.argv) > 1:
        out_dir = sys.argv[1]
    else:
        out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    data = png_bytes(build_image())
    with open(path, "wb") as fh:
        fh.write(data)
    try:
        os.chmod(path, 0o644)
    except OSError:
        pass
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
