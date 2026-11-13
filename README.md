# tearsgram

Мод-сборка Telegram для iOS на базе Swiftgram с локальным архивом удалённых сообщений,
режимом призрака и собственным значком над Dynamic Island.

База: [Swiftgram/Telegram-iOS](https://github.com/Swiftgram/Telegram-iOS) (Swiftgram 13.1.1,
коммит `e3a392272b182dbf975d4ac5fc33b40a5954d749`) + мод-патчи из
[gandon-pro/Swiftgram-Mod](https://github.com/gandon-pro/Swiftgram-Mod).

Всё, что лежит в этой папке, — оверлей. Он накладывается на форк мод-репозитория и перекрашивает
его в tearsgram: имя, bundle id, иконки, значок, экран настроек, артефакты CI.

> Сборка `.ipa` — только на macOS. На Windows исходники можно хранить и править, но Xcode и Bazel
> для iOS там не запускаются. Рабочий путь без своего Mac — GitHub Actions на macOS-раннере,
> инструкция ниже. Собранный CI-артефакт подписан тестовым сертификатом upstream и требует
> переподписи в Sideloadly.

---

## Что уже есть в базе (не пишется заново)

Мод-репозиторий уже реализует обе функции, оверлей их только переименовывает и дополняет:

| Функция | Где в исходниках |
| --- | --- |
| Архив удалённых сообщений (текст + ссылки на медиа) | `submodules/TelegramCore/Sources/Settings/SGDeletedMessages.swift` |
| Перехват серверного удаления до применения | `submodules/TelegramCore/Sources/State/HistoryViewStateValidation.swift` (`sgArchiveDeletedMessages`) |
| Полупрозрачные «оставленные» пузыри в чате | атрибут `SGDeletedMessageAttribute`, `submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode` |
| Экран архива | `Swiftgram/SGSettingsUI/Sources/SGDeletedMessagesController.swift` |
| Режим призрака (online / typing / recording / uploads / read / stories / interactions) | `submodules/TelegramCore/Sources/State/Managed*` + `Swiftgram/SGSimpleSettings/Sources/SGPrivacySettings.swift` |
| Значок над Dynamic Island | `submodules/Display/Source/WindowContent.swift` (`badgeView`) |
| Фоновое сканирование удалёнок | `submodules/TelegramUI/Sources/AppDelegate.swift` (`deletedMessagesRefresh`) |

Ограничения механики (важно понимать до установки):

- Восстанавливаются только сообщения, которые **этот клиент уже получил** и которые ещё лежат в
  локальной базе Postbox. Удалённое до первого запуска клиента не появится.
- Секретные чаты, view-once и self-destructing медиа исключены намеренно.
- Архив по умолчанию 200 записей, лимит меняется в настройках (1…10000) или отключается
  переключателем «Бесконечный архив».
- «Призрак» подавляет исходящие индикаторы, но сервер видит отправку сообщений, реакций и звонков.
  Уже отправленные read-отметки не отзываются.

## Что добавляет оверлей tearsgram

1. Брендинг: `CFBundleDisplayName`/`CFBundleName` = `tearsgram` во всех таргетах и расширениях,
   bundle id `com.tearsgram.app`, свои иконки и альтернативные иконки.
2. Значок над Dynamic Island `tearsgram`: зелёная пилюля с логотипом и надписью, 93×22 pt
   (279×66 px @3x) — ровно как штатный, чтобы не заезжать под остров на 14 Pro / 15 / 16 / 17.
3. Переключатель значка в настройках: `tearsgram` ↔ штатные Swiftgram/Telegram
   (`Default`, `Sky`, `Night`, `Titanium`, `Pro`, `Day`, `Sparkling`, `Ducky`).
4. Экран настроек мода переименован из `Nigga` в `tearsgram`, ссылка «Значок приложения»
   вынесена в раздел «Оформление» без требования Pro.
5. Точка входа в этот экран. В upstream у `sgModSettingsController` **нет ни одного вызова** —
   ни в `SGSettingsController`, ни в `ThemeSettingsController`, ни в `AccountContext`, проверено
   поиском по дереву репозитория. Без патча экран существовал, но открыть его было нечем, то есть
   ни удалённых сообщений, ни призрака в сборке фактически не было. Оверлей добавляет:
   - секцию-заголовок `tearsgram` и строку-ссылку в `SGSettingsController` (вверху списка
     Swiftgram-настроек);
   - внутренний URL-роут `tg://sg/tearsgram` и алиас `tg://sg/mod` в `SGTelegramUIExtensions.swift`
     (все Swiftgram-роуты живут под хостом `sg`, см. `submodules/TelegramUI/Sources/OpenUrl.swift`,
     ветку `case "sg":`).
6. CI-workflow `Build tearsgram` и артефакт `tearsgram-resign-required.ipa`.

---

## Сборка

### 1. Форк

1. Открой https://github.com/gandon-pro/Swiftgram-Mod → **Fork** → имя репозитория `tearsgram`.
2. Склонируй форк (или работай через веб-интерфейс):

```bash
git clone --recursive -j8 https://github.com/<твой-логин>/tearsgram.git
cd tearsgram
```

### 2. Наложи оверлей

Скопируй **содержимое** этой папки в корень форка (папки `Swiftgram/`, `mod-tools/`, `tools/`,
`branding/`, `.github/`, файлы `README.md`, `TEARSGRAM-CHANGES.md`) и выполни:

```bash
python tools/apply.py
```

Скрипт идемпотентный. Точки правки:

| Файл | Что делает |
| --- | --- |
| `submodules/Display/Source/WindowContent.swift` | заменяет рендерер значка и блок `Window1.init` |
| `Swiftgram/SGSettingsUI/Sources/SGModSettingsController.swift` | добавляет `import SGProUI`, `SGModLink.appBadge`, строку «Значок приложения» |
| `Swiftgram/SGSettingsUI/Sources/SGSettingsController.swift` | добавляет секцию `tearsgram` и ссылку на экран мода |
| `Swiftgram/SGSettingsUI/BUILD` | зависимость `//Swiftgram/SGProUI:SGProUI` |
| `Swiftgram/SGTelegramUIExtensions/Sources/SGTelegramUIExtensions.swift` | роуты `tg://sg/tearsgram`, `tg://sg/mod` |
| `Telegram/BUILD`, `submodules/TelegramUI/Sources/AppDelegate.swift` | переименование бренда |
| `Swiftgram/SGProUI/Sources/AppBadgeSelectorController.swift`, `mod-tools/brand-ipa.py`, `mod-tools/prepare-mod-icon.py` | полная замена из `overlay/` |
| `.github/workflows/build-tearsgram.yml` | новый workflow |

Повторный запуск печатает все `False` и ничего не меняет. В конце скрипт проверяет результат
(`verify()`): отсутствие `Nigga`/`niggagram`, наличие рендерера значка, ровно по одному вхождению
каждой правки в настройках, наличие роутов, ассетов значка и всех 15 файлов альтернативных иконок.
При расхождении — ненулевой код возврата и список проблем.

Перегенерировать графику (после замены `branding/logo.png`):

```bash
python tools\make_branding.py
```

`branding/logo.png` — единственный источник правды: любая картинка (640×640, 1024×1024,
не квадрат — обрежется по центру), из неё собирается иконка. Апскейл до 1024 идёт с
LANCZOS + UnsharpMask, поэтому исходник меньше 1024 px не мылится.

`tools/make_artwork.py` — запасной вариант: рисует типографский постер «Silk Road»
(бледно-голубая бумага, серифный зелёный заголовок в тонкой рамке, подпись
`ANONYMOUS MARKETPLACE`, зелёная птица) в `branding/logo.png`. Нужен только если
своего арта нет.

Скрипт собирает: `branding/AppIcon-1024.png`, `mod-tools/app-icons/NGCustom*`,
`Swiftgram/SGAppBadgeAssets/Images.xcassets/TearsgramAppBadge.imageset/*`
(чёрная плашка 279×66 px @3x с белой надписью `tearsgram`, без миниатюры —
93×22 pt под Dynamic Island).

```bash
git add -A
git commit -m "tearsgram branding + badge"
git push
```

### 3. Секреты

`Settings → Secrets and variables → Actions → New repository secret`:

| Имя | Значение |
| --- | --- |
| `TELEGRAM_API_ID` | число с https://my.telegram.org/apps |
| `TELEGRAM_API_HASH` | 32 hex-символа оттуда же |

Без них сборка IPA падает на шаге `configure-ci.py`. Значения встраиваются в бинарник
(как в любом Telegram-клиенте) и не печатаются в логах.

### 4. Запуск сборки

`Actions → Build tearsgram → Run workflow → mode: ipa`.

Что делает workflow (`runs-on: xcode-27`, таймаут 180 минут):

1. выбирает Xcode из `versions.json`;
2. `mod-tools/check-swift.py` — парсит изменённые Swift-файлы настоящим фронтендом Swift;
3. юнит-тесты настроек/звука/иконок;
4. `configure-ci.py` — генерирует конфигурацию из секретов и тестового профиля;
5. `git submodule update --init --recursive --jobs 4`;
6. ставит Bazel нужной версии с проверкой sha256;
7. импортирует тестовый сертификат upstream (`build-system/fake-codesigning`);
8. `prepare-mod-icon.py` → иконка из `branding/AppIcon-1024.png`;
9. `Make.py build --configuration=release_arm64`;
10. `brand-ipa.py` → `tearsgram-resign-required.ipa`;
11. загружает артефакт `tearsgram-IPA-<номер>` (хранится 7 дней).

Если лейбл `xcode-27` недоступен в твоём аккаунте, поменяй в workflow `runs-on` на доступный
macOS-образ (например `macos-15`) и добавь к `Make.py` флаг `--overrideXcodeVersion`; версия
Xcode должна быть не ниже указанной в `versions.json`.

### 5. Установка через Sideloadly (Windows)

1. Скачай артефакт из Actions, распакуй zip → внутри `tearsgram-resign-required.ipa`.
2. Установи iTunes (из apple.com, не из Microsoft Store) и Sideloadly с https://sideloadly.io.
3. Подключи iPhone кабелем, разблокируй, нажми «Trust».
4. Sideloadly: перетащи `.ipa` в окно, впиши свой Apple ID в `Apple account`,
   при необходимости `Advanced → Anisette` оставь по умолчанию, нажми **Start**.
5. Введи пароль Apple ID (уходит только на серверы Apple для подписи). Если включена
   2FA — введи код.
6. На iPhone: `Настройки → Основные → VPN и управление устройством → Разработчик приложения →
   Доверять`.
7. Free Apple ID: приложение живёт 7 дней, потом переподписать тем же способом (данные сохраняются).
   Платный Developer Program: до 1 года.

Bundle id `com.tearsgram.app` не пересекается с оригинальным Swiftgram, поэтому обе версии
можно держать рядом.

---

## Настройки внутри приложения

Путь: `Настройки → Swiftgram → tearsgram` (заголовок и строка вверху списка) либо ссылка
`tg://sg/tearsgram` / `tg://sg/mod` — открывается тот же экран.

- **Оформление → Значок приложения** — значок над Dynamic Island.
  Выбор применяется сразу (`context.sharedContext.mainWindow?.badgeView.image`) и сохраняется
  в `SGSimpleSettings.customAppBadge`; при следующем запуске `Window1.init` читает это значение.
  Пустое значение = `tearsgram`; `Components/AppBadge` = штатный значок Swiftgram.
- **Приватность → Режим призрака** — мастер-переключатель, ниже отдельные индикаторы.
- **Удалённые сообщения** — включить сохранение, лимит архива, «Бесконечный архив»,
  «Обрабатывать удалёнки в фоне», вход в **Архив удалённых сообщений**.

В чате удалённое сообщение остаётся пузырём с прозрачностью 50 % и меткой времени удаления;
текст и ссылки на уже скачанные медиа доступны, нескачанные файлы могут не открыться.

## Проверка после установки (два аккаунта)

1. Аккаунт A: `Настройки → Swiftgram → tearsgram → Удалённые сообщения` → включить.
2. Аккаунт B пишет A сообщение, A его получает, B удаляет у себя.
3. У A сообщение остаётся полупрозрачным, текст виден в архиве.
4. Выключить «Режим призрака» и проверить, что online/typing/read снова уходят.
5. Включить «Скрывать онлайн» и с аккаунта B убедиться, что A «был(а) недавно».
6. `Оформление → Значок приложения`: переключить на `Swiftgram (Default)` — пилюля меняется
   на штатную, вернуть `tearsgram`.
7. Открыть `tg://sg/tearsgram` (Safari, адресная строка) — должен открыться тот же экран
   (проверка роута). Если открылся официальный Telegram, iOS отдала схему `tg` другому клиенту;
   тогда проверяй вход через настройки.

## Диагностика

| Симптом | Причина |
| --- | --- |
| `Build configuration created` не появляется | не заданы секреты `TELEGRAM_API_ID`/`TELEGRAM_API_HASH` |
| `Required Xcode ... is unavailable` | нет раннера с нужной версией Xcode |
| `Test provisioning profile expired` | истёк тестовый профиль upstream; обнови `build-system/fake-codesigning/profiles` |
| Sideloadly: `Provision.cpp:150` | Apple ID без валидной сессии — выйди и войди заново, проверь 2FA |
| Приложение падает на старте после переподписи | обычно срезаны App Groups; в моде уже есть fallback на sandbox-контейнер (`SGAppStorage`) |
| Значок не появился | устройство не в списке `DEVICE_MODELS_WITH_APP_BADGE_SUPPORT` (`Swiftgram/SGAppBadgeOffset`) |
| `tg://sg/tearsgram` открывает официальный Telegram | оба клиента регистрируют схему `tg`; входи в экран через `Настройки → Swiftgram → tearsgram` |
| Экрана `tearsgram` нет в настройках Swiftgram | оверлей не применён: `python tools/apply.py` не запускался или упал на проверке `verify()` |

## Лицензия и правовой статус

Исходники Swiftgram/Telegram-iOS распространяются по GPL-подобным лицензиям — изменённые
исходники должны быть опубликованы. Это неофициальный клиент: не используй имя Telegram,
не выдавай сборку за официальное приложение. API ID/hash должны быть свои.