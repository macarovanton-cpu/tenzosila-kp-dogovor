<!-- review-banner -->
> **[DEFERRED — Фаза 3]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-006 — Active price loader с JSON fallback

Status: planned  
Size: medium  
Depends on: AP-005

## Goal

Научить загрузчик цен получать active price list из Supabase, а при
недоступности БД или отсутствии active версии безопасно возвращать
`data/prices.json`.

## Why

Это ключевой переходный слой: менеджерский экран КП продолжает работать, даже
если production-БД прайсов ещё не готова или временно недоступна.

## Likely touched files

- `src/data_loader.py`
- `src/storage/price_lists.py`
- `tests/test_app_flow.py`
- `docs/admin_panel_status.md`

## New files

- возможно `src/admin/price_loader.py`
- `tests/admin/test_active_price_loader.py`

## Tests

- DB unavailable -> JSON fallback.
- No active price list -> JSON fallback.
- Active price list -> структура совместима с текущим `prices`.
- AppTest smoke КП.

## Manual verification

- Запустить КП без Supabase credentials и убедиться, что страница открывается.
- В test DB создать active price и убедиться, что loader возвращает его.

## Done criteria

- Формат результата совместим с текущими `get_price_by_model_id`,
  `get_option_price`, `src/pricing.py`.
- Streamlit cache не мешает ручному обновлению active прайса.
- Нет изменения бизнес-расчётов.

## Risks

- Кэш `@st.cache_data` может скрывать смену active версии.
- Ошибка fallback может сломать весь КП экран.
