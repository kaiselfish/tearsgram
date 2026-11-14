import Foundation
import UIKit
import UserNotifications
import AVFoundation
import SwiftSignalKit
import Postbox
import TelegramCore
import TelegramPresentationData
import TelegramUIPreferences
import LocalizedPeerData
import AccountContext
import SGSimpleSettings

// MARK: - Local notifications for a build without APNs
//
// A re-signed IPA (Sideloadly + free Apple ID) never receives an
// `aps-environment` entitlement, and the bundle id is no longer
// `ph.telegra.Telegraph`, so `registerForRemoteNotifications()` fails and
// Telegram's push pipeline can never deliver a payload. This file replaces the
// missing remote notifications with local ones:
//
//  * `SGBackgroundSilenceAudio` keeps the process running with a looping silent
//    track. `UIBackgroundModes` already contains `audio`.
//  * while running, `allowBackgroundTimeExtension` plus `shouldBeServiceTaskMaster`
//    keep Telegram's update loop connected, so new messages reach the postbox.
//  * `SGLocalNotificationManager` watches `pollStateUpdateCompletion()` and posts
//    a `UNNotificationRequest` per chat with a newer unread message, using the
//    peerId/accountId keys that `AppDelegate.userNotificationCenter(_:didReceive:)`
//    already understands, so tapping opens the chat.

private func sgLocalNotificationLog(_ text: String) {
    Logger.shared.log("SGLocalNotifications", text)
}

private let sgLastDeliveredIdsPrefix = "sg.localNotifications.lastIds."
private let sgMaximumMessageAge: Int32 = 300

// MARK: - Silent audio that keeps the process alive in the background

private final class SGBackgroundSilenceAudio {
    private var player: AVAudioPlayer?
    private var session: AVAudioSession?
    private var interruptionObserver: NSObjectProtocol?

    func start() {
        if self.player != nil {
            return
        }
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playback, mode: .default, options: [.mixWithOthers])
            try session.setActive(true)
        } catch {
            sgLocalNotificationLog("audio session unavailable: \(error)")
            return
        }
        guard let url = SGBackgroundSilenceAudio.silenceURL() else {
            try? session.setActive(false, options: [.notifyOthersOnDeactivation])
            return
        }
        do {
            let player = try AVAudioPlayer(contentsOf: url)
            player.numberOfLoops = -1
            // The file itself is all-zero samples, so full volume is still silence
            // and iOS keeps the audio session (and the process) alive.
            player.volume = 1.0
            player.prepareToPlay()
            guard player.play() else {
                sgLocalNotificationLog("silent player refused to start")
                try? session.setActive(false, options: [.notifyOthersOnDeactivation])
                return
            }
            self.player = player
            self.session = session
            self.observeInterruptions()
            sgLocalNotificationLog("background keep-alive audio started")
        } catch {
            sgLocalNotificationLog("silent player failed: \(error)")
            try? session.setActive(false, options: [.notifyOthersOnDeactivation])
        }
    }

    /// A phone call or an alarm deactivates the session; without this the process
    /// loses its audio background mode and is suspended after the interruption.
    private func observeInterruptions() {
        guard self.interruptionObserver == nil else {
            return
        }
        self.interruptionObserver = NotificationCenter.default.addObserver(
            forName: AVAudioSession.interruptionNotification,
            object: AVAudioSession.sharedInstance(),
            queue: OperationQueue.main,
            using: { [weak self] notification in
                guard let self else {
                    return
                }
                guard let rawType = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                    let type = AVAudioSession.InterruptionType(rawValue: rawType)
                else {
                    return
                }
                switch type {
                case .began:
                    sgLocalNotificationLog("audio interrupted")
                case .ended:
                    guard let player = self.player, self.session != nil else {
                        return
                    }
                    try? self.session?.setActive(true)
                    if !player.isPlaying {
                        _ = player.play()
                    }
                    sgLocalNotificationLog("audio resumed after interruption")
                @unknown default:
                    break
                }
            }
        )
    }

    func stop() {
        if let observer = self.interruptionObserver {
            NotificationCenter.default.removeObserver(observer)
            self.interruptionObserver = nil
        }
        self.player?.stop()
        self.player = nil
        let session = self.session
        self.session = nil
        try? session?.setActive(false, options: [.notifyOthersOnDeactivation])
        if session != nil {
            sgLocalNotificationLog("background keep-alive audio stopped")
        }
    }

    private static func silenceURL() -> URL? {
        let directory = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        let url = directory.appendingPathComponent("tearsgram-background-silence.wav")
        if FileManager.default.fileExists(atPath: url.path) {
            return url
        }
        guard let data = SGBackgroundSilenceAudio.silenceWavData(seconds: 1.0) else {
            return nil
        }
        do {
            try data.write(to: url, options: .atomic)
            return url
        } catch {
            sgLocalNotificationLog("could not write silence file: \(error)")
            return nil
        }
    }

    /// 8 kHz mono 16-bit PCM RIFF/WAVE full of zero samples.
    private static func silenceWavData(seconds: Double, sampleRate: Int = 8000) -> Data? {
        let frames = Int(Double(sampleRate) * seconds)
        guard frames > 0 else {
            return nil
        }
        let payloadBytes = frames * 2
        var data = Data(capacity: 44 + payloadBytes)

        func appendUInt32(_ value: UInt32) {
            var littleEndian = value.littleEndian
            withUnsafeBytes(of: &littleEndian) { data.append(contentsOf: $0) }
        }
        func appendUInt16(_ value: UInt16) {
            var littleEndian = value.littleEndian
            withUnsafeBytes(of: &littleEndian) { data.append(contentsOf: $0) }
        }
        func appendASCII(_ ascii: String) {
            data.append(contentsOf: Array(ascii.utf8))
        }

        appendASCII("RIFF")
        appendUInt32(UInt32(36 + payloadBytes))
        appendASCII("WAVE")
        appendASCII("fmt ")
        appendUInt32(UInt32(16))
        appendUInt16(UInt16(1))
        appendUInt16(UInt16(1))
        appendUInt32(UInt32(sampleRate))
        appendUInt32(UInt32(sampleRate * 2))
        appendUInt16(UInt16(2))
        appendUInt16(UInt16(16))
        appendASCII("data")
        appendUInt32(UInt32(payloadBytes))
        data.append(Data(count: payloadBytes))
        return data
    }
}

// MARK: - Per-account update watcher

private final class SGAccountNotificationWatcher {
    private let accountContext: AccountContext
    private let disposable = MetaDisposable()
    private var stopped = false

    init(accountContext: AccountContext) {
        self.accountContext = accountContext
        self.subscribe()
    }

    func stop() {
        self.stopped = true
        self.disposable.dispose()
    }

    private func subscribe() {
        guard !self.stopped else {
            return
        }
        let account = self.accountContext.account
        // One-shot signal: it completes after the next state update, so
        // re-subscribe to stay attached for the whole app lifetime.
        self.disposable.set((account.stateManager.pollStateUpdateCompletion()
        |> deliverOnMainQueue).start(next: { [weak self] _ in
            guard let self, !self.stopped else {
                return
            }
            SGLocalNotificationManager.shared.deliver(accountContext: self.accountContext)
        }, completed: { [weak self] in
            Queue.mainQueue().async {
                self?.subscribe()
            }
        }))
    }
}

// MARK: - Manager

final class SGLocalNotificationManager {
    static let shared = SGLocalNotificationManager()

    private var sharedContext: SharedAccountContextImpl?
    private var wakeupManager: SharedWakeupManager?
    private var accountsDisposable: Disposable?
    private var accountListDisposable: Disposable?
    private var watchers: [AccountRecordId: SGAccountNotificationWatcher] = [:]
    private var deliveryDisposables: [AccountRecordId: MetaDisposable] = [:]
    private var activeAccountContexts: [AccountContext] = []
    private var delivering: Set<AccountRecordId> = []
    private var isInForeground = true
    private var keepAliveDisposable: Disposable?

    private init() {
    }

    func activate(sharedContext: SharedAccountContextImpl, wakeupManager: SharedWakeupManager) {
        // `[self]`: the outer closure runs on the main queue and the manager is a
        // process-wide singleton, so an explicit strong capture is intentional
        // here; a nested `[weak self]` inside an implicitly-strong closure is a
        // Swift 6 error.
        Queue.mainQueue().async { [self] in
            guard self.accountsDisposable == nil else {
                return
            }
            self.sharedContext = sharedContext
            self.wakeupManager = wakeupManager
            self.requestAuthorizationIfNeeded()
            self.accountsDisposable = (sharedContext.activeAccountContexts
            |> deliverOnMainQueue).startStrict(next: { [weak self] accounts in
                self?.updateWatchedAccounts(accounts.accounts.map { $0.1 })
            })
        }
    }

    func setForeground(_ foreground: Bool) {
        guard self.isInForeground != foreground else {
            return
        }
        self.isInForeground = foreground
        if foreground {
            self.stopKeepAlive()
        } else {
            self.startKeepAliveIfNeeded()
        }
    }

    /// Used by the background refresh task: deliver for every signed-in account,
    /// then report completion.
    func deliverNow(completion: @escaping () -> Void) {
        guard SGPrivacySettings.localNotifications else {
            completion()
            return
        }
        if !self.activeAccountContexts.isEmpty {
            self.deliverAll(self.activeAccountContexts, completion: completion)
            return
        }
        // Cold background launch: the account list signal has not emitted yet.
        guard let sharedContext = self.sharedContext else {
            completion()
            return
        }
        let disposable = MetaDisposable()
        self.accountListDisposable = disposable
        disposable.set((sharedContext.activeAccountContexts
        |> take(1)
        |> deliverOnMainQueue).start(next: { [weak self] accounts in
            guard let self else {
                completion()
                return
            }
            let contexts = accounts.accounts.map { $0.1 }
            self.updateWatchedAccounts(contexts)
            self.deliverAll(contexts, completion: completion)
        }, completed: {
        }))
    }

    private func deliverAll(_ contexts: [AccountContext], completion: @escaping () -> Void) {
        if contexts.isEmpty {
            completion()
            return
        }
        let group = DispatchGroup()
        for context in contexts {
            group.enter()
            self.deliver(accountContext: context, completion: {
                group.leave()
            })
        }
        group.notify(queue: DispatchQueue.main) {
            completion()
        }
    }

    // MARK: delivery

    func deliver(accountContext: AccountContext, completion: (() -> Void)? = nil) {
        guard SGPrivacySettings.localNotifications else {
            completion?()
            return
        }
        let accountId = accountContext.account.id
        if self.delivering.contains(accountId) {
            completion?()
            return
        }
        self.delivering.insert(accountId)

        let presentationData = accountContext.sharedContext.currentPresentationData.with { $0 }
        let disposable = MetaDisposable()
        self.deliveryDisposables[accountId]?.dispose()
        self.deliveryDisposables[accountId] = disposable

        disposable.set((accountContext.account.viewTracker.tailChatListView(groupId: .root, count: 40)
        |> take(1)
        |> deliverOnMainQueue).start(next: { [weak self] view, _ in
            guard let self else {
                return
            }
            self.process(view: view, accountContext: accountContext, presentationData: presentationData)
        }, completed: { [weak self] in
            guard let self else {
                return
            }
            self.delivering.remove(accountId)
            self.deliveryDisposables.removeValue(forKey: accountId)
            completion?()
        }))
    }

    private func process(view: ChatListView, accountContext: AccountContext, presentationData: PresentationData) {
        let account = accountContext.account
        let storeKey = sgLastDeliveredIdsPrefix + "\(account.id.int64)"
        let rawStored = UserDefaults.standard.dictionary(forKey: storeKey) ?? [:]
        var stored: [String: Int] = [:]
        for (key, value) in rawStored {
            if let number = value as? NSNumber {
                stored[key] = number.intValue
            } else if let int = value as? Int {
                stored[key] = int
            }
        }
        var lastIds = stored
        var totalUnread: Int32 = 0
        let now = Int32(Date().timeIntervalSince1970)
        var delivered = 0

        for entry in view.entries {
            guard case let .MessageEntry(data) = entry else {
                continue
            }
            guard let readState = data.readState, readState.state.count > 0 else {
                continue
            }
            if !readState.isMuted {
                totalUnread += readState.state.count
            }
            guard let peer = data.renderedPeer.peer else {
                continue
            }
            let cloudMessages = data.messages.filter { $0.id.namespace == Namespaces.Message.Cloud }
            guard let topMessage = cloudMessages.max(by: { $0.id.id < $1.id.id }) else {
                continue
            }
            let peerKey = "\(data.renderedPeer.peerId.toInt64())"
            let previousId = lastIds[peerKey]
            let currentId = Int(topMessage.id.id)
            lastIds[peerKey] = max(currentId, previousId ?? 0)

            guard !self.isInForeground, !readState.isMuted else {
                continue
            }
            guard let previousId, currentId > previousId else {
                continue
            }
            guard now - topMessage.timestamp < sgMaximumMessageAge else {
                continue
            }
            guard topMessage.flags.contains(.Incoming) else {
                continue
            }
            self.post(notificationFor: topMessage, peer: peer, accountContext: accountContext, presentationData: presentationData, totalUnread: totalUnread)
            delivered += 1
        }

        if lastIds != stored {
            UserDefaults.standard.set(lastIds, forKey: storeKey)
        }
        if #available(iOS 16.0, *), totalUnread > 0 {
            UNUserNotificationCenter.current().setBadgeCount(Int(totalUnread), withCompletionHandler: nil)
        }
        if delivered > 0 {
            sgLocalNotificationLog("delivered \(delivered) notification(s) for account \(account.id.int64)")
        }
    }

    private func post(notificationFor message: Message, peer: Peer, accountContext: AccountContext, presentationData: PresentationData, totalUnread: Int32) {
        let strings = presentationData.strings
        var title = EnginePeer(peer).displayTitle(strings: strings, displayOrder: presentationData.nameDisplayOrder)
        if title.isEmpty {
            title = "tearsgram"
        }

        var body = EngineMessage(message).text
        if body.isEmpty {
            body = attachmentPlaceholder(for: message)
        }
        if let author = message.author, author.id != peer.id, (peer is TelegramGroup || peer is TelegramChannel) {
            let authorName = EnginePeer(author).displayTitle(strings: strings, displayOrder: presentationData.nameDisplayOrder)
            if !authorName.isEmpty, !body.isEmpty {
                body = "\(authorName): \(body)"
            }
        }
        if body.isEmpty {
            body = " "
        }

        let accountId = accountContext.account.id
        let threadIdentifier = "\(accountId.int64)_\(peer.id.toInt64())"

        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        content.threadIdentifier = threadIdentifier
        // The keys match AppDelegate.peerIdFromNotification / messageIdFromNotification,
        // so tapping the notification opens the exact chat and message.
        var userInfo: [AnyHashable: Any] = [:]
        userInfo["accountId"] = accountId.int64
        userInfo["peerId"] = peer.id.toInt64()
        userInfo["messageId.namespace"] = Int32(Namespaces.Message.Cloud)
        userInfo["messageId.id"] = message.id.id
        content.userInfo = userInfo
        if totalUnread > 0 {
            content.badge = NSNumber(value: Int(totalUnread))
        }
        if #available(iOS 15.0, *) {
            content.interruptionLevel = .active
        }

        let request = UNNotificationRequest(identifier: "sg.\(threadIdentifier)", content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request, withCompletionHandler: { error in
            if let error {
                sgLocalNotificationLog("could not deliver notification: \(error)")
            }
        })
    }

    // MARK: keep-alive

    private func startKeepAliveIfNeeded() {
        guard SGPrivacySettings.localNotifications, SGPrivacySettings.backgroundKeepAlive else {
            return
        }
        guard self.keepAliveDisposable == nil else {
            return
        }
        guard !self.activeAccountContexts.isEmpty else {
            return
        }

        let audio = SGBackgroundSilenceAudio()
        audio.start()

        let disposable = MetaDisposable()
        // 10 s keeps the explicit-extension deadline (30 s) always in the future,
        // while renewing the underlying background task a third as often as a
        // 5 s tick would.
        let timer = SwiftSignalKit.Timer(timeout: 10.0, repeat: true, completion: { [weak self] in
            guard let self else {
                return
            }
            guard SGPrivacySettings.localNotifications, SGPrivacySettings.backgroundKeepAlive, !self.isInForeground else {
                Queue.mainQueue().async {
                    self.stopKeepAlive()
                }
                return
            }
            // Keep the update loop master and the grace window open, otherwise
            // SharedWakeupManager pauses the connection a few seconds after the
            // app leaves the foreground and nothing new ever reaches the postbox.
            self.wakeupManager?.allowBackgroundTimeExtension(timeout: 30.0, extendNow: true)
            for context in self.activeAccountContexts {
                context.account.shouldBeServiceTaskMaster.set(.single(.always))
            }
        }, queue: .mainQueue())
        timer.start()
        disposable.set(ActionDisposable {
            timer.invalidate()
            audio.stop()
        })
        self.keepAliveDisposable = disposable
        sgLocalNotificationLog("background keep-alive enabled for \(self.activeAccountContexts.count) account(s)")
    }

    private func stopKeepAlive() {
        guard let disposable = self.keepAliveDisposable else {
            return
        }
        self.keepAliveDisposable = nil
        disposable.dispose()
    }

    // MARK: helpers

    private func updateWatchedAccounts(_ contexts: [AccountContext]) {
        self.activeAccountContexts = contexts
        var updated: [AccountRecordId: SGAccountNotificationWatcher] = [:]
        for context in contexts {
            let id = context.account.id
            if let existing = self.watchers[id] {
                updated[id] = existing
            } else {
                updated[id] = SGAccountNotificationWatcher(accountContext: context)
            }
        }
        for (id, watcher) in self.watchers where updated[id] == nil {
            watcher.stop()
        }
        self.watchers = updated
        if contexts.isEmpty {
            self.stopKeepAlive()
        } else if !self.isInForeground {
            self.startKeepAliveIfNeeded()
        }
    }

    private func requestAuthorizationIfNeeded() {
        let center = UNUserNotificationCenter.current()
        center.getNotificationSettings(completionHandler: { settings in
            guard settings.authorizationStatus == .notDetermined else {
                return
            }
            center.requestAuthorization(options: [.alert, .sound, .badge], completionHandler: { granted, error in
                sgLocalNotificationLog("notification authorization granted: \(granted) error: \(String(describing: error))")
            })
        })
    }

    private func attachmentPlaceholder(for message: Message) -> String {
        for media in message.media {
            if media is TelegramMediaImage {
                return "📷"
            }
            if let file = media as? TelegramMediaFile {
                if file.isSticker {
                    return "😀"
                }
                if file.isVideo {
                    return "🎬"
                }
                if file.isAnimated {
                    return "🎞"
                }
                if file.isVoice {
                    return "🎤"
                }
                return "📎"
            }
            if media is TelegramMediaPoll {
                return "📊"
            }
        }
        return "💬"
    }
}