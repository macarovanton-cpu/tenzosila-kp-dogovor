# Admin Panel Task Breakdown

Декомпозиция пути из `docs/production_architecture_plan.md` в небольшие задачи
для **одного разработчика + AI-агентов**. Документ переработан в ревью
(см. `docs/admin_panel_review_notes.md`): план приземлён, переведён на
**value-first / JSON-first**, enterprise-часть отложена и запаркована.

Одна задача = один логический commit. Код приложения не переписывается: админка
наращивается вокруг текущих границ `src/app.py`, `src/data_loader.py`,
`src/pricing.py`, `src/spec_builder.py`, `src/storage/*`, `src/contracts/*`.

## Принципы (для одиночного разработчика)

1. **Сначала польза, потом инфраструктура.** БД не нужна для первой пользы.
2. **JSON-first.** Безопасный локальный слой и file-based сценарии раньше БД.
3. **Read-only / semi-manual раньше полноценной админки.**
4. **Не трогать опасное автономно:** расчёт цены, snapshot/HANDOFF, договорный
   экран, генерация DOCX, применение миграций.
5. **Не плодить роли/согласования/аудит, пока пользователь один.**
6. **Если можно проще без потери пользы — выбрать простой вариант.**

## Гейт по версии

`production_architecture_plan.md` §4: админку начинать **после закрытия
v2.1**. По `docs/STATUS.md` v2.1 ещё открыт (шаги 10-11). Поэтому:
- **Фаза 1** (локальная, ничего не ломает) — можно делать сейчас.
- **Фаза 2** (UI) — желательно после v2.1.
- **Фаза 3+** (runtime/БД/engine/договор) — строго после v2.1.

## Уровни безопасности агента

| Уровень | Значение |
|---|---|
| `safe_for_autonomous_agent` | Чистый локальный код/docs/тесты, без изменения runtime, БД, UI. Можно автономно/ночью. |
| `requires_human_review_after` | Агент делает, человек обязан проверить результат до использования (весь Streamlit-UI). |
| `requires_human_decision_before` | Нужно решение человека до старта (схема БД, бизнес-пороги, роли). |
| `do_not_run_autonomously` | Только с человеком в цикле, НЕ ночью (pricing-математика, snapshot/HANDOFF, договор, DOCX, миграции к реальной БД). |

---

## Фаза 1 — Foundation (ACTIVE, JSON-only, без БД, без UI)

Чистый Python + документация + read-only диагностика. Вся фаза
`safe_for_autonomous_agent`. Даёт первую пользу без риска для runtime.

| ID | Title | Goal | Business value | New files | Tests | Depends on | Safety | Size |
|---|---|---|---|---|---|---|---|---|
| AP-000 | Документация формата прайса | Описать формат `data/prices.json` (модели/опции/классы) | Единый референс формата; разблокирует валидатор и нормализатор | `docs/price_format.md` | docs-only | none | safe_for_autonomous_agent | small |
| AP-003 | Canonical model + normalizer прайса | `prices.json` → плоские price items без потери полей | Один формат для diff/валидации/будущей БД | `src/admin/price_models.py`, `src/admin/price_normalizer.py`, `tests/admin/test_price_normalizer.py` | unit (counts 45/65, классы 20/36/4/5/1) | AP-000 | safe_for_autonomous_agent | medium |
| AP-004 | Валидатор формата прайса | Проверять обяз. поля/типы/классы текущего `prices.json` | Плохой прайс ловится до использования | `src/admin/price_validator.py`, `tests/admin/test_price_validator.py` | unit good/bad rows | AP-003 | safe_for_autonomous_agent | medium |
| AP-013 | Price diff (две версии прайса) | Чистая функция new/changed/removed по нормализованным items | Сравнение прайсов без БД и без UI | `src/admin/price_diff.py`, `tests/admin/test_price_diff.py` | unit на фикстурах | AP-003 | safe_for_autonomous_agent | small |
| AP-009 | Read-only диагностика прайса | Функция/CLI: counts, классы, expired `valid_from`, нулевые/пустые цены, модели без цены | Видеть здоровье текущего прайса из терминала | `src/admin/price_diagnostics.py`, `tests/admin/test_price_diagnostics.py` | unit | AP-004 | safe_for_autonomous_agent | small |

---

## Фаза 2 — Minimal admin UI (ACTIVE, всё ещё JSON, без БД, без записи в data/)

Третья Streamlit-страница: read-only обзор + один безопасный сценарий
(validate + diff + download проверенного файла). **Не пишет в `data/`, не пишет
в БД.** Желательно после закрытия v2.1.

| ID | Title | Goal | Business value | New files | Tests | Depends on | Safety | Size |
|---|---|---|---|---|---|---|---|---|
| AP-008 | Shell страницы админки | Третья страница-заглушка в навигации | Каркас, дальше UI растёт мелкими шагами | `src/pages/3_Админка.py`, `src/admin/__init__.py` | AppTest smoke | AP-000 | requires_human_review_after | small |
| AP-015 | Read-only панель прайса и правил | Показать диагностику (AP-009) + коэффициенты A/B/C из `config.py` read-only | Админ видит состояние прайса и правила без терминала | `src/admin/price_overview_view.py` | UI/service tests | AP-008, AP-009 | requires_human_review_after | small |
| AP-010 | Validate + diff + download загруженного прайса | Загрузить подготовленный JSON → валидировать (AP-004) → diff с текущим (AP-013) → отдать проверенный файл на скачивание | Безопасно подготовить новый прайс без БД и без правки `data/` руками вслепую | `src/admin/price_upload_view.py`, фикстуры | service/UI tests | AP-004, AP-013, AP-008 | requires_human_review_after | medium |

После Фазы 2 уже есть практический результат: видеть текущий прайс, безопасно
проверять и сравнивать новый, не ломая `data/prices.json` и не трогая расчёт.

---

## Фаза 3 — DEFERRED: версионирование прайса в БД

Подключать **только** после того, как Фаза 2 доказала пользу, **и** v2.1 закрыт.
Здесь впервые появляются миграции. Любая миграция к реальной БД —
`do_not_run_autonomously`.

| ID | Title | Goal | Depends on | Safety | Size |
|---|---|---|---|---|---|
| AP-001 | Baseline DB-схема и миграционный каркас | Зафиксировать `kps`/`contracts`, завести `supabase/migrations/` | none | requires_human_decision_before | small |
| AP-002 | Миграции price-list таблиц | `price_lists`, `price_items`, `price_imports`, `price_import_errors` | AP-001 | requires_human_decision_before / apply=do_not_run_autonomously | medium |
| AP-005 | Storage repository прайсов | save/read версий прайса в Supabase | AP-002, AP-003 | requires_human_review_after | medium |
| AP-006 | Active price loader + JSON fallback | `load_prices` берёт active из БД, при сбое — `data/prices.json` | AP-005 | requires_human_review_after | medium |
| AP-007 | price_list_id в snapshot КП | Хранить версию прайса/цены в snapshot, защитить старые КП | AP-006 | do_not_run_autonomously | small |
| AP-011 | CSV/XLSX adapter импорта | Табличный формат без универсального PDF-парсера | AP-010 | requires_human_review_after | medium |
| AP-012 | Журнал ошибок импорта | Сохранять/показывать import errors | AP-004, AP-010 | requires_human_review_after | small |
| AP-014 | Активация/архив/rollback прайса | Статусы draft/validated/active/archived, один active | AP-005, AP-013 | requires_human_decision_before / apply=do_not_run_autonomously | medium |

---

## Фаза 4 — DEFERRED: pricing engine

Только после Фазы 3. Трогает расчёт цены и snapshot — самый чувствительный код.

| ID | Title | Goal | Depends on | Safety | Size |
|---|---|---|---|---|---|
| AP-016 | Модели pricing engine | `PricingContext`, `PriceBounds`, `PriceDecision` | AP-015 | requires_human_review_after | small |
| AP-017 | Parity engine текущих правил | Повторить A/B/C/UNKNOWN/on_request + ширину | AP-016 | requires_human_review_after | medium |
| AP-018 | Интеграция engine в price widgets | Перевести model/options UI на engine без смены UX | AP-017 | do_not_run_autonomously | large |
| AP-019 | Bounds в snapshot позиций КП | min/recommended/max/price_status по item | AP-018 | do_not_run_autonomously | medium |
| AP-020 | Валидация отклонений цены | Статусы ok/comment_required/approval_required/on_request | AP-019 | requires_human_decision_before | medium |
| AP-021 | UI комментариев по отклонениям | Просить комментарий при отклонении | AP-020 | do_not_run_autonomously | medium |

---

## Фаза 5 — PARKED: enterprise (вне near-term MVP)

Преждевременно для одного пользователя. Пересмотреть **только** при реальной
потребности (несколько пользователей, реальный руководитель-согласующий,
требование аудита). Сейчас НЕ детализируется как готовые задачи — это эпики.

| ID | Title | Эпик | Safety |
|---|---|---|---|
| AP-022 | Миграции rule set таблиц | Управляемые правила | requires_human_decision_before / apply=do_not_run_autonomously |
| AP-023 | Storage и loader rule sets | Управляемые правила | requires_human_review_after |
| AP-024 | Admin rule sets read-only | Управляемые правила | requires_human_review_after |
| AP-025 | Draft-edit глобальных правил | Управляемые правила | requires_human_decision_before |
| AP-026 | Исключения pricing | Управляемые правила | requires_human_decision_before |
| AP-027 | Users/roles/permissions schema | Роли | requires_human_decision_before / apply=do_not_run_autonomously |
| AP-028 | Current user adapter и guards | Роли | requires_human_decision_before |
| AP-029 | Approval request storage | Согласования | do_not_run_autonomously |
| AP-030 | Создание approval из КП | Согласования | do_not_run_autonomously |
| AP-031 | Очередь согласований руководителя | Согласования | requires_human_review_after |
| AP-032 | Блокировка договора при pending approval | Согласования | do_not_run_autonomously |
| AP-033 | Audit log schema/service | Аудит | do_not_run_autonomously |
| AP-034 | Аудит critical actions | Аудит | requires_human_review_after |
| AP-035 | Справочники managers/payment в БД | Справочники | requires_human_review_after |
| AP-036 | Admin UI справочников | Справочники | requires_human_review_after |
| AP-037 | Template versions и scanner | Шаблоны | do_not_run_autonomously |
| AP-038 | Admin template upload + smoke | Шаблоны | do_not_run_autonomously |
| AP-039 | Appendix library versioning | Приложения | do_not_run_autonomously |
| AP-040 | Data quality service | Качество данных | requires_human_review_after |
| AP-041 | Data quality dashboard | Качество данных | requires_human_review_after |
| AP-042 | Contract service boundary | Рефакторинг договора | do_not_run_autonomously |
| AP-043 | Generation metadata and runbook | Воспроизводимость документов | do_not_run_autonomously |

---

## Recommended Order

1. **Фаза 1** (`AP-000 → AP-003 → AP-004 → AP-013 → AP-009`) — можно начинать
   сейчас, автономно.
2. **Фаза 2** (`AP-008 → AP-015 → AP-010`) — после v2.1, с проверкой человеком.
3. **Фаза 3** — только если Фаза 2 показала пользу и нужна история версий в БД.
4. **Фаза 4** — только после Фазы 3, под ручным контролем (pricing).
5. **Фаза 5** — пересмотр по реальной потребности; пока не запускать.

`NEXT_TASK` = **AP-000**. Детальные самодостаточные task-файлы есть для активных
задач (Фаза 1-2). Deferred/parked задачи будут детализированы при входе в их фазу.
