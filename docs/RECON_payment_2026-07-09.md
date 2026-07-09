# Разведка: блок оплаты (2026-07-09)

Read-only карта. Ничего не менялось.

## 1. Дефолт оплаты 30/40/30 — где рождается

Общесистемный дефолт — НЕ 30/40/30. Дефолтный пресет всего модуля —
`split_by_items` (`data/payment_terms.json:19`, `"default_preset_id":
"split_by_items"`) — это 50/50 по весам и фундаменту, 0/100 по доставке
и монтажу (строки 79-127 того же файла).

30/40/30 — дефолт другого, опционального пресета `v2_prepay_preship_postpay`
(`data/payment_terms.json:33-38`, `"default_percents": {"prepay": 30,
"preship": 40}`, postpay = 100-30-40=30 считается на рендере, не хранится).

Проблема дублирования источника истины: числа 30/40 (и 50/50, 0/100 для
split) захардкожены ещё в 4 местах кода как fallback (используются только
если ключ отсутствует в state/snapshot, но живут отдельно от JSON):
- `src/generators/payment_renderer.py:105-106,93` (`render_v2`, `render_v1`)
- `src/ui/payment_section.py:97,104`
- `src/contracts/payment_line.py:108,116-118` (`_non_split_phases`)
- `src/contracts/payment_line.py:187-192` (`_DEFAULT_SPLIT_PERCENTS`, для
  split-пресета: scales/foundation 50/50, delivery/installation 0/100;
  комментарий в коде честно называет это «страховкой для битых снапшотов»)

## 2. render_payment_block — вход/выход/вызовы, почему бандл не делится

Определение: `src/generators/payment_renderer.py:136-138`
```python
def render_payment_block(
    state: dict[str, Any], spec_items: list[dict], payment_terms_json: dict
) -> str:
```
Вход — `state` (пресет + проценты + сплиты), `spec_items` (список позиций
спецификации), `payment_terms_json` (загруженный `data/payment_terms.json`).
Выход — plain-text блок «Условия поставки» (для `split_by_items` —
через `render_split_by_items`, строки 33-88 того же файла).

Call sites:
- `src/generators/kp_generator.py:184,230` — сборка КП, результат идёт в
  docxtpl-контекст как `payment_terms_block`.
- `src/contracts/from_kp.py:331` — `build_specification_from_kp_snapshot`
  (легаси 5-слотовый шаблон).
- `src/contracts/from_kp.py:480` — `build_spec_v2_data`, вызывается как
  `render_payment_block(state, raw_spec_items, payment_terms)`, где
  `raw_spec_items = build_spec_items(state, prices, models_json)` (строка 479).
- В `2_Договор.py` прямого вызова нет — там (строка ~507-509) зовётся
  `build_specification_from_kp_snapshot(...)`, которая внутри дёргает
  `render_payment_block`. Отдельно, в районе строк 1029-1071, работает
  ВТОРОЙ, независимый путь — ручная таблица `get_payment_lines()` →
  `_row_to_line`/`format_payment_line`, построенная через
  `build_lines_from_snapshot` (`src/contracts/payment_line.py`), а не через
  `render_payment_block`. Это два параллельных механизма генерации текста
  оплаты для разных документов (КП vs Договор/Спецификация — см. п.6).

**Почему сумма бандла ОРИОН (весы+фундамент+монтаж как одна позиция) НЕ
делится по позициям, а платится общей суммой:**

Каждая позиция спецификации несёт ровно один `payment_group`
(`src/contracts/spec_items.py:8-18`, поле `payment_group`). Присваивается
функцией `resolve_payment_group()` (`src/spec_builder.py:226-245`):
```python
def resolve_payment_group(item_key: str) -> str:
    if item_key.startswith("foundation_"): return "foundation"
    ...
    if item_key in ("install_default", "verification_default", "orion_install"):
        return "installation_and_verification"
    if item_key == "orion_cable_poles":
        return "foundation"
    return "scales"          # <-- фоллбэк для orion_lite/orion_standard/orion_auto целиком
```
Для ключей самого бандла (`orion_lite`, `orion_standard`, `orion_auto`, ...)
ни одно явное условие не срабатывает — они падают в фоллбэк `"scales"`.
Вся цена бандла (весы + вшитый шеф-монтаж) целиком уходит в бакет «весы» и
делится по процентам весов, а не по процентам монтажа.

Суммирование по бакету не разбивает позицию внутри себя —
`_bucket_total()` (`src/contracts/payment_line.py:222-232`) суммирует
`total` целых позиций, сгруппированных по `payment_group`.

Есть механизм разбиения бандла на компоненты — `_expand_orion_options()`
(`src/contracts/from_kp.py:113-171`, докстринг: «FIX_SPEC §A1: расщепить
бандл ОРИОН на отдельные позиции спецификации... пропорционально
components из прайса»), НО он вызывается только при сборке отображаемых
строк спецификации (`from_kp.py:388,558` — то, что видит клиент как список
товаров), а НЕ при `build_spec_items()` (`from_kp.py:479`), который питает
и `render_payment_block`, и `build_lines_from_snapshot`. Поэтому таблица
спецификации может показывать ОРИОН расщеплённым на компоненты, а расчёт
графика оплаты видит тот же бандл одной позицией с `payment_group="scales"`.

## 3. Редактор оплаты (payment_lines_editor)

Функция — `render_payment_lines_editor()`, `src/ui/payment_lines_editor.py:241-311`.
Вызывается из `src/pages/2_Договор.py:871` (`render_payment_lines_editor()`,
между спецификацией и вложением фундамента).

**Откуда берёт строки:** единственный источник для `st.data_editor` —
`st.session_state["contract"]["payment_lines"]`, геттер/сеттер
`get_payment_lines`/`set_payment_lines` в `src/contracts/state.py:118-126`.
Дефолт при инициализации — пустой список (`state.py:25`).

Отдельно хранится «снапшот дефолта» — `contract["kp_payment_snapshot"]`
(заполняется при загрузке КП, `2_Договор.py:516-518`) — исходный пресет
оплаты из мастера КП (v1/v2/v3/prepay_100/split_by_items).

**Overrides:** это не два параллельных состояния с флагом, а ОДНА ячейка
(`payment_lines`), которая перезаписывается либо кнопкой, либо ручным
редактированием:
- Кнопка «Заполнить по умолчанию» (`payment_lines_editor.py:249-263`) читает
  `kp_payment_snapshot`, строит строки через `build_lines_from_snapshot(...)`
  и ПЕРЕЗАПИСЫВАЕТ `payment_lines` — предыдущие ручные правки безвозвратно
  теряются (без подтверждения).
- Любое изменение в `st.data_editor` (`key="payment_editor"`, строки 266-291)
  немедленно синхронизируется обратно в `payment_lines` (строка 287).
"Дефолт" живёт только в `kp_payment_snapshot`, "текущее" — единственный
`payment_lines`.

**Группировка по тексту:** метки событий — хардкод-словарь `_TRIGGER_LABELS`
(`payment_lines_editor.py:28-36`), ключи которого — `PaymentTrigger` enum
(`src/contracts/payment_line.py:10-16`: SPEC_SIGNED, FOUNDATION_ACT,
SHIPMENT_READY, BRIGADE_READY, WORK_ACT, DELIVERED). Тексты триггеров в
договоре — отдельный хардкод-словарь `TRIGGER_TEXTS` (`payment_line.py:19-26`).
Привязка "Аванс"/"При отгрузке" к процентам — комбинация колонок `Тип`
(предоплата/доплата/оплата, хардкод `_KINDS`), `Основа` (хардкод `_PREPS`),
`Объект` (свободный текст) и `Событие` (из `_TRIGGER_LABELS`) — всё
захардкожено в Python, никакого внешнего конфига для меток нет.

**Валидация суммы 100%:** раздельно error/warning
(`_validate_rows`, `payment_lines_editor.py:200-238`):
- Блокирующая ошибка — только если Σ% внутри одной "смысловой группы"
  (ключ = база+объект, `_pct_group_key`) превышает 100% (допуск 0.01).
- Некритичные warning — если Σ сумм не совпадает с ИТОГО спецификации
  (избыток или недобор), или если база строки больше ИТОГО.
- Автодобор остатка: если Σ% группы == 100% (в допуске), последняя строка
  группы получает остаток базы, чтобы суммы сходились точно
  (`_recompute_amounts`, строки 168-193).
- Если 100% не набрано ровно — хард-блока нет, только warning.

**Ключи session_state, читает/пишет:** всё внутри `contract` namespace —
`contract["payment_lines"]` (rw), `contract["kp_payment_snapshot"]` (r),
`contract["specification"]["items"]` (r, через `get_spec_items()`), плюс
Streamlit-виджет-ключ `payment_editor` (удаляется при регенерации из
дефолта). Финальная генерация договора (`2_Договор.py:1031,1066-1071`)
читает те же `get_payment_lines()` и тот же `_row_to_line`/
`format_payment_line`, что и сам редактор — то есть финальный текст
строится из того же состояния, что видно в UI, без отдельного пересчёта.

## 4. Что доступно на входе для будущей сеялки (бакеты/суммы/флаги)

**SpecItem** (`src/contracts/spec_items.py:8-18`):
```python
class SpecItem(TypedDict):
    id: str
    name: str
    unit: str
    quantity: float
    price_per_unit: float
    total: float
    payment_group: int | None   # аннотация устарела — фактически строка
    is_custom: bool
    source: Literal["preset", "custom"]
    metadata: dict
```
`payment_group` фактически строка: `"scales" | "foundation" | "delivery" |
"installation_and_verification" | None`, проставляется `resolve_payment_group()`
(`src/spec_builder.py:226-245`) при сборке позиций, для custom-позиций —
через `_payment_group_by_name()` (`src/contracts/from_kp.py:79-88`).
Дополнительно `metadata["scope"]` хранит более узкий подтип позиции
(например `"fundament"`/`"rama"` для монтажа).

Список позиций в состоянии договора живёт в
`contract["specification"]["items"]`, доступен через
`get_spec_items()`/`set_spec_items()` (`src/contracts/state.py:106-115`) —
НЕ отдельный top-level ключ `spec_items`.

**Сумма по каждой позиции — есть:** `total = quantity * price_per_unit`
(`recalculate_totals`, `spec_items.py:43-47`).

**Агрегация сумм по бакетам — уже реализована** в нескольких местах
параллельно (не единая функция):
- `src/contracts/payment_line.py:222-232` (`_bucket_total`) — используется
  `build_lines_from_snapshot` для 4 бакетов: scales/foundation/delivery/
  installation_and_verification (строки 263-266).
- `src/generators/payment_renderer.py:13-23` (`get_active_payment_groups`) —
  булевы флаги "бакет активен" + `has_orion`, для КП-текста.
- `2_Договор.py:250-262` (`_items_to_rows`) — конвертация `payment_group` в
  русские UI-метки бакетов «Оборудование/Фундамент/Монтаж и поверка».

**contract["flags"]** (`src/contracts/state.py:33-37`) — НЕ флаги наличия
видов работ. Единственные два флага — про зимний бетон/наценку
(`winter_concrete`, `winter_surcharge`, `winter_surcharge_amount`). Наличия
фундамента/монтажа как булева флага НЕТ — оно определяется динамически по
содержимому `spec_items` (`any(it["payment_group"]=="foundation" for it in
spec_items)` и аналоги, см. `_active_buckets`/`get_active_payment_groups`).

**contract["scope_overrides"]** (`state.py:38-43`) — override-строки
сценария (`foundation_scope`, `installation_scope`, `verification_scope`,
`orion_poles_scope`), используются в рендере пунктов договора
(clauses), не в оплате.

**contract["extracted"] / contract["card"]** — таких ключей НЕТ. Реальные
top-level ключи `contract`: `requisites, specification, manual, uploads
(kp, card — пути к файлам, не данные), ai_raw, generated, kp_snapshot,
payment_lines, kp_payment_snapshot, attachments, flags, scope_overrides`
(`src/contracts/state.py:8-44`). Ближайший аналог "снапшота КП" —
`contract["kp_snapshot"]` (весь JSONB снапшот КП из Supabase: `model`,
`options`, `custom_items`, `installation_scope`, `payment`, `spec_overrides`,
`flags`, `delivery_address`).

## 5. Понятие «веха»/«бакет», привязанного к событию

Слова "milestone"/"веха"/"этап" как идентификаторы в коде НЕ встречаются.
Слово "bucket" — только в комментариях/переводе UI (`_BUCKET_OPTIONS`,
`_bucket_total`), не как отдельная доменная абстракция.

НО функционально эквивалентная концепция уже есть и связана со spec_items —
это НЕ плоский список "текст+% без связи с позициями":
- `PaymentTrigger` enum (`payment_line.py:10-16`) — событие-триггер оплаты.
- `PaymentLine` dataclass (`payment_line.py:29-41`) — строка с полями
  `kind, share_pct, share_object, amount, trigger, due, due_unit,
  base_amount`.
- `build_lines_from_snapshot()` → `_build_split_lines`-эквивалент
  (`payment_line.py:240-346`) генерирует строки, суммируя `spec_items` по
  бакету (`_bucket_total`) и привязывая сумму к конкретному триггеру:
  предоплата весов → SPEC_SIGNED, доплата фундамента → FOUNDATION_ACT,
  доплата весов/доставки → SHIPMENT_READY, монтаж/поверка →
  BRIGADE_READY/WORK_ACT.

Важная оговорка: эта привязка "бакет → триггер" работает ТОЛЬКО для
дефолтного пресета `split_by_items`. Остальные пресеты (v1/v2/v3/
prepay_100/custom) — действительно плоские: процент/сумма от общего итога
спецификации, без разбивки по позициям (`_build_non_split_lines`,
`payment_line.py:143-182`).

## 6. Куда пишутся строки оплаты в docx

Два разных механизма для двух разных документов:

**a) КП** — обычный jinja-плейсхолдер через `docxtpl`:
```python
# src/generators/kp_generator.py:184-185,230
payment_text = render_payment_block(state, spec_items, payment_terms_json)
payment_rt = _payment_listing(payment_text)   # docxtpl.Listing
...
"payment_terms_block": payment_rt,
```
Плейсхолдер `{{ payment_terms_block }}` вписывается в шаблон
`src/generators/make_template.py:493-495` и фигурирует в списке ожидаемых
плейсхолдеров (строка 701). `DocxTemplate.render()` подставляет значение
стандартным Jinja-механизмом.

**b) Договор/Спецификация** — двупроходная схема: сначала `docxtpl`, потом
РУЧНАЯ вставка абзацев через `python-docx` по текстовому маркеру
`{{PAYMENT_SECTION}}` (это литеральный текст-маркер в шаблоне, ищется
вручную, НЕ jinja-переменная контекста):
```python
# src/contracts/compose.py:26,29-53
payment_lines: list[str] = context.get("_payment_lines", [])
...
if payment_lines:
    found = _replace_marker_with_paragraphs(contract_doc, "{{PAYMENT_SECTION}}", payment_lines)
else:
    found = _remove_marker(contract_doc, "{{PAYMENT_SECTION}}")
```
Аналогично для спецификации — `src/contracts/spec_v2_filler.py:300-307`
(`fill_spec_v2`), тот же маркер `{{PAYMENT_SECTION}}`. Подстановка —
клонирование абзаца (не таблицы), функция `_replace_marker_with_paragraphs`
(`spec_v2_filler.py:136-149`).

Список `_payment_lines` собирается в `2_Договор.py:1031,1066-1071` из
ручной таблицы `get_payment_lines()` (та же, что в редакторе
`payment_lines_editor.py`), либо (если менеджер её не трогал) — через
`render_payment_block`/`_payment_lines_from_data`.

Затрагиваемые docx-шаблоны: `templates/contracts/supply_contract.docx`,
`supply_appendix_1.docx`, `supply_appendix_2.docx`,
`templates/contracts/spec_v2.docx`. Маркер `{{PAYMENT_SECTION}}` также
фигурирует в `src/contracts/supply_filler.py:353`.

## Сводка для будущей сеялки по вехам

- Данные для привязки оплаты к этапам уже есть: `payment_group` на каждой
  позиции спецификации + `_bucket_total()` по нему + `PaymentTrigger` enum.
  Механизм `build_lines_from_snapshot()`/`split_by_items` — фактически
  прототип "сеялки по вехам", но только для одного пресета.
- Главный дефект для этой цели — бандл ОРИОН не расщепляется перед расчётом
  оплаты (`resolve_payment_group` даёт весам весь бандл целиком), хотя для
  отображения в спецификации расщепление уже есть (`_expand_orion_options`,
  но по другому пути данных).
- Понятия "веха" как явной сущности нет — есть склейка bucket+trigger внутри
  `payment_line.py`, специфичная для split_by_items.
- Оплата physически пишется в docx двумя разными механизмами (jinja для
  КП, ручной маркер для договора/спецификации) — любое изменение формата
  строки придётся синхронизировать в обоих местах.
