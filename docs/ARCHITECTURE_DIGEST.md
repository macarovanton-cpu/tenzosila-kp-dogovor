# Архитектурный дайджест — Tenzosila KP & Dogovor

Назначение документа: дать внешнему архитектору (не видящему код) достаточно
структурной информации, чтобы спроектировать миграцию на новый стек. Описывает
ЧТО есть и ИНТЕРФЕЙСЫ, не реализацию.

Текущий стек: Python 3.11+, Streamlit (UI = серверный рендеринг Python,
`st.session_state` как единственный state), Supabase/Postgres (2 таблицы),
JSON/YAML-справочники в `data/`, генерация DOCX (python-docx + docxtpl +
docxcompose). Однопользовательский инструмент для отдела продаж — не
многопользовательское веб-приложение в классическом смысле (нет auth, ролей,
конкурентного доступа к одной записи).

---

## 0. Принятые архитектурные решения и обоснование

Контекст владельца, под который принимались решения:

- **Solo-разработчик**, по основной роли — **менеджер по продажам** (не
  инженер). Пишет код в режиме vibe-coding с AI-ассистентом (Claude Code).
  Базовый Python, **не фронтендер** — с нуля осваивал и Streamlit, и Supabase
  в рамках этого же проекта (т.е. способен освоить новый стек, но
  раскачка отнимает реальные недели).
- Тариф **Claude Pro** — квота на Opus (топовая модель) ограничена;
  большая часть кода пишется на модели среднего тира. Это ограничивает
  объём кода, который реалистично удержать в фокусе за одну сессию —
  архитектура должна оставаться **модульной и с маленькими файлами**
  (текущее правило проекта: файлы ≤200 строк).
- Прод-требования: интеграция с **Bitrix24** (фаза 3+, через REST API,
  вероятно iframe встраивание фронтенда внутрь Bitrix), будущие
  **межмодульные агенты** (пример: тендерный модуль читает архив ТЗ →
  прокидывает данные в конфигуратор КП → конфигуратор прокидывает в
  договор), и **минимум платных сервисов** (сейчас уже плата за Supabase
  и Streamlit Cloud/хостинг — цель сократить, не приумножить).

### Решение 1 — Backend: FastAPI, модульный монолит

**Что:** один Python-процесс (или несколько модулей внутри одного
деплой-юнита) на FastAPI, эндпоинты группируются по доменам (kp, contracts,
admin/prices, tender — по мере появления), без микросервисной нарезки.

**Почему под этот профиль:**
- Переиспользует 100% существующей бизнес-логики на Python (`spec_builder`,
  `pricing`, `validation`, `contracts/*`, `admin/*` — это чистые функции без
  Streamlit-зависимостей за исключением `st.cache_data`/`st.secrets` в
  паре мест, см. §7) — не нужно переписывать домен на другой язык.
- FastAPI даёт синхронный ход миграции: сначала API-обёртка над текущими
  функциями, потом постепенная замена Streamlit-страниц на React-страницы,
  говорящие с тем же backend. Не требует big-bang переписывания.
  Модульный монолит — не microservices — соответствует масштабу
  (одна команда, один owner, один деплой) и не создаёт эксплуатационной
  нагрузки (service mesh, межсервисные контракты), которую solo-разработчик
  не потянет.
- Открывает **HTTP API**, который одинаково обслуживает: будущий React-фронт,
  межмодульных агентов (тендер → КП — сейчас невозможно, т.к. вся логика
  живёт внутри процесса Streamlit и session_state), и, в фазе 3+, Bitrix24
  (через REST/iframe).

**Что архитектору стоит зачелленджить:** текущая бизнес-логика активно
использует Python-словари/TypedDict (`SpecItem`, снапшот КП) без строгой
валидации на границах (см. §7 — session_state как source of truth). Перенос
в FastAPI потребует явных Pydantic-схем на входе/выходе — это добавит
дисциплины, которой сейчас нет, и это осознанный побочный эффект решения,
а не бесплатный бонус.

### Решение 2 — БД: self-hosted PostgreSQL на VPS (не Supabase)

**Что:** тот же Postgres (Supabase — это Postgres + обвязка), но
самостоятельно поднятый на VPS, с тонкой FastAPI-обёрткой вместо
Supabase SDK/PostgREST.

**Почему:** данные (коммерческая информация о клиентах, цены, договоры)
остаются на своём сервере — не в managed-сервисе третьей стороны;
сокращение платных тарифов (Supabase имеет free tier с лимитами, но
рост данных/трафика упирается в платный план — тот же Postgres на уже
арендованном VPS не даёт второго счёта); FastAPI и так должен дублировать
часть обвязки Supabase (auth не нужен — single-tenant инструмент, но
RLS/политики Supabase всё равно не используются в текущем коде —
`supabase_client.py` работает через `service_role`-подобный доступ
напрямую по таблицам `kps`/`contracts`).

**Что архитектору стоит зачелленджить:** Supabase-специфичных фич в текущем
коде **не используется** (нет Realtime, нет Storage, нет Auth, нет RLS-
политик в бизнес-логике) — миграция клиента тривиальна (замена SDK-вызовов
на `asyncpg`/`SQLAlchemy` + пара таблиц с JSONB-колонками). Это снижает
риск решения почти до нуля, но также означает, что self-hosting не даёт
принципиально новых возможностей — выигрыш чисто в стоимости и контроле
над данными, а обратная сторона — самостоятельные бэкапы/апдейты/мониторинг,
которые раньше делал Supabase.

### Решение 3 — Frontend: React + Tailwind + shadcn/ui

**Что:** SPA на React, стилизация Tailwind, компонентная библиотека
shadcn/ui.

**Почему:** нужна дизайн-планка выше, чем позволяет Streamlit (который
жёстко диктует свою визуальную грамматику — колонки/expander/data_editor);
shadcn/ui даёт готовые доступные компоненты без необходимости писать
дизайн-систему с нуля (критично для не-фронтендера — снижает объём
незнакомой предметной области); React — стандарт, вокруг которого
максимум готовых примеров для AI-ассистента (важно при vibe-coding —
модели лучше знают React, чем нишевые фреймворки); **iframe-встраивание
в Bitrix24** — Bitrix принимает произвольные HTML/JS-приложения через
iframe/виджет, отдельный React-бандл встраивается туда естественно.

**Что архитектору стоит зачелленджить:** это самый большой разрыв в
компетенциях владельца (см. профиль — «НЕ фронтендер»). React + Tailwind +
shadcn — глубокий стек для человека, который писал UI только через
`st.number_input`/`st.selectbox`. Формы в текущем UI **тяжёлые и
взаимозависимые** (каскад модель→опции→цены→спецификация→оплата с кучей
условной видимости — см. `src/ui/*`), переписать это 1:1 на React —
не «перенос вёрстки», а полноценная фронтенд-разработка форм с
состоянием, которой раньше не было. Стоит явно спланировать, сколько
итераций с AI-ассистентом это потребует, и не предполагать, что перенос
будет быстрее backend-части.

### Решение 4 — Деплой: docker-compose на VPS

**Что:** `docker-compose` с сервисами (FastAPI backend, React static build
за nginx или отдаваемый тем же FastAPI, Postgres, возможно worker для
DOCX-генерации), один VPS.

**Почему:** минимум платных сервисов (один VPS вместо Streamlit
Cloud + Supabase + отдельный хостинг фронта); docker-compose —
самый низкий порог входа в контейнеризацию для solo-разработчика
(нет Kubernetes, нет оркестрации, нет multi-node); повторяемый деплой
через один файл, который легко попросить AI-ассистента сгенерировать
и поддерживать.

**Что архитектору стоит зачелленджить:** single-VPS — single point of
failure (нет отказоустойчивости), это осознанный компромисс под масштаб
(внутренний инструмент отдела продаж, не публичный SaaS) — уместность
стоит подтвердить, а не предполагать по умолчанию. DOCX-генерация
(python-docx/docxtpl/docxcompose, см. §4) — CPU/IO-bound синхронная
операция; при переносе в FastAPI её стоит явно вынести в background-worker
(или хотя бы `run_in_threadpool`), иначе она блокирует event loop —
это то, чего Streamlit-модель (по одному rerun на клиента) сейчас
маскирует.

---

## 1. Инвентарь модулей

### `src/` — верхний уровень (Streamlit-специфика + чистая логика)

| Модуль | Назначение | Точки входа |
|---|---|---|
| `app.py` | Роутер навигации Streamlit (`st.navigation` + 3 страницы). | `pg.run()` |
| `state.py` | Инициализация `st.session_state` конфигуратора КП (плоские ключи), колбэки каскада модель→опции. | `init_state()`, `initial_state()`, `on_cascade_change()`, `reset_options()` |
| `config.py` | Константы: пути к JSON, `VAT_RATE=0.22`, `MAX_COEFF=1.4`, `MIN_COEFF_B=0.6`, `SYNTHETIC_DEALER_FACTOR=0.92`, порядок/лейблы блоков опций. | — (константы) |
| `data_loader.py` | Загрузка справочников (`@st.cache_data(ttl=3600)`) + хелперы поиска по id. | `load_models/load_prices/load_payment_terms/load_options_meta/load_managers`, `get_model_by_id`, `get_price_by_model_id` |
| `filters.py` | Каскадная фильтрация моделей (линейка→нагрузка→длина), сборка `model_id`. | `model_id_from_cascade`, `calc_default_deck_mm` |
| `pricing.py` | Логика ценовых слайдеров: диапазоны по 3 классам цен, цветовая индикация. | `get_slider_params`, `get_model_slider_params`, `SliderParams` (dataclass) |
| `spec_builder.py` | Сборка позиций спецификации КП (модель + опции + custom) с учётом override. | `build_spec_items`, `resolve_payment_group`, `build_construction_description` |
| `validation.py` | Валидация состояния КП перед генерацией. | `validate(state, prices, models_json, payment_terms, managers) -> (errors, warnings)` |
| `term_days.py` | Расчёт сроков исполнения по ролям позиций (scales/foundation/install/verification/delivery), масштабирование под ручной срок. | `calculate_term_days_per_item`, `resolve_term_role`, `TermDaysTooSmallError` |

### `src/pages/` — 3 страницы Streamlit-приложения

- `1_Коммерческое_предложение.py` — конфигуратор КП (модель, опции, оплата,
  спецификация) → генерация `kp_template.docx`, сохранение в Supabase
  (`kps`).
- `2_Договор.py` — генерация договора из снапшота КП или AI-экстракции
  файлов; режимы A (из базы КП) / B (загрузка файлов вручную).
- `3_Админка.py` — админ-панель прайса (PDF-first импорт/валидация/запись
  `prices.json`).

### `src/ui/` — Streamlit-виджеты конфигуратора КП

| Модуль | Назначение |
|---|---|
| `header.py` | Шапка КП: номер, дата, менеджер, клиент. |
| `sidebar.py` | Итоговая сводка КП + кнопка генерации + сохранение в Supabase (`save_kp`) + список последних КП. |
| `model_section.py` | Каскад выбора модели + слайдер цены модели. |
| `equipment_section.py` | Выбор датчика/индикатора. |
| `construction_section.py` | Параметры конструкции платформы (балки, настил) — влияют только на текст спецификации, не на цену. |
| `options_section.py` | Рендер опций по блокам (`OPTION_BLOCKS_ORDER`), ценовые виджеты, описание типа фундамента. |
| `specification_section.py` | Таблица позиций КП (`st.data_editor`) с ручной правкой qty/price → `spec_items_overrides`. |
| `payment_section.py` | UI пресетов оплаты КП (5 пресетов из `payment_terms.json`). |
| `payment_lines_editor.py` | Редактор платёжных строк переменной длины на странице Договора (scope-default скелет, см. §0/v2.1). |
| `mobile.py` | Адаптация UI под мобильный форм-фактор. |

### `src/generators/` — рендеринг КП (DOCX, движок docxtpl)

| Модуль | Назначение |
|---|---|
| `kp_generator.py` | `build_template_context(state)` → `DocxTemplate.render()` → `apply_spec_vmerge()` → байты DOCX. Также `build_filename`. |
| `payment_renderer.py` | Текст блока «Условия поставки» по пресету оплаты (5 веток рендера). |
| `spec_vmerge.py` | Пост-обработка таблицы спецификации: раскодирование маркеров `⟦MERGE:...⟧` в `<w:vMerge>` для слияния ячеек срока по ролям. |
| `make_template.py` | Разовый скрипт сборки `kp_template.docx` из эталонного файла (не рантайм-код). |

### `src/storage/` — доступ к Supabase

| Модуль | Назначение |
|---|---|
| `snapshot_builder.py` | `build_kp_snapshot(state) -> dict` — плоский state → компактный JSONB для колонки `kps.data` (см. §2). |
| `supabase_client.py` | CRUD над таблицами `kps`/`contracts`: `save_kp`, `get_kp_by_number`, `list_recent_kps`, `search_kps_by_contractor`, `delete_kp`, `save_contract`, `get_contracts_by_kp_id`. |

### `src/contracts/` — модуль генерации договоров (самый крупный, 22 файла)

| Модуль | Назначение |
|---|---|
| `state.py` | `st.session_state["contract"]` — namespace для страницы Договор (requisites/specification/manual/uploads/attachments/flags/scope_overrides). |
| `from_kp.py` | Снапшот КП → позиции/контекст договора. Ядро моста КП→Договор (см. §3). |
| `spec_items.py` | `SpecItem` (TypedDict) — единица позиции спецификации; `_option_key_to_spec_id` — маппинг ключа опции КП → canonical id (источник бага `custom_N`, см. §7). |
| `extractor.py` | Извлечение текста из PDF/DOCX + вызов AI (OpenRouter, `qwen/qwen3-235b-a22b`) для распознавания реквизитов/спецификации. |
| `requisites_parser.py` | Regex-парсер реквизитов (fallback без AI): ИНН/КПП/ОГРН/БИК/р-с/к-с/адреса/директор — консервативный, при неоднозначности возвращает пусто. |
| `requisites_transforms.py` | Трансформации текста: `director_initials`, `position_genitive` (словарь), `infer_director_gender`, `acts_participle`, `named_form`, `full_name_from_short`. |
| `clauses_loader.py` | Загрузка/валидация `data/clauses.yaml` в `ClausesLibrary`. |
| `clauses_dsl.py` | Безопасный DSL-парсер `applies_when` через ограниченный `ast`-eval (whitelist переменных, только `and/or/not/==/!=/in`). |
| `clauses_context.py` | `build_clauses_context(deal) -> dict` — 8 переменных контекста (`foundation_scope`, `installation_scope`, `verification_scope`, `has_orion`, `orion_poles_scope`, `winter_concrete`, `winter_surcharge`, `base_type`). |
| `clauses_renderer.py` | `build_contract_clauses(deal)` — фильтрация по `applies_when` + сквозная нумерация + Jinja2-рендер текста пункта. |
| `filler.py` | Низкоуровневый python-docx filler: `merge_runs`, `replace_in_paragraph`, `fill_template`, `fill_spec_with_items`, `get_unfilled_placeholders`. |
| `spec_v2_filler.py` | Рендер `spec_v2.docx`: таблица позиций (через `filler.fill_spec_with_items`) + маркерная замена секций (`{{PAYMENT_SECTION}}`, `{{TERMS_SECTION}}`, `{{CLAUSE_SECTION_*}}`) + таблица комплекта. |
| `supply_filler.py` | Контекст для 3-шаблонного «Договора поставки» (docxtpl-флоу): `build_supply_context`, `_buyer_context` (склонение реквизитов покупателя), `build_supply_tth`. |
| `supplier.py` | `SUPPLIER: dict` — статичные реквизиты ООО «ТПК «Тензосила» (единый источник истины). |
| `payment_line.py` | `PaymentLine` (dataclass) + `PaymentTrigger` (Enum, 6 значений) + `format_payment_line` — модель строки оплаты договора поставки. |
| `terms_renderer.py` | `render_terms_section(deal, spec_items) -> list[str]` — динамические строки сроков для spec_v2. |
| `kit_renderer.py` | `build_kit_items(model, line_defaults, sensor, indicator, cable_m) -> list[dict]` — комплект поставки. |
| `tth_context.py` | `build_tth_data(model, sensor) -> dict[str,str]` — технические характеристики (ТТХ) из справочников. |
| `fundament_lookup.py` | Резолвинг файла строительного задания/контрольного листа из `data/fundament/` по типу фундамента и числу секций. |
| `compose.py` | Склейка DOCX через `docxcompose`: `compose_supply` (3 шаблона → 1 файл), `compose_spec_with_attachments` (спецификация + внешние приложения). |
| `utils.py` | Числа/даты прописью: `number_to_words`, `days_genitive`, `format_date_parts`, `MONTHS_RU`. |

### `src/admin/` — админ-панель прайса (16 файлов, чистые функции + Streamlit views)

| Модуль | Назначение |
|---|---|
| `price_models.py` | `PriceItem` (frozen dataclass) — canonical-запись модели/опции прайса. |
| `price_normalizer.py` | `normalize_prices(prices_json) -> list[PriceItem]` — JSON → плоский canonical формат. |
| `price_validator.py` | `validate_prices(items) -> list[ValidationIssue]` — структурная валидация по price_class. |
| `price_validation_split.py` | `split_validation(items, old_items=None) -> ValidationSplit` — блокеры vs предупреждения + сравнительные warnings. |
| `price_diagnostics.py` | `diagnose_prices(prices) -> PriceDiagnostics` — сводка здоровья прайса (истёк ли, нулевые цены и т.д.), CLI-обёртка. |
| `price_diff.py` | `diff_prices(old, new) -> PriceDiff` (added/removed/changed по значимым полям). |
| `price_business_summary.py` | `build_business_summary(old, new) -> BusinessSummary` — diff в бизнес-языке (цена вверх/вниз/новое/удалено/«под запрос»). |
| `price_pdf_dealer.py` / `price_pdf_retail.py` | Парсеры PDF-прайсов (дилерский/розничный) через `pdfplumber` → `list[PriceItem]`. |
| `price_pdf_merge.py` | `merge_price_items(dealer_items, retail_items) -> list[PriceItem]` — слияние двух PDF-источников. |
| `price_write_service.py` | `write_prices(merge_result) -> WriteResult` — backup → three-way merge (PDF-снимок + JSON-only carryover) → atomic write → сброс кэша; `rollback_prices`. |
| `price_upload_service.py` | `analyze_uploaded_price_json(bytes, current_prices) -> PriceUploadAnalysis` — валидация/diff загруженного JSON без Streamlit runtime. |
| `price_upload_view.py`, `price_update_view.py`, `price_overview_view.py` | Streamlit-рендер (view-слой) поверх сервисов выше. |

### Прочее

- `scripts/` — одноразовые CLI-утилиты (патчи DOCX-шаблонов, генерация тестовых КП, конвертер PDF-чертежей фундамента в DOCX `pdf_to_fundament_core.py`). **Не рантайм-код продукта.**
- `tests/` — 90 файлов pytest (юнит + `tests/contracts/`, `tests/admin/`, синтетические e2e-фикстуры).
- `data/fundament/` — библиотека внешних DOCX (строительные задания + контрольные листы), не код.
- `knowledge_base/` — read-only референсы по типу средства измерения ВЕСТА.

---

## 2. Модель данных

### JSON-справочники (`data/`)

**`models.json`** (2750 строк) — статичный каталог моделей ВЕСТА.
```
{
  "_meta": {version, generated_at, source[], scope{lines,lengths_m,max_loads_t}, notes[]},
  "equipment_defaults": {sensor: {...}, indicator: {...}},   // температурные диапазоны по умолчанию
  "line_defaults": {"С": {...}, "СЛ": {...}, ...},            // балки/датчик/индикатор по умолчанию на линейку
  "models": [
    {id, full_name, line, max_load_t, length_m, width_m, sections, sensors_count,
     mass_kg, beam_profile, deck_default_mm, min_load_t, verification_division_kg,
     n_intervals, axle_loads_t{single,double,triple,quad}, dual_range?, data_incomplete, notes}
    // ~90 моделей
  ]
}
```

**`prices.json`** (1310 строк) — коммерческие цены, редактируется через
админ-панель (`src/admin/`).
```
{
  "_meta": {version, source_retail, source_dealer, currency, vat_note,
            valid_from, valid_until?, notes[], updated_at},
  "models": { "vesta-фл-60-18": {retail, dealer_ru, dealer_discount_pct}, ... },
  "options": {
    "<option_key>": {
      price_class: "A_retail_and_dealer" | "B_retail_only" | "C_manual_range",
      price_retail, price_dealer_ru?, discount_pct?,
      range_min?, range_max?,               // только C_manual_range
      on_request?: bool, allow_customer_value?: bool,
      applies_to_lines?[], applies_to_lengths?[],
      label?, notes?, components?[], individual_calc? (ОРИОН)
    }, ...
  }
}
```
Цены **с НДС 22%** везде. `prices.backup.json` — авто-бэкап последней
записи (см. `price_write_service.write_prices`).

**`options.json`** (185 строк) — описательный текст (не цены): состав
пакетов ПАК ОРИОН (`pak_orion_packages[]` с `components[]`), описания
вариантов фундамента — используется только для caption-подсказок в UI КП.

**`payment_terms.json`** (143 строки) — 5 пресетов условий оплаты
(`v1_prepay_postpay`, `v2_prepay_preship_postpay`, `v3_postpay_only`,
`prepay_100`, `split_by_items`), каждый с `body_template` (Python
`.format()`-строка с плейсхолдерами `{prepay}`, `{days}` и т.д.) и
дефолтными процентами. `split_by_items.groups[]` — 4 группы
(scales/foundation/delivery/installation_and_verification) с
собственными `default_percents`.

**`managers.json`** (18 строк) — список менеджеров (`id`, имя,
`is_default`), `default_manager_id`.

**`equipment_specs.json`** (677 строк) — справочник `sensors[]` (датчики:
manufacturer, model, type digital/analog, температурный диапазон) и
`terminals[]` (весовые индикаторы) — источник данных для ТТХ и комплекта
поставки.

**`clauses.yaml`** (284 строки, `strictyaml`) — библиотека пунктов
договора.
```yaml
sections: [{id, title, section_number}, ...]   # 4 секции: obligations_supplier,
                                                # obligations_customer,
                                                # special_conditions, final
clauses:
  - id: <snake_case>
    section: <section_id>
    order: <int>                    # сортировка внутри секции
    applies_when: '<DSL-выражение>' # eval на 8 переменных контекста
    text: |
      <текст пункта, поддерживает Jinja {{ }}>
    related_to: [<tag>, ...]        # задел на будущее, не используется рендерером
```

### Supabase / PostgreSQL (2 таблицы)

**`kps`** — снапшот коммерческого предложения.
```
id (pk), kp_number (unique, on_conflict upsert), kp_date, client_name,
model_id, total_price, manager_id, data (JSONB — см. КП-снапшот ниже),
created_at, updated_at
```

**`contracts`** — сгенерированный договор.
```
id (pk), kp_id (fk → kps), contract_number, contract_date, object_address,
spec_number, requisites (JSONB), specification (JSONB)
```

Обе таблицы читаются/пишутся напрямую через `supabase-py` SDK
(`_get_client().table(name)...`), без RLS-логики в коде приложения —
доступ идёт по общему ключу (`SUPABASE_URL`/`SUPABASE_KEY` из
`st.secrets`/env). Списковые операции ограничены `limit`+`order` без
пагинации курсором.

### КП-снапшот (`kps.data`, строится `build_kp_snapshot(state)`)

```
{
  metadata: {kp_valid_days, warranty_months},
  model: {line, max, length, width, price},
  foundation_execution: str | null,      // "пандусный"|"приямок"|"rama_concrete"|... — для выбора файла строит. задания
  foundation_sections: int | null,        // 2|3|4, авто из длины (LENGTH_TO_SECTIONS), переопределяемо
  model_code: "ВЕСТА-{line}-{max}-{length}" | null,
  installation_scope: "full" | "shefmontazh" | null,
  equipment: {sensor_id, indicator_id, cable_m},
  construction: {beam, beam_count, center_beam, center_beam_count, deck_mm, underlining_mm},
  metrology: {is_dual_range},
  options: { "<key>": {price, qty, customer_side, retail, dealer_is_synthetic, dimensions?} },  // только enabled=true
  custom_items: [{name, price}, ...],     // без UI-id (id только в session_state)
  spec_overrides: { "<item_key>": {qty?, price?} },
  payment: {preset_id, days, custom_text, split_state, v1_prepay, v2_prepay, v2_preship, v3_days, v3_trigger_id}
}
```

Это единственный **контракт данных между модулем КП и модулем Договора** —
любая миграция должна сохранить его форму (или явно версионировать), т.к.
`src/contracts/from_kp.py` разбирает его по фиксированным путям.

### Контрактный session_state (`st.session_state["contract"]`, `contracts/state.py`)

```
{
  requisites: dict[str,str],       // ЗАКАЗЧИК_* плоские поля
  specification: dict + {items: list[SpecItem]},
  manual: {contract_number, contract_date, object_address, spec_number, valid_until},
  uploads: {kp, card},
  ai_raw: dict | null,             // сырой ответ AI-экстрактора
  generated: ... | null,
  kp_snapshot: dict,
  payment_lines: list[dict],       // строки редактора оплаты договора
  kp_payment_snapshot: dict,
  attachments: {build_task_path, build_task_source, control_sheet_path, include_control_sheet},
  flags: {winter_concrete, winter_surcharge, winter_surcharge_amount},
  scope_overrides: {foundation_scope, installation_scope, verification_scope, orion_poles_scope}
}
```

### `SpecItem` (позиция спецификации договора, `contracts/spec_items.py`)

```python
class SpecItem(TypedDict):
    id: str                 # "weights"|"delivery"|"installation"|"verification"
                             # |"foundation"|"fence"|"bytovka"|"orion"|"custom_<n>"
    name: str
    unit: str
    quantity: float
    price_per_unit: float
    total: float
    payment_group: int | None
    is_custom: bool
    source: Literal["preset", "custom"]
    metadata: dict           # {"scope": ..., "customer_side": ..., "bucket": ...}
```
`metadata.scope` — вход для DSL `applies_when` в clauses.yaml (см. §3).

---

## 3. Публичные интерфейсы

Функции, порождающие артефакты договора/КП (сигнатура → вход → выход →
побочные эффекты).

**`build_specification_from_kp_snapshot(kp_row, prices, models_json, payment_terms) -> dict[str, str]`**
(`contracts/from_kp.py:164`)
Вход: строка из Supabase `kps` + справочники. Выход: плоский dict
`СПЕЦ_*` (до 5 позиций спецификации + суммы + сроки + до 6 строк оплаты)
для `filler.fill_template` (legacy v1-флоу, `contract.docx` +
`spec_foundation_install.docx`). Побочных эффектов нет (чистая функция),
логирует warning при >5 строк (шаблон вмещает 5 слотов) или неизвестном
ключе опции.

**`build_spec_rows_from_snapshot(kp_row, prices=None) -> list[dict]`**
(`from_kp.py:254`) Список строк `{name, qty, price, price_display,
customer_side}` из снапшота — источник для supply-флоу (`_supply_spec_rows`).

**`build_specification_items(kp_row, prices=None) -> list[SpecItem]`**
(`from_kp.py:437`) Снапшот → список `SpecItem` с заполненным `metadata`
(scope фундамента/монтажа/ОРИОН) — вход для `build_clauses_context`.
Неизвестный ключ опции → `id="custom_<uuid8>"`, `is_custom=True` (см. §7,
баг `custom_N`).

**`build_spec_v2_data(kp_row, prices, models_json, payment_terms, equipment_specs) -> (data, items, deal)`**
(`from_kp.py:326`) Комплексная сборка контекста для `fill_spec_v2`:
`data` — плейсхолдеры + служебные ключи `_payment_lines`/`_terms_lines`/
`_kit_items`; `items` — `SpecItem[]`; `deal` — контекст для clauses
(`items`, `scope_overrides`, `flags`, `delivery_address`).

**`fill_spec_v2(template_path, data, items, deal, output_path) -> None`**
(`contracts/spec_v2_filler.py:241`) Главная точка рендера v2-спецификации:
таблица позиций (клонирование шаблонной строки таблицы) + маркерная замена
4 динамических секций (`{{PAYMENT_SECTION}}`, `{{TERMS_SECTION}}`, таблица
комплекта, `{{CLAUSE_SECTION_<section_id>}}` ×4) + автонумерация clauses
через `build_contract_clauses`. Побочный эффект: пишет DOCX-файл на диск
(`output_path`), затем читает его обратно для второго прохода правок.

**`build_supply_context(ctx, items, deal, payment_rows, manual, contract_date) -> dict`**
(`contracts/supply_filler.py:274`) Собирает **полный** docxtpl-контекст
для 3 шаблонов «Договора поставки» (реквизиты сторон в родительном падеже,
товар, суммы, сроки, ТТХ, `spec_rows`/`kit_rows` для jinja-циклов,
`_payment_lines` — служебный ключ для двупрохода). Единственный вызов;
чистая функция.

**`compose_supply(context, output_path) -> None`** (`contracts/compose.py:15`)
Рендерит 3 docxtpl-шаблона (`supply_contract.docx`, `supply_appendix_1.docx`,
`supply_appendix_2.docx`) → делает второй проход по `supply_contract` для
переменной длины блока оплаты (`_replace_marker_with_paragraphs`/
`_remove_marker`) → склеивает все 3 в один файл через `docxcompose`.
Побочный эффект: временные файлы (`tempfile.NamedTemporaryFile`),
удаляются в `finally` (см. §7 для родственного бага в
`compose_spec_with_attachments`).

**`build_clauses_context(deal) -> dict`** (`contracts/clauses_context.py:39`)
Вычисляет 8 переменных DSL-контекста
(`foundation_scope`, `base_type`, `installation_scope`, `verification_scope`,
`has_orion`, `orion_poles_scope`, `winter_concrete`, `winter_surcharge`) из
`deal.items` (по `metadata.scope`) с fallback на `deal.scope_overrides`,
затем на доменные дефолты (например: монтаж есть → фундамент по умолчанию
"строит заказчик"). Чистая функция, без побочных эффектов.

**`build_contract_clauses(deal) -> dict[str, list[RenderedClause]]`**
(`contracts/clauses_renderer.py:48`) Загружает `clauses.yaml` (кэш в
module-level `_LIBRARY`), фильтрует пункты по `applies_when.evaluate(context)`,
считает сквозную нумерацию с 4, вычисляет `obligations_range`
(диапазон номеров обязательств заказчика для перекрёстной ссылки),
рендерит текст через `jinja2.Environment(undefined=jinja2.Undefined)`.

**Petrovich (склонение ФИО, зависимость `petrovich>=2.0.1`)** — используется
в `contracts/requisites_transforms.py::decline_fio` (не показан полный
код в исследовании, но вызывается из `supply_filler._buyer_context` для
получения ФИО директора в родительном падеже — «Путь A: авто-склонение»).
Должность склоняется отдельно через ручной словарь `position_genitive`
(petrovich не умеет должности) — неизвестная должность → пустая строка
(fallback на именительный, не падает). Пол директора — эвристика по
суффиксу отчества (`infer_director_gender`, 4 женских суффикса) с
возможностью ручного override (`ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ`).

**AI-экстракция реквизитов** — `contracts/extractor.py`:
`extract_card_data(card_path) -> dict` (карточка контрагента → AI, режим
A) и `extract_kp_data_legacy(kp_path, card_path) -> dict` (режим B).
Провайдер: **OpenRouter**, модель `qwen/qwen3-235b-a22b`, системные
промпты в `contracts/prompts/*.txt`. Побочный эффект: сетевой вызов,
API-ключ из `st.secrets["OPENROUTER_API_KEY"]`.

**Fallback-парсер без AI** — `requisites_parser.parse_requisites(text) -> dict[str,str]`
консервативный regex по ИНН/КПП/ОГРН/БИК/р-с/к-с (с валидацией контрольной
суммы ИНН и якорным разрешением неоднозначностей БИК↔КПП, р/с↔к/с) —
при неоднозначности поле не заполняется (не угадывает).

---

## 4. DOCX-пайплайн

### Библиотеки

- **python-docx** (`>=1.1.0`) — низкоуровневая работа с OOXML: прямая
  манипуляция параграфами/ранами/таблицами через `lxml`-элементы
  (`_p`, `_tr`, `qn()`-namespace хелперы). Используется как для чтения,
  так и для хирургической правки шаблонов (`scripts/patch_*.py`) и для
  runtime-рендера двух флоу ниже.
- **docxtpl** (`>=0.18.0`) — Jinja2-шаблонизация поверх DOCX
  (`{{ var }}`, `{% if %}`, `{%tr for row in rows %}` для строк таблиц).
  Используется для КП (`kp_template.docx`) и для «Договора поставки»
  (3 шаблона).
- **docxcompose** (`>=1.4.0`) — склейка нескольких DOCX-документов в один
  с сохранением стилей/разрывов страниц (`python-docx` сам по себе этого
  не умеет). Используется для (а) договора поставки — 3 шаблона → 1 файл,
  (б) спецификации v1 + внешние приложения (строительные задания).
- **lxml** (`>=5.0.0`) — транзитивная зависимость `python-docx`, местами
  используется напрямую (`fromstring`/`tostring` в патч-скриптах через
  `xml.etree`, не `lxml` напрямую — уточнение: патч-скрипты используют
  стандартный `xml.etree.ElementTree`, не `lxml`).
- **pdfplumber** (`>=0.10.0`) — извлечение текста/таблиц из PDF (парсеры
  прайса, экстракция КП/карточки контрагента для AI).
- **pymupdf** (`fitz`, `>=1.27`) — рендер PDF-страниц в PNG (конвертер
  чертежей фундамента `pdf_to_fundament_core.py`), не используется в
  основном рантайм-пайплайне договоров.

### Файлы шаблонов (`templates/`)

| Файл | Движок | Назначение |
|---|---|---|
| `kp_template.docx` | docxtpl | Коммерческое предложение. Динамическая таблица позиций `{%tr for item in spec_items %}` + пост-обработка `apply_spec_vmerge` (кастомные текстовые маркеры → `<w:vMerge>`). |
| `contracts/contract.docx` | python-docx (`filler.fill_template`, простая `{{KEY}}`-замена без Jinja) | Legacy v1 договор подряда — константный текст, реквизиты сторон. |
| `contracts/spec_foundation_install.docx` | python-docx (`filler.fill_spec_with_items`) | Legacy v1 спецификация: фиксированный набор до 5 позиций + строки платежа/сроков как отдельные плейсхолдеры (`СПЕЦ_ОПЛАТА_П1..6`). |
| `contracts/spec_v2.docx` | Гибрид: python-docx для таблицы позиций (клонирование строки) + python-docx с маркерными параграфами для динамических секций + `jinja2.Environment` **только для текста clause** (не для всего документа) | v2-спецификация — сквозная нумерация обязательств, зависящих от scope (см. §0, документ `architecture/contracts_v2_1.md`). |
| `contracts/supply_contract.docx`, `supply_appendix_1.docx`, `supply_appendix_2.docx` | docxtpl (полный Jinja) + второй python-docx проход для блока оплаты переменной длины | «Договор поставки» (10-раздельный, без монтажа/фундамента) — отдельный документный класс, три файла склеиваются в один. |
| `templates/README.md` | — | Документирует плейсхолдеры и regen-процедуру для `kp_template.docx`. |

### Трёхслойная модель пайплайна

Ни один шаблон не рендерится «в один проход одним движком» — везде
явно или неявно три слоя:

1. **Слой данных** — плоские context-словари (`СПЕЦ_*`, `ПОКУПАТЕЛЬ_*`,
   `ПОСТАВЩИК_*`, `ТТХ_*`) + служебные списки (`spec_items`, `spec_rows`,
   `kit_rows`, `_payment_lines`, `_terms_lines`). Строится доменными
   billder-функциями (§3), не знает о DOCX.
2. **Слой заполнения (filler)** — переводит данные слоя 1 в конкретные
   правки OOXML: либо через Jinja-рендер docxtpl (`.render(context)`),
   либо через прямую замену текста в ранах (`filler.replace_in_paragraph`,
   regex `{{KEY}}` без Jinja-логики), либо через клонирование/удаление
   XML-элементов (строки таблиц, целые параграфы-маркеры).
3. **Слой композиции** — постобработка готового DOCX: слияние ячеек
   (`spec_vmerge`), склейка нескольких файлов в один (`docxcompose` в
   `compose.py`), для текстовых полей внутри textbox (недоступны через
   `python-docx` API) — точечная XML-правка через `zipfile`
   (`filler._replace_textbox_placeholders`).

Смешение движков (docxtpl vs чистый python-docx) — **исторический
артефакт эволюции** (KP и Договор поставки писались как docxtpl с самого
начала; Договор подряда v1/v2 перешёл на ручной python-docx, когда
понадобилась секционная логика, которую Jinja внутри Word плохо
поддерживает — переменное число динамических секций/параграфов). Для
нового стека это сигнал: если рендеринг документов переносится на другой
язык/сервис, стоит **унифицировать на одном движке** (либо полностью
Jinja-based шаблоны с richer control flow, либо перейти на HTML→DOCX/PDF
рендеринг через сторонний сервис) — 3 разных техники в одном пайплайне
не масштабируются на новые типы документов.

---

## 5. Зависимости (`requirements.txt`)

| Пакет | Версия | Роль |
|---|---|---|
| `streamlit` | ≥1.45.0 | UI-фреймворк, весь фронт текущей версии. |
| `python-docx` | ≥1.1.0 | Низкоуровневая работа с DOCX/OOXML. |
| `docxtpl` | ≥0.18.0 | Jinja2-шаблонизация DOCX. |
| `docxcompose` | ≥1.4.0 | Склейка нескольких DOCX в один. |
| `python-slugify` | ≥8.0.0 | Транслитерация/слаги (имена файлов). |
| `lxml` | ≥5.0.0 | XML-парсинг, транзитивно для python-docx. |
| `pandas` | ≥2.0.0 | `DataFrame` для `st.data_editor` (таблицы позиций в UI). |
| `openai` | ≥1.0 | SDK-клиент, используется против **OpenRouter** endpoint (не OpenAI напрямую) для AI-экстракции реквизитов. |
| `supabase` | ≥2.0 | Клиент БД/снапшотов КП и договоров. |
| `pdfplumber` | ≥0.10.0 | Извлечение текста/таблиц из PDF (прайсы, карточки контрагентов, КП). |
| `pymupdf` | ≥1.27 | Рендер PDF-страниц (конвертер чертежей фундамента). |
| `strictyaml` | ≥1.6.0 | Строгая загрузка `clauses.yaml` (типизированный YAML, меньше сюрпризов чем PyYAML). |
| `petrovich` | ≥2.0.1 | Библиотека склонения русских ФИО по падежам (используется для родительного падежа в преамбуле договора). |

Тесты: `pytest` (упомянут в командах CLAUDE.md, не в requirements.txt —
вероятно dev-зависимость вне списка или устанавливается отдельно).

---

## 6. Поток данных: КП → снапшот → договор

```
┌─────────────────────────────────────────────────────────────┐
│ Streamlit: страница «Коммерческое предложение»               │
│  st.session_state (плоские ключи: model_id, options{}, ...)  │
└───────────────┬───────────────────────────────────────────────┘
                │ build_kp_snapshot(state)
                ▼
        КП-снапшот (dict, см. §2) ──────► kp_generator.build_template_context()
                │                                  │
                │ save_kp(...)                      ▼
                ▼                          DocxTemplate(kp_template.docx).render()
        Supabase.kps.data (JSONB)                    │
                │                                    ▼
                │                          apply_spec_vmerge() → КП.docx (выдаётся менеджеру)
                │
                │ get_kp_by_number() / list_recent_kps()
                ▼
┌─────────────────────────────────────────────────────────────┐
│ Streamlit: страница «Договор» — режим A (из базы)             │
│  kp_row = Supabase.kps row                                    │
└───────────────┬───────────────────────────────────────────────┘
                │
                ├─► build_specification_from_kp_snapshot(kp_row, ...) ──► legacy v1 (contract.docx + spec_foundation_install.docx)
                │
                └─► build_spec_v2_data(kp_row, ...) = (data, items, deal)
                             │
                             ├─► build_clauses_context(deal) ──► build_contract_clauses(deal)
                             │                                           │
                             └─► fill_spec_v2(spec_v2.docx, data, items, deal, out) ◄──┘
                                          (v2-флоу, актуальный)

Параллельно — режим B / реквизиты покупателя:
  Загрузка файла контрагента ──► extractor.extract_card_data() [AI, OpenRouter]
                              ──► requisites_parser.parse_requisites() [fallback, regex]
                              ──► merge_requisites() → st.session_state["contract"]["requisites"]

«Договор поставки» (отдельный документный класс, без монтажа/фундамента):
  kp_snapshot + requisites + manual-поля (номер, дата, адрес, срок действия)
        ──► build_supply_context(...) ──► compose_supply(...) [docxtpl ×3 + docxcompose]
        ──► supply_contract + appendix_1 + appendix_2, склеенные в 1 файл

Сохранение договора:
  save_contract(kp_id, contract_number, ..., requisites, specification) ──► Supabase.contracts
```

Ключевое свойство потока: **снапшот КП — единственная точка сцепления**
между модулем КП и модулем Договора. Договор не читает `st.session_state`
конфигуратора КП напрямую — только сериализованный JSONB. Реквизиты
покупателя и ручные поля договора (номер, даты, адрес, срок действия,
флаги зимнего периода) существуют **только** в `st.session_state["contract"]`
на клиенте и в колонках `contracts.requisites`/`contracts.specification`
после сохранения — какого-либо шага «снапшот договора обратно влияет на
КП» нет (однонаправленный поток КП→Договор).

---

## 7. Ограничения и подводные камни

### Открытые баги/техдолг (см. `docs/STATUS.md` за актуальным статусом)

- **`custom_N` — корневой баг маппинга позиций.** Монтаж/фундамент,
  сохранённые конфигуратором КП как незнакомый ключ опции, попадают в
  спецификацию договора с `id="custom_<uuid8>"` и **без** `metadata.scope`.
  `build_clauses_context` ищет строго `items_by_id["installation"]` —
  не находит → `installation_scope="none"` → обязательства сторон по
  монтажу/фундаменту в договоре могут не появиться, хотя монтаж физически
  оплачивается. Диагностирован, не пофикшен, оценка воздействия на
  боевые (не синтетические) spec-договоры — не завершена. Затрагивает
  ~90% договоров (у монтажа своя специфика).
- **EOL `data/prices.json`.** `write_prices` пишет LF, репозиторий в CRLF
  → после каждой записи прайса через UI файл выглядит "phantom modified"
  в git. Требует `.gitattributes` (`text eol=lf`) — не сделано.
- **`ПОКУПАТЕЛЬ_ТЕЛЕФОН` не всегда попадает в реквизиты** покупателя в
  договоре поставки (парсер консервативен по телефону — см. STATUS на
  момент чтения; может быть уже закрыто).
- **Автовыбор типа договора не работает** (зависит от фикса `custom_N`) —
  тип договора менеджер выставляет вручную.
- **Temp-файл не удаляется при падении `fill_template`** внутри
  `compose_spec_with_attachments` (`contracts/compose.py`): путь `filled`
  добавляется в `tmp_files` (список на очистку в `finally`) **после**
  вызова `fill_template(...)`, который уже мог создать файл на диске и
  затем поднять исключение — в этом случае файл остаётся, минуя очистку.
- **`vMerge` для ячеек таблицы спецификации** в других флоу (кроме
  `trHeight`, который закрыт) — не унифицирован между KP/legacy/v2/supply
  флоу; каждый решает слияние ячеек по-своему (`spec_vmerge.py` для КП,
  ручной XML в `spec_v2_filler.py`/`supply_filler.py` для остального).

### Архитектурные особенности, которые повлияют на миграцию

- **`st.session_state` как source of truth.** И конфигуратор КП
  (плоские ключи), и модуль Договора (`st.session_state["contract"]`,
  вложенный namespace) держат весь рабочий стейт в session_state
  Streamlit — эквивалента отдельного domain-объекта/сервиса нет. Перенос
  на React+FastAPI потребует **спроектировать API-контракт с нуля**
  (что сейчас лежит в session_state, должно стать либо client-side state
  (React), либо явным запросом к backend) — 1:1 переноса не будет.
- **Функции с побочным доступом к Streamlit runtime** внутри «чистой»
  бизнес-логики: `data_loader.py` — `@st.cache_data`; `extractor.py` —
  `st.secrets["OPENROUTER_API_KEY"]`; `supabase_client.py` —
  `st.secrets["SUPABASE_URL"/"SUPABASE_KEY"]` (с fallback на
  `os.environ`, так что миграция частично уже совместима). При переносе
  в FastAPI эти точки нужно явно развязать (кэш → Redis/in-memory TTL,
  секреты → env/vault).
- **DOCX-рендеринг — синхронный, файловый I/O, CPU-bound.** Использует
  временные файлы (`tempfile.NamedTemporaryFile`), пишет/читает DOCX с
  диска несколько раз за один рендер (двупроходные флоу). При переносе в
  API — кандидат на background job/worker, не на прямой request/response
  без таймаута.
- **Два независимых движка шаблонизации** (docxtpl / ручной python-docx) —
  см. §4, сигнал для унификации при редизайне пайплайна документов, не
  для копирования как есть.
- **`clauses.yaml` DSL — самодельный, но нарочно ограниченный.**
  Whitelist переменных + whitelist AST-узлов (`ast.parse` + ручная
  валидация) — не `eval()` в открытом виде, безопасно для встраивания в
  YAML, редактируемый без деплоя кода. При миграции стоит сохранить как
  есть (не изобретать новый DSL) — уже проверен в бою.
- **Нет пагинации/курсоров** в списковых Supabase-запросах
  (`list_recent_kps`, `search_kps_by_contractor`) — простой `limit()`.
  Не проблема на текущем объёме (внутренний инструмент), но не
  масштабируется бездумно при переносе на PostgreSQL напрямую — стоит
  сразу заложить cursor-based pagination в новом API, если ожидается
  рост объёма КП.
- **Нет многопользовательской модели/auth.** Ни ролей, ни разграничения
  доступа, ни аудит-лога изменений — однопользовательский (или
  «доверенная команда из нескольких менеджеров без RBAC») инструмент.
  Bitrix24-интеграция (фаза 3+) неизбежно поднимет вопрос идентификации
  пользователя — сейчас в модели данных этого понятия просто нет (ни в
  `kps`, ни в `contracts` нет `user_id`/`created_by`, есть только
  `manager_id` как атрибут данных, не как identity).
- **AI-экстракция реквизитов — единая точка отказа** в проде (упомянуто
  в архитектурном документе `contracts_v2_1.md`): режим B (ручной ввод)
  существует специально как fallback, когда AI недоступен — при
  редизайне сохранить этот принцип (не завязывать генерацию договора
  жёстко на доступность внешнего AI-провайдера).
- **`custom_items` в UI имеют стабильный id, в snapshot — нет** (снапшот
  отдаёт только `name`/`price`) — намеренное решение (см.
  `snapshot_builder._build_custom_items`), но означает, что identity
  произвольных позиций теряется на границе КП→Договор; при построении
  нового API стоит решить, нужен ли sквозной id для трассировки
  custom-позиций через весь жизненный цикл сделки.
