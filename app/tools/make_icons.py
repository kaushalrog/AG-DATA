#!/usr/bin/env python3
"""Generate the AG-DATA app icons (PNG 192/512 + SVG) with the Python standard library only.

Design: white leaf with a green vein on a solid green square (works as a maskable icon:
all artwork sits inside the central 80% safe zone). Original artwork, CC0 (see ../ASSETS.md).
Usage:  python3 app/tools/make_icons.py
"""
import math
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "icons")

BG = (31, 107, 58)      # #1f6b3a
LEAF = (255, 255, 255)
VEIN = (31, 107, 58)
SOIL = (232, 196, 120)  # #e8c478 small soil arc

# Leaf = lens (intersection of two circles), rotated -45 degrees.
R, C = 0.6802, 0.4002   # half-length 0.55, half-width 0.28
COS, SIN = math.cos(math.radians(45)), math.sin(math.radians(45))


def colour_at(x, y):
    """x, y in [-1, 1]; returns RGB."""
    # soil arc at the bottom
    if y > 0.55 and y < 0.68 and abs(x) < 0.5:
        return SOIL
    # rotate into leaf frame, leaf centred slightly above centre
    ly = y + 0.08
    u = x * COS - ly * SIN
    v = x * SIN + ly * COS
    in_leaf = (u * u + (v - C) ** 2 <= R * R) and (u * u + (v + C) ** 2 <= R * R)
    # stem from the lower-left tip of the leaf down to the soil
    on_stem = abs(x + 0.0) < 0.035 and 0.1 < y < 0.58
    if in_leaf:
        if abs(v) < 0.03 and abs(u) < 0.48:
            return VEIN
        for off in (-0.25, 0.0, 0.25):  # side veins
            if abs(v - 0.6 * (u - off)) < 0.022 and 0 < v < 0.18 and abs(u) < 0.45:
                return VEIN
            if abs(v + 0.6 * (u - off)) < 0.022 and -0.18 < v < 0 and abs(u) < 0.45:
                return VEIN
        return LEAF
    if on_stem:
        return LEAF
    return BG


def render(size, ss=3):
    rows = []
    for py in range(size):
        row = bytearray([0])  # filter type 0
        for px in range(size):
            acc = [0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    x = ((px + (sx + 0.5) / ss) / size) * 2 - 1
                    y = ((py + (sy + 0.5) / ss) / size) * 2 - 1
                    c = colour_at(x, y)
                    acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]
            n = ss * ss
            row += bytes((acc[0] // n, acc[1] // n, acc[2] // n))
        rows.append(bytes(row))
    return b"".join(rows)


def png(size, raw):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 2 2" width="512" height="512">
<rect x="-1" y="-1" width="2" height="2" fill="#1f6b3a"/>
<rect x="-0.5" y="0.55" width="1" height="0.13" rx="0.06" fill="#e8c478"/>
<rect x="-0.035" y="0.1" width="0.07" height="0.48" fill="#fff"/>
<g transform="translate(0 -0.08) rotate(-45)">
<path d="M-0.55 0 A0.6802 0.6802 0 0 1 0.55 0 A0.6802 0.6802 0 0 1 -0.55 0Z" fill="#fff"/>
<path d="M-0.48 0H0.48" stroke="#1f6b3a" stroke-width="0.06"/>
</g>
</svg>
"""

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for s in (192, 512):
        with open(os.path.join(OUT, f"icon-{s}.png"), "wb") as f:
            f.write(png(s, render(s, 3 if s <= 192 else 2)))
    with open(os.path.join(OUT, "app-icon.svg"), "w") as f:
        f.write(SVG)
    print("wrote icon-192.png, icon-512.png, app-icon.svg to", os.path.normpath(OUT))
