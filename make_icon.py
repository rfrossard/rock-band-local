#!/usr/bin/env python3
"""
Generates the Fross Song Manager icon — Matrix Edition.
Outputs icon_source.png (1024×1024) in the same directory.
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "icon_source.png"
SIZE = 1024

# ── Canvas ────────────────────────────────────────────────────────────────────
img  = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
draw = ImageDraw.Draw(img)

GREEN      = (0,  255,  65, 255)    # Matrix #00FF41
GREEN_DIM  = (0,   60,  20, 255)    # dark grid
GREEN_MID  = (0,  160,  50, 200)    # mid accent
GREEN_GLOW = (0,  255,  65,  60)    # subtle glow

# ── Background: subtle grid ───────────────────────────────────────────────────
GRID = 48
for x in range(0, SIZE, GRID):
    for y in range(0, SIZE, GRID):
        draw.rectangle([x, y, x + GRID - 1, y + GRID - 1],
                       fill=(0, 8, 2, 255))

# Faint grid lines
for x in range(0, SIZE, GRID):
    draw.line([(x, 0), (x, SIZE)], fill=(0, 25, 8, 255), width=1)
for y in range(0, SIZE, GRID):
    draw.line([(0, y), (SIZE, y)], fill=(0, 25, 8, 255), width=1)

# ── Matrix rain columns (decorative) ─────────────────────────────────────────
random.seed(42)
chars = "01アイウエオFGBMATRIX"
try:
    rain_font = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Courier New.ttf", 22)
except Exception:
    rain_font = None

if rain_font:
    for col in range(0, SIZE, 36):
        alpha = random.randint(15, 55)
        for row in range(0, SIZE, 28):
            c = random.choice(chars)
            draw.text((col + 2, row), c,
                      fill=(0, 200, 60, alpha), font=rain_font)

# ── Outer rounded border ──────────────────────────────────────────────────────
MARGIN = 36
R      = 80   # corner radius

def rounded_rect(d, xy, r, color, width=0, fill=None):
    x0, y0, x1, y1 = xy
    if fill:
        d.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
        d.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
        d.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill)
        d.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill)
        d.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill)
        d.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill)
    if width:
        for off in range(width):
            o = off
            d.arc([x0+o, y0+o, x0+2*r-o, y0+2*r-o], 180, 270, fill=color)
            d.arc([x1-2*r+o, y0+o, x1-o, y0+2*r-o], 270, 360, fill=color)
            d.arc([x0+o, y1-2*r+o, x0+2*r-o, y1-o], 90,  180, fill=color)
            d.arc([x1-2*r+o, y1-2*r+o, x1-o, y1-o], 0,   90,  fill=color)
            d.line([x0+r, y0+o, x1-r, y0+o], fill=color)
            d.line([x0+r, y1-o, x1-r, y1-o], fill=color)
            d.line([x0+o, y0+r, x0+o, y1-r], fill=color)
            d.line([x1-o, y0+r, x1-o, y1-r], fill=color)

rounded_rect(draw, [MARGIN, MARGIN, SIZE-MARGIN, SIZE-MARGIN],
             R, GREEN, width=6)
rounded_rect(draw, [MARGIN+20, MARGIN+20, SIZE-MARGIN-20, SIZE-MARGIN-20],
             R-10, GREEN_DIM, width=1)

# ── Guitar silhouette (simple) ────────────────────────────────────────────────
CX, CY = SIZE // 2, SIZE // 2 + 20

# Body (figure-8 ish)
body_top = (CX, CY - 60)
draw.ellipse([CX - 115, CY - 180, CX + 115, CY + 20],
             fill=(0, 18, 6, 255), outline=(0, 180, 55, 255), width=3)
draw.ellipse([CX - 140, CY - 10, CX + 140, CY + 250],
             fill=(0, 18, 6, 255), outline=(0, 180, 55, 255), width=3)

# Soundhole
draw.ellipse([CX - 42, CY + 80, CX + 42, CY + 165],
             fill=(0, 0, 0, 255), outline=GREEN_MID, width=2)

# Bridge
draw.rectangle([CX - 55, CY + 195, CX + 55, CY + 215],
               fill=(0, 140, 40, 255))

# Neck
draw.rectangle([CX - 22, CY - 360, CX + 22, CY - 170],
               fill=(0, 22, 8, 255), outline=(0, 150, 45, 255), width=2)

# Headstock
draw.rectangle([CX - 35, CY - 430, CX + 35, CY - 360],
               fill=(0, 22, 8, 255), outline=(0, 150, 45, 255), width=2)

# Tuning pegs (3 each side)
for i in range(3):
    y_peg = CY - 420 + i * 22
    draw.ellipse([CX - 55, y_peg - 7, CX - 35, y_peg + 7],
                 fill=GREEN_MID)
    draw.ellipse([CX + 35, y_peg - 7, CX + 55, y_peg + 7],
                 fill=GREEN_MID)

# Strings (6)
for i in range(6):
    x_s = CX - 25 + i * 10
    draw.line([(x_s, CY - 370), (x_s, CY + 195)],
              fill=(0, 200, 60, 140), width=1)

# ── FGB text ──────────────────────────────────────────────────────────────────
try:
    font_main = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf", 168)
    font_sub  = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Courier New.ttf", 44)
except Exception:
    try:
        font_main = ImageFont.truetype(
            "/System/Library/Fonts/Menlo.ttc", 168)
        font_sub  = ImageFont.truetype(
            "/System/Library/Fonts/Menlo.ttc", 44)
    except Exception:
        font_main = ImageFont.load_default()
        font_sub  = ImageFont.load_default()

TEXT_Y = SIZE - 195

# Glow (multi-pass blur effect)
for offset in [(4, 4), (-4, -4), (4, -4), (-4, 4), (0, 0)]:
    alpha = 60 if offset != (0, 0) else 255
    draw.text((SIZE // 2 + offset[0], TEXT_Y + offset[1]), "FGB",
              fill=(0, 255, 65, alpha), font=font_main, anchor="mm")

# Subtitle
draw.text((SIZE // 2, TEXT_Y + 100), "SONG MANAGER",
          fill=GREEN_MID, font=font_sub, anchor="mm")

# ── Corner brackets ───────────────────────────────────────────────────────────
BL = 60  # bracket length
BW = 5   # bracket width
BC = 75  # bracket corner offset from edge
col = GREEN

for (bx, by), (hx, hy), (vx, vy) in [
    # top-left
    ((BC, BC + BL), (BC, BC), (BC + BL, BC)),
    # top-right
    ((SIZE-BC-BL, BC), (SIZE-BC, BC), (SIZE-BC, BC + BL)),
    # bottom-left
    ((BC, SIZE-BC-BL), (BC, SIZE-BC), (BC + BL, SIZE-BC)),
    # bottom-right
    ((SIZE-BC-BL, SIZE-BC), (SIZE-BC, SIZE-BC), (SIZE-BC, SIZE-BC-BL)),
]:
    draw.line([bx, by, hx, hy], fill=col, width=BW)
    draw.line([hx, hy, vx, vy], fill=col, width=BW)

# ── Save ──────────────────────────────────────────────────────────────────────
img.save(str(OUT))
print(f"✅  Icon saved: {OUT}")
