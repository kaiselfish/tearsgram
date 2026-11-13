#!/usr/bin/env python3
"""Apply the tearsgram overlay to a checkout of gandon-pro/Swiftgram-Mod.

Usage (from the repository root):
    python tools/apply.py
    python tools/apply.py --repo C:\\path\\to\\tsg --check-only

The script is idempotent: running it twice produces the same tree and exits 0.
Every edit is anchored to text that exists in the upstream mod checkout; if an
anchor is missing the script prints the file and line and exits non-zero instead
of guessing.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent / "overlay"

CODE_DIRS = ("Swiftgram", "submodules", "Telegram", "mod-tools")

BRAND_REPLACEMENTS = (
    ("Niggagram", "tearsgram"),
    ("niggagram", "tearsgram"),
    ("NIGGAGRAM", "TEARSGRAM"),
    ("Nigga", "tearsgram"),
    ("NIGGA", "TEARSGRAM"),
)


class PatchError(RuntimeError):
    pass


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PatchError(message)


def replace_once(text: str, old: str, new: str, file: Path, label: str, marker: str | None = None) -> str:
    if marker is not None and marker in text:
        return text  # already applied
    count = text.count(old)
    if count == 0:
        if new in text:
            return text  # already applied
        raise PatchError(f"{file}: anchor not found for {label!r}:\n{old[:200]}")
    require(count == 1, f"{file}: anchor for {label!r} matched {count} times, expected 1")
    return text.replace(old, new, 1)


# --------------------------------------------------------------------------- #
# 1. Whole-file replacements
# --------------------------------------------------------------------------- #

def copy_overlay(repo: Path) -> list[str]:
    applied: list[str] = []
    for source in sorted(OVERLAY.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(OVERLAY)
        if relative.parts[0] == ".github":
            continue
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        new = source.read_bytes()
        if target.exists() and target.read_bytes() == new:
            continue
        target.write_bytes(new)
        applied.append(str(relative).replace("\\", "/"))
    workflow = OVERLAY / ".github/workflows/build-tearsgram.yml"
    if workflow.exists():
        target = repo / ".github/workflows/build-tearsgram.yml"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != workflow.read_bytes():
            shutil.copyfile(workflow, target)
            applied.append(".github/workflows/build-tearsgram.yml")
    return applied


# --------------------------------------------------------------------------- #
# 2. Badge renderer in Display/WindowContent.swift
# --------------------------------------------------------------------------- #

TEARSGRAM_BADGE_FUNCTION = '''/// tearsgram badge shown under the Dynamic Island in screenshots.
/// Same geometry as the stock badge: 93 x 22 pt (279 x 66 px @3x), so it does
/// not overlap the compact island on iPhone 14 Pro / Pro Max and later.
public func tearsgramAppBadgeImage() -> UIImage? {
    let size = CGSize(width: 93.0, height: 22.0)
    UIGraphicsBeginImageContextWithOptions(size, false, 0.0)
    defer { UIGraphicsEndImageContext() }

    let bounds = CGRect(origin: .zero, size: size)
    let pill = UIBezierPath(roundedRect: bounds, cornerRadius: size.height / 2.0)
    pill.addClip()

    // Palette taken from the tearsgram logo: deep forest green -> mint.
    let deep = UIColor(red: 0.042, green: 0.310, blue: 0.153, alpha: 1.0).cgColor
    let mid = UIColor(red: 0.086, green: 0.541, blue: 0.267, alpha: 1.0).cgColor
    if let context = UIGraphicsGetCurrentContext(),
       let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [deep, mid] as CFArray, locations: [0.0, 1.0]) {
        context.drawLinearGradient(gradient, start: CGPoint(x: 0.0, y: 0.0), end: CGPoint(x: size.width, y: 0.0), options: [])
    }

    // Logo mark: the app icon cropped into a circle when it is bundled,
    // otherwise a mint disc with the date-appropriate "t".
    let markRect = CGRect(x: 2.0, y: 2.0, width: 18.0, height: 18.0)
    UIGraphicsGetCurrentContext()?.saveGState()
    UIBezierPath(ovalIn: markRect).addClip()
    if let mark = UIImage(bundleImageName: "TearsgramBadgeMark") {
        mark.draw(in: markRect)
    } else {
        UIColor(red: 0.84, green: 0.96, blue: 0.88, alpha: 1.0).setFill()
        UIBezierPath(ovalIn: markRect).fill()
        let glyph = "t" as NSString
        let glyphFont = UIFont(descriptor: UIFont.systemFont(ofSize: 13.0, weight: .bold).fontDescriptor.withDesign(.serif) ?? UIFont.systemFont(ofSize: 13.0, weight: .bold).fontDescriptor, size: 13.0)
        let glyphSize = glyph.size(withAttributes: [.font: glyphFont])
        glyph.draw(at: CGPoint(x: markRect.midX - glyphSize.width / 2.0, y: markRect.midY - glyphSize.height / 2.0 - 0.5), withAttributes: [.font: glyphFont, .foregroundColor: UIColor(red: 0.042, green: 0.310, blue: 0.153, alpha: 1.0)])
    }
    UIGraphicsGetCurrentContext()?.restoreGState()

    let text = "tearsgram" as NSString
    let availableWidth = size.width - 24.0 - 4.0
    var font = UIFont(descriptor: UIFont.systemFont(ofSize: 11.0, weight: .semibold).fontDescriptor.withDesign(.rounded) ?? UIFont.systemFont(ofSize: 11.0, weight: .semibold).fontDescriptor, size: 11.0)
    let measuredWidth = text.size(withAttributes: [.font: font]).width
    if measuredWidth > availableWidth {
        font = font.withSize(font.pointSize * availableWidth / measuredWidth)
    }
    let textSize = text.size(withAttributes: [.font: font])
    let textRect = CGRect(x: 24.0 + (availableWidth - textSize.width) / 2.0, y: (size.height - textSize.height) / 2.0, width: textSize.width, height: textSize.height)
    text.draw(in: textRect, withAttributes: [.font: font, .foregroundColor: UIColor(red: 0.90, green: 0.98, blue: 0.92, alpha: 1.0)])
    return UIGraphicsGetImageFromCurrentImageContext()
}
'''

OLD_INIT = '''        let savedBadge = SGSimpleSettings.shared.customAppBadge
        if !savedBadge.isEmpty && savedBadge != "NiggagramAppBadge", let image = UIImage(bundleImageName: savedBadge) {
            self.badgeView.image = image
        } else {
            self.badgeView.image = niggagramAppBadgeImage()
        }
'''

NEW_INIT = '''        // Empty value (fresh install) means the tearsgram badge. Any saved
        // stock asset name, including "Components/AppBadge", wins over it.
        let savedBadge = SGSimpleSettings.shared.customAppBadge
        if !savedBadge.isEmpty, savedBadge != "TearsgramAppBadge", let image = UIImage(bundleImageName: savedBadge) {
            self.badgeView.image = image
        } else {
            self.badgeView.image = UIImage(bundleImageName: "TearsgramAppBadge") ?? tearsgramAppBadgeImage()
        }
'''


def patch_window_content(repo: Path) -> bool:
    path = repo / "submodules/Display/Source/WindowContent.swift"
    text = read(path)
    original = text

    if "func niggagramAppBadgeImage" in text:
        start = text.index("public func niggagramAppBadgeImage() -> UIImage? {")
        end_marker = "\nprivate struct WindowReservedArea"
        end = text.index(end_marker, start)
        text = text[:start] + TEARSGRAM_BADGE_FUNCTION + text[end:]

    if "tearsgramAppBadgeImage()" not in text:
        raise PatchError(f"{path}: badge renderer missing after patch")

    if OLD_INIT in text:
        text = text.replace(OLD_INIT, NEW_INIT, 1)
    elif NEW_INIT not in text:
        raise PatchError(f"{path}: Window1.init badge block not recognised")

    text = text.replace("niggagramAppBadgeImage()", "tearsgramAppBadgeImage()")

    if text != original:
        write(path, text)
        return True
    return False


# --------------------------------------------------------------------------- #
# 3. Settings screen: add the badge entry
# --------------------------------------------------------------------------- #

def patch_mod_settings(repo: Path) -> bool:
    path = repo / "Swiftgram/SGSettingsUI/Sources/SGModSettingsController.swift"
    text = read(path)
    original = text

    text = replace_once(
        text,
        "import SGItemListUI\nimport SGSimpleSettings",
        "import SGItemListUI\nimport SGSimpleSettings\nimport SGProUI",
        path,
        "SGProUI import",
        marker="import SGProUI",
    )

    text = replace_once(
        text,
        "private enum SGModLink: Hashable {\n    case archive\n    case pseudoPro\n    case icons\n}",
        "private enum SGModLink: Hashable {\n    case archive\n    case pseudoPro\n    case icons\n    case appBadge\n}",
        path,
        "SGModLink.appBadge",
        marker="case appBadge\n}",
    )

    text = replace_once(
        text,
        '        case .icons:\n            pushImpl?(sgModIconsController(context: context))',
        '        case .icons:\n            pushImpl?(sgModIconsController(context: context))\n'
        '        case .appBadge:\n'
        '            if #available(iOS 14.0, *) {\n'
        '                pushImpl?(sgAppBadgeSettingsController(context: context))\n'
        '            }',
        path,
        "SGModLink switch",
        marker="case .appBadge:",
    )

    anchor = 'entries.append(.disclosure(id: counter.count, section: .appearance, link: .icons, text: ru ? "Иконка приложения" : "App icon"))'
    addition = (
        anchor
        + "\n        if #available(iOS 14.0, *) {\n"
        + '            entries.append(.disclosure(id: counter.count, section: .appearance, link: .appBadge, text: ru ? "Значок приложения" : "App badge"))\n'
        + "        }"
    )
    text = replace_once(text, anchor, addition, path, "app badge row", marker="link: .appBadge")

    if text != original:
        write(path, text)
        return True
    return False


# --------------------------------------------------------------------------- #
# 4. Build graph: SGSettingsUI needs SGProUI
# --------------------------------------------------------------------------- #

def patch_settings_build(repo: Path) -> bool:
    path = repo / "Swiftgram/SGSettingsUI/BUILD"
    text = read(path)
    if "SGProUI:SGProUI" in text:
        return False
    anchor = '        "//Swiftgram/SGItemListUI:SGItemListUI",'
    require(anchor in text, f"{path}: SGItemListUI dependency line not found")
    text = text.replace(anchor, anchor + '\n        "//Swiftgram/SGProUI:SGProUI",', 1)
    write(path, text)
    return True


# --------------------------------------------------------------------------- #
# 4. Entry points: the mod settings screen has no caller in the upstream fork,
#    so wire it into the Swiftgram settings screen and a URL route.
# --------------------------------------------------------------------------- #

def patch_swiftgram_settings(repo: Path) -> bool:
    path = repo / "Swiftgram/SGSettingsUI/Sources/SGSettingsController.swift"
    text = read(path)
    original = text

    text = replace_once(
        text,
        "private enum SGDisclosureLink: String {\n    case contentSettings\n    case languageSettings\n}",
        "private enum SGDisclosureLink: String {\n    case contentSettings\n    case languageSettings\n    case tearsgram\n}",
        path,
        "SGDisclosureLink.tearsgram",
        marker="case tearsgram\n}",
    )

    anchor = "    let id = SGItemListCounter()\n"
    addition = (
        anchor
        + "    \n"
        + '    entries.append(.header(id: id.count, section: .content, text: "tearsgram", badge: nil))\n'
        + '    entries.append(.disclosure(id: id.count, section: .content, link: .tearsgram, text: presentationData.strings.baseLanguageCode.hasPrefix("ru") ? "Приватность, удалённые сообщения, значок" : "Privacy, deleted messages, app badge"))\n'
    )
    text = replace_once(text, anchor, addition, path, "tearsgram settings row", marker='text: "tearsgram", badge: nil')

    text = replace_once(
        text,
        "        switch (link) {\n            case .languageSettings:",
        "        switch (link) {\n"
        "            case .tearsgram:\n"
        "                pushControllerImpl?(sgModSettingsController(context: context))\n"
        "            case .languageSettings:",
        path,
        "tearsgram settings route",
        marker="case .tearsgram:",
    )

    if text != original:
        write(path, text)
        return True
    return False


def patch_url_routes(repo: Path) -> bool:
    path = repo / "Swiftgram/SGTelegramUIExtensions/Sources/SGTelegramUIExtensions.swift"
    text = read(path)
    if 'case "tearsgram", "mod":' in text:
        return False
    anchor = '    case "settings":\n        navigationController?.pushViewController(sgSettingsController(context: context))\n        return true\n'
    require(anchor in text, f"{path}: settings URL route not found")
    text = text.replace(
        anchor,
        anchor
        + '    case "tearsgram", "mod":\n'
        + '        navigationController?.pushViewController(sgModSettingsController(context: context))\n'
        + '        return true\n',
        1,
    )
    write(path, text)
    return True


# --------------------------------------------------------------------------- #
# 5. Global brand rename inside code directories
# --------------------------------------------------------------------------- #

TEXT_SUFFIXES = {".swift", ".py", ".plist", ".json", ".strings", ".bzl", ".build", ".sh", ".txt"}
TEXT_NAMES = {"BUILD", "BUILD.bazel", "WORKSPACE", "WORKSPACE.bazel"}


def is_text_source(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES or path.name in TEXT_NAMES


def brand_rename(repo: Path) -> list[str]:
    changed: list[str] = []
    for directory in CODE_DIRS:
        root = repo / directory
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or not is_text_source(path):
                continue
            if "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            updated = text
            for old, new in BRAND_REPLACEMENTS:
                updated = updated.replace(old, new)
            if updated != text:
                write(path, updated)
                changed.append(str(path.relative_to(repo)).replace("\\", "/"))
    return changed


# --------------------------------------------------------------------------- #
# 6. Verification
# --------------------------------------------------------------------------- #

def verify(repo: Path) -> list[str]:
    problems: list[str] = []
    leftover = re.compile(r"Nigga|NIGGA|niggagram|Niggagram")
    for directory in CODE_DIRS:
        root = repo / directory
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or not is_text_source(path) or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if leftover.search(line):
                    problems.append(f"{path.relative_to(repo)}:{number}: {line.strip()[:120]}")

    window = repo / "submodules/Display/Source/WindowContent.swift"
    if window.is_file():
        text = read(window)
        if "tearsgramAppBadgeImage" not in text:
            problems.append("WindowContent.swift: tearsgram badge renderer missing")
        if "NiggagramAppBadge" in text:
            problems.append("WindowContent.swift: old badge sentinel still present")

    badge_asset = repo / "Swiftgram/SGAppBadgeAssets/Images.xcassets/TearsgramAppBadge.imageset"
    if not badge_asset.is_dir():
        problems.append("TearsgramAppBadge.imageset is missing; run python tools/make_branding.py")

    settings = repo / "Swiftgram/SGSettingsUI/Sources/SGModSettingsController.swift"
    if settings.is_file():
        text = read(settings)
        for token, expected in (
            ("import SGProUI", 1),
            ("case appBadge\n}", 1),
            ("case .appBadge:", 1),
            ("link: .appBadge", 1),
        ):
            actual = text.count(token)
            if actual != expected:
                problems.append(f"SGModSettingsController.swift: {token!r} appears {actual} times, expected {expected}")
        if "sgAppBadgeSettingsController" not in text:
            problems.append("SGModSettingsController.swift: badge screen is not wired")

    settings_build = repo / "Swiftgram/SGSettingsUI/BUILD"
    if settings_build.is_file() and read(settings_build).count("SGProUI:SGProUI") != 1:
        problems.append("SGSettingsUI/BUILD: expected exactly one SGProUI dependency")

    swiftgram_settings = repo / "Swiftgram/SGSettingsUI/Sources/SGSettingsController.swift"
    if swiftgram_settings.is_file():
        text = read(swiftgram_settings)
        for token, expected in (
            ("case tearsgram\n}", 1),
            ("link: .tearsgram", 1),
            ("case .tearsgram:", 1),
            ("sgModSettingsController(context: context)", 1),
        ):
            actual = text.count(token)
            if actual != expected:
                problems.append(f"SGSettingsController.swift: {token!r} appears {actual} times, expected {expected}")

    routes = repo / "Swiftgram/SGTelegramUIExtensions/Sources/SGTelegramUIExtensions.swift"
    if routes.is_file() and read(routes).count('case "tearsgram", "mod":') != 1:
        problems.append("SGTelegramUIExtensions.swift: tg://tearsgram route is missing")

    icons = repo / "mod-tools/app-icons"
    for name in ("NGCustom1", "NGCustom2", "NGCustom3"):
        for suffix in ("60@2x", "60@3x", "76", "76@2x", "83.5@2x"):
            file = icons / f"{name}-{suffix}.png"
            if not file.is_file():
                problems.append(f"missing icon {file.relative_to(repo)}; run python tools/make_branding.py")

    for relative in (
        "mod-tools/brand-ipa.py",
        "mod-tools/prepare-mod-icon.py",
        ".github/workflows/build-tearsgram.yml",
        "branding/AppIcon-1024.png",
    ):
        if not (repo / relative).is_file():
            problems.append(f"missing {relative}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository root (default: cwd)")
    parser.add_argument("--check-only", action="store_true", help="only report what is missing")
    args = parser.parse_args()

    repo = args.repo.resolve()
    if not (repo / "submodules/Display/Source/WindowContent.swift").is_file():
        print(f"error: {repo} is not a Swiftgram-Mod checkout", file=sys.stderr)
        return 2

    if args.check_only:
        problems = verify(repo)
        for problem in problems:
            print(problem)
        return 1 if problems else 0

    try:
        copied = copy_overlay(repo)
        window_changed = patch_window_content(repo)
        settings_changed = patch_mod_settings(repo)
        build_changed = patch_settings_build(repo)
        swiftgram_settings_changed = patch_swiftgram_settings(repo)
        routes_changed = patch_url_routes(repo)
        renamed = brand_rename(repo)
    except PatchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print("overlay files written:", len(copied))
    for name in copied:
        print("  +", name)
    print("WindowContent.swift patched:", window_changed)
    print("SGModSettingsController.swift patched:", settings_changed)
    print("SGSettingsUI/BUILD patched:", build_changed)
    print("SGSettingsController.swift patched:", swiftgram_settings_changed)
    print("SGTelegramUIExtensions.swift patched:", routes_changed)
    print("files rebranded:", len(renamed))
    for name in renamed:
        print("  ~", name)

    problems = verify(repo)
    if problems:
        print("\nverification problems:", file=sys.stderr)
        for problem in problems:
            print("  !", problem, file=sys.stderr)
        return 1
    print("\nOK: tearsgram overlay applied. Commit and run the Build tearsgram workflow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())