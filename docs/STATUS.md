# STATUS — Tenzosila KP & Dogovor

Последнее обновление: 2026-05-23

---

## Где мы сейчас

**v1.0 — clauses library + override UI. Задачи 6, 7, 8 выполнены.**

Последний тег: **v1.0** (clauses library, override UI, spec_v2 генерация).

---

## Что закрыто за последние сессии

**Архитектурная чистка репо (закрыто):**
- Удалён дубль `src/data_loaders/`, мёртвый `src/models/`, `test_generate.py` перенесён в `scripts/`
- Архив старых findings в `docs/archive/`
- Бэкапы шаблонов в `templates/contracts/backup/`, старые в `templates/backup/` снесены
- `03_knowledge_base/` → `knowledge_base/`
- `01_concept/`, `02_plan/` удалены
- `.gitignore` дополнен (`docs/superpowers/`, `_repo_tree.txt`)
- CLAUDE.md обновлён: knowledge_base path, Supabase, contract namespace, verification, plan mode, error log

**Архитектура v2 договоров — теория (закрыто):**
- `docs/architecture/contracts_v2.md` — концепция «структура vs данные»
- `docs/contract_templates_v1/` — 9 эталонных шаблонов в Markdown (референс)
- `data/clauses.yaml` — черновик 24 clauses (пометка: pre-legal-review)
- Принято решение: два контейнера, `contract.docx` (рамка) и `spec_v2.docx` (спецификация) — отдельные документы

**Шаг 6 архитектуры v2 (закрыто, тег v0.9):**
- `src/contracts/spec_items.py` — SpecItem TypedDict, make_custom_item
- `build_specification_items()` в `from_kp.py`
- `set_spec_items()` / `get_spec_items()` в state.py
- `fill_spec_with_items()` — двухшаговый python-docx рендер
- UI: st.data_editor с num_rows="dynamic", кнопка «+ Добавить позицию», пересчёт total реактивный

**Шаг 7 архитектуры v2 — задачи 1-4 (закрыто, не теговано):**
- `src/contracts/clauses_dsl.py` — AST-парсер applies_when, whitelist 6 переменных (foundation_scope, installation_scope, verification_scope, has_orion, orion_poles_scope, winter_concrete), security-тесты
- `src/contracts/clauses_loader.py` — загрузка clauses.yaml через strictyaml, валидация
- `src/contracts/clauses_context.py` — build_clauses_context(deal), 6 переменных DSL из SpecItems, маппинг fundament_jb/fundament/rama
- `src/contracts/clauses_renderer.py` — RenderedClause, нумерация 4.1-6.2, jinja-подстановка, obligations_range
- 53 теста зелёные, 178/178 contract tests, 385/390 общий
- strictyaml добавлен в requirements.txt
- В data/clauses.yaml добавлен section_number: 4/5/6/7

**Шаг 7 архитектуры v2 — задачи 6, 7, 8 (закрыто, тег v1.0):**
- `src/contracts/state.py` — flags + scope_overrides в `_CONTRACT_DEFAULTS`
- UI "Особые условия": checkbox зимний период, expander override-флаги (4 selectbox), expander предпросмотр пунктов
- `src/pages/2_Договор.py` — генерация спецификации переключена на fill_spec_v2 + fallback
- `tests/contracts/test_page_dogovor_overrides.py` — 5 тестов (winter_concrete, foundation_scope, verification_scope overrides)

**Шаг 7 архитектуры v2 — задача 5 (закрыто):**
- Создан `templates/contracts/spec_v2.docx` — шаблон с маркерами {{CLAUSE_SECTION_*}}
- Создан `src/contracts/spec_v2_filler.py` — fill_spec_v2()
- Создан `scripts/create_spec_v2_template.py`
- Создан `tests/contracts/test_fill_spec_v2.py` — 10 тестов (но проверяют len, не контент ячеек)
- Найден баг: ячейки таблицы позиций пустые (`_set_cell_text` не создаёт w:t при их отсутствии)
- Найдено: ТТХ зашиты под ВЕСТА-СЛ-80-18-Ц, кит зашит, оплата 6 слотов, сроки 3 строки, год 2026 хардкод, лишняя кавычка в «Тензосила»

---

## Следующие задачи (v1.1+)

---

## Известные ограничения v1.0 (для следующего цикла)

- Нумерация Приложений фиксированная (№1, №2), без учёта ОРИОН-Приложений и материалов — backlog v1.1
- ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА — константа «не более 50 м», не зависит от длины кабеля сделки
- Контрольный лист только при `foundation_scope == "customer_builds"`

---

## Открытый техдолг (после v1.0)

- [ ] Юридический ревью clauses.yaml (формулировки 24 пунктов)
- [ ] UI-глюки страницы Договор:
  - «Последние КП» — клик не загружает snapshot
  - «Номер КП» — Ctrl+V не работает
  - Реализовать поиск КП по названию Заказчика
- [ ] 5 падающих test_e2e_synthetic (с Части 8)
- [ ] Выбор финальной AI-модели для extractor
- [ ] Обновление эталонов фикстур под модель items
- [ ] Архитектурный рефакторинг data_loader: убрать дублирование equipment_specs.json ↔ models.json
- [ ] vMerge слияние ячеек в таблице спецификации DOCX
- [ ] Фаза 1.7 — деплой на Streamlit Cloud (или VPS)
- [ ] Тендерный модуль
- [ ] База знаний компании (референс-лист 30–50 кейсов)
- [ ] Bitrix24 REST API

---

## Теги версий

- `v0.6` — стабильный модуль договоров (один шаблон, базовый extractor)
- `v0.7` — Supabase-интеграция, двухрежимный UI
- `v0.8` — закрытие багов после ручной проверки КП→договор (Промты A, B, C)
- `v0.9` — массив позиций спецификации + кастомные позиции + data_editor с пересчётом total
- `v1.0` — clauses library, override UI, spec_v2 генерация