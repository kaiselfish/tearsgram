#!/usr/bin/env python3
"""Generate tearsgram bitmap assets from branding/logo.png.

Outputs
-------
branding/AppIcon-1024.png                                  main app icon (@1x master)
mod-tools/app-icons/NGCustom{1,2,3}-*.png                  alternate icons for brand-ipa.py
Swiftgram/SGAppBadgeAssets/.../TearsgramAppBadge.imageset  badge under the Dynamic Island

The badge is drawn at 279 x 66 px (93 x 22 pt @3x) so it matches the stock
Swiftgram badge geometry and never overlaps the compact Dynamic Island.

Run after replacing branding/logo.png:
    python tools/make_branding.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "branding" / "logo.png"
APP_ICON = ROOT / "branding" / "AppIcon-1024.png"
ICON_DIR = ROOT / "mod-tools" / "app-icons"
BADGE_DIR = ROOT / "Swiftgram" / "SGAppBadgeAssets" / "Images.xcassets" / "TearsgramAppBadge.imageset"

DEEP = (11, 79, 39)
MID = (22, 144, 63)
MINT = (234, 251, 239)
SKY_TOP = (234, 243, 252)
SKY_BOTTOM = (198, 221, 241)

FONT_CANDIDATES_BOLD = (
    r"C:\Windows\Fonts\georgiab.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
)
FONT_CANDIDATES_REGULAR = (
    r"C:\Windows\Fonts\georgia.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
)


def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES_BOLD if bold else FONT_CANDIDATES_REGULAR:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size)


def cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    width, height = size
    scale = max(width / image.width, height / image.height)
    resized = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def default_logo() -> Image.Image:
    """Placeholder wordmark in the logo palette; replace branding/logo.png."""
    size = 1024
    icon = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(icon)
    for y in range(size):
        t = y / (size - 1)
        draw.line(
            [(0, y), (size, y)],
            fill=(
                round(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t),
                round(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t),
                round(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t),
            ),
        )

    bloom = Image.new("L", (size, size), 0)
    ImageDraw.Draw(bloom).ellipse((90, 40, 760, 700), fill=110)
    bloom = bloom.filter(ImageFilter.GaussianBlur(160))
    icon = Image.composite(Image.new("RGB", (size, size), (255, 255, 255)), icon, bloom)

    draw = ImageDraw.Draw(icon)
    monogram = load_font(620, bold=True)
    text = "t"
    box = draw.textbbox((0, 0), text, font=monogram)
    draw.text(
        ((size - (box[2] - box[0])) / 2 - box[0], 130 - box[1]),
        text,
        font=monogram,
        fill=DEEP,
    )

    wordmark = load_font(132, bold=True)
    label = "tearsgram"
    box = draw.textbbox((0, 0), label, font=wordmark)
    draw.text(((size - (box[2] - box[0])) / 2 - box[0], 680), label, font=wordmark, fill=MID)
    return icon


def build_icon(logo: Image.Image) -> Image.Image:
    if logo.size == (1024, 1024):
        return logo.convert("RGB")
    return cover(logo.convert("RGB"), (1024, 1024))


def build_badge(logo: Image.Image) -> Image.Image:
    """Pale-blue pill with the artwork cropped into a disc and green wordmark."""
    width, height = 279, 66
    badge = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)

    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = gradient.load()
    for x in range(width):
        t = x / (width - 1)
        t = t ** 0.9
        pixels_row = (
            round(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t),
            round(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t),
            round(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t),
            255,
        )
        for y in range(height):
            pixels[x, y] = pixels_row

    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=height // 2, fill=255)
    badge.paste(gradient, (0, 0), mask)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=(height - 2) // 2, outline=MID + (110,), width=2)

    # The artwork itself, cropped into a disc on the left. The crop is centred
    # on the masked bust so the disc reads as a portrait and not as squashed
    # title text at 18 pt.
    mark_size = 54
    mark_box = (6, (height - mark_size) // 2)
    source = logo.convert("RGB")
    side = int(min(source.width, source.height) * 0.56)
    cx = source.width // 2
    cy = min(source.height, int(source.height * 0.70))
    left = max(0, min(source.width - side, cx - side // 2))
    top = max(0, min(source.height - side, cy - side // 2))
    mark = cover(source.crop((left, top, left + side, top + side)), (mark_size, mark_size)).convert("RGBA")
    mark_mask = Image.new("L", (mark_size, mark_size), 0)
    ImageDraw.Draw(mark_mask).ellipse((0, 0, mark_size - 1, mark_size - 1), fill=255)
    badge.paste(mark, mark_box, mark_mask)
    draw.ellipse(
        (mark_box[0], mark_box[1], mark_box[0] + mark_size - 1, mark_box[1] + mark_size - 1),
        outline=(255, 255, 255, 235),
        width=2,
    )

    font = load_font(34, bold=True)
    text = "tearsgram"
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]
    available = width - (mark_box[0] + mark_size + 10) - 10
    while text_width > available and font.size > 12:
        font = load_font(font.size - 1, bold=True)
        box = draw.textbbox((0, 0), text, font=font)
        text_width = box[2] - box[0]
    x = mark_box[0] + mark_size + 10 + (available - text_width) // 2 - box[0]
    y = (height - (box[3] - box[1])) // 2 - box[1]
    draw.text((x, y), text, font=font, fill=DEEP + (255,))
    return badge


def alternate(base: Image.Image, tint: tuple[int, int, int, int] | None) -> Image.Image:
    icon = base.convert("RGBA")
    if tint is not None:
        overlay = Image.new("RGBA", icon.size, tint)
        icon = Image.alpha_composite(icon, overlay)
    return icon.convert("RGB")


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    print("  ", path.relative_to(ROOT))


def main() -> int:
    if not LOGO.exists():
        print(f"branding/logo.png not found, writing the default tearsgram wordmark")
        LOGO.parent.mkdir(parents=True, exist_ok=True)
        default_logo().save(LOGO, "PNG", optimize=True)

    logo = Image.open(LOGO).convert("RGB")
    icon = build_icon(logo)
    save_png(icon, APP_ICON)

    variants = (
        ("NGCustom1", None),
        ("NGCustom2", (10, 90, 45, 70)),
        ("NGCustom3", (20, 60, 120, 55)),
    )
    sizes = (("60@2x", 120), ("60@3x", 180), ("76", 76), ("76@2x", 152), ("83.5@2x", 167))
    for name, tint in variants:
        artwork = alternate(icon, tint)
        for suffix, dimension in sizes:
            save_png(artwork.resize((dimension, dimension), Image.LANCZOS), ICON_DIR / f"{name}-{suffix}.png")

    badge = build_badge(logo)
    save_png(badge, BADGE_DIR / "TearsgramAppBadge@3x.png")
    save_png(badge.resize((186, 44), Image.LANCZOS), BADGE_DIR / "TearsgramAppBadge@2x.png")
    save_png(badge.resize((93, 22), Image.LANCZOS), BADGE_DIR / "TearsgramAppBadge.png")

    contents = {
        "images": [
            {"filename": "TearsgramAppBadge.png", "idiom": "universal", "scale": "1x"},
            {"filename": "TearsgramAppBadge@2x.png", "idiom": "universal", "scale": "2x"},
            {"filename": "TearsgramAppBadge@3x.png", "idiom": "universal", "scale": "3x"},
        ],
        "info": {"author": "xcode", "version": 1},
    }
    path = BADGE_DIR / "Contents.json"
    path.write_text(json.dumps(contents, indent=2) + "\n", encoding="utf-8")
    print("  ", path.relative_to(ROOT))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())