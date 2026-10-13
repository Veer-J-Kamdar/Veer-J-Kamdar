#!/usr/bin/env python3
"""Optional: convert assets/profile-photo.jpg into an animated ASCII SVG.

Run locally after adding your own photo:
  pip install -r scripts/requirements.txt
  python scripts/generate_ascii_portrait.py

The photo stays local. The output SVG contains the ASCII art, not the photo.
"""
from PIL import Image, ImageOps
import os
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "assets", "profile-photo.jpg")
OUTPUT = os.path.join(ROOT, "ascii-portrait.svg")
RAMP = " .:-=+*#%@"
WIDTH = 96
CELL_W, CELL_H = 7.0, 11.0

if not os.path.exists(SOURCE):
    raise SystemExit("Add your own photo at assets/profile-photo.jpg first.")

im = Image.open(SOURCE).convert("L")
im = ImageOps.fit(im, (WIDTH, int(WIDTH * 0.85)))
pixels = im.load()
rows = []
for y in range(im.height):
    row = []
    for x in range(im.width):
        idx = round(pixels[x, y] / 255 * (len(RAMP)-1))
        row.append(RAMP[len(RAMP)-1-idx])
    rows.append("".join(row))

width, height = WIDTH*CELL_W+30, im.height*CELL_H+55
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">',
    '<rect width="100%" height="100%" fill="#0d1117"/>',
    '<style>text{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre}</style>',
    f'<text x="12" y="20" fill="#39ff88" font-size="10">VEER@GITHUB:~$ ./whoami --ascii</text>',
]
for i, row in enumerate(rows):
    parts.append(
        f'<text x="12" y="{42+i*CELL_H:.1f}" fill="#c9d1d9" font-size="10" '
        f'xml:space="preserve">{escape(row)}</text>'
    )
parts.append('<rect x="0.5" y="0.5" width="99%" height="99%" rx="5" fill="none" stroke="#30363d"/>')
parts.append("</svg>")
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(parts))
print("Generated ascii-portrait.svg")
