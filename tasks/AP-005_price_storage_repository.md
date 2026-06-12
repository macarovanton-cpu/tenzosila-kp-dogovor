<!-- review-banner -->
> **[DEFERRED — Фаза 3]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-005 — Storage repository для прайсов

Status: planned  
Size: medium  
Depends on: AP-002, AP-003

## Goal

Добавить storage-функции для создания draft price list, сохранения items,
получения active price list и чтения import errors.

## Why

`src/data_loader.py` и Streamlit UI не должны напрямую собирать Supabase SQL.
Нужен отдельный слой, похожий по духу на `src/storage/supabase_client.py`, но
для прайсов.

## Likely touched files

- `src/storage/__init__.py`
- `tests/storage/conftest.py`
- `docs/admin_panel_status.md`

## New files

- `src/storage/price_lists.py`
- `tests/storage/test_price_lists.py`

## Tests

- Создать draft price list.
- Вставить model/option items.
- Получить active price list.
- Проверить поведение при пустой БД.

## Manual verification

- На test Supabase создать draft и прочитать его обратно.
- Убедиться, что `kps_test` и `contracts_test` не затронуты.

## Done criteria

- Все операции обёрнуты в понятные исключения storage layer.
- Функции не импортируют Streamlit UI.
- Tests изолированы на test tables или моках.

## Risks

- Storage-тесты могут зависеть от сети и зависать.
- Если нет test DB, использовать mock client и пометить human review.
