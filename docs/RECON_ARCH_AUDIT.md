# RECON: Архитектурный аудит перед миграцией (2026-07-12)

Read-only разведка. Источник правды — код на коммите 3eb5fb2.
Маркировка: **ФАКТ** — прочитано в коде (файл:символ указан),
**ГИПОТЕЗА** — вывод, не прослеженный до конца.

## 0. Стартовая точка (сверка с документами)

**ФАКТ.** `core/` — пустой каркас: все 10 файлов (включая
`core/settings.py`) по 0 строк, созданы коммитом f47be5a (P0-05).
Стражи границ `tests/test_core_boundaries.py` (нет `import streamlit`
в core/, нет кросс-импортов kp↔contracts) существуют и им пока нечего
охранять. STATUS.md здесь не врёт: активный фронт P0-06 «развязка
секретов». Весь живой код — в `src/`; «границы core/» ниже читаются как
«что из src/ готово к переносу».

---

## 1. Границы core/: что чисто, что тянет UI

### 1.1 Чистое (переносимо в core/ без правок) — ФАКТ

Ни одного `import streamlit` / `st.` / `session_state`:

- `src/contracts/` — 23 из 26 файлов: `from_kp.py`, `spec_items.py`,
  `payment_line.py`, `filler.py`, `compose.py`, `terms_renderer.py`,
  `clauses_loader.py`, `clauses_dsl.py`, `clauses_context.py`,
  `clauses_renderer.py`, `kit_renderer.py`, `tth_context.py`,
  `fundament_lookup.py`, `supplier.py`, `supply_filler.py`, `kp_load.py`,
  `requisites_extract.py`, `requisites_parser.py`,
  `requisites_validation.py`, `requisites_transforms.py`,
  `recommendations.py`, `custom_work_types.py`, `utils.py`.
- `src/generators/` — все 4: `kp_generator.py`, `payment_renderer.py`,
  `spec_vmerge.py`, `make_template.py`.
- `src/storage/snapshot_builder.py` — `build_kp_snapshot(state)` чистая,
  принимает Mapping.
- `src/utils/format.py`.
- `src/admin/` — 12 из 15 (вся логика прайса: `price_normalizer`,
  `price_validator`, `price_diff`, `price_write_service`,
  `price_upload_service`, `price_pdf_*` и др.).

Оговорка: многие из них транзитивно импортируют `src/data_loader.py`
(см. 1.2) — развязка загрузчика идёт первой, иначе «чистые» модули
тащат Streamlit через один импорт.

### 1.2 Связанное со Streamlit — ФАКТ, ранжировано по блокирующей силе

| # | Место | Что именно | Риск для FastAPI | Цена бездействия |
|---|---|---|---|---|
| 1 | `src/data_loader.py`: `load_models`, `load_prices`, `load_payment_terms`, `load_options_meta`, `load_managers` | `@st.cache_data(ttl=3600)` на каждом | Декоратор требует Streamlit-рантайм; вне его — деградация/шум. Транзитивно заражает почти все «чистые» модули | Блокирует любой импорт core/ из FastAPI. Первая задача порта (совпадает с P0-06/07) |
| 2 | `src/contracts/extractor.py` (строки 95, 156) | `st.secrets["OPENROUTER_API_KEY"]` — **без env-fallback** | AI-экстракция реквизитов падает вне Streamlit | Блокирует режим B договора на новом стеке (Фаза 2); не блокирует Фазу 1 |
| 3 | `src/contracts/state.py` — целиком | Адаптер `st.session_state["contract"]`: `ensure_contract_state`, `sync_widget_*`, `collect_for_template` и вся оркестрация | Это не «портировать», это переписать как DTO-границу запрос↔ответ | Пока нет явной схемы состояния договора — нет и API договора |
| 4 | `src/storage/kp_restore.py`: `apply_kp_snapshot_to_state`, `_purge_widget_keys` | Пишут в `st.session_state`; чистая часть `reconstruct_kp_state` отделена | Обёртка остаётся в фасаде, ядро переносится — раскол уже готов | Низкая — раскол очевиден |
| 5 | `src/contracts/spec_v2_filler.py` (~строка 262) | `st.warning(...)` в `_load_model_and_deps` + `import streamlit` на уровне модуля — **единственный st.* внутри DOCX-ядра** | Импорт streamlit в замороженном пайплайне; вне рантайма — шум/NoSessionContext в happy-path генерации спецификации | Одна строка правки (logging), но пока она есть — DOCX-ядро формально непереносимо |
| 6 | `src/storage/supabase_client.py`: `_get_client` | `st.secrets` **с fallback на os.environ** (try/except) | Работает под FastAPI как есть | Почти нулевая; косметика — убрать streamlit-ветку при переносе |
| 7 | `src/admin/price_update_view.py`, `price_overview_view.py`, `price_upload_view.py` | UI-вьюхи; `price_update_view` — stateful-визард на `session_state["price_update_stage"...]` | Остаются в Streamlit до Фазы 3b по плану | Нулевая для Фаз 0–2 |
| 8 | `src/app_pages/2_Договор.py:303` | `@st.cache_data` на вычислении — бизнес-логика в UI-слое | Логика не переедет сама | Малая, но учесть при порте договора |

**ФАКТ (скрытая связанность через форму данных, не через import).**
`build_kp_snapshot(state)` читает ~30 плоских ключей session_state;
`from_kp._reconstruct_state(kp_row)` собирает такой же state-подобный
dict из снапшота. Схема этих ключей — нигде не записанный контракт.
Для FastAPI это главный проектный долг: нужен явный Pydantic-DTO
(запланировано как P0-схемы, подтверждаю необходимость по коду).

**Итог по вопросу 1.** FastAPI поверх core/ блокируют ровно четыре вещи:
(а) `@st.cache_data` в data_loader; (б) `st.secrets` в extractor;
(в) отсутствие явной схемы state (session_state как неявный контракт);
(г) одна строка `st.warning` в spec_v2_filler. Всё остальное — уже
чистые функции.

---

## 2. Скрытая связанность

### 2.1 DOCX-пайплайн — ФАКТ

- `src/generators/kp_generator.py: generate_kp(state, prices) -> bytes` —
  в память, шаблон по **абсолютному** пути от `__file__`. Порт-готов,
  но `build_template_context` дёргает `load_*` из data_loader (п. 1.2#1).
- `src/contracts/filler.py: fill_template / fill_spec_with_items` —
  пишут **файлы на диск** (`output_path` + tmp рядом).
- `src/contracts/compose.py` — `_SUPPLY_TEMPLATES = Path("templates/contracts")`
  — **относительный, cwd-зависимый** путь; `compose_spec_with_attachments`
  пишет временные `_attach_N_*.docx` рядом с выходным файлом.
- `src/app_pages/2_Договор.py` — шаблоны и `OUTPUT_DIR = Path("output/contracts")`
  относительные; артефакты пишутся под детерминированными именами
  `Договор_{номер}_*.docx` в общую папку, потом `read_bytes()` →
  `session_state["contract"]["generated"]`. **Гонки/коллизии при
  конкурентных запросах** в многопользовательском бэкенде.
  Плюс traceback-дамп при падении `fill_spec_v2` пишется в `docs/`
  (сайд-эффект записи в рабочую копию репозитория).
- `src/contracts/clauses_renderer.py` — `_LIBRARY` module-global кэш
  `data/clauses.yaml` **без инвалидации**; путь `Path("data/clauses.yaml")`
  относительный. В долгоживущем FastAPI-процессе правка YAML не
  подхватится до рестарта.

Риск: пайплайн заморожен (И-3) и мигрирует as-is — но «as-is» здесь
включает cwd-зависимость, файловые артефакты с коллизиями имён и
глобальный кэш. Это не переписывание пайплайна, это его **обвязка**
(пути, temp-директория на запрос) — её придётся строить в Фазе 0/2.

### 2.2 Снапшоты Supabase — ФАКТ

- Схема `kps.data` (JSONB), собирает `snapshot_builder.build_kp_snapshot`:
  `metadata / model / foundation_execution / foundation_sections /
  model_code / installation_scope / equipment / construction / metrology /
  options / custom_items / spec_overrides / payment`.
  **Поля версии схемы нет** — совместимость держится на дефолтах при
  чтении (`kp_restore.reconstruct_kp_state`, `from_kp._reconstruct_state`).
  План И-2 требует `snapshot_version: 1` — ещё не внедрено.
- Таблица `contracts`: `save_contract` / `get_contracts_by_kp_id`
  определены в `supabase_client.py`, **вызовов нет нигде в src/**
  (проверено grep). **Договор не персистится вообще.**
- КП→Договор идёт **через снапшот из Supabase**, не через живой
  session_state (`2_Договор.py` → `get_kp_by_number` →
  `kp_load.build_kp_payload` → `from_kp.*`, оба модуля чистые).
  Всё, чего нет в схеме снапшота, до договора не доходит в принципе.

### 2.3 Состояние ТОЛЬКО в session_state (испаряется при выносе UI) — ФАКТ

Весь namespace `st.session_state["contract"]` живёт в памяти процесса и
никуда не сериализуется: `requisites` (+`requisites_manual`),
`specification.items` (правленные в data_editor SpecItem),
`manual` (номер/дата договора, адрес объекта), `flags` (winter_*),
`scope_overrides`, `attachments` (пути к файлам на диске!),
`payment_lines`, `ai_raw`, `generated` (байты DOCX),
`kp_snapshot` / `kp_payment_snapshot`. Закрыл вкладку — потерял договор.
При миграции это состояние надо либо оформить в модель запроса/ответа,
либо начать реально писать таблицу `contracts` (код уже есть, простаивает).

### 2.4 data/prices.json при двух процессах — ФАКТ + ГИПОТЕЗА

**ФАКТ.** `price_write_service.write_prices`: backup → merge →
атомарная запись (mkstemp + os.replace) → `load_prices.clear()`.
Инвалидация кэша — **только в своём процессе**; `load_prices` кэширован
с TTL 3600 с.
**ГИПОТЕЗА (арифметика, не прослежено вживую).** Как только рядом со
Streamlit-продом встанет FastAPI (Фаза 0–1 по плану: Streamlit-админка
жива до 3b), запись прайса из админки не инвалидирует кэш второго
процесса → до часа КП/договоры считаются по устаревшему прайсу.
Файл общий — кэш нет.

### 2.5 extractor.py — ФАКТ

`pdfplumber` + `python-docx` + openai SDK → OpenRouter
(`qwen/qwen3-235b-a22b`), промпты из `src/contracts/prompts/*.txt`
(пути от `__file__` — корректно). Streamlit-зависимость ровно одна:
`st.secrets` (п. 1.2#2). По STATUS уже решено переписать его на единый
LLM-слой (P0-21) — до тех пор достаточно env-fallback.

---

## 3. Инвариант «сумма КП = сумма договора»

### 3.1 Точки расчёта — ФАКТ

| Слой | Место | Формула | Тип денег |
|---|---|---|---|
| КП: позиции | `src/spec_builder.py: build_spec_items` | `total = price*qty`, **применяет** `state["spec_items_overrides"]` через `_apply_override` | int |
| КП: итог UI | `src/pricing.py: calc_totals` | `sum(int(total)) * model_qty`; НДС `round(x*0.22/1.22)` | int |
| КП: итог DOCX | `src/generators/kp_generator.py` | `subtotal = sum(item["total"]) * qty` из тех же override-aware spec_items | int |
| Договор: позиции | `src/contracts/from_kp.py: build_specification_items` | цены **напрямую из снапшота**, override НЕ применяется | float |
| Договор: итог (v1) | `from_kp.py: build_specification_from_kp_snapshot` | `grand_total = sum(rows.price)*qty` из `build_spec_rows_from_snapshot` — **override-слепой** | int |
| Договор: итог DOCX | `src/contracts/filler.py: fill_spec_with_items` | `sum(int(item.total))` — усечение, не round | int |
| Оплата: генерация | `src/contracts/payment_line.py: build_lines_from_snapshot` | не-split: последняя строка добирает остаток (Σ==total точно); split: `round(bucket*pct/100)` по бакетам **без общего добора** | int |
| Оплата: редактор | `src/ui/payment_lines_editor.py: _recompute_amounts` | `round(pct/100*база)`; добор остатка только внутри группы при Σ%==100; строки с `share_pct=None` **не пересчитываются** | int |

### 3.2 Где инвариант рвётся — по убыванию тяжести

**Р-1. ФАКТ. Ручная правка цен в КП теряется договором (главный разрыв).**
КП DOCX печатает итог по `build_spec_items` (override применён).
Снапшот сохраняет override отдельным ключом `spec_overrides`
(`snapshot_builder.py`), канонические цены — без него. Договорный путь
(`from_kp.build_specification_items`, `build_spec_rows_from_snapshot`)
читает только канонические цены; `_apply_override` существует **только**
в `spec_builder.py`. Итог: менеджер поправил цену позиции в КП →
КП и договор показывают разные суммы, никакой страж это не ловит.

**Р-2. ФАКТ. Расхождение внутри одного документа договора.**
В `build_specification_from_kp_snapshot`: `grand_total` считается из
override-слепых `rows`, а платёжные строки — из
`build_spec_items(state,...)`, где state (`_reconstruct_state`, ключ
`spec_items_overrides`) override **содержит**. При наличии override в КП
СПЕЦ_ИТОГО и график оплаты одной и той же спецификации считаются от
разных сумм.

**Р-3. ФАКТ. Оплата ≠ ИТОГО — только warning, недобор до N ₽ молчит.**
`payment_lines_editor._validate_rows`: error лишь при Σ% по базе > 100.
Недобор/перебор сумм — warning, причём недобор в пределах
`max(len(rows),1)` рублей проглатывается (строка ~234). Генерация не
блокируется — договор может уйти с графиком, не покрывающим ИТОГО.

**Р-4. ФАКТ. Split-режим: независимое округление бакетов + «застывшие»
плоские строки.** `payment_line.py`: бакеты округляются без общего
добора (±рубли на нечётных суммах); «защёлки» ставят `share_pct=None`,
а `_recompute_amounts` такие строки не пересчитывает — при изменении цен
строка застывает на старой сумме (признано комментарием в коде,
payment_line.py ~351–358).

**Р-5. ФАКТ. Страж A5 проверяет формат, не арифметику.**
`spec_v2_filler._assert_full_payment_lines` матчит `^\s*\d+\.\d`
(full-формат строк) и применяется только к fallback-пути;
override-путь `_payment_lines` «доверен по построению»
(spec_v2_filler.py ~324–327). Сверки Σ(строк оплаты) == СПЕЦ_ИТОГО и
ИТОГО договора == итог КП **не существует нигде**.

**Р-6. ФАКТ. Legacy-снапшоты пересчитываются по живому прайсу.**
`kp_restore.reconstruct_kp_state`: пустой `model.price` → берётся
`retail` из **текущего** prices.json. Прайс изменился — сумма
восстановленного КП/договора уехала от оригинала. Для новых снапшотов
(price заполнен) — заморожено, риска нет.

**Р-7. ФАКТ (маппинг) / ГИПОТЕЗА (эффект). Семантически неверный маппинг.**
`from_kp.build_spec_v2_data` кладёт `data_json["spec_overrides"]`
(прайсовые правки по ключам позиций) в `deal["scope_overrides"]`,
который `clauses_context` читает как области работ
(foundation/installation/...). Сегодня ключи не пересекаются →
вероятно, безвредно (ГИПОТЕЗА), но это мина: scope-логика клауз может
однажды прочитать мусор, а настоящие scope_overrides из КП сюда не
попадают никогда.

**Р-8. ГИПОТЕЗА. float→int усечение в договоре.** SpecItem держит деньги
во float, `filler` берёт `int()` (усечение). При целочисленных ценах
безвредно; сработает только если появятся дробные цены.

**Где ставить единый страж** (самое дешёвое место): `kp_load.build_kp_payload`
— единственная точка handoff КП→Договор, там одновременно доступны
снапшот, overrides и построенные позиции; сверка «итог договора ==
итог КП» и/или применение override делается в одном месте.

---

## 4. Ранжированный список задач (предложения для TECH_DEBT.md)

ID — предложения (продолжение B-нумерации; вносить в TECH_DEBT.md
отдельной docs-сессией, здесь только фиксация). Оценка: S ≤ 0.5 дня,
M ≈ 1–2 дня, L ≥ 3 дней.

| ID | Задача | Оценка | Фаза 1 |
|---|---|---|---|
| B9 | Договор игнорирует `spec_overrides` КП (Р-1, Р-2): применить override в `from_kp` ИЛИ страж-сверка итогов в `build_kp_payload`. Прод-баг денег, существует уже сейчас | M | НЕ блокирует (но это дефект прода — чинить до/независимо от миграции) |
| B10 | Развязка `data_loader` от `@st.cache_data` (→ lru_cache / модульная загрузка) — совпадает с P0-06/07 | S | **БЛОКИРУЕТ** |
| B11 | env-fallback для `OPENROUTER_API_KEY` в extractor (или дождаться P0-21) + удалить streamlit-ветку из supabase_client | S | НЕ блокирует Ф1 (блокирует Ф2, режим B) |
| B12 | Явная DTO-схема KP-state (Pydantic) вместо неявного контракта session_state; `snapshot_version: 1` (И-2) | L | **БЛОКИРУЕТ** |
| B13 | Инвалидация прайса между процессами (2.4): mtime-check в загрузчике или сигнал | S | **БЛОКИРУЕТ** (со дня, когда процессов два) |
| B14 | Обвязка DOCX: абсолютные пути шаблонов от `__file__` (compose, 2_Договор), temp-директория на запрос вместо общего `output/contracts`, убрать traceback-дамп в docs/ | M | НЕ блокирует Ф1 (блокирует Ф2) |
| B15 | `st.warning` из `spec_v2_filler._load_model_and_deps` → logging; снять `import streamlit` с DOCX-ядра | S | НЕ блокирует Ф1 (блокирует порт contracts в core/) |
| B16 | Страж арифметики оплаты: Σ(строк) == СПЕЦ_ИТОГО как error (не warning), включая override-путь и share_pct=None-строки (Р-3, Р-4, Р-5) | M | НЕ блокирует |
| B17 | Маппинг `spec_overrides`→`scope_overrides` в `build_spec_v2_data` (Р-7): разъединить понятия | S | НЕ блокирует |
| C-x | Персист договора: включить мёртвые `save_contract`/`get_contracts_by_kp_id` или спроектировать модель состояния договора для Ф2; решает и «закрыл вкладку — потерял договор» | L | НЕ блокирует Ф1 (проектное решение Ф2) |
| C-x | `clauses_renderer._LIBRARY` — глобальный кэш без инвалидации: mtime-check при переносе | S | НЕ блокирует |

Сводка по блокерам Фазы 1: **B10 + B12 + B13** (и только они).
Порядок порта core/, вытекающий из карты: data_loader → storage →
kp (spec_builder/pricing/kp_generator) → contracts → admin-логика.

## 5. Что НЕ трогать и почему

- **DOCX-пайплайн изнутри** (`filler.py`, `compose.py`, `spec_v2_filler.py`
  кроме одной строки st.warning, `spec_vmerge.py`, clauses DSL) —
  заморожен инвариантом И-3, мигрирует as-is под golden-gate. B14 —
  это обвязка (пути/temp), не внутренности.
- **`src/contracts/state.py` и `kp_restore.apply_kp_snapshot_to_state`** —
  не портировать и не «чистить»: это Streamlit-фасад, он умирает вместе
  со Streamlit (Ф3b). Портируются только их чистые части
  (`reconstruct_kp_state`, схема состояния — через B12).
- **`data/*.json`, `knowledge_base/`** — правит Антон вручную, правило
  CLAUDE.md.
- **`tests/contracts/synthetic/`** — заведомо сломаны, исключены из
  прогона.
- **B1 (два семейства id в матчинге оплаты)** — уже решено «не фиксить
  превентивно» (TECH_DEBT.md).
- **Схему снапшота `kps.data`** — заморожена И-2; B12 добавляет только
  `snapshot_version`, форму не меняет.
- **Streamlit-админку прайса** — по плану живёт до Фазы 3b; сервисный
  слой под ней уже чистый.

---

*Метод: 3 параллельных Explore-прохода (Streamlit-связанность;
DOCX/снапшоты/данные; денежный инвариант) + ручная верификация
ключевых фактов (grep `_apply_override`/`save_contract`/`st.secrets`,
чтение from_kp.py, payment_lines_editor.py, spec_v2_filler.py,
test_core_boundaries.py). STATUS.md/TECH_DEBT.md использовались только
как гипотезы; расхождений с кодом, меняющих их выводы, не найдено —
кроме того, что «Фаза 0 не завершена» фактически означает «не начата»
(core/ пуст).*
