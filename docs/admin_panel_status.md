# Admin Panel Status

Источник истины по статусам задач `AP-*`. Порядок — по фазам из
`docs/admin_panel_task_breakdown.md`. Рабочая ветка: `main`.

Легенда статуса: `planned` · `in_progress` · `done` · `blocked` · `deferred` ·
`parked`. Агент берёт только задачу из `tasks/NEXT_TASK.md`.

`NEXT_TASK = AP-000`.

## Фаза 1 — Foundation (ACTIVE · JSON-only · safe_for_autonomous_agent)

| task_id | title | phase | safety | status | commit | tests | human_review | notes |
|---|---|---|---|---|---|---|---|---|
| AP-000 | Документация формата прайса | 1 | safe_for_autonomous_agent | done | this_commit | `rtk python -m pytest tests/test_pricing.py -q` | n/a | формат описан; B=36 по `price_class`, из них 1 `on_request` |
| AP-003 | Canonical model + normalizer прайса | 1 | safe_for_autonomous_agent | done | this_commit | `rtk python -m pytest tests/admin/test_price_normalizer.py -q` | n/a | плоские price items без подключения к runtime |
| AP-004 | Валидатор формата прайса | 1 | safe_for_autonomous_agent | done | this_commit | `rtk python -m pytest tests/admin/test_price_validator.py -q` | n/a | текущий прайс без error; `data_incomplete` = warning |
| AP-013 | Price diff (две версии прайса) | 1 | safe_for_autonomous_agent | planned |  | not_run | n/a | NEXT_TASK; dep AP-003; чистая функция |
| AP-009 | Read-only диагностика прайса | 1 | safe_for_autonomous_agent | planned |  | not_run | n/a | dep AP-004; без UI/БД |

## Фаза 2 — Minimal admin UI (ACTIVE · JSON · после v2.1)

| task_id | title | phase | safety | status | commit | tests | human_review | notes |
|---|---|---|---|---|---|---|---|---|
| AP-008 | Shell страницы админки | 2 | requires_human_review_after | planned |  | not_run | pending | dep AP-000; видимая страница |
| AP-015 | Read-only панель прайса и правил | 2 | requires_human_review_after | planned |  | not_run | pending | dep AP-008, AP-009 |
| AP-010 | Validate + diff + download прайса | 2 | requires_human_review_after | planned |  | not_run | pending | dep AP-004, AP-013, AP-008; НЕ пишет в data/ и БД |

## Фаза 3 — DEFERRED: версионирование прайса в БД (после v2.1 + пользы от Фазы 2)

| task_id | title | phase | safety | status | commit | tests | human_review | notes |
|---|---|---|---|---|---|---|---|---|
| AP-001 | Baseline DB-схема и миграционный каркас | 3 | requires_human_decision_before | deferred |  | not_run | pending | нужна сверка с live Supabase |
| AP-002 | Миграции price-list таблиц | 3 | do_not_run_autonomously (apply) | deferred |  | not_run | pending | миграции к реальной БД — только человеком |
| AP-005 | Storage repository прайсов | 3 | requires_human_review_after | deferred |  | not_run | pending | dep AP-002, AP-003 |
| AP-006 | Active price loader + JSON fallback | 3 | requires_human_review_after | deferred |  | not_run | pending | не убирать JSON fallback; учесть cache |
| AP-007 | price_list_id в snapshot КП | 3 | do_not_run_autonomously | deferred |  | not_run | pending | трогает snapshot/HANDOFF |
| AP-011 | CSV/XLSX adapter импорта | 3 | requires_human_review_after | deferred |  | not_run | pending | возможна новая зависимость — согласовать |
| AP-012 | Журнал ошибок импорта | 3 | requires_human_review_after | deferred |  | not_run | pending |  |
| AP-014 | Активация/архив/rollback прайса | 3 | do_not_run_autonomously (apply) | deferred |  | not_run | pending | меняет active версию |

## Фаза 4 — DEFERRED: pricing engine (после Фазы 3)

| task_id | title | phase | safety | status | commit | tests | human_review | notes |
|---|---|---|---|---|---|---|---|---|
| AP-016 | Модели pricing engine | 4 | requires_human_review_after | deferred |  | not_run | pending |  |
| AP-017 | Parity engine текущих правил | 4 | requires_human_review_after | deferred |  | not_run | pending | сначала parity, потом интеграция |
| AP-018 | Интеграция engine в price widgets | 4 | do_not_run_autonomously | deferred |  | not_run | pending | трогает расчёт цены |
| AP-019 | Bounds в snapshot позиций КП | 4 | do_not_run_autonomously | deferred |  | not_run | pending | трогает snapshot/HANDOFF |
| AP-020 | Валидация отклонений цены | 4 | requires_human_decision_before | deferred |  | not_run | pending | нужны бизнес-пороги |
| AP-021 | UI комментариев по отклонениям | 4 | do_not_run_autonomously | deferred |  | not_run | pending |  |

## Фаза 5 — PARKED: enterprise (пересмотр по реальной потребности)

| task_id | title | phase | safety | status | commit | tests | human_review | notes |
|---|---|---|---|---|---|---|---|---|
| AP-022 | Миграции rule set таблиц | 5 | do_not_run_autonomously (apply) | parked |  | not_run | pending | эпик: управляемые правила |
| AP-023 | Storage и loader rule sets | 5 | requires_human_review_after | parked |  | not_run | pending |  |
| AP-024 | Admin rule sets read-only | 5 | requires_human_review_after | parked |  | not_run | pending |  |
| AP-025 | Draft-edit глобальных правил | 5 | requires_human_decision_before | parked |  | not_run | pending |  |
| AP-026 | Исключения pricing | 5 | requires_human_decision_before | parked |  | not_run | pending |  |
| AP-027 | Users/roles/permissions schema | 5 | requires_human_decision_before | parked |  | not_run | pending | эпик: роли |
| AP-028 | Current user adapter и guards | 5 | requires_human_decision_before | parked |  | not_run | pending |  |
| AP-029 | Approval request storage | 5 | do_not_run_autonomously | parked |  | not_run | pending | эпик: согласования |
| AP-030 | Создание approval из КП | 5 | do_not_run_autonomously | parked |  | not_run | pending |  |
| AP-031 | Очередь согласований руководителя | 5 | requires_human_review_after | parked |  | not_run | pending |  |
| AP-032 | Блокировка договора при pending approval | 5 | do_not_run_autonomously | parked |  | not_run | pending | трогает договорный экран |
| AP-033 | Audit log schema/service | 5 | do_not_run_autonomously (apply) | parked |  | not_run | pending | эпик: аудит |
| AP-034 | Аудит critical actions | 5 | requires_human_review_after | parked |  | not_run | pending |  |
| AP-035 | Справочники managers/payment в БД | 5 | requires_human_review_after | parked |  | not_run | pending | эпик: справочники |
| AP-036 | Admin UI справочников | 5 | requires_human_review_after | parked |  | not_run | pending |  |
| AP-037 | Template versions и scanner | 5 | do_not_run_autonomously | parked |  | not_run | pending | эпик: шаблоны |
| AP-038 | Admin template upload + smoke | 5 | do_not_run_autonomously | parked |  | not_run | pending | генерация DOCX |
| AP-039 | Appendix library versioning | 5 | do_not_run_autonomously | parked |  | not_run | pending | риск для склейки приложений |
| AP-040 | Data quality service | 5 | requires_human_review_after | parked |  | not_run | pending |  |
| AP-041 | Data quality dashboard | 5 | requires_human_review_after | parked |  | not_run | pending |  |
| AP-042 | Contract service boundary | 5 | do_not_run_autonomously | parked |  | not_run | pending | рефакторинг договорного экрана |
| AP-043 | Generation metadata and runbook | 5 | do_not_run_autonomously | parked |  | not_run | pending |  |
