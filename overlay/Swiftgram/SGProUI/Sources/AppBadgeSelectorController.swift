import Foundation
import SwiftUI
import SGSwiftUI
import SGStrings
import SGSimpleSettings
import LegacyUI
import Display
import TelegramPresentationData
import AccountContext

/// Sentinel asset name for the built-in tearsgram badge. It is not an
/// xcassets image: the image comes from `TearsgramAppBadge` or, if the asset
/// is missing from the bundle, from the runtime renderer in Display.
let tearsgramAppBadgeAssetName = "TearsgramAppBadge"

struct AppBadge: Identifiable, Hashable {
    var id: String { assetName }
    let displayName: String
    let assetName: String
}

func getAvailableAppBadges() -> [AppBadge] {
    var appBadges: [AppBadge] = [
        .init(displayName: "tearsgram", assetName: tearsgramAppBadgeAssetName),
        .init(displayName: "Swiftgram (Default)", assetName: "Components/AppBadge"),
        .init(displayName: "Sky", assetName: "SkyAppBadge"),
        .init(displayName: "Night", assetName: "NightAppBadge"),
        .init(displayName: "Titanium", assetName: "TitaniumAppBadge"),
        .init(displayName: "Pro", assetName: "ProAppBadge"),
        .init(displayName: "Day", assetName: "DayAppBadge"),
    ]

    if SGSimpleSettings.shared.duckyAppIconAvailable || SGPrivacySettings.swiftpseudoPro {
        appBadges.append(.init(displayName: "Ducky", assetName: "DuckyAppBadge"))
    }
    appBadges.append(.init(displayName: "Sparkling", assetName: "SparklingAppBadge"))

    return appBadges
}

/// Resolves a badge asset name to an image. The tearsgram badge exists both as
/// a compiled asset and as a runtime fallback, so a stripped or missing
/// Images.xcassets entry cannot leave the status bar without a badge.
func appBadgeImage(for assetName: String) -> UIImage? {
    if assetName == tearsgramAppBadgeAssetName {
        return UIImage(bundleImageName: tearsgramAppBadgeAssetName) ?? tearsgramAppBadgeImage()
    }
    return UIImage(bundleImageName: assetName)
}

@available(iOS 14.0, *)
struct AppBadgeSettingsView: View {
    weak var wrapperController: LegacyController?
    let context: AccountContext

    @Environment(\.colorScheme) var colorScheme
    @Environment(\.lang) var lang: String

    @State var selectedBadge: AppBadge
    let availableAppBadges: [AppBadge] = getAvailableAppBadges()

    private enum Layout {
        static let cardCorner: CGFloat = 12
        static let imageHeight: CGFloat = 56
        static let columnSpacing: CGFloat = 16
        static let horizontalPadding: CGFloat = 20
    }

    private var columns: [SwiftUI.GridItem] {
        Array(repeating: GridItem(.flexible(), spacing: Layout.columnSpacing), count: 2)
    }

    init(wrapperController: LegacyController?, context: AccountContext) {
        self.wrapperController = wrapperController
        self.context = context

        let savedAssetName = SGSimpleSettings.shared.customAppBadge
        let normalizedAssetName = savedAssetName.isEmpty ? tearsgramAppBadgeAssetName : savedAssetName
        if let badge = getAvailableAppBadges().first(where: { $0.assetName == normalizedAssetName }) {
            self._selectedBadge = State(initialValue: badge)
        } else {
            self._selectedBadge = State(initialValue: getAvailableAppBadges().first!)
        }
    }

    private func onSelectBadge(_ badge: AppBadge) {
        let image = appBadgeImage(for: badge.assetName)
        DispatchQueue.main.async {
            self.selectedBadge = badge
            SGSimpleSettings.shared.customAppBadge = badge.assetName
            SGSimpleSettings.shared.synchronizeShared()
            self.context.sharedContext.mainWindow?.badgeView.image = image
        }
    }

    var body: some View {
        ScrollView {
            LazyVGrid(columns: columns, alignment: .center, spacing: Layout.columnSpacing) {
                ForEach(availableAppBadges) { badge in
                    Button {
                        onSelectBadge(badge)
                    } label: {
                        VStack(spacing: 8) {
                            Image(uiImage: appBadgeImage(for: badge.assetName) ?? UIImage())
                                .resizable()
                                .scaledToFit()
                                .frame(height: Layout.imageHeight)
                                .accessibilityHidden(true)

                            Text(badge.displayName)
                                .font(.footnote)
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color(colorScheme == .dark ? .secondarySystemBackground : .systemBackground))
                        .cornerRadius(Layout.cardCorner)
                        .overlay(
                            RoundedRectangle(cornerRadius: Layout.cardCorner)
                                .stroke(selectedBadge == badge ? Color.accentColor : Color.clear, lineWidth: 2)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, Layout.horizontalPadding)
            .padding(.vertical, 24)
        }
        .background(Color(colorScheme == .light ? .secondarySystemBackground : .systemBackground).ignoresSafeArea())
    }
}

@available(iOS 14.0, *)
public func sgAppBadgeSettingsController(context: AccountContext, presentationData: PresentationData? = nil) -> ViewController {
    let theme = presentationData?.theme ?? (UITraitCollection.current.userInterfaceStyle == .dark ? defaultDarkColorPresentationTheme : defaultPresentationTheme)
    let strings = presentationData?.strings ?? defaultPresentationStrings

    let legacyController = LegacySwiftUIController(
        presentation: .navigation,
        theme: theme,
        strings: strings
    )

    legacyController.statusBar.statusBarStyle = theme.rootController
        .statusBarStyle.style
    legacyController.title = "AppBadge.Title".i18n(strings.baseLanguageCode)

    let swiftUIView = SGSwiftUIView<AppBadgeSettingsView>(
        legacyController: legacyController,
        manageSafeArea: true,
        content: {
            AppBadgeSettingsView(wrapperController: legacyController, context: context)
        }
    )
    let controller = UIHostingController(rootView: swiftUIView, ignoreSafeArea: true)
    legacyController.bind(controller: controller)

    return legacyController
}