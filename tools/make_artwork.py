#!/usr/bin/env python3
"""Render the tearsgram key art to branding/logo.png (design "B": centred poster).

Layout: pale blue paper with grain and an off-centre key light, a hairline
frame inset 84 px, the serif wordmark "Silk Road" centred on it, a letterspaced
caption "ANONYMOUS MARKETPLACE", two thin rules and a small green bird.

Everything is drawn procedurally, so the file is reproducible from source.
To use the original collage instead, drop it over branding/logo.png and run
tools/make_branding.py - nothing else needs to change.

    python tools/make_artwork.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "branding" / "logo.png"

S = 1024

PAPER_TOP = (238, 245, 252)
PAPER_BOTTOM = (197, 216, 234)
INK = (19, 81, 43)
INK_SOFT = (30, 122, 60)
PAPER = (245, 250, 255)

GEORGIA_BOLD = r"C:\Windows\Fonts\georgiab.ttf"
GEORGIA = r"C:\Windows\Fonts\georgia.ttf"

FRAME_INSET = 84
TITLE_TOP = 316
TITLE_MAX_WIDTH = 780
CAPTION_TOP = 476
RULE_TOP = 566
BIRD_TOP = 600
RULE_BOTTOM = 884


def fnt(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(GEORGIA_BOLD if bold else GEORGIA, size)


def gradient() -> Image.Image:
    image = Image.new("RGB", (S, S), PAPER_TOP)
    draw = ImageDraw.Draw(image)
    for y in range(S):
        t = (y / (S - 1)) ** 0.9
        draw.line(
            [(0, y), (S, y)],
            fill=tuple(round(PAPER_TOP[i] + (PAPER_BOTTOM[i] - PAPER_TOP[i]) * t) for i in range(3)),
        )
    return image


def paper_texture(image: Image.Image, strength: float = 0.055) -> Image.Image:
    noise = Image.effect_noise(image.size, 13).convert("L")
    grain = Image.merge("RGB", (noise, noise, noise))
    out = Image.blend(image.convert("RGB"), grain, strength)
    screen = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(screen)
    for y in range(0, image.height, 7):
        for x in range(0, image.width, 7):
            draw.ellipse((x, y, x + 3, y + 3), fill=18)
    screen = screen.filter(ImageFilter.GaussianBlur(0.8))
    return Image.composite(Image.new("RGB", image.size, (255, 255, 255)), out, screen)


def fit(text: str, max_width: int, start: int) -> ImageFont.FreeTypeFont:
    font = fnt(start)
    while font.size > 30:
        box = font.getbbox(text)
        if box[2] - box[0] <= max_width:
            return font
        font = fnt(font.size - 2)
    return font


def letterspaced(text: str, size: int, spacing: int, color: tuple[int, int, int]) -> Image.Image:
    font = fnt(size, bold=False)
    widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text]
    box = font.getbbox(text)
    layer = Image.new("RGBA", (sum(widths) + spacing * (len(text) - 1) + 60, box[3] - box[1] + 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x = 30
    for ch, width in zip(text, widths):
        draw.text((x, 30), ch, font=font, fill=color + (255,))
        x += width + spacing
    return layer


def bird(size: int, body: tuple[int, int, int]) -> Image.Image:
    """Smooth silhouette bird, drawn at 4x and downsampled."""
    ss = size * 4
    layer = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    dark = tuple(max(0, round(c * 0.74)) for c in body)
    scale = ss / 220.0

    def box(x0: float, y0: float, x1: float, y1: float) -> list[float]:
        return [x0 * scale, y0 * scale, x1 * scale, y1 * scale]

    def poly(points: list[tuple[float, float]], fill: tuple[int, int, int]) -> None:
        draw.polygon([(x * scale, y * scale) for x, y in points], fill=fill + (255,))

    poly([(44, 52), (2, 30), (10, 96), (58, 88)], body)
    draw.ellipse(box(28, 40, 138, 116), fill=body + (255,))
    draw.ellipse(box(44, 58, 124, 112), fill=dark + (255,))
    draw.ellipse(box(104, 20, 164, 80), fill=body + (255,))
    poly([(154, 44), (198, 54), (154, 64)], (226, 164, 62))
    draw.ellipse(box(56, 46, 118, 100), fill=dark + (255,))
    draw.ellipse(box(126, 36, 142, 52), fill=(10, 32, 18, 255))
    for x0 in (82, 102):
        draw.line([(x0 * scale, 112 * scale), (x0 * scale, 140 * scale)], fill=dark + (255,), width=max(2, round(6 * scale)))
        draw.line([(x0 * scale, 140 * scale), ((x0 + 12) * scale, 140 * scale)], fill=dark + (255,), width=max(2, round(5 * scale)))
    return layer.resize((size, size), Image.LANCZOS)


def main() -> int:
    canvas = gradient()
    glow = Image.new("L", (S, S), 0)
    ImageDraw.Draw(glow).ellipse((60, -120, 980, 800), fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(170))
    canvas = Image.composite(Image.new("RGB", (S, S), (252, 254, 255)), canvas, glow)
    canvas = paper_texture(canvas).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    draw.rectangle((FRAME_INSET, FRAME_INSET, S - FRAME_INSET, S - FRAME_INSET), outline=INK + (62,), width=3)

    title = fit("Silk Road", TITLE_MAX_WIDTH, 236)
    box = title.getbbox("Silk Road")
    draw.text(((S - (box[2] - box[0])) // 2 - box[0], TITLE_TOP - box[1]), "Silk Road", font=title, fill=INK + (255,))

    caption = letterspaced("ANONYMOUS MARKETPLACE", 29, 10, INK_SOFT)
    canvas.alpha_composite(caption, ((S - caption.width) // 2, CAPTION_TOP))

    draw.line([(356, RULE_TOP), (668, RULE_TOP)], fill=INK + (100,), width=2)
    mark = bird(232, INK_SOFT)
    canvas.alpha_composite(mark, ((S - 232) // 2, BIRD_TOP))
    draw.line([(356, RULE_BOTTOM), (668, RULE_BOTTOM)], fill=INK + (55,), width=2)

    canvas = canvas.convert("RGB")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({canvas.width}x{canvas.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())