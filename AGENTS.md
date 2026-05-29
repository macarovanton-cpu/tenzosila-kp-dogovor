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
- JSON-справочники в `data/` — не трогать без явного указания пользователя.
- `knowledge_base/` — read-only, не редактировать.

## Git

- Conventional Commits **на русском**: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`
  - Пример: `feat: добавить валидацию суммы договора`
- Один коммит = один логический шаг.
- `git push` — **только по явному запросу пользователя**, самостоятельно не делать.
- Новые ветки — **не создавать**, работа в `main`.
- Перед коммитом: `pytest tests/` должен пройти. Если красное — не коммитить.

## Архитектурные инварианты

- Состояние КП: плоский `st.session_state` с префиксными ключами (`opt_{key}_enabled` и т.п.).
- Состояние договора: вложенная структура `st.session_state["contract"]`.
- Derived-значения (model_id, spec_items, суммы) — считать на рендере, не хранить в state.
- Валидация возвращает `(errors, warnings)`. `errors` блокируют кнопку.
- При смене модели — сбросить все options, поставить model_price = retail новой модели.

## Стиль кода

- Type hints везде.
- Комментарии на русском, имена переменных/функций на английском.
- Файлы ≤ 200 строк; при разрастании — разбивать.
- Новые зависимости в `requirements.txt` — только с одобрения пользователя.

## Текущий статус

Читай `docs/STATUS.md` — там актуальная фаза, открытые задачи, техдолг.
