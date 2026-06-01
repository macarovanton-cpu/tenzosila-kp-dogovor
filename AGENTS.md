# AGENTS.md — Tenzosila KP & Dogovor

Инструкция для Codex и других AI-агентов. Читай перед любой задачей.

## Стек

Python 3.11+, Streamlit, docxtpl, pytest. Supabase (PostgreSQL). JSON-справочники в `data/`.

## Структура

```
src/                # app.py + модули (config, data_loader, state, filters, pricing,
                    #   validation, spec_builder, ui/, generators/, contracts/, storage/)
data/               # models.json, prices.json, options.json, payment_terms.json, clauses.yaml
templates/          # DOCX-шаблоны (kp/, contracts/)
tests/              # pytest
docs/               # STATUS.md (источник правды о прогрессе), decisions.md, backlog.md
knowledge_base/     # read-only референсы
scripts/            # утилиты
```

## Команды

```bash
streamlit run src/app.py   # запуск приложения
pytest tests/ -v           # тесты (должны быть GREEN перед коммитом)
```

## Критические правила домена

- **НДС в РФ = 22%** — не 20%, не «стандартный». Не «исправлять» в документах.
- Цены в `prices.json` имеют 3 класса по `price_class`:
  - `A_retail_and_dealer`: slider `dealer_ru` ↔ `retail×1.4`, default `retail`.
  - `B_retail_only`: slider `retail×0.6` ↔ `retail×1.4`, default `retail`.
  - `C_manual_range`: `number_input` `range_min` ↔ `range_max`, default `price_retail`.
- Дефолт пресета оплаты — `split_by_items`.
- JSON-справочники в `data/` — не трогать без явного указания пользователя.
- `knowledge_base/` — read-only, не редактировать.
- Без согласования не делать: Битрикс-интеграцию, ORM, переписывание JSON в `data/`, правки в `knowledge_base/`.

## Git

- Conventional Commits **на русском**: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`
  - Пример: `feat: добавить валидацию суммы договора`
- Один коммит = один логический шаг.
- `git push` — **только по явному запросу пользователя**, самостоятельно не делать.
- Новые ветки — **не создавать**, работа в `main`.
- Перед коммитом: `pytest tests/` должен пройти. Если красное — не коммитить.

## Архитектурные инварианты

- Состояние КП: плоский `st.session_state` с префиксными ключами (`opt_{key}_enabled` и т.п.).
- Состояние договора: вложенная структура `st.session_state["contract"]`:
  `specification.items`, `flags`, `scope_overrides`, `card`, `extracted`.
- Snapshot КП→Договор обязан передавать `foundation_execution`,
  `foundation_sections`, `model_code`; контракт описан в `docs/HANDOFF.md`.
- Derived-значения (model_id, spec_items, суммы) — считать на рендере, не хранить в state.
- Валидация возвращает `(errors, warnings)`. `errors` блокируют кнопку.
- При смене модели — сбросить все options, поставить model_price = retail новой модели.

## Работа по задаче

- `docs/STATUS.md` — источник правды по текущей работе; читать «Активную задачу» в начале.
- В «Активной задаче» шаги ведутся чек-листом; текущий шаг помечен `← ТЕКУЩИЙ`.
- После завершения шага: поставить `[x]`, перенести маркер на следующий шаг,
  добавить запись в лог и отдельным коммитом зафиксировать галочку.

## Принципы разработки

- **Think Before Coding**: сначала понять задачу и неоднозначности, потом править.
- **Surgical Changes**: менять только то, что относится к задаче.
- **Verification First**: заранее назвать проверку и закрывать задачу только после неё.

## Стиль кода

- Type hints везде.
- Комментарии на русском, имена переменных/функций на английском.
- Файлы ≤ 200 строк; при разрастании — разбивать.
- Новые зависимости в `requirements.txt` — только с одобрения пользователя.

## Текущий статус

Читай `docs/STATUS.md` — там актуальная фаза, открытые задачи, техдолг.
