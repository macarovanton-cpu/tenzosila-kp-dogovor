<!-- review-banner -->
> **[DEFERRED — Фаза 4]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (расчёт цены)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-018 — Интеграция engine в price widgets

Status: planned  
Size: large  
Depends on: AP-017

## Goal

Перевести `render_model_section` и `render_options_section` на pricing engine,
сохранив прежний UX и значения слайдеров.

## Why

После parity engine должен стать источником расчётных границ для UI. Это
подготовит snapshot, comments и approvals.

## Likely touched files

- `src/ui/model_section.py`
- `src/ui/options_section.py`
- `src/pricing.py`
- `src/pricing_engine.py`
- `tests/test_model_section.py`
- `tests/test_options_section.py`
- `docs/admin_panel_status.md`

## New files

- возможно adapter `src/pricing_widget_adapter.py`

## Tests

- Existing model/options UI tests.
- Pricing parity tests.
- AppTest smoke для КП.

## Manual verification

- Открыть КП.
- Выбрать модель и несколько опций разных классов.
- Проверить min/default/max слайдера против текущего поведения.

## Done criteria

- Поведение слайдеров не изменилось.
- `on_request` всё ещё блокирует генерацию.
- Нет Streamlit widget key conflict.

## Risks

- Streamlit state может конфликтовать при смене модели.
- Задача достаточно широкая; не добавлять новые business rules здесь.
