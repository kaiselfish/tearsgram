#!/usr/bin/env python3
"""Generate tearsgram bitmap assets from branding/logo.png.

Outputs
-------
branding/AppIcon-1024.png                                  main app icon (@1x master)
mod-tools/app-icons/NGCustom{1,2,3}-*.png                  alternate icons for brand-ipa.py
Swiftgram/SGAppBadgeAssets/.../TearsgramAppBadge.imageset  badge under the Dynamic Island
Swiftgram/SGAppBadgeAssets/.../TearsgramTwilightBadge.imageset
Swiftgram/SGAppBadgeAssets/.../TearsgramTrollfaceBadge.imageset

The badges are drawn at 279 x 66 px (93 x 22 pt @3x) so they match the stock
Swiftgram badge geometry and never overlap the compact Dynamic Island.

Run after replacing branding/logo.png, branding/twilight.png or
branding/trollface.png:
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
ASSETS_DIR = ROOT / "Swiftgram" / "SGAppBadgeAssets" / "Images.xcassets"
TWILIGHT_SOURCE = ROOT / "branding" / "twilight.png"
TROLLFACE_SOURCE = ROOT / "branding" / "trollface.png"

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
    source = logo.convert("RGB")
    if source.size == (1024, 1024):
        return source
    scaled = cover(source, (1024, 1024))
    if source.width < 1024 or source.height < 1024:
        # Branding sources are usually smaller than the master; sharpen the
        # upscale so the icon does not look soft next to stock apps.
        scaled = scaled.filter(ImageFilter.UnsharpMask(radius=1.6, percent=55, threshold=2))
    return scaled


def build_badge(logo: Image.Image) -> Image.Image:
    """Near-black pill with the white tearsgram wordmark and no thumbnail."""
    width, height = 279, 66
    badge = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = gradient.load()
    for x in range(width):
        t = x / (width - 1)
        for y in range(height):
            v = y / (height - 1)
            pixels[x, y] = (
                round(30 - 12 * v),
                round(30 - 12 * v),
                round(32 - 12 * v),
                255,
            )

    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=height // 2, fill=255)
    badge.paste(gradient, (0, 0), mask)

    draw = ImageDraw.Draw(badge)
    # Hairline rim, like the system badge.
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=(height - 2) // 2, outline=(255, 255, 255, 30), width=2)

    draw = ImageDraw.Draw(badge)
    font = load_font(36, bold=True)
    text = "tearsgram"
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]
    available = width - 44
    while text_width > available and font.size > 12:
        font = load_font(font.size - 1, bold=True)
        box = draw.textbbox((0, 0), text, font=font)
        text_width = box[2] - box[0]
    x = (width - text_width) // 2 - box[0]
    y = (height - (box[3] - box[1])) // 2 - box[1]
    draw.text((x, y), text, font=font, fill=(246, 247, 249, 255))
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


def badge_pill_mask(width: int, height: int) -> Image.Image:
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=height // 2, fill=255)
    return mask


def fit_badge_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int = 36) -> ImageFont.FreeTypeFont:
    font = load_font(start, bold=True)
    while font.size > 12:
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
        font = load_font(font.size - 1, bold=True)
    return font


def build_photo_badge(
    source: Path,
    *,
    scrim: int = 0,
    white: int = 0,
    chip: bool = False,
    text_fill: tuple[int, int, int] = (255, 255, 255),
    stroke: int = 0,
    stroke_fill: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Full-bleed photo badge: the image fills the pill, the wordmark sits on top.

    scrim - how much black to lay over the photo (0-255) so white text reads
    white - how much white to lay over the photo (for dark-on-light artwork)
    chip  - draw a dark rounded plate behind the text
    stroke - outline width for the glyphs, for busy backgrounds
    """
    width, height = 279, 66
    photo = cover(Image.open(source).convert("RGB"), (width, height)).convert("RGBA")
    if scrim:
        photo = Image.alpha_composite(photo, Image.new("RGBA", (width, height), (0, 0, 0, scrim)))
    if white:
        photo = Image.alpha_composite(photo, Image.new("RGBA", (width, height), (255, 255, 255, white)))

    badge = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    badge.paste(photo, (0, 0), badge_pill_mask(width, height))

    draw = ImageDraw.Draw(badge)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=(height - 2) // 2, outline=(255, 255, 255, 46), width=2)

    text = "tearsgram"
    font = fit_badge_font(draw, text, width - 46)
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    centre = (width / 2.0, height / 2.0 + 1)

    if chip:
        pad_x, pad_y = 20, 10
        chip_width = text_width + pad_x * 2
        chip_height = text_height + pad_y * 2
        left = (width - chip_width) / 2
        top = (height - chip_height) / 2
        draw.rounded_rectangle(
            (left, top, left + chip_width, top + chip_height),
            radius=chip_height / 2,
            fill=(10, 10, 12, 208),
            outline=(255, 255, 255, 110),
            width=2,
        )
        draw.text(centre, text, font=font, anchor="mm", fill=text_fill + (255,))
        return badge

    if stroke:
        draw.text(centre, text, font=font, anchor="mm", fill=text_fill + (255,), stroke_width=stroke, stroke_fill=stroke_fill + (255,))
        return badge

    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((centre[0], centre[1] + 1.5), text, font=font, anchor="mm", fill=(0, 0, 0, 150))
    badge = Image.alpha_composite(badge, shadow.filter(ImageFilter.GaussianBlur(3)))
    draw = ImageDraw.Draw(badge)
    draw.text(centre, text, font=font, anchor="mm", fill=text_fill + (255,))
    return badge


def save_badge_imageset(image: Image.Image, name: str) -> None:
    directory = ASSETS_DIR / f"{name}.imageset"
    save_png(image, directory / f"{name}@3x.png")
    save_png(image.resize((186, 44), Image.LANCZOS), directory / f"{name}@2x.png")
    save_png(image.resize((93, 22), Image.LANCZOS), directory / f"{name}.png")
    contents = {
        "images": [
            {"filename": f"{name}.png", "idiom": "universal", "scale": "1x"},
            {"filename": f"{name}@2x.png", "idiom": "universal", "scale": "2x"},
            {"filename": f"{name}@3x.png", "idiom": "universal", "scale": "3x"},
        ],
        "info": {"author": "xcode", "version": 1},
    }
    path = directory / "Contents.json"
    path.write_text(json.dumps(contents, indent=2) + "\n", encoding="utf-8")
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
    save_badge_imageset(badge, "TearsgramAppBadge")

    if TWILIGHT_SOURCE.exists():
        save_badge_imageset(
            build_photo_badge(
                TWILIGHT_SOURCE,
                scrim=40,
                text_fill=(255, 255, 255),
                stroke=2,
                stroke_fill=(6, 10, 14),
            ),
            "TearsgramTwilightBadge",
        )
    else:
        print("  branding/twilight.png not found, skipping the twilight badge")

    if TROLLFACE_SOURCE.exists():
        save_badge_imageset(
            build_photo_badge(
                TROLLFACE_SOURCE,
                white=74,
                text_fill=(12, 12, 14),
                stroke=3,
                stroke_fill=(255, 255, 255),
            ),
            "TearsgramTrollfaceBadge",
        )
    else:
        print("  branding/trollface.png not found, skipping the trollface badge")

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())