#!/usr/bin/env python3
"""Convert a portrait photo into a monochrome, animated ASCII SVG.

Run locally:
  pip install -r scripts/requirements.txt
  python scripts/generate_ascii_portrait.py [photo.jpg] [output.svg]

The photo stays local. The output SVG contains the ASCII art, not the photo.
"""
import argparse
from html import escape
import os

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE = os.path.join(ROOT, "assets", "profile-photo.jpg")
DEFAULT_OUTPUT = os.path.join(ROOT, "ascii-portrait.svg")

COLS = 120
ART_W_TARGET = 800
CELL_W = ART_W_TARGET / COLS
CELL_H = CELL_W * 15 / 8
ROWS = round(COLS * 8 / 15)
RAMP = " .`:-=+*cs#%@"

BACKGROUND_THRESHOLD = 28
SUBJECT_PADDING = 30
GAMMA = 1.12
WHITE_FLOOR = 0.86

PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TEXT = "#7d8590"
INK = "#c9d1d9"
ROW_DUR = 5.8 / ROWS
STAGGER = ROW_DUR


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE)
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--static",
        action="store_true",
        help="write a non-animated SVG preview",
    )
    return parser.parse_args()


def isolate_subject(image):
    """Replace the edge-connected dark background while retaining dark hair."""
    gray = image.convert("L")
    corners = (
        gray.getpixel((0, 0)),
        gray.getpixel((gray.width - 1, 0)),
        gray.getpixel((0, gray.height - 1)),
        gray.getpixel((gray.width - 1, gray.height - 1)),
    )
    if any(value > BACKGROUND_THRESHOLD for value in corners):
        raise ValueError("Expected a dark background at all four image corners.")

    background = gray.point(
        lambda luminance: 255 if luminance <= BACKGROUND_THRESHOLD else 0
    )
    ImageDraw.floodfill(background, (0, 0), 128)
    foreground = background.point(lambda value: 0 if value == 128 else 255)
    bounds = foreground.getbbox()
    if bounds is None:
        raise ValueError("Could not detect a subject against the dark background.")

    left, top, right, bottom = bounds
    side = max(right - left, bottom - top) + SUBJECT_PADDING * 2
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    crop_left = center_x - side // 2
    crop_top = center_y - side // 2
    crop_right = crop_left + side
    crop_bottom = crop_top + side

    canvas = Image.new("L", (side, side), 255)
    source_box = (
        max(crop_left, 0),
        max(crop_top, 0),
        min(crop_right, gray.width),
        min(crop_bottom, gray.height),
    )
    source = gray.crop(source_box)
    mask = foreground.crop(source_box).filter(ImageFilter.GaussianBlur(1.0))
    subject = Image.composite(source, Image.new("L", source.size, 255), mask)
    canvas.paste(subject, (source_box[0] - crop_left, source_box[1] - crop_top))
    return canvas


def make_ascii_rows(source):
    image = Image.open(source)
    image = isolate_subject(image)
    image = ImageEnhance.Contrast(image).enhance(1.08)
    image = image.resize((COLS, ROWS), Image.Resampling.LANCZOS)
    pixels = image.load()

    rows = []
    for y in range(ROWS):
        chars = []
        for x in range(COLS):
            luminance = pow(pixels[x, y] / 255.0, GAMMA)
            if luminance >= WHITE_FLOOR:
                chars.append(" ")
                continue
            index = round((1.0 - luminance) * (len(RAMP) - 1))
            chars.append(RAMP[max(0, min(len(RAMP) - 1, index))])
        rows.append("".join(chars))
    return rows


def build_svg(rows, static=False):
    art_top = TITLEBAR_H + PAD * 0.35
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W:.0f}" '
        f'height="{CANVAS_H:.0f}" viewBox="0 0 {CANVAS_W:.0f} {CANVAS_H:.0f}" '
        'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        '<title>Veer Kamdar - monochrome ASCII portrait</title>',
        '<desc>A portrait types itself row by row in a terminal window.</desc>',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG}"/>'
        '</linearGradient></defs>',
        f'<rect width="{CANVAS_W:.0f}" height="{CANVAS_H:.0f}" rx="12" fill="url(#bg)"/>',
        f'<rect x="0.5" y="0.5" width="{CANVAS_W - 1:.0f}" '
        f'height="{CANVAS_H - 1:.0f}" rx="12" fill="none" stroke="{FRAME}"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W:.0f}" '
        f'y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
    ]

    for index in range(3):
        parts.append(
            f'<circle cx="{PAD + index * 16}" cy="{TITLEBAR_H / 2:.0f}" '
            f'r="5" fill="{INK}" opacity="{0.35 + index * 0.2:.2f}"/>'
        )

    parts.append(
        f'<text x="{CANVAS_W / 2:.1f}" y="{TITLEBAR_H / 2 + 4:.0f}" '
        f'fill="{TEXT}" font-size="12" text-anchor="middle">'
        'veer@github: ~$ ./portrait.sh</text>'
    )

    font_size = CELL_H * 0.86
    for row_index, line in enumerate(rows):
        row_top = art_top + row_index * CELL_H
        baseline = row_top + CELL_H * 0.74
        delay = row_index * STAGGER
        text = (
            f'<text xml:space="preserve" x="{PAD}" y="{baseline:.1f}" '
            f'fill="{INK}" font-size="{font_size:.1f}" textLength="{ART_W:.1f}" '
            f'lengthAdjust="spacing">{escape(line)}</text>'
        )
        if static:
            parts.append(text)
            continue

        parts.append(
            f'<clipPath id="row-{row_index}" clipPathUnits="userSpaceOnUse">'
            f'<rect x="{PAD}" y="{row_top:.1f}" '
            f'width="0" height="{CELL_H:.1f}"><animate attributeName="width" '
            f'from="0" to="{ART_W:.1f}" begin="{delay:.3f}s" '
            f'dur="{ROW_DUR:.3f}s" fill="freeze"/></rect></clipPath>'
        )
        parts.append(f'<g clip-path="url(#row-{row_index})">{text}</g>')
        parts.append(
            f'<rect y="{row_top + 1:.1f}" width="{CELL_W:.1f}" '
            f'height="{CELL_H - 2:.1f}" fill="{INK}" opacity="0">'
            f'<animate attributeName="x" from="{PAD}" to="{PAD + ART_W:.1f}" '
            f'begin="{delay:.3f}s" dur="{ROW_DUR:.3f}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
            f'<set attributeName="opacity" to="0" '
            f'begin="{delay + ROW_DUR:.3f}s"/></rect>'
        )

    status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
    status_y = status_line_y + 19
    parts.extend(
        [
            f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W:.0f}" '
            f'y2="{status_line_y:.1f}" stroke="{FRAME}"/>',
            f'<text x="{PAD}" y="{status_y:.1f}" fill="{TEXT}" font-size="13">'
            f'veer@github:~$ whoami <tspan fill="{INK}">Veer Kamdar</tspan></text>',
        ]
    )
    cursor_x = PAD + len("veer@github:~$ whoami Veer Kamdar ") * 13 * 0.6
    parts.append(
        f'<rect x="{cursor_x:.1f}" y="{status_y - 12:.1f}" width="8" height="14" '
        f'fill="{INK}"><animate attributeName="opacity" values="1;1;0;0" '
        'keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>'
    )
    parts.append("</svg>")
    return "".join(parts)


def main():
    args = parse_args()
    if not os.path.exists(args.source):
        raise SystemExit(f"Photo not found: {args.source}")
    rows = make_ascii_rows(args.source)
    svg = build_svg(rows, static=args.static)
    with open(args.output, "w", encoding="utf-8") as output:
        output.write(svg)
    print(f"Wrote {args.output} ({len(svg)} bytes; {CANVAS_W:.0f} x {CANVAS_H:.0f})")


if __name__ == "__main__":
    main()
