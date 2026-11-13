# tearsgram: точный список изменений поверх Swiftgram-Mod

Все правки делает `tools/apply.py`. Ниже — что именно и в каком файле.

| Файл | Изменение |
| --- | --- |
| `Swiftgram/SGProUI/Sources/AppBadgeSelectorController.swift` | Полная замена. Первым и дефолтным значком становится `TearsgramAppBadge`; добавлен штатный `Components/AppBadge` и остальные стоковые; убран гейт Pro; выбор применяется к `mainWindow.badgeView.image` сразу |
| `submodules/Display/Source/WindowContent.swift` | `niggagramAppBadgeImage()` → `tearsgramAppBadgeImage()` (зелёный градиент пилюли, логотип, надпись `tearsgram`); в `Window1.init` значение по умолчанию — tearsgram, стоковый ассет — если он сохранён пользователем |
| `Swiftgram/SGSettingsUI/Sources/SGModSettingsController.swift` | `import SGProUI`; `SGModLink.appBadge`; строка «Значок приложения / App badge» в разделе «Оформление»; переход на `sgAppBadgeSettingsController`; заголовок экрана `Nigga` → `tearsgram` |
| `Swiftgram/SGSettingsUI/Sources/SGSettingsController.swift` | `SGDisclosureLink.tearsgram`; заголовок-секция `tearsgram` и ссылка `Приватность, удалённые сообщения, значок / Privacy, deleted messages, app badge` вверху списка; в обработчике `link` — `pushControllerImpl?(sgModSettingsController(context: context))` |
| `Swiftgram/SGTelegramUIExtensions/Sources/SGTelegramUIExtensions.swift` | внутренние роуты `case "tearsgram", "mod":` → `sgModSettingsController` (рядом с существующим `case "settings":`) |
| `Swiftgram/SGSettingsUI/BUILD` | зависимость `//Swiftgram/SGProUI:SGProUI` |
| `Telegram/BUILD` | все `<string>Niggagram</string>` → `<string>tearsgram</string>`, `Open in Swiftgram` → `Open in tearsgram` |
| `submodules/TelegramUI/Sources/AppDelegate.swift` | текст ошибки хранилища `Niggagram ...` → `tearsgram ...` |
| `mod-tools/brand-ipa.py` | `BUNDLE_ID = "com.tearsgram.app"`, `APP_NAME = "tearsgram"` |
| `mod-tools/prepare-mod-icon.py` | источник иконки — `branding/AppIcon-1024.png` вместо `ModPrivacy.imageset/icon.jpg` |
| `Swiftgram/SGAppBadgeAssets/.../TearsgramAppBadge.imageset/` | новый ассет значка (93×22 pt, @1x/@2x/@3x) |
| `mod-tools/app-icons/NGCustom*.png` | альтернативные иконки tearsgram (120/180/76/152/167 px, RGB без альфы) |
| `.github/workflows/build-tearsgram.yml` | новый workflow: имя, артефакт `tearsgram-IPA-<n>`, файл `tearsgram-resign-required.ipa` |

## Что НЕ меняется

- Логика архива удалённых сообщений (`SGDeletedMessages.swift`) — используется как есть.
- Перехват удаления в `HistoryViewStateValidation.swift` — как есть.
- Подавление индикаторов призрака — как есть.
- `versions.json`, `MODULE.bazel`, тестовая подпись — как есть.

## Почему понадобились две дополнительные правки

В `gandon-pro/Swiftgram-Mod` функция `sgModSettingsController(context:)` объявлена, но не
вызывается ни из одного файла дерева (проверка: `GET /repos/gandon-pro/Swiftgram-Mod/git/trees/master?recursive=1`
+ полный текст `SGSettingsController.swift`, `ThemeSettingsController.swift`, `AccountContext.swift`,
`SharedAccountContext.swift`, `OpenUrl.swift` — вхождений `sgModSettingsController`/`SGModSettings` нет).
Экран с призраком, архивом и лимитами был недостижим. Оверлей добавляет ровно один UI-вход
(`SGSettingsController`) и один URL-вход (`tg://sg/tearsgram`), саму логику не трогая.

## Идентификаторы

- Bundle id: `com.tearsgram.app`
- App Group: `group.com.tearsgram.app` (при переподписи может отсутствовать — есть fallback)
- BGTask: `com.tearsgram.app.deletedMessagesRefresh`
- Display name: `tearsgram`
- Artifact: `tearsgram-IPA-<run_number>`
- Внутренний роут: `tg://sg/tearsgram`, алиас `tg://sg/mod` (хост `sg` — общий для всех
  Swiftgram-роутов, см. `OpenUrl.swift`, `case "sg":`)

## Значок: геометрия

Штатный `Components/AppBadge` — 279×66 px при @3x, то есть 93×22 pt. Пилюля вплотную
подходит к компактному Dynamic Island на 14 Pro/15/16/17, поэтому tearsgram-ассет и
runtime-рендерер используют ровно этот размер. Смещение по вертикали задаётся отдельно
в `Swiftgram/SGAppBadgeOffset/Sources/SGAppBadgeOffset.swift` (18…22 pt для устройств
с Dynamic Island) и оверлеем не меняется.