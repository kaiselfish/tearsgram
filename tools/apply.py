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

    // Near-black pill; the bundled asset uses the same colours.
    let top = UIColor(red: 0.118, green: 0.118, blue: 0.125, alpha: 1.0).cgColor
    let bottom = UIColor(red: 0.043, green: 0.043, blue: 0.047, alpha: 1.0).cgColor
    if let context = UIGraphicsGetCurrentContext(),
       let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [top, bottom] as CFArray, locations: [0.0, 1.0]) {
        context.drawLinearGradient(gradient, start: CGPoint(x: 0.0, y: 0.0), end: CGPoint(x: 0.0, y: size.height), options: [])
    }

    let text = "tearsgram" as NSString
    let availableWidth = size.width - 22.0
    var font = UIFont(descriptor: UIFont.systemFont(ofSize: 12.0, weight: .semibold).fontDescriptor.withDesign(.serif) ?? UIFont.systemFont(ofSize: 12.0, weight: .semibold).fontDescriptor, size: 12.0)
    let measuredWidth = text.size(withAttributes: [.font: font]).width
    if measuredWidth > availableWidth {
        font = font.withSize(font.pointSize * availableWidth / measuredWidth)
    }
    let textSize = text.size(withAttributes: [.font: font])
    let textRect = CGRect(x: (size.width - textSize.width) / 2.0, y: (size.height - textSize.height) / 2.0, width: textSize.width, height: textSize.height)
    text.draw(in: textRect, withAttributes: [.font: font, .foregroundColor: UIColor(red: 0.965, green: 0.969, blue: 0.976, alpha: 1.0)])
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
# 5. Local notifications: APNs is unavailable for a re-signed build, so the
#    client posts its own notifications while it is alive in the background.
# --------------------------------------------------------------------------- #

LOCAL_NOTIFICATIONS_SETTINGS_OLD = """    public static var videoNotes60FPS: Bool {
        get { preference("sg.mod.videoNotes60FPS", defaultValue: false) }
        set { set(newValue, for: "sg.mod.videoNotes60FPS") }
    }
}"""

LOCAL_NOTIFICATIONS_SETTINGS_NEW = """    public static var videoNotes60FPS: Bool {
        get { preference("sg.mod.videoNotes60FPS", defaultValue: false) }
        set { set(newValue, for: "sg.mod.videoNotes60FPS") }
    }

    /// A re-signed build never receives the aps-environment entitlement, so the
    /// client renders its own notifications instead of server push.
    public static var localNotifications: Bool {
        get { preference("sg.mod.localNotifications", defaultValue: true) }
        set { set(newValue, for: "sg.mod.localNotifications") }
    }

    /// Keeps the process running in the background with looping silent audio so
    /// the update loop stays connected and new messages reach the postbox.
    public static var backgroundKeepAlive: Bool {
        get { preference("sg.mod.backgroundKeepAlive", defaultValue: true) }
        set { set(newValue, for: "sg.mod.backgroundKeepAlive") }
    }
}"""

QUIET_HOURS_SETTINGS_OLD = """    /// Keeps the process running in the background with looping silent audio so
    /// the update loop stays connected and new messages reach the postbox.
    public static var backgroundKeepAlive: Bool {
        get { preference("sg.mod.backgroundKeepAlive", defaultValue: true) }
        set { set(newValue, for: "sg.mod.backgroundKeepAlive") }
    }
}"""

QUIET_HOURS_SETTINGS_NEW = """    /// Keeps the process running in the background with looping silent audio so
    /// the update loop stays connected and new messages reach the postbox.
    public static var backgroundKeepAlive: Bool {
        get { preference("sg.mod.backgroundKeepAlive", defaultValue: true) }
        set { set(newValue, for: "sg.mod.backgroundKeepAlive") }
    }

    /// Banner suppression window, `"off"` or `"23-8"` in local time. While the
    /// window is open no banner is posted; when it closes one summary arrives.
    public static var quietHours: String {
        get { UserDefaults.standard.string(forKey: "sg.mod.quietHours") ?? "off" }
        set {
            UserDefaults.standard.set(newValue, forKey: "sg.mod.quietHours")
            NotificationCenter.default.post(name: changed, object: nil)
        }
    }

    public static func quietHoursLabel(russian: Bool) -> String {
        let parts = quietHours.split(separator: "-")
        guard parts.count == 2, let start = Int(parts[0]), let end = Int(parts[1]) else {
            return russian ? "Выкл" : "Off"
        }
        return String(format: "%02d:00 - %02d:00", start, end)
    }
}"""

KEEP_VIEW_ONCE_SETTINGS_OLD = """        return String(format: "%02d:00 - %02d:00", start, end)
    }
}"""

KEEP_VIEW_ONCE_SETTINGS_NEW = """        return String(format: "%02d:00 - %02d:00", start, end)
    }

    /// One-time photos and videos stay in the chat after they are opened.
    /// Telegram marks them consumed and replaces the media with a placeholder;
    /// the client skips that step and drops the one-time attributes instead.
    public static var keepViewOnceMedia: Bool {
        get { preference("sg.mod.keepViewOnce", defaultValue: true) }
        set { set(newValue, for: "sg.mod.keepViewOnce") }
    }
}"""

KEEP_ONCE_HELPER_ANCHOR = """private typealias SignalKitTimer = SwiftSignalKit.Timer

private final class ManagedAutoremoveMessageOperationsHelper {"""

KEEP_ONCE_HELPER = """private typealias SignalKitTimer = SwiftSignalKit.Timer

/// tearsgram: the toggle lives in the Swiftgram settings module, which sits
/// above TelegramCore in the build graph, so read the raw defaults key here.
func sgKeepViewOnceMediaEnabled() -> Bool {
    let defaults = UserDefaults.standard
    if defaults.object(forKey: "sg.mod.keepViewOnce") == nil {
        return true
    }
    return defaults.bool(forKey: "sg.mod.keepViewOnce")
}

private final class ManagedAutoremoveMessageOperationsHelper {"""

KEEP_ONCE_EXPIRY_OLD = """                        } else {
                            transaction.updateMessage(message.id, update: { currentMessage in
                                var storeForwardInfo: StoreMessageForwardInfo?"""

KEEP_ONCE_EXPIRY_NEW = """                        } else if sgKeepViewOnceMediaEnabled(), message.flags.contains(.Incoming), message.containsSecretMedia, let autoclear = message.autoclearAttribute, autoclear.timeout == viewOnceTimeout {
                            // tearsgram: a one-time photo or video has just been
                            // viewed. Drop the one-time attributes and keep the
                            // media, so the message turns into an ordinary
                            // attachment instead of an expired placeholder.
                            transaction.updateMessage(message.id, update: { currentMessage in
                                var storeForwardInfo: StoreMessageForwardInfo?
                                if let forwardInfo = currentMessage.forwardInfo {
                                    storeForwardInfo = StoreMessageForwardInfo(authorId: forwardInfo.author?.id, sourceId: forwardInfo.source?.id, sourceMessageId: forwardInfo.sourceMessageId, date: forwardInfo.date, authorSignature: forwardInfo.authorSignature, psaType: forwardInfo.psaType, flags: forwardInfo.flags)
                                }
                                var updatedAttributes = currentMessage.attributes
                                updatedAttributes.removeAll(where: { $0 is AutoclearTimeoutMessageAttribute })
                                updatedAttributes.removeAll(where: { $0 is ConsumableContentMessageAttribute })
                                return .update(StoreMessage(id: currentMessage.id, customStableId: nil, globallyUniqueId: currentMessage.globallyUniqueId, groupingKey: currentMessage.groupingKey, threadId: currentMessage.threadId, timestamp: currentMessage.timestamp, flags: StoreMessageFlags(currentMessage.flags), tags: currentMessage.tags, globalTags: currentMessage.globalTags, localTags: currentMessage.localTags, forwardInfo: storeForwardInfo, authorId: currentMessage.author?.id, text: currentMessage.text, attributes: updatedAttributes, media: currentMessage.media))
                            })
                            transaction.clearTimestampBasedAttribute(id: entry.messageId, tag: tag)
                        } else {
                            transaction.updateMessage(message.id, update: { currentMessage in
                                var storeForwardInfo: StoreMessageForwardInfo?"""

KEEP_ONCE_REMOTE_OLD = """                    if message.id.peerId.namespace == Namespaces.Peer.SecretChat {
                    } else {
                        for i in 0 ..< updatedMedia.count {
                            if attribute.timeout == viewOnceTimeout || timestamp >= autoremoveExpiryTimestamp(countdownBeginTime: countdownBeginTime, timeout: attribute.timeout) {"""

KEEP_ONCE_REMOTE_NEW = """                    if message.id.peerId.namespace == Namespaces.Peer.SecretChat {
                    } else {
                        let keepViewOnce = sgKeepViewOnceMediaEnabled() && attribute.timeout == viewOnceTimeout
                        for i in 0 ..< updatedMedia.count {
                            if !keepViewOnce, attribute.timeout == viewOnceTimeout || timestamp >= autoremoveExpiryTimestamp(countdownBeginTime: countdownBeginTime, timeout: attribute.timeout) {"""

BG_TASK_OLD = """	<key>BGTaskSchedulerPermittedIdentifiers</key>
	<array>
		<string>$(PRODUCT_BUNDLE_IDENTIFIER).refresh</string>
	</array>"""

BG_TASK_NEW = """	<key>BGTaskSchedulerPermittedIdentifiers</key>
	<array>
		<string>$(PRODUCT_BUNDLE_IDENTIFIER).refresh</string>
		<string>$(PRODUCT_BUNDLE_IDENTIFIER).deletedMessagesRefresh</string>
		<string>$(PRODUCT_BUNDLE_IDENTIFIER).cleanup</string>
	</array>"""


def patch_local_notification_settings(repo: Path) -> bool:
    path = repo / "Swiftgram/SGSimpleSettings/Sources/SGPrivacySettings.swift"
    text = read(path)
    changed = False
    if "sg.mod.localNotifications" not in text:
        require(LOCAL_NOTIFICATIONS_SETTINGS_OLD in text, f"{path}: videoNotes60FPS block not found")
        text = text.replace(LOCAL_NOTIFICATIONS_SETTINGS_OLD, LOCAL_NOTIFICATIONS_SETTINGS_NEW, 1)
        changed = True
    if "sg.mod.quietHours" not in text:
        require(QUIET_HOURS_SETTINGS_OLD in text, f"{path}: backgroundKeepAlive block not found")
        text = text.replace(QUIET_HOURS_SETTINGS_OLD, QUIET_HOURS_SETTINGS_NEW, 1)
        changed = True
    # The label is compared by the unit tests, so keep it ASCII-only.
    old_label = 'String(format: "%02d:00 \u2013 %02d:00"'
    if old_label in text:
        text = text.replace(old_label, 'String(format: "%02d:00 - %02d:00"', 1)
        changed = True
    if "sg.mod.keepViewOnce" not in text:
        require(KEEP_VIEW_ONCE_SETTINGS_OLD in text, f"{path}: quietHoursLabel block not found")
        text = text.replace(KEEP_VIEW_ONCE_SETTINGS_OLD, KEEP_VIEW_ONCE_SETTINGS_NEW, 1)
        changed = True
    if changed:
        write(path, text)
    return changed


def patch_notification_settings(repo: Path) -> bool:
    path = repo / "Swiftgram/SGSettingsUI/Sources/SGModSettingsController.swift"
    text = read(path)
    original = text

    text = replace_once(
        text,
        "    case camera\n    case voice\n}",
        "    case camera\n    case voice\n    case notifications\n}",
        path,
        "SGModSection.notifications",
        marker="case notifications\n}",
    )

    text = replace_once(
        text,
        "    case pseudoPro, ghost, deleted, unlimitedArchive, background, video60, online, afterSend, typing, recording, uploads, reads, stories, interactions\n}",
        "    case pseudoPro, ghost, deleted, unlimitedArchive, background, video60, online, afterSend, typing, recording, uploads, reads, stories, interactions\n"
        "    case localNotifications, backgroundKeepAlive\n}",
        path,
        "SGModToggle.localNotifications",
        marker="case localNotifications, backgroundKeepAlive\n}",
    )

    text = replace_once(
        text,
        "        case .video60:\n            SGPrivacySettings.videoNotes60FPS = value",
        "        case .video60:\n            SGPrivacySettings.videoNotes60FPS = value\n"
        "        case .localNotifications:\n            SGPrivacySettings.localNotifications = value\n"
        "        case .backgroundKeepAlive:\n            SGPrivacySettings.backgroundKeepAlive = value",
        path,
        "notification toggles",
        marker="case .localNotifications:",
    )

    anchor = (
        '        entries.append(.toggle(id: counter.count, section: .camera, settingName: .video60, '
        'value: SGPrivacySettings.videoNotes60FPS, text: ru ? "Кружки: 60 FPS" : "Video messages: 60 FPS", enabled: true))'
    )
    addition = (
        '        entries.append(.header(id: counter.count, section: .notifications, text: ru ? "Уведомления" : "Notifications", badge: nil))\n'
        "        entries.append(.toggle(id: counter.count, section: .notifications, settingName: .localNotifications, value: "
        'SGPrivacySettings.localNotifications, text: ru ? "Локальные уведомления" : "Local notifications", enabled: true))\n'
        "        entries.append(.toggle(id: counter.count, section: .notifications, settingName: .backgroundKeepAlive, value: "
        'SGPrivacySettings.backgroundKeepAlive, text: ru ? "Не засыпать в фоне" : "Stay awake in background", enabled: SGPrivacySettings.localNotifications))\n'
        "        entries.append(.notice(id: counter.count, section: .notifications, text: ru ? "
        '"Пуш-уведомления от серверов Telegram в этой сборке недоступны: переподписанная подпись не даёт доступ к APNs, '
        'а bundle id com.tearsgram.app не совпадает с темой пушей Telegram. Поэтому уведомления показывает сам клиент, '
        'пока остаётся запущенным. С включённым «Не засыпать в фоне» он держит соединение и тихо играет беззвучную дорожку '
        '(расход батареи выше). После принудительного закрытия из свайпа уведомления не приходят до следующего запуска." '
        ': "Push from Telegram servers cannot work in this build: a re-signed profile has no APNs access, and '
        "com.tearsgram.app does not match the push topic of Telegram. The client therefore posts its own notifications "
        "while it stays running. With Stay awake in background enabled it keeps the connection and plays a silent track "
        '(higher battery use). After a swipe-up force quit no notifications arrive until the next launch."))\n'
        + anchor
    )
    text = replace_once(text, anchor, addition, path, "notification rows", marker="section: .notifications, settingName: .localNotifications")

    if text != original:
        write(path, text)
        return True
    return False


QUIET_HOURS_SHEET_OLD = """    }, setOneFromManyValue: { setting in
        guard setting == "voiceEffect" else { return }"""

QUIET_HOURS_SHEET_NEW = """    }, setOneFromManyValue: { setting in
        if setting == "quietHours" {
            let data = context.sharedContext.currentPresentationData.with { $0 }
            let ru = data.strings.baseLanguageCode.hasPrefix("ru")
            let sheet = ActionSheetController(presentationData: data)
            let options: [(value: String, title: String)] = [
                (value: "off", title: ru ? "Выкл" : "Off"),
                (value: "23-8", title: "23:00 - 08:00"),
                (value: "22-7", title: "22:00 - 07:00"),
                (value: "0-7", title: "00:00 - 07:00"),
                (value: "1-9", title: "01:00 - 09:00")
            ]
            var items: [ActionSheetItem] = options.map { option in
                ActionSheetButtonItem(title: option.title, color: .accent, action: { [weak sheet] in
                    sheet?.dismissAnimated()
                    SGPrivacySettings.quietHours = option.value
                    changed.set(true)
                })
            }
            items.append(ActionSheetButtonItem(title: data.strings.Common_Cancel, color: .accent, font: .bold, action: { [weak sheet] in
                sheet?.dismissAnimated()
            }))
            sheet.setItemGroups([ActionSheetItemGroup(items: items)])
            presentImpl?(sheet, ViewControllerPresentationArguments(presentationAnimation: .modalSheet))
            return
        }
        guard setting == "voiceEffect" else { return }"""

TEST_NOTIFICATION_OLD = """    }, action: { action in
        if action == "saveArchiveLimit","""

TEST_NOTIFICATION_NEW = """    }, action: { action in
        if action == "testNotification" {
            let data = context.sharedContext.currentPresentationData.with { $0 }
            let ru = data.strings.baseLanguageCode.hasPrefix("ru")
            let now = Date()
            let formatter = DateFormatter()
            formatter.dateFormat = "HH:mm:ss"
            let content = UNMutableNotificationContent()
            content.title = "tearsgram"
            content.body = (ru ? "Проверка уведомлений в " : "Notification test at ") + formatter.string(from: now)
            content.sound = .default
            let identifier = "sg.test.\\(Int(now.timeIntervalSince1970))"
            let request = UNNotificationRequest(identifier: identifier, content: content, trigger: UNTimeIntervalNotificationTrigger(timeInterval: 5.0, repeats: false))
            UNUserNotificationCenter.current().add(request, withCompletionHandler: { _ in
            })
            return
        }
        if action == "saveArchiveLimit","""

QUIET_HOURS_ROWS_ANCHOR = "        entries.append(.toggle(id: counter.count, section: .camera, settingName: .video60,"

QUIET_HOURS_ROWS = (
    '        entries.append(.oneFromManySelector(id: counter.count, section: .notifications, settingName: "quietHours", '
    'text: ru ? "Тихие часы" : "Quiet hours", value: SGPrivacySettings.quietHoursLabel(russian: ru), '
    "enabled: SGPrivacySettings.localNotifications))\n"
    '        entries.append(.action(id: counter.count, section: .notifications, actionType: "testNotification", '
    'text: ru ? "Проверить уведомление" : "Send a test notification", kind: .generic))\n'
    "        entries.append(.notice(id: counter.count, section: .notifications, text: ru ? "
    '"Тихие часы: пока окно открыто, баннеры не показываются, но сообщения считаются. Когда окно закрывается, '
    "приходит одна сводка: сколько сообщений пришло и в скольких чатах. Если открыть приложение раньше, сводка "
    "не появится. «Проверить уведомление» пришлёт тестовый баннер через 5 секунд: нажми кнопку и сверни приложение.\" "
    ': "Quiet hours: while the window is open no banners are posted, but messages are counted. When the window closes '
    "one summary arrives with the number of messages and chats. Opening the app first drops the summary. Send a test "
    'notification posts a banner in 5 seconds: tap the button, then send the app to the background."))\n'
)


def patch_quiet_hours_ui(repo: Path) -> bool:
    path = repo / "Swiftgram/SGSettingsUI/Sources/SGModSettingsController.swift"
    text = read(path)
    original = text

    text = replace_once(
        text,
        "import SGProUI\n",
        "import SGProUI\nimport UserNotifications\n",
        path,
        "UserNotifications import",
        marker="import UserNotifications",
    )
    text = replace_once(
        text,
        QUIET_HOURS_SHEET_OLD,
        QUIET_HOURS_SHEET_NEW,
        path,
        "quiet hours selector",
        marker='if setting == "quietHours"',
    )
    text = replace_once(
        text,
        TEST_NOTIFICATION_OLD,
        TEST_NOTIFICATION_NEW,
        path,
        "test notification action",
        marker='if action == "testNotification"',
    )
    text = replace_once(
        text,
        QUIET_HOURS_ROWS_ANCHOR,
        QUIET_HOURS_ROWS + QUIET_HOURS_ROWS_ANCHOR,
        path,
        "quiet hours rows",
        marker='settingName: "quietHours"',
    )

    # Keep the sheet titles ASCII-only so they match the settings label.
    if "\u2013" in text:
        repaired: list[str] = []
        for line in text.splitlines(keepends=True):
            if 'title: "' in line:
                line = line.replace("\u2013", "-")
            repaired.append(line)
        text = "".join(repaired)

    if text != original:
        write(path, text)
        return True
    return False


def patch_view_once_media(repo: Path) -> bool:
    """Keep one-time photos and videos after they have been opened.

    Telegram marks such a message as consumed and immediately replaces the
    media with `TelegramMediaExpiredContent`. Skipping that replacement and
    dropping the one-time attributes turns the message into an ordinary
    attachment that can be opened again.
    """
    changed = False

    path = repo / "submodules/TelegramCore/Sources/State/ManagedAutoremoveMessageOperations.swift"
    text = read(path)
    original = text
    if "sgKeepViewOnceMediaEnabled" not in text:
        require(KEEP_ONCE_HELPER_ANCHOR in text, f"{path}: helper anchor not found")
        text = text.replace(KEEP_ONCE_HELPER_ANCHOR, KEEP_ONCE_HELPER, 1)
    text = replace_once(
        text,
        KEEP_ONCE_EXPIRY_OLD,
        KEEP_ONCE_EXPIRY_NEW,
        path,
        "keep consumed one-time media",
        marker="sgKeepViewOnceMediaEnabled(), message.flags.contains(.Incoming)",
    )
    if text != original:
        write(path, text)
        changed = True

    path = repo / "submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift"
    text = read(path)
    original = text
    text = replace_once(
        text,
        KEEP_ONCE_REMOTE_OLD,
        KEEP_ONCE_REMOTE_NEW,
        path,
        "keep remotely consumed one-time media",
        marker="let keepViewOnce = sgKeepViewOnceMediaEnabled()",
    )
    if text != original:
        write(path, text)
        changed = True

    path = repo / "Swiftgram/SGSettingsUI/Sources/SGModSettingsController.swift"
    text = read(path)
    original = text
    text = replace_once(
        text,
        "    case localNotifications, backgroundKeepAlive\n}",
        "    case localNotifications, backgroundKeepAlive\n    case keepViewOnce\n}",
        path,
        "SGModToggle.keepViewOnce",
        marker="case keepViewOnce\n}",
    )
    text = replace_once(
        text,
        "        case .deleted:\n"
        "            SGPrivacySettings.keepDeletedMessages = value\n"
        "            if !value {\n"
        "                // Remove only locally retained, server-deleted rows from this account.\n"
        "                let _ = sgRemoveRetainedMessages(postbox: context.account.postbox).start()\n"
        "            }\n",
        "        case .deleted:\n"
        "            SGPrivacySettings.keepDeletedMessages = value\n"
        "            if !value {\n"
        "                // Remove only locally retained, server-deleted rows from this account.\n"
        "                let _ = sgRemoveRetainedMessages(postbox: context.account.postbox).start()\n"
        "            }\n"
        "        case .keepViewOnce:\n"
        "            SGPrivacySettings.keepViewOnceMedia = value\n",
        path,
        "keep once toggle handler",
        marker="case .keepViewOnce:",
    )
    anchor = (
        '        entries.append(.header(id: counter.count, section: .notifications, '
        'text: ru ? "Уведомления" : "Notifications", badge: nil))'
    )
    addition = (
        "        entries.append(.toggle(id: counter.count, section: .deleted, settingName: .keepViewOnce, "
        'value: SGPrivacySettings.keepViewOnceMedia, text: ru ? "Одноразовые фото и видео" : "Keep one-time photos and videos", enabled: true))\n'
        "        entries.append(.notice(id: counter.count, section: .deleted, text: ru ? "
        '"После просмотра одноразовое фото или видео остаётся в чате как обычное вложение: его можно открыть снова, '
        "переслать или сохранить. Отметка о просмотре всё равно уходит отправителю. Работает для входящих в облачных "
        'чатах; секретные чаты не затрагиваются." '
        ': "After viewing, a one-time photo or video stays in the chat as an ordinary attachment: it can be opened '
        "again, forwarded or saved. The read receipt is still sent to the sender. Works for incoming media in cloud "
        'chats; secret chats are not affected."))\n'
        + anchor
    )
    text = replace_once(
        text,
        anchor,
        addition,
        path,
        "keep once rows",
        marker="section: .deleted, settingName: .keepViewOnce",
    )
    if text != original:
        write(path, text)
        changed = True

    return changed


def patch_local_notifications(repo: Path) -> bool:
    path = repo / "submodules/TelegramUI/Sources/AppDelegate.swift"
    text = read(path)
    original = text

    text = replace_once(
        text,
        "            let sharedApplicationContext = SharedApplicationContext(sharedContext: sharedContext, notificationManager: notificationManager, wakeupManager: wakeupManager)",
        "            let sharedApplicationContext = SharedApplicationContext(sharedContext: sharedContext, notificationManager: notificationManager, wakeupManager: wakeupManager)\n"
        "            SGLocalNotificationManager.shared.activate(sharedContext: sharedContext, wakeupManager: wakeupManager)",
        path,
        "local notification activation",
        marker="SGLocalNotificationManager.shared.activate(",
    )

    text = replace_once(
        text,
        "    func handleWillEnterForeground() {\n",
        "    func handleWillEnterForeground() {\n        SGLocalNotificationManager.shared.setForeground(true)\n",
        path,
        "local notification foreground",
        marker="SGLocalNotificationManager.shared.setForeground(true)",
    )

    text = replace_once(
        text,
        "    func handleDidEnterBackground() {\n        self.scheduleDeletedMessagesRefresh()",
        "    func handleDidEnterBackground() {\n        SGLocalNotificationManager.shared.setForeground(false)\n        self.scheduleDeletedMessagesRefresh()",
        path,
        "local notification background",
        marker="SGLocalNotificationManager.shared.setForeground(false)",
    )

    text = replace_once(
        text,
        "                guard SGPrivacySettings.keepDeletedMessages && SGPrivacySettings.backgroundDeletedMessages else {\n"
        "                    task.setTaskCompleted(success: true)\n"
        "                    return\n"
        "                }",
        "                guard SGPrivacySettings.localNotifications || (SGPrivacySettings.keepDeletedMessages && SGPrivacySettings.backgroundDeletedMessages) else {\n"
        "                    task.setTaskCompleted(success: true)\n"
        "                    return\n"
        "                }",
        path,
        "background refresh gate",
        marker="guard SGPrivacySettings.localNotifications || (SGPrivacySettings.keepDeletedMessages && SGPrivacySettings.backgroundDeletedMessages) else {\n                    task.setTaskCompleted",
    )

    text = replace_once(
        text,
        "                    context.wakeupManager.replaceCurrentExtensionWithExternalTime(completion: { finish(true) }, timeout: 25.0)",
        "                    context.wakeupManager.replaceCurrentExtensionWithExternalTime(completion: {\n"
        "                        SGLocalNotificationManager.shared.deliverNow(completion: {\n"
        "                            finish(true)\n"
        "                        })\n"
        "                    }, timeout: 25.0)",
        path,
        "background refresh notifications",
        marker="SGLocalNotificationManager.shared.deliverNow(",
    )

    text = replace_once(
        text,
        '        let identifier = "\\(Bundle.main.bundleIdentifier!).deletedMessagesRefresh"\n'
        "        guard SGPrivacySettings.keepDeletedMessages && SGPrivacySettings.backgroundDeletedMessages else {",
        '        let identifier = "\\(Bundle.main.bundleIdentifier!).deletedMessagesRefresh"\n'
        "        guard SGPrivacySettings.localNotifications || (SGPrivacySettings.keepDeletedMessages && SGPrivacySettings.backgroundDeletedMessages) else {",
        path,
        "background refresh scheduling",
        marker="SGPrivacySettings.localNotifications || (SGPrivacySettings.keepDeletedMessages && SGPrivacySettings.backgroundDeletedMessages) else {\n            BGTaskScheduler",
    )

    if text != original:
        write(path, text)
        return True
    return False


def patch_background_tasks(repo: Path) -> bool:
    changed = False
    for relative in ("Telegram/Telegram-iOS/Info.plist", "Telegram/Telegram-iOS/InfoBazel.plist"):
        path = repo / relative
        if not path.is_file():
            raise PatchError(f"{relative}: not found")
        text = read(path)
        if "deletedMessagesRefresh" in text:
            continue
        require(BG_TASK_OLD in text, f"{path}: BGTaskSchedulerPermittedIdentifiers block not found")
        write(path, text.replace(BG_TASK_OLD, BG_TASK_NEW, 1))
        changed = True
    return changed


# --------------------------------------------------------------------------- #
# 6. Global brand rename inside code directories
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

    for extra in ("TearsgramTwilightBadge", "TearsgramTrollfaceBadge"):
        asset = repo / f"Swiftgram/SGAppBadgeAssets/Images.xcassets/{extra}.imageset"
        if not asset.is_dir():
            problems.append(f"{extra}.imageset is missing; run python tools/make_branding.py")
        selector = repo / "Swiftgram/SGProUI/Sources/AppBadgeSelectorController.swift"
        if selector.is_file() and f'"{extra}"' not in read(selector):
            problems.append(f"AppBadgeSelectorController.swift: {extra} is not listed")

    settings = repo / "Swiftgram/SGSettingsUI/Sources/SGModSettingsController.swift"
    if settings.is_file():
        text = read(settings)
        for token, expected in (
            ("import SGProUI", 1),
            ("case appBadge\n}", 1),
            ("case .appBadge:", 1),
            ("link: .appBadge", 1),
            ("section: .notifications, settingName: .localNotifications", 1),
            ('settingName: "quietHours"', 1),
            ('actionType: "testNotification"', 1),
            ("import UserNotifications", 1),
            ("section: .deleted, settingName: .keepViewOnce", 1),
            ("case keepViewOnce\n}", 1),
            ("case .keepViewOnce:", 1),
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

    local_notifications = repo / "submodules/TelegramUI/Sources/SGLocalNotifications.swift"
    if not local_notifications.is_file():
        problems.append("SGLocalNotifications.swift is missing from submodules/TelegramUI/Sources")
    else:
        text = read(local_notifications)
        for token in ("SGBackgroundSilenceAudio", "SGAccountNotificationWatcher", "setBadgeCount", "threadIdentifier", "quietHoursRange", "flushQuietDigest"):
            if token not in text:
                problems.append(f"SGLocalNotifications.swift: {token} is missing")

    autoremove = repo / "submodules/TelegramCore/Sources/State/ManagedAutoremoveMessageOperations.swift"
    if not autoremove.is_file():
        problems.append("ManagedAutoremoveMessageOperations.swift is missing from TelegramCore")
    else:
        text = read(autoremove)
        for token in (
            "func sgKeepViewOnceMediaEnabled()",
            "sgKeepViewOnceMediaEnabled(), message.flags.contains(.Incoming)",
            "updatedAttributes.removeAll(where: { $0 is ConsumableContentMessageAttribute })",
        ):
            if token not in text:
                problems.append(f"ManagedAutoremoveMessageOperations.swift: {token} is missing")

    consumed = repo / "submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift"
    if consumed.is_file() and "let keepViewOnce = sgKeepViewOnceMediaEnabled()" not in read(consumed):
        problems.append("MarkMessageContentAsConsumedInteractively.swift: remote consumption is not guarded")

    privacy_settings = repo / "Swiftgram/SGSimpleSettings/Sources/SGPrivacySettings.swift"
    if privacy_settings.is_file():
        text = read(privacy_settings)
        # Each key legitimately appears twice: once in the getter and once in the setter.
        for key, declaration in (
            ("sg.mod.localNotifications", "public static var localNotifications: Bool"),
            ("sg.mod.backgroundKeepAlive", "public static var backgroundKeepAlive: Bool"),
            ("sg.mod.quietHours", "public static var quietHours: String"),
            ("sg.mod.keepViewOnce", "public static var keepViewOnceMedia: Bool"),
        ):
            if text.count(key) != 2:
                problems.append(f"SGPrivacySettings.swift: {key!r} appears {text.count(key)} times, expected 2")
            if text.count(declaration) != 1:
                problems.append(
                    f"SGPrivacySettings.swift: {declaration!r} appears {text.count(declaration)} times, expected 1"
                )
        if text.count("func quietHoursLabel") != 1:
            problems.append("SGPrivacySettings.swift: quietHoursLabel is missing")

    app_delegate = repo / "submodules/TelegramUI/Sources/AppDelegate.swift"
    if app_delegate.is_file():
        text = read(app_delegate)
        for token in (
            "SGLocalNotificationManager.shared.activate(",
            "SGLocalNotificationManager.shared.setForeground(true)",
            "SGLocalNotificationManager.shared.setForeground(false)",
            "SGLocalNotificationManager.shared.deliverNow(",
        ):
            if text.count(token) != 1:
                problems.append(f"AppDelegate.swift: {token!r} appears {text.count(token)} times, expected 1")
        if "SGPrivacySettings.localNotifications || (SGPrivacySettings.keepDeletedMessages && SGPrivacySettings.backgroundDeletedMessages)" not in text:
            problems.append("AppDelegate.swift: background refresh does not run for local notifications")

    for relative in ("Telegram/Telegram-iOS/Info.plist", "Telegram/Telegram-iOS/InfoBazel.plist"):
        path = repo / relative
        if not path.is_file():
            problems.append(f"missing {relative}")
            continue
        text = read(path)
        for identifier in ("refresh", "deletedMessagesRefresh", "cleanup"):
            if f"$(PRODUCT_BUNDLE_IDENTIFIER).{identifier}</string>" not in text:
                problems.append(f"{relative}: $(PRODUCT_BUNDLE_IDENTIFIER).{identifier} is not a permitted background task")

    icons = repo / "mod-tools/app-icons"
    icon_suffixes = ("60@2x", "60@3x", "76", "76@2x", "83.5@2x")
    for name in ("NGCustom1", "NGCustom2"):
        for suffix in icon_suffixes:
            file = icons / f"{name}-{suffix}.png"
            if not file.is_file():
                problems.append(f"missing icon {file.relative_to(repo)}; run python tools/make_branding.py")
    if not (icons / "NGCustom0-60@3x.png").is_file():
        problems.append("missing icon mod-tools/app-icons/NGCustom0-60@3x.png; run python tools/make_branding.py")
    for suffix in icon_suffixes:
        stale = icons / f"NGCustom3-{suffix}.png"
        if stale.is_file():
            problems.append(f"stale icon {stale.relative_to(repo)}; run python tools/make_branding.py")

    brand_ipa = repo / "mod-tools/brand-ipa.py"
    if brand_ipa.is_file():
        text = read(brand_ipa)
        if "NGCustom3" in text:
            problems.append("mod-tools/brand-ipa.py: NGCustom3 is still packaged")
        if "DEFAULT_ICON_PREVIEW" not in text:
            problems.append("mod-tools/brand-ipa.py: primary icon preview is not embedded")

    mod_icons = repo / "Swiftgram/SGSettingsUI/Sources/SGModIconsController.swift"
    if mod_icons.is_file():
        text = read(mod_icons)
        if "NGCustom0-60@3x" not in text:
            problems.append("SGModIconsController.swift: default icon preview is not wired")
        if "for index in 1 ... 3 {" in text:
            problems.append("SGModIconsController.swift: hard-coded 1 ... 3 icon loop is still present")

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
        notification_settings_changed = patch_local_notification_settings(repo)
        notification_ui_changed = patch_notification_settings(repo)
        quiet_hours_changed = patch_quiet_hours_ui(repo)
        view_once_changed = patch_view_once_media(repo)
        local_notifications_changed = patch_local_notifications(repo)
        background_tasks_changed = patch_background_tasks(repo)
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
    print("SGPrivacySettings.swift patched:", notification_settings_changed)
    print("notification settings rows patched:", notification_ui_changed)
    print("quiet hours rows patched:", quiet_hours_changed)
    print("one-time media retention patched:", view_once_changed)
    print("AppDelegate.swift local notifications patched:", local_notifications_changed)
    print("background task identifiers patched:", background_tasks_changed)
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