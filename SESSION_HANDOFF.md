# ZAPFIT Server — сессия 2026-10-28 (handoff, v0.25.0) → обновлена сессиями 2026-10-29 (v0.27.0 → v0.28.0 «Соревнования»)

**Проект:** `D:\projex\serverZap` (git-клон, ветка `master`)
**GitHub:** https://github.com/mrSaT13/serverZAPPFIT
**MOBILE-КЛИЕНТ:** `D:\apktrack\endurain-flutter` (0.8.9+39 = сборка на телефоне;
в `D:\zapfit-github\endurain-flutter` старая копия 0.8.5 — не использовать;
Release-репо APK: `mrSaT13/ZAPFIT-app-andoid-`, app_update_service сверяется с
pubspec.yaml). Ориентировка по клиенту: `lib/core/services/*` (`api_client.dart`,
auth/websocket/health/feed…), экраны `lib/features/*`, соревнования —
`lib/features/activities/tabs/preparation_tab.dart` (офлайн-движок готовности:
рейтинг = недельный объём/требуемый, ступени 5/10/21.5+ км → 20/30/45/60 км/нед).
**Версия:** 0.27.0 + коммит **`a16a7bc` запушен 2026-10-29**; CI #57 success.
**ГЛАВНЫЙ УРОК сессии «каталог пуст»:** в репо ДВА Dockerfile — корневой `Dockerfile`
(его собирает CI: `.github/workflows/docker.yml` → `file: ./Dockerfile`) и
`docker/Dockerfile` (только локальные сборки, `docker-compose.build.yml` тоже берёт
корневой). Правки упаковки каталога трижды делались в `docker/Dockerfile`, а CI
собирал корневой, где `COPY backend/assets ./assets` при `WORKDIR /app/backend`
клали снапшот в `/app/backend/assets`, а код (`exercise_catalog.py`) ищет
`parents[2]` → `/app/assets`. Теперь оба Dockerfile копируют в `/app/assets`, а
`load_snapshot()` ищет по трём кандидиатам (`_CATALOG_SEARCH`) — раскладка
упаковки больше не может оставить каталог пустым. ПРОВЕРКА КАТОГА В БУДУЩЕМ:
`docker exec zapfit-app ls -la /app/assets` должно показывать
`exercise_catalog.json` + `exercise_names_ru.json`; в логе при старте —
`Seeded exercise catalog: 914`.

---

# ИСТОРИЧЕСКАЯ ЧАСТЬ (сессии 1–2, v0.25.0 / dependabot)

**Версия на тот момент:** 0.25.0 (бамп 0.24.1 → 0.25.0: `backend/pyproject.toml`, `backend/uv.lock`,
`backend/app/core/config.py` → `API_VERSION`, `backend/tests/core/test_config_extra.py`,
`frontend/package.json` + `package-lock.json`, User-Agent `ZAPFIT/0.25` в `nutrition/off_client.py`)
**Стек:** FastAPI + PostgreSQL + Redis (бэкенд), Vue 3 + TS + Tailwind 4 + TanStack Query (фронт)
**Коммит той сессии:** `a52538f` «feat: AI plan generator, workout/nutrition charts,
enriched wger catalog, v0.25.0» (137 файлов, +3142/−565) — **запушлен, CI
Build & Push Docker Image #53 = completed successfully (2m 32s)**.

---

## Итог сессии (что сделано)

### 1. Диагностика пустого пикера упражнений (ПРИЧИНА НАЙДЕНА)
- В `docker-compose.yml` (он в `.gitignore`, в репу НЕ идёт) был закреплён старый
  образ `ghcr.io/mrsat13/serverzappfit:sha-bc271db` — коммит `bc271db` **не является
  предком HEAD** и не содержит фикса `704d9bd` (COPY `backend/assets` в образ).
  → в контейнере нет `exercise_catalog.json` → таблица пуста → `/workouts/exercises/meta` 500 → пикер пуст.
- Локальный `docker-compose.yml` переключён на `:latest` (UTF-16 LE + BOM сохранены,
  YAML проверен). На СЕРВЕРЕ пользователь ставит тег сам.
- Харденинг: `catalog_router._snapshot_or_none()` — при отсутствии снапшота эндпоинты
  не 500-ят, `/meta` отдаёт `seedError: 1`, пикер показывает подсказку
  «каталог не засеян» (`workouts.picker.notSeeded`, ru/en).

### 2. ИИ-генератор плана (ГОТОВО)
- `backend/app/workouts/ai_planner.py` (новый): free-text цель → черновик плана.
  - Провайдер общий с нутри-ассистентом: `nutrition.ai.get_ai_settings` / `chat_completion`
    (server_settings: `ai_enabled/ai_base_url/ai_model`, ключ Fernet).
  - Каталог в промпт сужается по ключевым словам ru/en → категории
    (`_CATEGORY_KEYWORDS`, `_focus_category_ids`); каждая строка
    `id | имя | категория | снаряды`.
  - ИИ **только предлагает**: строгий JSON → `parse_plan_json` (терпит fences/прозу) →
    `validate_draft` (вымышленные id отбрасываются, имена ре-резолвятся из каталога,
    cap `MAX_EXERCISES=30`); клиент сохраняет обычным `POST /workouts`.
  - Ошибки: `AiPlanError`; роутер → 502; не настроен → 503.
- Роутер: `GET /workouts/ai/status`, `POST /workouts/ai/plan` (зарегистрированы до `/{plan_id}`).
- Схемы: `AiPlanGenerateRequest`, `AiPlanDraft(Exercise)`, `AiStatusRead`.
- Фронт: `PlanDialog.vue` — кнопка «Создать с ИИ» (Sparkles), панель с textarea
  (`inputFieldClass`), lazy-статус, `applyAiDraft` заполняет редактор; ключи `workouts.ai.*`.

### 3. Графики тренировок и питания (ГОТОВО)
- Бэкенд:
  - `GET /workouts/statistics?date_from&date_to` — недельная агрегация
    (`crud.weekly_statistics`, ISO-понедельник, дефолт 90 дней, 400 на инверсию/>366 дней);
    схемы `WorkoutStatistics(Point)`.
  - `GET /nutrition/trend?date_from&date_to` — дневные итоги (`crud.daily_totals`, group-by),
    дефолт 30 дней, cap 366; `burned` из activities (best-effort, как в `/summary`);
    схемы `NutritionTrend(Point)`.
- Фронт:
  - Общий `composables/useMetricChart.ts` (mount/update/teardown через
    `useChartProvider` + `useRenderProvidersReady`); `useHealthMetricChart.ts` — реэкспорт.
  - Тренировки: секция «Графики» (`WorkoutsView`), `WorkoutWeeklyChart.vue`
    (тонаж/сессии, bar), `ExerciseProgressChart.vue` (1RM + вес, line, селект упражнения).
  - Питание: `NutritionTrendCharts.vue` (диапазон 14/30/90; ref строковый!) +
    `NutritionCaloriesChart.vue` (bar + пунктир burned) + `NutritionMacrosChart.vue` (3 линии).
  - Дата-виджет питания: label + input **в одну строку**.
  - Ключи: `workouts.sections.charts`, `workouts.charts.*` (ru/en),
    `health.nutrition.trend.*` (ru/en); `queryKeys.workouts.statistics()`.

### 4. Обогащение каталога из wger (ГОТОВО, по выбору пользователя)
- Источник: `D:\wger-master\wger-master` (wger, AGPL; данные CC-BY-SA).
  - Взято из смешанного `translations.json`: **276 советов** (`exercises.exercisecomment`)
    и **114 алиасов** (`exercises.alias`) — оба ссылаются на pk переводов, а не на упражнение!
    + `core/fixtures/licenses.json` → 5 CC-лицензий.
  - НЕ взято: фото/видео (в репо только тестовые заглушки, реальные медиа на wger.de
    через API — отдельная фича), фикстуры nutrition/gym/trophies — тестовые.
  - Русских переводов в источнике ровно 10 — больше взять неоткуда.
- `backend/scripts/generate_exercise_catalog.py` (новый) — воспроизводимый генератор:
  `python scripts/generate_exercise_catalog.py D:\wger-master\wger-master`.
  **БАГ, который он чинит:** язык в фикстурах — числовой pk → маппится на коды через
  `core/fixtures/languages.json`; выход — компактный однострочный JSON (как оригинал).
- Снапшот `backend/assets/exercise_catalog.json` пересобран: старые данные сверены
  1:1 (0 регрессий), добавлены `aliases`/`tips` (per-lang dict) и `license` (строка).
- БД: `ExerciseCatalog.aliases/tips/license_name` + миграция
  `v0_25_0_catalog_enrichment.py` (rev `e5f6a7b8c9d0`, ← `d7e9f2a4c618`);
  `seed_catalog` их пишет; `main._seed_exercise_catalog` при старте один раз
  перезасеивает старые строки (условие: `license_name IS NULL AND aliases='{}' AND tips='{}'`... см. код: `enriched==0`).
- API: `_matches_query` ищет и по алиасам; `CatalogExerciseRead += license/aliases/tips`.
- Пикер: под строкой упражнения — совет техники (`displayTip`, язык → en).

### 5. Качество кода / чистка (ГОТОВО)
- `ruff check .` → **0 ошибок** (было 28): автофикс импортов/мертвых импортов +
  ручные правки: `apprise.py`/`server_settings/*`/`import_service` → `contextlib.suppress`
  или логирование (S110/SIM105), `ActivityComment` TYPE_CHECKING-импорт (F821),
  `server_settings/router` теперь отдаёт ответ провайдера (F841), N806/E402 в тестах.
  Per-file-ignores: `app/workouts/ai_planner.py` (RUF001 — кириллица в промпте),
  `tests/**` (+RUF001), `scripts/**` (T201 print — CLI).
- `ruff format .` → 690/690 (переформатировано 24).
- `assert` в `ai_planner.generate_plan` заменён на явный `AiPlanError` (S101).
- Frontend: **prettier --write по всем 76 файлам** (пользователь просил править все),
  `oxlint`/`eslint`/`vue-tsc` — чисто; vitest **685/685** ✅.
- mypy: **203 ошибки vs 205 на HEAD** (сверял через worktree) — новых нет.

### 6. Тесты бэкенда
- Новые: `tests/workouts/{test_statistics,test_ai_planner,test_router,test_catalog}.py`,
  `tests/nutrition/test_trend.py` — **49 зелёных**; вместе с core/server_settings/gears = 500+ ✅.
- Запуск: `uv` СЛОМАН в этом окружении («uv trampoline failed to canonicalize script path»).
  Использовать напрямую: `D:\projex\serverZap\backend\.venv\Scripts\python.exe -m pytest ...`
  (перед кириллицей: `$env:PYTHONIOENCODING='utf-8'`).

---

## Известные проблемы (НЕ в этой сессии, не блокеры)

1. **Полный `pytest` зависает** на `tests/core/test_apprise.py::
   TestAppriseServiceInit::test_reads_smtp_settings` (~48%, после `tests/activities/activity/{test_crud,test_router}.py`).
   - **Воспроизводится и на чистом HEAD** (проверено в worktree) → старое, CI не запускает тесты.
   - Механика (расследовано плагином-наблюдателем): psycopg подключается с
     `hostaddr=::1`, ждёт приветствие сервера (`wait_conn`, timeout **130с**),
     при этом в netstat НЕТ ни слушателя, ни соединения на :5432; изолированно тест
     проходит за 0.9с (отказ за 2с — на этой машине отказ ~2с). Таймеры
     faulthandler/вотчдога в отравленном процессе не срабатывают (процесс к тому
     моменту живёт с 1 потоком и 0 CPU) — механизм НЕ выяснен до конца.
   - Направление для продолжения: bisection внутри `test_crud.py` по тестам,
     что именно «отравляет» сетевое поведение; вероятный прод-фикс —
     `connect_timeout` в `core/database.py create_engine` (заодно защита при падении БД).
2. ~~**Dependabot: 170 уязвимостей** (11 critical)~~ — **разобрано (см. «Сессия 2» ниже)**:
   обновление локов закрыло большую часть. Осталось: фронт 4 low (deepmerge — фикса
   ещё нет у авторов), бэк 64 записи в 4 пакетах под карантином `exclude-newer = 30 дней`
   (authlib/pillow/certifi — заедут сами ~11.11 при пересборке лока).
3. Старые mypy-ошибки (203, все существовали и раньше) — по желанию разобрать.
4. `SESSION_HANDOFF.md` (этот файл) и `alice-flasher/` — не коммитились автоматически:
   Alice не коммитить никогда; этот файл закоммитить при следующем удобном случае.

---

## Деплой (что делать на сервере)

1. В compose на сервере: `image: ghcr.io/mrsat13/serverzappfit:latest`
   (или точный `:sha-e3c6a07`).
2. `docker compose pull && docker compose up -d`.
3. При старте автоматически: alembic → `v0_28_0` (таблица `competitions`) →
   автосид каталога. Руками ничего не нужно.
4. **Соревнования:** сервер 0.28.0 добавляет домен `/api/v1/competitions`
   (CRUD + `GET /competitions/next` с готовностью; scopes
   `competitions:read/write`; миграция `b8c9d0e1f2a3` ← `a7b2c3d4e5f6`).
   Web: виджет «Подготовка» на Обзоре (`features/competitions/…`,
   скрыт, если нет будущих стартов). Flutter: preparation_tab синкается
   (push/pull/tombstones, коммит `20bba4d` в ZAPFIT-app-andoid · собрать APK
   и bump версии при релизе — pubspec всё ещё 0.8.9+39).
   **Синхронизация упражнений** отдаёт описания с EN-фоллбеком (пикер,
   кнопка ℹ).
5. Аудит «синхронизация комментариев»: сервер и web-клиент полноценно
   работают (`/activities_comments` CRUD + UI в ActivityDetailView),
   Flutter-клиент комментариев НЕ показывает и не пишет — так и осталось
   в TODO (комментарий-сервис + экран с комментариями на
   `activity_detail_screen/feed`); идеи для следующей сессии ниже.

## Полезные команды/заметки окружения
- Python: `D:\projex\serverZap\backend\.venv\Scripts\python.exe` (3.14); `uv` не работает.
- Проверки бэк: `python -m ruff check .`, `python -m ruff format --check .`,
  `python -m mypy app` (baseline ~203 старых), тесты по каталогам (полный сьют висит — см. выше).
- Проверки фронта (`frontend/`): `npm run type-check`, `npm run lint:check`,
  `npm run format:check`, `npm test` (685).
- PowerShell 5.1: нет `??`; кириллица требует `PYTHONIOENCODING=utf-8`;
  `docker-compose.yml` — UTF-16 LE с BOM (редактировать байтово/через Unicode-кодировку).
- Генератор каталога: `python scripts/generate_exercise_catalog.py D:\wger-master\wger-master`
  (после обновления wger — пересобрать снапшот и закоммитить `backend/assets/`).

---

## Сессия 2 — Dependabot: разбор и обновление зависимостей (2026-10-28, позже)

**Коммиты этой сессии:** `f923574` (fix: upload path) + `4006d42` (chore: refresh
dependency locks to close Dependabot alerts).

**Аудит источники:** `gh` CLI в окружении нет; **OSV API сломан** (эндпоинт `querybatch`
игнорирует версию — отдаёт уязвимости даже для `99.0.0`, НЕ использовать для вердиктов!).
Надёжно: бэк — официальная PyPI vulnerability API по точным версиям из `uv.lock`
(скрипты в `%TEMP%\opencode\`: `make_reqs.py`, `pypi_audit.py`), фронт — `npm audit`.

**Сделано:**
- `uv lock --upgrade` + `uv sync` через **uv 0.11.18, поставленный pip-ом во временный
  венв** (штатный `uv` в окружении по-прежему сломан). Ключевые бампы: fastapi 0.141.1,
  starlette 1.7.0, uvicorn 0.54.0, apprise 2.0.0, python-multipart 0.0.32, authlib 1.8.0,
  pillow 12.3.0, sqlalchemy 2.1.1, websockets 17.1, safeuploads 1.1.1.
- **`joserfc>=1.6.8,<1.7` в `pyproject.toml`** — 1.7+ требует `sub:StringOrURI`, а
  `token_manager.py` кладёт `int user.id` → 1.7.x **ломает вход/рефреш токенов**
  (поймали тесты). 1.6.8 содержит оба фикса (CVE-2026-48990, CVE-2026-49852).
- Фронт: `npm audit fix` ×2 + вручную `vue@3.5.44`, `vitest@4.1.12` (npm update их
  не двигал) → **0 critical/high** (было 2 critical + 10 high).
- `app/core/file_uploads.py::_resolve_upload_path` — отклоняет имена, нормализующиеся
  в саму директорию (пробел на Windows) — фикс гипотезисного теста; ruff чист.

**Тесты:** бэк ~4031 (2 пачки) — все зелёные после фиксов; фронт 685/685 + типы + сборка.

**Известный артефакт окружения (НЕ прод):** `tests/core/test_file_uploads.py` (2 теста)
падают **только в длинном общем прогоне** с ошибкой «Validation memory limit exceeded»:
safeuploads ждёт, что на Windows модуля `resource` нет (монитор памяти выключен), а в
сборке Python 3.14 на этой машине он **builtin** → включён, и в 96-минутной сессии цепляет
рост памяти процесса. В изоляции — зелёные. В проде (Linux) монитор считает корректно:
срабатывает только на реальную зигзаг-бомбу (+512MB за одну валидацию).

**Остаток уязвимостей:** фронт 4 low (цепочка `vite-plugin-pwa → workbox →
@rollup/plugin-node-resolve → deepmerge`; фикса deepmerge ещё нет — 4.3.1 последний;
`npm audit fix --force` НЕ применять — он деградирует vite-plugin-pwa до 0.2.1).
Бэк prod: pillow 55 + authlib 6 + certifi 2 + otel-api 1 — все заблокированы карантином
`exclude-newer = 30 дней` (фиксы вышли 14–20.10, карантин истекает ~11.11 → заедут сами).
Оценка риска при карантине: низкая (pillow только генерирует QR, валидацию токенов делает
патченный joserfc, certifi — устаревший корень). Dev: virtualenv 11, filelock 3, uv 2,
dnspython 1 — неважно для прода.

---

## Сессия 3 — каталог 914+RU, лента, инвентарь для ИИ, виджеты (2026-10-29, v0.27.0)

**Заголовок:** `feat: exercise catalog 914 + russian names, feed publishing, training inventory, overview nutrition widgets, v0.27.0`.

**Коммит:** (смотри HEAD) + `fix: scanner dialog, privacy publish toggle` в теле.

### 1. Каталог упражнений (ядро запроса пользователя)
- **+42 упражнения** из публичного датасета wrkout/exercises.json (Unlicense,
  источник `exercises.json-master/` — добавлен в `.gitignore`, снапшот уже вшит):
  маппинг полей (category по primaryMuscles, equipment/muscles → словари wger,
  id 10000+crc32(name) — стабильные, uuid `wrkout-<crc32>`, license Unlicense,
  instructions → description). Новые словари: equipment 13 Machine, 14 Medicine ball,
  15 Foam roller, 16 Other; muscles 17 Adductor group, 18 Hip abductors, 19 Forearm flexors.
- **Русские названия для всех 914** упражнений — `backend/assets/exercise_names_ru.json`
  (id → ru; перегенерируемые исходники переводов лежали в exercises.json-master,
  удалены). Снапшот пересобран `scripts/enrich_catalog.py` (новый, идемпотентный:
  merge extra + ru overlay; хард-правило — не перезаписывает нативные wger-ru).
- **Поиск по языку**: `GET /workouts/exercises?lang=ru|en` — `_matches_query`
  сопоставляет только язык запроса (+канонический en всегда); `_display_name`
  сортирует по названию на языке UI. Фронт `searchCatalog` передаёт `lang`,
  пикер перезапускает поиск при смене локали.
- **Uptime-сид**: `main._seed_exercise_catalog` пересеивает, если
  count < snapshot count ИЛИ строки без ru-имён (LIKE '%"ru"%').
- i18n: новые equipment/muscles ключи в ru/en `workouts.json`.

### 2. Публикация тренировок в ленту (opt-in)
- Новая настройка `users_privacy_settings.publish_workouts_in_feed`
  (default **false**, миграция `v0_27_0_workout_feed.py`, rev `a7b2c3d4e5f6` ← `e5f6a7b8c9d0`).
- `POST /workouts/sessions` при включённой настройке пишет Activity
  (type 19, distance 0, start = session.date 12:00 UTC, elapsed = duration,
  calories, description = comment + "N упражнений · M подходов · V кг"
  по preferred_language ru/en, hide_* наследуются от privacy).
  `workout_sessions.activity_id` (FK SET NULL) — ссылка.
- `DELETE /workouts/sessions/{id}` удаляет связанную Activity (best-effort).
  Обновления сессий нет (API не имеет PUT).
- Фронт: тумблер в PrivacySettingsCard (`publishTitle/publishWorkoutsInFeed(+Hint)`),
  types/profile.ts, `UsersMe`/`UsersPrivacySettingsUpdate` в api.generated.ts
  (**обновлён вручную** — npx не смог скачать openapi-typescript; при следующем
  нормальном `npm run gen:api` проверь drift-CI).

### 3. Инвентарь для ИИ (Gears → «Тренировочный инвентарь»)
- Таблица `user_equipment` (name, equipment_id → словарь каталога, weight_kg,
  quantity), CRUD `/workouts/equipment` (модели: `workouts/equipment_{models,schema,crud,router}.py`,
  включён перед `/{plan_id}`).
- Фронт: `EquipmentDialog.vue` на GearsView (кнопка «Тренировочный инвентарь»),
  сервис + queryKeys.workouts.equipment(), i18n `gears.equipment.*` ru/en.
- ИИ-планировщик: `generate_plan(..., user_id)` → `inventory_block` добавляется
  в промпт; каталог жёстко фильтруется до допустимого снаряжения
  (`_ALWAYS_AVAILABLE_EQUIPMENT = {4,7}` — коврик+собственный вес) c fallback
  на полный каталог, если фильтр высушил выборку.
- Тесты: `tests/workouts/test_equipment.py` (7), `test_feed.py` (10),
  lang-тесты в `test_catalog.py`, `TestInventoryBlock` в `test_ai_planner.py`.

### 4. «Обзор»: виджеты питания + сканер
- `HealthDashboardView`: секция «Питание» (съедено + Б/У/Ж, сожжено, баланс)
  из `useNutritionSummaryQuery` (новое `queryKeys.nutrition.summary`,
  `features/nutrition/composables/useNutrition.ts`).
- **Сканер штрих-кодов починен**: `NutritionScannerDialog.vue` —
  `await nextTick()` + `flush:'post'` (Html5Qrcode создавался до монтирования
  портала диалога → «HTML Element with id=nutrition-scanner not found»).
- Иконки: gym-типы (10/19/20/41/46/47) получили Dumbbell в `activityTypeIcon`.

### 5. Системный инцидент окружения (НЕ prod): сломан loopback
- Пол утрачивал соединения на 127.0.0.1/::1 (accept не получал connect),
  что вешало **asyncio-тесты и TestClient**; вероятная причина — KumaFlow (VPN;
  WFP-фильтры; 5 процессов). НО это же объясняет и старое зависание
  `tests/core/test_apprise.py` из прошлой сессии! После перезагрузки ПК
  loopback восстановлен, все async-прогоны зелёные. В прод — не переносить,
  на CI не влияет. Для грядущих отборов: `asyncio.run(asyncio.sleep(0))` —
  чек здоровья loopback перед полном прогоном.

### Итог проверок v0.27.0
- Backend: `ruff check/format` ✅; mypy — в правленых файлах 0 ошибок (207
  старых в чужих модулях: strava 66, activities 67, auth 44 — то же, что было);
  финальные прогоны pytest: `workouts + privacy + profile/router + config = 294 passed`,
  в последний заход `tests\workouts + users_privacy + profile_router + config = 282 passed`.
- Frontend: vue-tsc ✅, oxlint/eslint ✅, prettier ✅, vitest **685/685** ✅.
- i18n JSON валидированы (ru/en workouts/gears/settings + health).

### Статус на момент сохранения handoff (2026-10-29)
- Коммит `2468705` **запушен** в `master` ✅ (`9a38bf0..2468705`).
- CI «Build & Push Docker Image» #56 для `2468705` был **in_progress** в момент
  сохранения: https://github.com/mrSaT13/serverZAPPFIT/actions/runs/40869643177 —
  при возобновлении проверить: success → деплоить; failure → лог, приоритетно
  `openapi-types-check` drift (api.generated.ts правил руками).
- `exercises.json-master/` — заигнорен (`# local exercise source dataset`),
  снапшот = единственный артефакт в репо; временные файлы переводов в нём не
  коммитились.
- `oauth/uv.lock`, `package-lock.json`, `pyproject.toml`, `config.py`,
  `test_config_extra.py`, `off_client.py` — версионный бамп 0.26.0 → 0.27.0 ✅
  (`uv lock` пересобирать не требовалось).

### ЧТО ОСТАЛОСЬ / ИДЕИ НА СЛЕДУЮЩУЮ СЕССИЮ
1. **Деплой** на сервере: тег `:latest` в compose → `docker compose pull && up -d`,
   лог будет `Exercise catalog stale ... — re-seeding` → `Seeded exercise catalog: 914`.
   Ручная проверка: пикер (русские имена! поиск «жим»), сканер камеры (HTTPS),
   тумблер публикации + сохранение тренировки → ленты, инвентарь + «Создать с ИИ».
2. **Деплой: если CI #56 упал** — сначала лог drift-wf или сборки образов.
3. Open-продолжения со старых сессий: 4 low npm (deepmerge, фикса нет); бэк-каран
   `exclude-newer=30 дней` истекает ~11.11 — пересобрать лок после; ~207 старых
   mypy-ошибок; «полный pytest» больше не виснет после перезагрузки (loopback) —
   но известный пункт `connect_timeout` в `core/database.py` всё равно полезен.
4. Картинки упражнений (jpg в exercises.json-master) — отложExplicitly по решению
   пользователя; когда решит встраивать — писать менеджер путей
   (например, статический роут `/exercise-images/{id}.jpg` с снапшот-полем).
5. Возможные позднейшие доработки фич: галочка «опубликовать» прямо в диалоге
   сессии (сейчас — только глобальный тумблер), локализация настроек
   `gears.equipment.*` на все 31 локаль (сейчас fallback en).
