# Feature Roadmap

This is a list of desired features; more of a wishlist than a time-oriented list of planned work.

## Security

- Passkey support

## Social

- Text Posts
- Threaded Comments on Activities and Posts
- Reactions (likes, etc.) to Activities, Comments, and Posts
- Events - for racing events or group workouts
- Challenges
  - Specific goals (calories, distance, time, etc.)
  - Time-bound
  - Leaderboards (optional)
  - Award badges (optional)
- Federation (via ActivityPub)

---

## ZAPFIT notes — gap to Strava / SportsTracker (2026-08-29)

**Ядро трекинга уже ≥ Strava:** активности 46 типов + streams/HR-зоны/laps, gear+components, health (weight/steps/sleep scoring/poop/water/RHR), goals, followers+комменты, SSO/APK. Социал ~25% — нет сегментов/Kudos/клубов/ленты/маршрутов.

**P0 (паритет соцсети):** сегменты+лидерборд, лайки, клубы, Route Builder+heatmap, лента+посты, треды.

**P1:** групповые челленджи/бейджи, ивенты, Workout Builder+календарь, расширенная аналитика CTL/ATL/PR, публичный OAuth API.

**P2:** Live/Beacon, DM, Paywall, Federation.

## Immediate — Email SMTP (mail.ru) — TODO P0

**Проблема:** `backend/app/core/apprise.py:30` + `backend/app/core/config.py:149` требуют `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM`. Без них `AppriseService.is_smtp_configured()==false` и `password_reset_tokens/utils.py:282` молча `return False` — письмо сброса не уходит, в логе `send_email skipped: SMTP not configured`.

**Где текст письма:** `backend/app/auth/password_reset_tokens/email_messages.py:11` `get_password_reset_email()` + `backend/app/core/email_templates.py:9` палитра `BRAND_PRIMARY #1d9e75` (сейчас зеленый Endurain, надо #2563eb ZAPFIT) и `wrap_email()` локализует через `core/i18n` ключи `password_reset.*`. Менять тексты — в `backend/app/core/i18n/locales/*.json` и `frontend/src/i18n/locales/*/`.

**Настройка для mail.ru (пример для `.env` / `docker-compose.yml`):**
```env
SMTP_HOST=smtp.mail.ru
SMTP_PORT=465
SMTP_USERNAME=your@mail.ru
SMTP_PASSWORD=app_password_из_https://account.mail.ru/user/2-step-auth/passwords
SMTP_FROM=your@mail.ru
SMTP_SECURE=true
SMTP_SECURE_TYPE=ssl   # 465→ssl, 587→starttls
ZAPFIT_HOST=https://your-domain.ru
```
Для 587: `SMTP_PORT=587` + `SMTP_SECURE_TYPE=starttls`. Для mail.ru нужен **пароль приложения** (если 2FA выкл — обычный пароль, но лучше вкл 2FA + app password). `SMTP_FROM` обязателен = `SMTP_USERNAME`, иначе mail.ru реджектит. После правки: `docker compose up -d --force-recreate` + проверка `docker logs backend | grep "Email sent"` и тест сброса.

**TODO в коде:** сменить `_LOGO_URL` в `email_templates.py:29` с `codeberg.org/.../logo_light.png` на `ghcr`/`your-domain`, палитру на ZAPFIT, добавить проверку SMTP при старте (`check_required_env_vars` — варнинг если не настроен, уже есть).

## Map — 2GIS evaluation (optional, not P0)

**Текущее:** `frontend/src/providers/leafletMapProvider.ts:37` OSM + `ESRI_SATELLITE_URL` (Спутник), бэкенд `server_settings/utils.py:12` шаблоны + `schema.py:17` `DEFAULT_ALLOWED_TILE_DOMAINS` с `*.arcgisonline.com`. Выбор слоя хранится в `localStorage zapfit:mapLayer`.

**2GIS браузерный API:** эндпойнты типа `https://catalog.api.2gis.com/3.0/items` / `https://tile2.maps.2gis.com/tiles?x={x}&y={y}&z={z}&v=...` требуют `key` (бесплатный после регистрации на https://docs.2gis.com). Парсить без ключа — нарушит ToS и сломается при смене `v` версии. CSP `img-src` уже `https:` пропускает, но `DEFAULT_ALLOWED_TILE_DOMAINS` надо добавить `https://*.2gis.com` + `https://*.maps.2gis.com` если используем.

**Реально ли:** да — добавить в `TILE_MAPS_TEMPLATES`:
```py
"2gis": {"name":"2GIS","url_template":"https://tile2.maps.2gis.com/tiles?x={x}&y={y}&z={z}","attribution":"© 2GIS","map_background_color":"#e8e8e8","requires_api_key_frontend":True}
```
+ прокинуть ключ через `tileserver_api_key` или отдельный `DGIS_API_KEY`. Для реверс-геокода 2GIS не нужен — уже есть `nominatim/photon`. Парсить “браузерный” `catalog.api` без ключа — хрупко, лучше официальный `places` API. Оценка: 1-2 дня интеграции, но приоритет ниже email.

## Next steps (предложение)

1. SMTP mail.ru — настроить `.env` + пересобрать бэкенд, тест сброса, обновить палитру писем.
2. P0 социал — сегменты/лайки/клубы после email.
3. 2GIS — отложить до запроса, оставить Esri спутник как дефолт.
