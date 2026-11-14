#!/usr/bin/env python3
"""Generate the tearsgram bitmap assets from the files in branding/.

Inputs / outputs
----------------
branding/shit.png      -> branding/AppIcon-1024.png   primary Home Screen icon
branding/logo.png      -> mod-tools/app-icons/NGCustom1-*   "Icon 1"
branding/hubert.png    -> mod-tools/app-icons/NGCustom2-*   "Icon 2"
branding/shit.png      -> mod-tools/app-icons/NGCustom0-60@3x.png  picker preview
branding/twilight.png  -> .../TearsgramTwilightBadge.imageset
branding/trollface.png -> .../TearsgramTrollfaceBadge.imageset

There is no third alternate icon any more: NGCustom3-* is deleted on every run.

The badges are drawn at 279 x 66 px (93 x 22 pt @3x) so they match the stock
Swiftgram badge geometry and never overlap the compact Dynamic Island. They
have no rim, no border and no lettering unless a wordmark is requested.

Run after replacing any file in branding/:
    python tools/make_branding.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "branding" / "logo.png"
SHIT = ROOT / "branding" / "shit.png"
HUBERT = ROOT / "branding" / "hubert.png"
APP_ICON = ROOT / "branding" / "AppIcon-1024.png"
ICON_DIR = ROOT / "mod-tools" / "app-icons"
ASSETS_DIR = ROOT / "Swiftgram" / "SGAppBadgeAssets" / "Images.xcassets"
TWILIGHT_SOURCE = ROOT / "branding" / "twilight.png"
TROLLFACE_SOURCE = ROOT / "branding" / "trollface.png"

ICON_SIZES = (("60@2x", 120), ("60@3x", 180), ("76", 76), ("76@2x", 152), ("83.5@2x", 167))
ICON_PREVIEW = ICON_DIR / "NGCustom0-60@3x.png"

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


def build_badge() -> Image.Image:
    """Near-black pill with the white tearsgram wordmark, no rim, no thumbnail."""
    width, height = 279, 66
    badge = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = gradient.load()
    for x in range(width):
        for y in range(height):
            v = y / (height - 1)
            pixels[x, y] = (
                round(30 - 12 * v),
                round(30 - 12 * v),
                round(32 - 12 * v),
                255,
            )

    badge.paste(gradient, (0, 0), badge_pill_mask(width, height))

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


def opaque(image: Image.Image) -> Image.Image:
    """Home Screen icons must be opaque RGB: flatten any alpha onto white."""
    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, (255, 255, 255))
        canvas.paste(rgba, (0, 0), rgba)
        return canvas
    return image.convert("RGB")


def save_icon_set(source: Image.Image, name: str) -> None:
    artwork = opaque(source)
    for suffix, dimension in ICON_SIZES:
        save_png(artwork.resize((dimension, dimension), Image.LANCZOS), ICON_DIR / f"{name}-{suffix}.png")


def remove_icon_set(name: str) -> None:
    for suffix, _ in ICON_SIZES:
        path = ICON_DIR / f"{name}-{suffix}.png"
        if path.exists():
            path.unlink()
            print("  removed", path.relative_to(ROOT))


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    print("  ", path.relative_to(ROOT))


def badge_pill_mask(width: int, height: int, supersample: int = 4) -> Image.Image:
    """Anti-aliased pill mask: drawn 4x larger and downsampled, so the edge is
    smooth without any drawn rim or border."""
    big = Image.new("L", (width * supersample, height * supersample), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, width * supersample - 1, height * supersample - 1),
        radius=(height * supersample) // 2,
        fill=255,
    )
    return big.resize((width, height), Image.LANCZOS)


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
    text: str | None = None,
    scrim: int = 0,
    white: int = 0,
    chip: bool = False,
    text_fill: tuple[int, int, int] = (255, 255, 255),
    stroke: int = 0,
    stroke_fill: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Image badge: the picture fills the pill, optional wordmark on top.

    text  - None keeps the badge as a pure picture, no lettering
    scrim - how much black to lay over the photo (0-255) so white text reads
    white - how much white to lay over the photo (for dark-on-light artwork)
    chip  - draw a dark rounded plate behind the text

    No rim is drawn: the pill is only the picture cut by a smooth mask, exactly
    like the stock Swiftgram badges.
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
    if not text:
        return badge

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
    primary = SHIT if SHIT.exists() else LOGO
    if not primary.exists():
        print("branding/shit.png and branding/logo.png are missing, writing the default tearsgram wordmark")
        LOGO.parent.mkdir(parents=True, exist_ok=True)
        default_logo().save(LOGO, "PNG", optimize=True)
        primary = LOGO

    icon = build_icon(Image.open(primary).convert("RGB"))
    save_png(icon, APP_ICON)
    save_png(icon.resize((180, 180), Image.LANCZOS), ICON_PREVIEW)

    variants = (
        ("NGCustom1", LOGO),
        ("NGCustom2", HUBERT),
    )
    for name, source in variants:
        if source.exists():
            save_icon_set(build_icon(Image.open(source).convert("RGB")), name)
        else:
            print(f"  {source.relative_to(ROOT)} not found, skipping {name}")
    remove_icon_set("NGCustom3")

    badge = build_badge()
    save_badge_imageset(badge, "TearsgramAppBadge")

    if TWILIGHT_SOURCE.exists():
        save_badge_imageset(build_photo_badge(TWILIGHT_SOURCE), "TearsgramTwilightBadge")
    else:
        print("  branding/twilight.png not found, skipping the twilight badge")

    if TROLLFACE_SOURCE.exists():
        save_badge_imageset(build_photo_badge(TROLLFACE_SOURCE), "TearsgramTrollfaceBadge")
    else:
        print("  branding/trollface.png not found, skipping the trollface badge")

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())