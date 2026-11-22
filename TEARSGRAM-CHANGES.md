# tearsgram: точный список изменений поверх Swiftgram-Mod

Все правки делает `tools/apply.py`. Ниже — что именно и в каком файле.

| Файл | Изменение |
| --- | --- |
| `Swiftgram/SGProUI/Sources/AppBadgeSelectorController.swift` | Полная замена. Первым и дефолтным значком становится `TearsgramAppBadge`; добавлены `Twilight` (`TearsgramTwilightBadge`) и `Trollface` (`TearsgramTrollfaceBadge`), затем штатный `Components/AppBadge` и остальные стоковые; убран гейт Pro; выбор применяется к `mainWindow.badgeView.image` сразу |
| `submodules/Display/Source/WindowContent.swift` | `niggagramAppBadgeImage()` → `tearsgramAppBadgeImage()` (чёрная пилюля-градиент и белая серифная надпись `tearsgram`, без рамки); в `Window1.init` значение по умолчанию — tearsgram, стоковый ассет — если он сохранён пользователем |
| `Swiftgram/SGSettingsUI/Sources/SGModSettingsController.swift` | `import SGProUI`; `SGModLink.appBadge`; строка «Значок приложения / App badge» в разделе «Оформление»; переход на `sgAppBadgeSettingsController`; заголовок экрана `Nigga` → `tearsgram` |
| `Swiftgram/SGSettingsUI/Sources/SGSettingsController.swift` | `SGDisclosureLink.tearsgram`; заголовок-секция `tearsgram` и ссылка `Приватность, удалённые сообщения, значок / Privacy, deleted messages, app badge` вверху списка; в обработчике `link` — `pushControllerImpl?(sgModSettingsController(context: context))` |
| `Swiftgram/SGTelegramUIExtensions/Sources/SGTelegramUIExtensions.swift` | внутренние роуты `case "tearsgram", "mod":` → `sgModSettingsController` (рядом с существующим `case "settings":`) |
| `Swiftgram/SGSimpleSettings/Sources/SGPrivacySettings.swift` | Новые настройки `localNotifications` и `backgroundKeepAlive` (обе включены по умолчанию) |
| `submodules/TelegramUI/Sources/SGLocalNotifications.swift` | Новый файл. Локальные уведомления вместо невозможного APNs: сторож `pollStateUpdateCompletion()`, беззвучная дорожка, продление фонового времени, `UNNotificationRequest` с ключами `accountId`/`peerId`/`messageId.*` |
| `submodules/TelegramUI/Sources/AppDelegate.swift` | Активация менеджера уведомлений, переключение фона/форграунда, доставка уведомлений в фоновой задаче `deletedMessagesRefresh` |
| `Telegram/Telegram-iOS/Info.plist`, `InfoBazel.plist` | `BGTaskSchedulerPermittedIdentifiers`: добавлены `.deletedMessagesRefresh` и `.cleanup` (без них iOS не запускает задачу и пишет в лог отказ) |
| `Swiftgram/SGSettingsUI/BUILD` | зависимость `//Swiftgram/SGProUI:SGProUI` |
| `Telegram/BUILD` | все `<string>Niggagram</string>` → `<string>tearsgram</string>`, `Open in Swiftgram` → `Open in tearsgram` |
| `submodules/TelegramUI/Sources/AppDelegate.swift` | текст ошибки хранилища `Niggagram ...` → `tearsgram ...` |
| `mod-tools/brand-ipa.py` | `BUNDLE_ID = "com.tearsgram.app"`, `APP_NAME = "tearsgram"` |
| `mod-tools/prepare-mod-icon.py` | источник иконки — `branding/AppIcon-1024.png` вместо `ModPrivacy.imageset/icon.jpg` |
| `Swiftgram/SGSettingsUI/Sources/SGModIconsController.swift` | Полная замена. Список иконок строится по фактически упакованным `CFBundleAlternateIcons` (без жёсткого `1 ... 3`), у «Стандартной» превью берётся из `NGCustom0-60@3x.png`, устаревший выбор сбрасывается на дефолт |
| `Swiftgram/SGAppBadgeAssets/.../TearsgramAppBadge.imageset/` | новый ассет значка (93×22 pt, @1x/@2x/@3x), без рамки |
| `Swiftgram/SGAppBadgeAssets/.../TearsgramTwilightBadge.imageset/`, `.../TearsgramTrollfaceBadge.imageset/` | фото-бейджи из `branding/twilight.png` и `branding/trollface.png`: картинка в пилюле, без текста и без окантовки |
| `mod-tools/app-icons/NGCustom{1,2}-*.png` | альтернативные иконки (120/180/76/152/167 px, RGB без альфы): `NGCustom1` из `branding/logo.png`, `NGCustom2` из `branding/hubert.png`; третьей иконки нет |
| `mod-tools/app-icons/NGCustom0-60@3x.png` | превью главной иконки для списка выбора; `brand-ipa.py` кладёт его в корень `.app` |
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

Рамки нет ни у одного из трёх бейджей: пилюля вырезается маской, нарисованной в 4× и
уменьшенной LANCZOS, поэтому край сглажен без нарисованной обводки.

## Иконки

| Строка в настройках | Регистрация | Источник |
| --- | --- | --- |
| `Стандартная` | основной `Assets.car` (Icon Composer `ModIcon.png`) | `branding/shit.png` |
| `Иконка 1` | `CFBundleAlternateIcons["NGCustom1"]` | `branding/logo.png` |
| `Иконка 2` | `CFBundleAlternateIcons["NGCustom2"]` | `branding/hubert.png` |

`mod-tools/brand-ipa.py` регистрирует ровно `NGCustom1` и `NGCustom2` и кладёт рядом
`NGCustom0-60@3x.png` — превью главной иконки для списка. Экрана «Иконка 3» больше нет:
строки строятся по фактическому содержимому `CFBundleAlternateIcons`.

## Уведомления: почему пуша нет и что вместо него

Переподписанный `.ipa` (Sideloadly + бесплатный Apple ID) не получает entitlement
`aps-environment`: в профиле его нет, а сам профиль создан для `com.tearsgram.app`.
Серверы Telegram отправляют пуши в тему `ph.telegra.Telegraph`, подменить её чужим
bundle id нельзя. Итог: `registerForRemoteNotifications()` не даёт токен, и ни один
серверный пуш до устройства не доходит — это ограничение подписи, а не баг клиента.

Поэтому уведомления показывает сам клиент, пока он жив:

1. `SGAccountNotificationWatcher` подписывается на `pollStateUpdateCompletion()`
   каждого аккаунта. Сигнал одноразовый (отдаёт `[MessageId]` и завершается), поэтому
   после каждого события подписка сразу восстанавливается.
2. На событии `SGLocalNotificationManager` читает `tailChatListView(groupId: .root, count: 40)`
   и по каждому чату с непрочитанными сравнивает верхний id с сохранённым в
   `UserDefaults` (`sg.localNotifications.lastIds.<accountId>`). Уведомление ставится, если
   id вырос, сообщение входящее, чат не заглушён, приложение не на переднем плане и
   сообщению меньше 300 секунд.
3. Текст уведомления — `title` из имени чата, `body` из текста или типа вложения,
   в группах и каналах — с именем автора. `threadIdentifier` и `identifier` содержат
   `accountId` и `peerId`, `userInfo` — те же ключи, что разбирает
   `AppDelegate.userNotificationCenter(_:didReceive:)`, поэтому тап открывает нужный чат
   и сообщение. Значок приложения — суммарное число непрочитанных (`setBadgeCount`, iOS 16+).
4. `SGBackgroundSilenceAudio` играет сгенерированный WAV из нулевых сэмплов
   (8 кГц, 16 бит, 1 с, `numberOfLoops = -1`) в категории `.playback` с `.mixWithOthers`.
   `UIBackgroundModes` уже содержит `audio`, поэтому процесс не приостанавливается.
5. Раз в 10 секунд таймер вызывает `allowBackgroundTimeExtension(timeout: 30, extendNow: true)`
   и ставит `shouldBeServiceTaskMaster = .always`. Без этого `SharedWakeupManager.updateAccounts`
   через несколько секунд после ухода в фон снимает мастерство и останавливает апдейты.

Ограничения, которые нельзя обойти кодом:

- после принудительного закрытия (свайп вверх) уведомлений нет до следующего запуска:
  локальные уведомления некому создавать, а серверный пуш недоступен;
- сканируется только основной список чатов (`.root`), архивные чаты не покрыты;
- беззвучная дорожка и продление фонового времени расходуют батарею; оба поведения
  отключаются в `Настройки → Swiftgram → tearsgram → Уведомления`;
- при звонке или будильнике аудиосессия прерывается; после окончания прерывания
  плеер запускается снова (наблюдатель `AVAudioSession.interruptionNotification`).

## Тихие часы и проверка уведомлений

`Настройки → Swiftgram → tearsgram → Уведомления`:

- `Тихие часы` (`sg.mod.quietHours`, значения `off` / `23-8` / `22-7` / `0-7` / `1-9`,
  по умолчанию `off`). Пока окно открыто по локальному времени, баннеры не ставятся:
  `SGLocalNotificationManager.process` считает сообщения в `sg.localNotifications.quietCount.<accountId>`
  и число чатов в `sg.localNotifications.quietChats.<accountId>`. Когда окно закрывается,
  `flushQuietDigest` показывает одну сводку «Пока было тихо: N сообщений в M чатах»
  (идентификатор `sg.quiet.digest.<accountId>`, повторная сводка заменяет предыдущую).
  Если открыть приложение раньше, `setForeground(true)` стирает счётчики без баннера:
  непрочитанные и так видны в списке чатов. Окно, переходящее через полночь (`23-8`),
  обрабатывается как `hour >= 23 || hour < 8`.
- `Проверить уведомление` — ставит локальное уведомление с задержкой 5 секунд
  (`UNTimeIntervalNotificationTrigger`), чтобы успеть свернуть приложение: в форграунде
  iOS баннер не показывает. Ничего не отправляет в сеть и не требует разрешений сверх уже
  выданных.

## Одноразовые фото и видео

`Настройки → Swiftgram → tearsgram` → `Одноразовые фото и видео`
(`sg.mod.keepViewOnce`, по умолчанию включено).

Входящее одноразовое медиа хранится как обычное сообщение с `AutoclearTimeoutMessageAttribute`
(`timeout == viewOnceTimeout`, то есть `0x7fffffff`) и `ConsumableContentMessageAttribute`.
При открытии клиент ставит `consumed = true`, записывает `countdownBeginTime = сейчас` —
и `managedAutoremoveMessageOperations(isRemove: false)` по тегу 1 срабатывает через ноль
секунд, заменяя `TelegramMediaImage`/`TelegramMediaFile` на `TelegramMediaExpiredContent`
и удаляя атрибут. Именно поэтому фото исчезает сразу после просмотра.

С включённым переключателем ветка в `ManagedAutoremoveMessageOperations.swift` вместо
замены медиа делает сообщение обычным вложением:

- `AutoclearTimeoutMessageAttribute` и `ConsumableContentMessageAttribute` удаляются,
  `AutoremoveTimeoutMessageAttribute` (автоудаление чата) остаётся, поэтому TTL переписки
  по-прежнему работает;
- медиа не заменяется, таймер снимается через `clearTimestampBasedAttribute`;
- `containsSecretMedia` становится `false`, и пузырь рендерится как обычное фото или видео:
  его можно открыть повторно, переслать и сохранить в галерею;
- сообщению возвращаются теги `photoOrVideo` и `photo`/`video`: одноразовые медиа
  хранятся без них (секретные медиа не попадают в общие медиа), и без тега чат-галерея
  не находила это сообщение;
- строка помечается локальным тегом `TearsgramKeptOnce` (бит 2 `LocalMessageTags`), и
  `chatMessageGalleryControllerData` открывает её как `standaloneMessage`, а не через
  `peerMessagesAtId`. Поэтому нажатие всегда открывает именно это фото или видео, а не
  соседнее;
- отметка о просмотре всё равно уходит отправителю (`markMessageContentAsConsumed`), у него
  сообщение удаляется как обычно.

Тот же флаг проверяется в `markMessageContentAsConsumedRemotely`: если одноразовое медиа
израсходовано на другом устройстве, локальная копия не превращается в заглушку.

Ограничения: работает для входящих сообщений в облачных чатах; секретные чаты не
затрагиваются, потому что там сообщение удаляется целиком. Если сервер уже удалил файл,
а приложение потеряло локальный кеш (переустановка, очистка данных), восстановить медиа
неоткуда — сохраняется ровно то, что успело скачаться на устройство.

## Сохранение и пересылка защищённых медиа

`Настройки → Swiftgram → tearsgram → Приватность` → `Сохранять и пересылать защищённые медиа`
(`sg.mod.ignoreCopyProtection`, по умолчанию включено).

В Telegram «защита контента» — это два флага: `noforwards` у сообщения (бит 26,
`MessageFlags.CopyProtected`) и `copyProtectionEnabled` у чата или канала. Клиент по ним
скрывает «Сохранить в галерею» и «Переслать». Сама метка `scam` ничего не запрещает —
это предупреждение в шапке; ограничения дают именно эти два флага.

Переключатель заставляет `Message.isCopyProtected()` возвращать `false`, а проверки
`copyProtectionEnabled` в меню сообщения, галерее и `OpenChatMessage` игнорировать флаг.
В результате:

- в галерее появляются «Сохранить в галерею» и «Создать стикер»;
- в контекстном меню появляются «Переслать», «Копировать» и внешний шаринг;
- медиа в галерее не считается capture-protected, поэтому скриншот не затемняется.

Сохранение выполняется локально и работает всегда, пока файл скачан или есть в кеше.
Пересылка уходит на сервер: если канал включает запрет пересылки на своей стороне (а не
только просит клиентов его соблюдать), сервер может ответить ошибкой. В этом случае
помогает «сохранить и отправить заново» — это уже обычная отправка файла.