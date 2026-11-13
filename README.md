Tearsgram – Modified Telegram for iOS
A modified Telegram build for iOS based on Swiftgram, featuring:
- A local archive of deleted messages.
- Ghost mode (hiding online, typing, read receipts, etc.).
- A custom badge above the Dynamic Island.
Base: Swiftgram/Telegram-iOS (Swiftgram 13.1.1, commit e3a392272b182dbf975d4ac5fc33b40a5954d749) + modification patches

Important: Building an .ipa file requires macOS. On Windows, you can store and edit the source code, but Xcode and Bazel for iOS cannot run there.

If you don't have a Mac, you can use GitHub Actions with a macOS runner. Instructions are provided below.

The CI-built artifact is signed with an upstream test certificate and must be re-signed using Sideloadly.


1. Features Already Included in the Base
The modification repository already implements both main features. The overlay only renames and extends them.
Feature	Location in source code
Deleted message archive (text + media links)	submodules/TelegramCore/Sources/Settings/SGDeletedMessages.swift
Interception of server-side deletions before they are applied	submodules/TelegramCore/Sources/State/HistoryViewStateValidation.swift (sgArchiveDeletedMessages)
Semi-transparent "left behind" message bubbles in chats	SGDeletedMessageAttribute
Archive screen	Swiftgram/SGSettingsUI/Sources/SGDeletedMessagesController.swift
Ghost mode (online / typing / recording / uploads / read / stories / interactions)	submodules/TelegramCore/Sources/State/Managed* + Swiftgram/SGSimpleSettings/Sources/SGPrivacySettings.swift
Badge above the Dynamic Island	submodules/Display/Source/WindowContent.swift (badgeView)
Background scanning for deleted messages	submodules/TelegramUI/Sources/AppDelegate.swift (deletedMessagesRefresh)

Important limitations
- Only messages that this client has already received and that still exist in the local Postbox database can be recovered. Messages deleted before the client was first launched will not appear.
- Secret chats, view-once media, and self-destructing media are intentionally excluded.
- The archive holds 200 entries by default. The limit can be changed in settings (1–10,000) or disabled using the "Unlimited Archive" toggle.
- Ghost mode suppresses outgoing indicators, but the server still sees messages, reactions, and calls being sent.
- Read receipts that have already been sent cannot be withdrawn.
-
- License and Legal Status
The Swiftgram/Telegram-iOS source code is distributed under GPL-like licenses. Modified source code must therefore be published.

This is an unofficial client. Do not use the Telegram name or present this build as an official Telegram application.

Note: The original Russian document cuts off mid-sentence at the end of this section, so the final sentence is incomplete in the source.

In short: This document explains how to create your own branded version of Swiftgram called Tearsgram, build it through GitHub Actions without owning a Mac, and install it on an iPhone using Sideloadly.
