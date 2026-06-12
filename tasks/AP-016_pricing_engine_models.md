<!-- review-banner -->
> **[DEFERRED — Фаза 4]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-016 — Модели pricing engine

Status: planned  
Size: small  
Depends on: AP-015

## Goal

Ввести доменные модели pricing engine: входной контекст, границы цены и
результат решения.

## Why

Сейчас UI получает `SliderParams` из `src/pricing.py`. Перед выносом правил в
БД нужен слой, который описывает min/recommended/max, status и причины решения
без привязки к Streamlit.

## Likely touched files

- `src/pricing.py`
- `tests/test_pricing.py`
- `docs/admin_panel_status.md`

## New files

- `src/pricing_engine.py` или `src/pricing/engine.py`, если будет выбран package
- `tests/test_pricing_engine.py`

## Tests

- Импорт моделей без Streamlit.
- Dataclass/TypedDict fields покрывают model/option/service.
- Defaults не меняют существующий pricing behavior.

## Manual verification

- Запустить Python import модуля.
- Убедиться, что существующий КП открывается без использования нового engine.

## Done criteria

- Есть `PriceBounds` с min/recommended/max.
- Есть `PriceDecision` с selected/status/requires_comment/requires_approval.
- Старые функции `get_slider_params` и `get_model_slider_params` не сломаны.

## Risks

- Ранняя абстракция может начать дублировать `SliderParams`. Держать слой
  минимальным.
