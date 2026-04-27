# Tenzosila KP & Dogovor Configurator

Внутренний инструмент для менеджеров Тензосилы: конфигуратор КП по автовесам ВЕСТА.
Следующая фаза — генерация договоров.

## Источник правды о прогрессе
**docs/STATUS.md** — читай первым. Там текущая фаза, открытые вопросы, план.

## Стек
Python 3.11+, Streamlit, docxtpl, pytest. Никаких БД и ORM — только JSON-справочники.

## Структура
```
src/          # код (app.py + config/data_loader/state/filters/pricing/validation/spec_builder + ui/ + generators/)
data/         # models.json, prices.json, options.json, payment_terms.json
templates/    # DOCX-шаблоны
tests/        # pytest
docs/         # STATUS.md, decisions.md, backlog.md
03_knowledge_base/  # референсы и описание типа (read-only)
```

## Команды
```bash
streamlit run src/app.py
pytest tests/ -v
```

## Ключевые архитектурные решения
- **Плоский session_state** с префиксными ключами (`opt_{key}_enabled`, `opt_{key}_price`). Вложенных dict нет, кроме `options`.
- **3 класса цен** (поле `price_class` в prices.json):
  - `A_retail_and_dealer` — slider [dealer_ru ↔ retail×1.4], default retail
  - `B_retail_only` — slider [retail×0.6 ↔ retail×1.4], default retail
  - `C_manual_range` — number_input [range_min ↔ range_max], default price_retail
- **При смене модели** — сбросить все options, поставить model_price = retail новой модели.
- **Derived** (model_id, spec_items, суммы) — считаем на рендере, не храним в state.
- **Валидация** возвращает `(errors, warnings)`. errors блокируют кнопку.
- **Дефолт пресета оплаты** — `split_by_items`.

## Правила работы
- JSON-справочники правлю в чате вручную. Не переписывай их.
- Type hints везде. Комментарии на русском, имена на английском.
- Файлы ≤200 строк, при разрастании — разбивай.
- Новые зависимости в requirements.txt — только с моего одобрения.
- Git: Conventional Commits на русском (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`). Один коммит = один шаг из STATUS.md.
- Code сам делает `git add` и `git commit` после закрытия каждого блока работы.
- Code **НЕ делает `git push`** — пуш только по явному запросу пользователя.
- Code **НЕ создаёт новые ветки** — работа в `main`.
- Перед коммитом: `pytest tests/` должен пройти. Если красное — не коммитить.

## Не делать без согласования
Битрикс-интеграцию, БД, ORM, сложные валидации ФИО/email (MVP — хватает непустоты), переписывание JSON в data/, правки в 03_knowledge_base/.

## Домен
ВЕСТА — автовесы Тензосилы. Линейки в MVP: С, СЛ, Ф, ФЛ, П. Обозначение: ВЕСТА-[линейка]-[max_т]-[длина_м]-[Ц]. Терминология — `03_knowledge_base/spravochnik_vesta_fixed.md`.

## Skills

Для работы со Streamlit используй установленный скилл в `~/.claude/skills/streamlit/`. Главные материалы:
- `~/.claude/skills/streamlit/AGENTS.md` — обзор скилла
- `~/.claude/skills/streamlit/developing-with-streamlit/` — паттерны разработки
- `~/.claude/skills/streamlit/template/` — шаблоны компонентов

При правке Streamlit-компонентов в `src/ui/` — сначала свериться с актуальными API из этих материалов, не работать "по памяти".
