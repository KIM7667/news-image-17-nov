"""Draw a newspaper front page summing up Tuesday, 17 November 2026.

Pure standard library (struct, zlib, os, sys, pathlib). No network, no
randomness, fully deterministic: two runs write byte-identical PNGs.

The image is drawn entirely in code: a 5x7 bitmap font defined below plus
flat shapes (rectangles, lines, circles). No bundled image is used.
"""

import os
import struct
import sys
import zlib
from pathlib import Path

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (250, 246, 235)
PANEL = (255, 252, 244)
INK = (18, 18, 24)
NAVY = (15, 42, 74)
NAVY_DARK = (10, 30, 55)
GOLD = (201, 162, 39)
RED = (178, 34, 34)
TEAL = (14, 110, 110)
BLUE = (28, 84, 160)
GREY = (110, 110, 108)
LIGHT_GREY = (200, 200, 196)
SKY = (140, 190, 220)
WATER = (70, 130, 180)
WHITE = (255, 255, 255)
ORANGE = (220, 110, 20)

# ------------------------------------------------------- 5x7 bitmap font
# Each glyph is 7 rows of 5 bits ('#' = ink). Verified row by row against
# the intended letter shape before use.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


class Canvas:
    """A plain RGB pixel buffer with flat-shape drawing helpers."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def hline(self, x, y, length, color, thick=1):
        self.rect(x, y, length, thick, color)

    def vline(self, x, y, length, color, thick=1):
        self.rect(x, y, thick, length, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        for i in range(steps + 1):
            x = x0 + dx * i // steps
            y = y0 + dy * i // steps
            self.rect(x, y, thick, thick, color)

    def circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, color)

    def text(self, x, y, s, scale, color):
        """Draw string s with top-left at (x, y); returns width in px."""
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx - x - scale

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale

    def text_centered(self, cx, y, s, scale, color):
        self.text(cx - self.text_width(s, scale) // 2, y, s, scale, color)


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    char_w = 6 * scale
    max_chars = max(1, (max_width + scale) // char_w)
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if len(trial) <= max_chars:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


# ------------------------------------------------------------------- PNG
def chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    out += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    return out


def write_png(canvas, path):
    raw = bytearray()
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        start = y * canvas.w * 3
        raw += canvas.px[start:start + canvas.w * 3]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    Path(path).write_bytes(png)
    return len(png)


# ------------------------------------------------------------- page layout
def kicker(cv, x, y, text, color):
    """Coloured kicker bar + uppercase kicker text."""
    cv.rect(x, y, 10, 14, color)
    cv.text(x + 18, y, text, 2, color)


def panel(cv, x, y, w, h, accent):
    cv.rect(x, y, w, h, PANEL)
    cv.rect(x, y, w, 6, accent)
    # thin dark border
    cv.rect(x, y + 6, w, 2, INK)
    cv.rect(x, y + h - 2, w, 2, INK)
    cv.rect(x, y, 2, h, INK)
    cv.rect(x + w - 2, y, 2, h, INK)


def draw_bridge(cv, x, y, w, h):
    """Kerch bridge: two towers, deck with a broken gap, smoke, water."""
    # sky strip
    cv.rect(x, y, w, h, SKY)
    # water
    cv.rect(x, y + h - 26, w, 26, WATER)
    cv.hline(x, y + h - 26, w, WHITE, 2)
    deck_y = y + h - 62
    mid = x + w // 2
    # deck: two spans with a collapsed gap in the middle
    cv.rect(x + 8, deck_y, mid - x - 48, 10, INK)
    cv.rect(mid + 40, deck_y, x + w - 8 - (mid + 40), 10, INK)
    # fallen span fragment, tilted into the water
    cv.line(mid - 40, deck_y + 8, mid - 6, deck_y + 26, INK, 6)
    # towers
    for tx in (x + 90, x + w - 110):
        cv.rect(tx, y + 14, 16, deck_y - y - 14, NAVY)
        cv.rect(tx - 6, y + 8, 28, 8, NAVY)
    # cables from towers to deck
    cv.line(x + 98, y + 16, x + 40, deck_y, GREY, 2)
    cv.line(x + 98, y + 16, mid - 48, deck_y, GREY, 2)
    cv.line(x + w - 102, y + 16, mid + 48, deck_y, GREY, 2)
    cv.line(x + w - 102, y + 16, x + w - 40, deck_y, GREY, 2)
    # smoke puffs rising from the gap
    cv.circle(mid - 8, deck_y - 14, 12, GREY)
    cv.circle(mid + 14, deck_y - 26, 15, LIGHT_GREY)
    cv.circle(mid + 2, deck_y - 44, 10, GREY)
    # small fire glow at the break
    cv.circle(mid - 30, deck_y - 2, 7, ORANGE)
    cv.circle(mid + 30, deck_y - 2, 7, ORANGE)


def draw_tanker(cv, x, y, w):
    """Small oil tanker on waves with a flame."""
    cv.rect(x, y + 22, w, 16, NAVY)
    cv.rect(x + 8, y + 10, 26, 12, RED)
    cv.rect(x + w - 40, y + 4, 18, 18, INK)
    cv.hline(x - 6, y + 42, w + 12, WATER, 3)
    cv.hline(x + 10, y + 48, w - 20, WATER, 2)
    # flame above the cargo
    cv.line(x + 20, y + 10, x + 14, y - 4, ORANGE, 3)
    cv.line(x + 22, y + 10, x + 28, y - 6, ORANGE, 3)
    cv.circle(x + 21, y - 6, 4, ORANGE)


def draw_flags(cv, x, y):
    """Three small summit flags on poles."""
    for i, col in enumerate((RED, BLUE, GOLD)):
        px = x + i * 46
        cv.vline(px, y, 44, INK, 3)
        cv.rect(px + 3, y, 34, 20, col)
        cv.rect(px + 3, y + 20, 34, 3, WHITE)


def draw_bank(cv, x, y):
    """Bank building: pediment, columns, steps."""
    cv.line(x, y + 16, x + 34, y, INK, 3)
    cv.line(x + 34, y, x + 68, y + 16, INK, 3)
    cv.rect(x, y + 16, 68, 4, INK)
    for i in range(3):
        cv.rect(x + 6 + i * 24, y + 22, 8, 26, INK)
    cv.rect(x - 4, y + 50, 76, 4, INK)


def draw_rocket(cv, x, y):
    """Rocket going up, with flame and smoke."""
    cv.line(x + 20, y, x + 34, y + 22, RED, 2)
    cv.line(x + 48, y, x + 34, y + 22, RED, 2)
    cv.rect(x + 20, y + 22, 28, 26, NAVY)
    cv.circle(x + 34, y + 32, 6, WHITE)
    cv.rect(x + 12, y + 38, 8, 14, RED)
    cv.rect(x + 48, y + 38, 8, 14, RED)
    cv.circle(x + 34, y + 56, 6, ORANGE)
    cv.circle(x + 28, y + 62, 4, GREY)
    cv.circle(x + 42, y + 62, 4, GREY)


def draw_hub(cv, x, y):
    """Five blocks (EU states) with an arrow to a small house."""
    for i in range(5):
        cv.rect(x + i * 16, y + 6, 12, 12, BLUE if i % 2 else TEAL)
    cv.line(x + 8, y + 26, x + 66, y + 40, INK, 3)
    cv.line(x + 66, y + 40, x + 56, y + 34, INK, 3)
    cv.line(x + 66, y + 40, x + 56, y + 46, INK, 3)
    # house
    cv.line(x + 78, y + 44, x + 96, y + 28, RED, 3)
    cv.line(x + 96, y + 28, x + 114, y + 44, RED, 3)
    cv.rect(x + 82, y + 44, 28, 20, NAVY)


def story_panel(cv, x, y, w, h, accent, kicker_text, headline, deck,
                deck_scale, icon):
    panel(cv, x, y, w, h, accent)
    ix = x + 16
    iy = y + 18
    kicker(cv, ix, iy, kicker_text, accent)
    lines = wrap_text(headline, 4 if w > 400 else 3, w - 32)
    hy = iy + 34
    for line in lines:
        cv.text(ix, hy, line, 4 if w > 400 else 3, INK)
        hy += (4 if w > 400 else 3) * 7 + 8
    dy = hy + 6
    for line in wrap_text(deck, deck_scale, w - 32):
        cv.text(ix, dy, line, deck_scale, INK)
        dy += deck_scale * 7 + 5
    # Icons sit below the deck text, never on top of it.
    icon_y = dy + 8
    if icon == "tanker":
        draw_tanker(cv, ix, icon_y, 120)
    elif icon == "flags":
        draw_flags(cv, ix, icon_y - 6)
    elif icon == "bank":
        draw_bank(cv, ix, icon_y)
    elif icon == "rocket":
        draw_rocket(cv, ix, icon_y - 12)
    elif icon == "hub":
        draw_hub(cv, ix, icon_y - 10)


def build():
    cv = Canvas(W, H, PAPER)

    # ---- masthead: dark navy band, title + date
    cv.rect(0, 0, W, 140, NAVY)
    cv.rect(0, 136, W, 4, GOLD)
    cv.text_centered(W // 2, 26, "THE WORLD TODAY", 8, WHITE)
    cv.text_centered(W // 2, 100, "TUESDAY, 17 NOVEMBER 2026", 4, GOLD)

    # ---- lead story: Kerch bridge
    panel(cv, 16, 152, 992, 280, RED)
    kicker(cv, 36, 172, "EUROPE / CONFLICT", RED)
    cv.text(36, 204, "KERCH BRIDGE HIT AGAIN", 6, INK)
    dy = 258
    for line in wrap_text(
            "ROAD SPAN COLLAPSES IN SECOND UKRAINIAN STRIKE IN A DAY",
            3, 952):
        cv.text(36, dy, line, 3, INK)
        dy += 26
    draw_bridge(cv, 36, 306, 952, 116)

    # ---- middle row: Hormuz tankers, Trump Asia trip
    story_panel(cv, 16, 444, 484, 272, TEAL,
                "MIDDLE EAST / SHIPPING",
                "TANKERS HIT BY MINES OFF HORMUZ",
                "TWO TANKERS CATCH FIRE; THIRD US CARRIER HEADS TO THE REGION",
                3, "tanker")
    story_panel(cv, 524, 444, 484, 272, BLUE,
                "ASIA / DIPLOMACY",
                "TRUMP IN MANILA, THEN SHENZHEN",
                "XI, TRUMP AND PUTIN TO MEET THURSDAY AT APEC SUMMIT",
                3, "flags")

    # ---- bottom row: banking glitch, Vulcan failure, Rwanda hub
    story_panel(cv, 16, 728, 320, 240, GOLD,
                "BUSINESS / TECH",
                "JPMORGAN BUG HALTS BANKING",
                "SOFTWARE GLITCH, NOT CYBERATTACK, HITS ONLINE BANKING AND ZELLE",
                2, "bank")
    story_panel(cv, 352, 728, 320, 240, NAVY,
                "SPACE",
                "VULCAN ROCKET FAILS",
                "40 AMAZON SATELLITES LOST MINUTES AFTER LAUNCH",
                2, "rocket")
    story_panel(cv, 688, 728, 320, 240, RED,
                "EUROPE / MIGRATION",
                "FIVE EU STATES PLAN RWANDA HUB",
                "JOINT RETURN CENTRE FOR REJECTED ASYLUM SEEKERS",
                2, "hub")

    # ---- footer strip
    cv.rect(0, 976, W, 48, NAVY)
    cv.text_centered(W // 2, 992, "SOURCES: BBC, AL JAZEERA, AP, REUTERS",
                     2, WHITE)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = build()
    size = write_png(cv, os.path.join(out_dir, "entry.png"))
    sys.stdout.write("wrote %s bytes\n" % size)


if __name__ == "__main__":
    main()
