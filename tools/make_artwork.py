#!/usr/bin/env python3
"""Render the tearsgram key art (the "Silk Road" collage) to branding/logo.png.

The composition follows the reference collage: pale blue paper field, dark
green serif wordmark, small letterspaced caption, a cut-out bust in a striped
shirt with an anonymity bar across the eyes, a translucent "ghost" hand
reaching in from the right and a small green bird on the shoulder.

Everything is drawn procedurally so the file is reproducible without any
binary source art. Replace branding/logo.png with the original scan/photograph
and rerun tools/make_branding.py if pixel-exact artwork is required.

    python tools/make_artwork.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "branding" / "logo.png"

SIZE = 1024

BG_TOP = (230, 240, 249)
BG_BOTTOM = (178, 200, 222)
PAPER = (248, 251, 254)
GREEN_DEEP = (18, 74, 40)
GREEN_MID = (30, 118, 60)
INK = (26, 26, 30)
HAIR = (36, 32, 30)
SKIN = (233, 206, 181)
SKIN_SHADE = (208, 176, 149)
SHIRT = (246, 243, 233)
STRIPE = (27, 28, 34)

FONT_BOLD = r"C:\Windows\Fonts\georgiab.ttf"
FONT_REGULAR = r"C:\Windows\Fonts\georgia.ttf"

FIGURE_SCALE = 1.0
FIGURE_OFFSET = (18, 30)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def fit_font(text: str, max_width: int, start: int, bold: bool = True, floor: int = 40) -> ImageFont.FreeTypeFont:
    f = font(start, bold)
    while f.size > floor:
        box = f.getbbox(text)
        if box[2] - box[0] <= max_width:
            return f
        f = font(f.size - 2, bold)
    return f


def background() -> Image.Image:
    canvas = Image.new("RGB", (SIZE, SIZE), BG_TOP)
    draw = ImageDraw.Draw(canvas)
    for y in range(SIZE):
        t = (y / (SIZE - 1)) ** 0.85
        draw.line(
            [(0, y), (SIZE, y)],
            fill=(
                round(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t),
                round(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t),
                round(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t),
            ),
        )

    glow = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(glow).ellipse((-260, -420, 900, 700), fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(190))
    canvas = Image.composite(Image.new("RGB", (SIZE, SIZE), PAPER), canvas, glow)

    noise = Image.effect_noise((SIZE, SIZE), 14).convert("L")
    grain = Image.merge("RGB", (noise, noise, noise))
    canvas = Image.blend(canvas, grain, 0.055)

    screen = Image.new("L", (SIZE, SIZE), 0)
    screen_draw = ImageDraw.Draw(screen)
    for y in range(0, SIZE, 7):
        for x in range(0, SIZE, 7):
            screen_draw.ellipse((x, y, x + 3, y + 3), fill=24)
    screen = screen.filter(ImageFilter.GaussianBlur(0.7))
    canvas = Image.composite(Image.new("RGB", (SIZE, SIZE), (255, 255, 255)), canvas, screen)
    return canvas.convert("RGBA")


def letterspaced(text: str, f: ImageFont.FreeTypeFont, tracking: int, fill: tuple[int, int, int]) -> Image.Image:
    widths = [f.getbbox(ch)[2] - f.getbbox(ch)[0] for ch in text]
    box = f.getbbox(text)
    layer = Image.new("RGBA", (sum(widths) + tracking * (len(text) - 1) + 40, box[3] - box[1] + 60), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x = 20
    for ch, w in zip(text, widths):
        draw.text((x, 20), ch, font=f, fill=fill + (255,))
        x += w + tracking
    return layer


def wordmark(canvas: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas)
    f = fit_font("Silk Road", 762, 260, bold=True)
    text = "Silk Road"
    box = f.getbbox(text)
    x = (SIZE - (box[2] - box[0])) // 2 - box[0]
    y = 116 - box[1]
    draw.text((x + 3, y + 5), text, font=f, fill=(255, 255, 255, 150))
    draw.text((x, y), text, font=f, fill=GREEN_DEEP + (255,))

    caption = "ANONYMOUS MARKETPLACE"
    layer = letterspaced(caption, font(35, bold=False), 13, GREEN_MID)
    canvas.alpha_composite(layer, ((SIZE - layer.width) // 2, 346))

    rule_y = 372
    draw.line([(SIZE // 2 - 410, rule_y), (SIZE // 2 - 200, rule_y)], fill=GREEN_MID + (150,), width=2)
    draw.line([(SIZE // 2 + 200, rule_y), (SIZE // 2 + 410, rule_y)], fill=GREEN_MID + (150,), width=2)


def torso_mask() -> Image.Image:
    mask = Image.new("L", (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(mask)
    points = [
        (198, SIZE),
        (196, 902),
        (232, 834),
        (302, 780),
        (372, 748),
        (372, 706),
        (648, 706),
        (648, 748),
        (718, 780),
        (788, 834),
        (824, 902),
        (822, SIZE),
    ]
    draw.polygon(points, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(5)).point(lambda v: 255 if v > 120 else 0)


def figure_layer() -> Image.Image:
    mask = torso_mask()

    shirt = Image.new("RGBA", (SIZE, SIZE), SHIRT + (255,))
    sdraw = ImageDraw.Draw(shirt)
    for y in range(706, SIZE + 40, 46):
        sdraw.rectangle((0, y, SIZE, y + 22), fill=STRIPE + (255,))
    shade = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(shade).ellipse((-160, 800, 500, 1520), fill=86)
    shade = shade.filter(ImageFilter.GaussianBlur(130))
    shirt = Image.composite(Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 42)), shirt, shade)

    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    layer.paste(shirt, (0, 0), mask)

    # Neck sits behind both the shirt collar and the head.
    neck = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ndraw = ImageDraw.Draw(neck)
    ndraw.rounded_rectangle((474, 650, 552, 764), radius=22, fill=SKIN + (255,))
    ndraw.ellipse((474, 682, 552, 716), fill=SKIN_SHADE + (255,))
    layer.alpha_composite(neck)

    # Re-paste the shirt so the collar covers the neck base.
    neck_hidden = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    neck_hidden.paste(shirt, (0, 0), mask)
    layer.alpha_composite(neck_hidden)

    head = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(head)
    hdraw.ellipse((392, 440, 634, 700), fill=HAIR + (255,))
    hdraw.ellipse((414, 482, 612, 744), fill=SKIN + (255,))
    hdraw.ellipse((414, 482, 612, 566), fill=HAIR + (255,))
    hdraw.chord((414, 482, 612, 704), 200, 340, fill=HAIR + (255,))
    hdraw.rounded_rectangle((430, 582, 596, 618), radius=12, fill=INK + (255,))
    hdraw.line([(430, 600), (596, 600)], fill=(74, 74, 82, 255), width=2)
    layer.alpha_composite(head)
    return layer


def composition_shadow() -> Image.Image:
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", (SIZE, SIZE), (24, 40, 60, 96)), (14, 18), torso_mask())
    return shadow.filter(ImageFilter.GaussianBlur(16))


def figure(canvas: Image.Image) -> None:
    canvas.alpha_composite(composition_shadow())
    layer = figure_layer()
    scaled = layer.resize((round(SIZE * FIGURE_SCALE), round(SIZE * FIGURE_SCALE)), Image.LANCZOS)
    canvas.alpha_composite(scaled, FIGURE_OFFSET)


def ghost_hand(canvas: Image.Image) -> None:
    """Translucent hand entering from the right edge, fingers splayed upward."""
    scale = 4
    w, h = 384, 430
    pad = 40
    mask = Image.new("L", ((w + pad) * scale, (h + pad) * scale), 0)
    draw = ImageDraw.Draw(mask)

    def capsule(box: tuple[int, int, int, int]) -> None:
        x0, y0, x1, y1 = [v * scale for v in box]
        draw.rounded_rectangle((x0, y0, x1, y1), radius=(x1 - x0) // 2, fill=255)

    # Palm and wrist run off the right edge of the frame.
    capsule((196, 196, 330, 400))
    draw.rectangle((290 * scale, 250 * scale, (w + pad) * scale, 372 * scale), fill=255)
    # Four fingers, splayed slightly, all rooted inside the palm.
    capsule((134, 58, 178, 268))
    capsule((178, 26, 222, 268))
    capsule((222, 36, 266, 268))
    capsule((266, 78, 306, 280))
    # Thumb pushed out to the left.
    capsule((92, 176, 140, 320))

    mask = mask.filter(ImageFilter.GaussianBlur(1.2 * scale))
    mask = mask.resize((w + pad, h + pad), Image.LANCZOS)

    inner = mask.filter(ImageFilter.MinFilter(11))
    edge = ImageChops.subtract(mask, inner).filter(ImageFilter.GaussianBlur(0.8))

    hand = Image.new("RGBA", mask.size, (238, 247, 255, 0))
    hand.putalpha(mask.point(lambda v: int(v * 0.34)))
    rim_layer = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    rim_layer.putalpha(edge.point(lambda v: int(v * 0.55)))
    hand = Image.alpha_composite(hand, rim_layer)

    hand = hand.rotate(-14, resample=Image.BICUBIC, expand=False)
    canvas.alpha_composite(hand, (SIZE - w - 10, 396))


def bird(canvas: Image.Image) -> None:
    w, h = 230, 170
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    body = (34, 132, 68, 255)
    wing = (21, 100, 52, 255)
    draw.polygon([(16, 78), (62, 54), (108, 68), (74, 100)], fill=body)
    draw.ellipse((44, 42, 140, 110), fill=body)
    draw.ellipse((112, 26, 160, 74), fill=body)
    draw.polygon([(154, 42), (194, 53), (154, 62)], fill=(232, 168, 56, 255))
    draw.polygon([(58, 58), (104, 40), (122, 70), (82, 90), (62, 78)], fill=wing)
    draw.ellipse((132, 40, 143, 51), fill=(12, 44, 24, 255))
    draw.line([(88, 108), (86, 136)], fill=(24, 92, 48, 255), width=5)
    draw.line([(106, 108), (108, 136)], fill=(24, 92, 48, 255), width=5)
    draw.line([(80, 136), (92, 136)], fill=(24, 92, 48, 255), width=4)
    draw.line([(102, 136), (114, 136)], fill=(24, 92, 48, 255), width=4)
    layer = layer.rotate(-8, resample=Image.BICUBIC)
    canvas.alpha_composite(layer, (206, 690))


def main() -> int:
    canvas = background()
    ghost_hand(canvas)
    figure(canvas)
    bird(canvas)
    wordmark(canvas)

    canvas = canvas.convert("RGB")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({canvas.width}x{canvas.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())