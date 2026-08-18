> [!NOTE]
> **Зеркало GitHub** — Если вы просматриваете этот репозиторий на GitHub, обратите внимание, что это зеркало только для чтения. Задачи, pull request и вся активность проекта отслеживаются на Codeberg: [https://codeberg.org/endurain-project/endurain](https://codeberg.org/endurain-project/endurain)

> [!IMPORTANT]
> **Это форк ZAPFIT** — переименованный, локально дополненный билд
> [Endurain](https://codeberg.org/endurain-project/endurain). ZAPFIT
> наследует код Endurain по лицензии AGPL-3.0-or-later и добавляет
> мастер настройки при первом входе, нативную русскую локализацию,
> опцию темы `system` и дополнительные хуки брендинга. Все товарные знаки,
> метаданные проекта и трекеры задач Codeberg остаются собственностью
> оригинальных авторов Endurain. Подробности см. в разделе [Благодарности](#благодарности)
> ниже.

> [!NOTE]
> **Endurain на временном замораживании функций** — Проект не приостановлен. Фокус смещается с новых функций на укрепление основ. Подробнее [здесь](https://docs.endurain.com/blog/2026/05/23/pausing-new-features-so-endurain-can-keep-growing/)

<div align="center">
  <img src="logo/brand_logo_dark_theme.png" width="128" height="128">

  # ZAPFIT (форк Endurain)

  <a href="https://translate.codeberg.org/engage/endurain/"><img src="https://translate.codeberg.org/widget/endurain/svg-badge.svg" alt="Статус перевода"></a>
  [![Лицензия](https://img.shields.io/badge/license-AGPL%20v3-blue)](./LICENSE)
  [![Релиз](https://img.shields.io/badge/dynamic/json?url=https://codeberg.org/api/v1/repos/endurain-project/endurain/releases/latest&query=$.tag_name&label=release&color=blue)](https://codeberg.org/endurain-project/endurain/releases)
  [![Звёзды](https://img.shields.io/badge/dynamic/json?url=https://codeberg.org/api/v1/repos/endurain-project/endurain&query=$.stars_count&label=stars&logo=codeberg)](https://codeberg.org/endurain-project/endurain)
  [![Политика товарных знаков](https://img.shields.io/badge/trademark-Endurain%E2%84%A2-blue)](./TRADEMARK.md)

  **Самостоятельно размещаемый сервис фитнес-трекинга**  
  Посетите [Mastodon профиль](https://fosstodon.org/@endurain) и [Discord сервер](https://discord.gg/6VUjUq2uZR) Endurain.

  <img src="screenshot_01.png" alt="Скриншот Endurain">
</div>

## 🚀 Попробовать демо

Познакомьтесь с Endurain без установки:

**Демо URL:** [https://demo.endurain.com](https://demo.endurain.com)

- **Логин:** `admin`
- **Пароль:** `admin`
- **Расписание сброса:** Ежедневно в полночь (часовой пояс Europe/Lisbon)

> ⚠️ **Примечание:** Демо-окружение сбрасывается каждый день. Не храните важные данные.

## Содержание

- [Документация Endurain](https://docs.endurain.com)
- [Что такое Endurain?](#что-такое-endurain)
- [Скриншоты Endurain](https://docs.endurain.com/gallery/)
- [Спонсоры](#спонсоры)
- [Участие в проекте](#участие-в-проекте)
- [Помощь с переводом](#помощь-с-переводом)
- [Лицензия](#лицензия)

## Благодарности

ZAPFIT — это самостоятельный **форк** проекта [Endurain](https://codeberg.org/endurain-project/endurain) (AGPL-3.0-or-later), первоначально написанный Жуаном Виторией Силвой и сообществом Endurain. ZAPFIT опирается на эту основу, и авторы оригинала заслуживают огромной благодарности за их работу.

Отличия от оригинала:
- Мастер настройки при первом входе (полная настройка сервера за один проход после логина).
- Нативная русская (`ru`) локализация фронтенда.
- Опция темы `system` и настраиваемая тема/язык/имя бренда по умолчанию.
- Переменная окружения `ZAPFIT_HOST` (устаревшая `ENDURAIN_HOST` всё ещё поддерживается).

## Что такое Endurain?

Endurain — это самостоятельно размещаемый сервис фитнес-трекинга, разработанный для предоставления пользователям полного контроля над своими данными и средой размещения. Это аналог Strava, но с акцентом на приватность и кастомизацию. Построен на:

- **Фронтенд:** Vue.js 3 с TypeScript, Tailwind CSS и компонентами shadcn-vue, с Pinia и TanStack Query для управления состоянием
- **Бэкенд:** Python FastAPI, Alembic, SQLAlchemy, Apprise, stravalib и python-garminconnect для интеграции со Strava и Garmin Connect, gpxpy, tcxreader и fitdecode для импорта файлов .gpx, .tcx и .fit соответственно
- **База данных:** PostgreSQL для эффективного управления данными
- **Наблюдаемость:** Jaeger для базового трекинга и мониторинга
- **Интеграции:** Поддержка Strava и Garmin Connect. Также поддерживается ручная загрузка активностей с помощью файлов .gpx, .tcx и .fit

Для развёртывания доступен Docker-образ, подробный пример можно найти в файле `docker-compose.yml.example`. Конфигурация осуществляется через переменные окружения, обеспечивая гибкость и простоту настройки.

Для получения дополнительной информации см. [документацию](https://docs.endurain.com) Endurain.

## Спонсоры

Огромное спасибо спонсорам проекта! Ваша поддержка помогает проекту развиваться.

Поддержите разработку Endurain на:

- [Buy Me a Coffee](https://buymeacoffee.com/endurain)
- [liberapay](https://liberapay.com/endurain/)
- [Patreon](https://patreon.com/u84745218)
- [GitHub Sponsors (архивированный репозиторий)](https://github.com/endurain-project/endurain)

## Участие в проекте

Приглашаем к участию! Пожалуйста, откройте задачу для обсуждения любых изменений или улучшений перед отправкой PR. Ознакомьтесь с [руководством по участию](CONTRIBUTING.md) для получения подробной информации.

## Помощь с переводом

Endurain поддерживает несколько языков, и вы можете помочь перевести его на другие языки через [Codeberg Translate](https://translate.codeberg.org/projects/endurain/).

## Лицензия

Этот проект распространяется под лицензией AGPL-3.0-or-later — см. файл [LICENSE](LICENSE) для получения подробной информации.

## Уведомление о товарном знаке

Endurain® — товарный знак Жуана Витории Силвы и остаётся собственностью оригинальных авторов.

Этот **форк ZAPFIT** намеренно использует отдельное название и не претендует на какие-либо права на название или логотип Endurain. Вы можете самостоятельно размещать ZAPFIT; коммерческое использование названия или логотипов **Endurain** (например, предложения платного хостинга, продуктов или услуг) **не разрешено без предварительного письменного разрешения** от авторов Endurain.

Подробности см. в [`TRADEMARK.md`](./TRADEMARK.md).

<div align="center">
  <sub>ZAPFIT — форк <a href="https://codeberg.org/endurain-project">Endurain</a> | Сделано с ❤️</sub>
</div>
