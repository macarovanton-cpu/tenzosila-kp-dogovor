# Production Architecture v1

**Проект:** Tenzosila KP & Dogovor
**Дата:** 2026-06-12
**Статус:** проектирование (к реализации)
**Заменяет:** разделы roadmap из `production_architecture_plan.md` (диагностика оттуда остаётся в силе)

---

## 0. Назначение и рамки

Это целевая архитектура достройки MVP до целостного внутреннего инструмента.
Документ написан так, чтобы по нему можно было кодить шаг за шагом с Claude Code,
не додумывая решения по ходу.

**Контекст, который определяет всё:**

- Инструмент **внутренний**, для отдела продаж Тензосилы (единицы пользователей).
- Разработчик — один, не-инженер, vibe-coding с AI.
- Деплой — **Вариант А**: один инстанс на Streamlit Cloud, все заходят по ссылке,
  одна общая Supabase.
- **Ролей нет.** Цену менеджеры определяют сами. Согласований нет.
- **Админка нужна** только для РОП: крутить несколько настроек цен
  (например ×2 на Орион, ×2 на автовесы, НДС, коэффициенты коридора).

Из этого следует: НЕ строим RBAC, rules engine, approval workflow, мультикомпанию,
версионирование шаблонов, нормализацию позиций КП. Всё это — за горизонтом v1.

---

## 1. Три несущих решения

Вся архитектура стоит на них. Если меняется одно — пересматривать раздел.

### Решение 1 — админ-доступ без ролей

Гейт админ-страницы = список email в конфиге (`ADMIN_EMAILS`).
Авторство действий = email из сессии Supabase Auth (встроен при деплое
Streamlit Cloud + Supabase). Никаких таблиц `users/roles/permissions`.

```python
if st.user.email not in ADMIN_EMAILS:
    st.stop()
```

### Решение 2 — snapshot замораживает ИТОГОВЫЕ значения, а не ссылки на версии

Каждое КП сохраняет фактически использованные числа по каждой строке
(base / min / recommended / max / selected + какой множитель применён).
Старое КП и договор воспроизводятся из своего блоба и не зависят от текущих
настроек прайса.

Следствие: версионирование настроек становится опциональным (нужно для аудита,
не для корректности). Это убирает целый пласт версионных таблиц.

### Решение 3 — множитель = пре-множитель на base ДО коридорной математики

«×2 на Орион» = у всех позиций категории Orion `base` удваивается, и уже потом
считается класс цены A/B/C. На позицию применяется **ровно один** множитель по
приоритету `item > category > item_type > global(=1.0)`. Без компаундинга.

---

## 2. Модель данных (Supabase / PostgreSQL)

Минимальный набор. Типы ориентировочные, точный DDL пишется в миграциях.

### 2.1 Новые таблицы

**`price_lists`** — версии прайса

| поле | тип | примечание |
|---|---|---|
| id | uuid pk | |
| version | text | напр. "2026-06" |
| status | text | draft \| active \| archived |
| valid_from | date | |
| is_active | bool | одна активная версия |
| source_filename | text | имя загруженного файла |
| created_by | text | email |
| activated_at | timestamptz | |
| created_at | timestamptz | |

**`price_items`** — позиции (активной и архивных версий)

| поле | тип | примечание |
|---|---|---|
| id | uuid pk | |
| price_list_id | uuid fk | |
| item_type | text | model \| option \| service |
| item_key | text | ключ как в текущем JSON |
| category | text | напр. "orion" |
| label | text | |
| price_retail | numeric | |
| price_dealer | numeric | |
| price_class | text | A \| B \| C \| UNKNOWN \| on_request |
| range_min | numeric | для класса C |
| range_max | numeric | для класса C |
| on_request | bool | |
| raw | jsonb | исходная строка прайса целиком |

**`pricing_settings`** — то, что крутит РОП (типизированный key-value реестр)

| поле | тип | примечание |
|---|---|---|
| id | uuid pk | |
| key | text unique | напр. "mult_orion" |
| value_type | text | number \| percent \| bool \| multiplier |
| value | numeric | значение |
| target | jsonb | `{scope, match}` — на что действует |
| label | text | человекочитаемая подпись для формы |
| is_active | bool | |
| updated_by | text | email |
| updated_at | timestamptz | |

Сид при инициализации (переносит текущие константы из `config.py`):

| key | value_type | value | target |
|---|---|---|---|
| vat_rate | percent | 0.22 | `{scope:"global"}` |
| max_coeff | number | 1.4 | `{scope:"global"}` |
| min_coeff_b | number | 0.6 | `{scope:"global"}` |
| synthetic_dealer_factor | number | 0.92 | `{scope:"global"}` |
| mult_orion | multiplier | 1.0 | `{scope:"category", match:"orion"}` |
| mult_models | multiplier | 1.0 | `{scope:"item_type", match:"model"}` |

Дальше РОП добавляет строки через UI — форма рендерится по `value_type`
автоматически.

**`audit_log`** — append-only

| поле | тип |
|---|---|
| id | uuid pk |
| actor | text (email) |
| action | text |
| entity_type | text |
| entity_id | text |
| before | jsonb |
| after | jsonb |
| meta | jsonb |
| created_at | timestamptz |

**`generated_documents`** — хранение и повторная выдача

| поле | тип | примечание |
|---|---|---|
| id | uuid pk | |
| kp_id | uuid nullable | |
| contract_id | uuid nullable | |
| doc_type | text | kp \| contract \| spec \| appendix |
| storage_key | text | ключ в Supabase Storage |
| template_tag | text | git-тег/хеш шаблона, НЕ таблица версий |
| created_by | text | email |
| created_at | timestamptz | |

### 2.2 Изменения существующих таблиц

- **`kps`**: добавить `price_list_id (uuid)`, `settings_snapshot (jsonb)`.
  Позиции остаются в `data (jsonb)` — **не нормализуем**.
- **`contracts`**: структурно без изменений, читает snapshot из `kps`.

### 2.3 Миграции

Папка `db/migrations/`, нумерованные `.sql`, применяются Supabase CLI.

- `0001_baseline.sql` — фиксирует текущие `kps`/`contracts` как есть.
- Дальше любая правка схемы — только новой миграцией. Ручных правок в дашборде
  Supabase не делаем.

---

## 3. Код: новые модули и ответственность

```
src/pricing/
  engine.py        # resolve(line, price_list, settings) -> PriceResult. Сердце.
  settings.py      # load_active()/save() pricing_settings, типизация значений
  price_repo.py    # get_active_price_list() из БД, fallback на data/prices.json
src/storage/
  audit.py         # log(actor, action, entity, before, after, meta)
  documents.py     # store(bytes, meta) / fetch(id) — Supabase Storage
src/checks/
  docx_validate.py # leak-check ({{ }}), totals-check после генерации
src/pages/
  3_Админ.py       # страница РОП (гейт по ADMIN_EMAILS)
```

Существующие `pricing.py`, `snapshot_builder.py`, `kp_generator.py`,
`from_kp.py` — **не удаляем**, дорабатываем по ходу.

### 3.1 Контракт `PriceResult`

Что `engine.resolve` возвращает на каждую строку спецификации:

```python
@dataclass
class PriceResult:
    item_key: str
    base_price: float          # raw из прайса (retail или dealer по классу)
    applied_multiplier: float  # 1.0 если нет
    multiplier_source: str     # "mult_orion" | "" | ...
    effective_base: float      # base_price * applied_multiplier
    min_price: float
    recommended_price: float
    max_price: float
    selected_price: float       # выбор менеджера; по умолчанию = recommended
    price_status: str          # ok | below_rec | below_min | above_max | on_request
    requires_comment: bool     # selected вне [min..rec] и т.п.
    comment: str
```

---

## 4. Механика множителя (точная)

`engine.resolve` для одной позиции:

1. `raw_base = price_retail` (или `price_dealer` — по классу цены)
2. найти применимый множитель по приоритету `item > category > item_type > global`
   — **ровно один**, не перемножаем
3. `effective_base = raw_base * multiplier`
4. посчитать коридор от `effective_base`:
   - **класс A**: `min = dealer * mult`, `rec = effective_base`, `max = effective_base * max_coeff`
   - **класс B**: `min = effective_base * min_coeff_b`, `rec = effective_base`, `max = effective_base * max_coeff`
   - **класс C**: `min = range_min`, `max = range_max` — множитель к ручному диапазону **НЕ применяем**
   - **UNKNOWN**: synthetic dealer через `synthetic_dealer_factor`, дальше как A
   - **on_request**: блок генерации до ручной цены

**Пример.** Орион, retail 100 000, класс B, `mult_orion = 2.0`,
`min_coeff_b = 0.6`, `max_coeff = 1.4`:

```
effective_base = 100 000 * 2.0 = 200 000
min = 200 000 * 0.6 = 120 000
rec = 200 000
max = 200 000 * 1.4 = 280 000
```

В snapshot замораживается весь коридор + `applied_multiplier = 2.0`,
`multiplier_source = "mult_orion"`.

---

## 5. Потоки данных

### 5.1 Генерация КП

```
price_repo.get_active() ──┐
settings.load_active() ───┴─► engine.resolve(каждая строка) ► PriceResult[]
 ► менеджер правит selected_price
 ► selected вне recommended ⇒ requires_comment=true, audit.log("manual_price")
 ► snapshot_builder замораживает:
      price_list_id, settings_snapshot,
      по каждой строке {base, min, rec, max, selected, mult, mult_source, comment}
 ► kp_generator рендерит DOCX из snapshot (не из live state)
 ► docx_validate: нет {{ }}, итоги бьются
 ► documents.store(docx, meta)
 ► audit.log("kp_generated")
```

### 5.2 Генерация договора

```
читает snapshot из kps
 ► from_kp строит ContractDraft ТОЛЬКО из замороженных значений (без пересчёта)
 ► генерация DOCX
 ► docx_validate
 ► documents.store
 ► audit.log("contract_generated")
```

Договор не угадывает цену/прайс/условия заново. Это закрывает риск пересчёта
старых документов по новым настройкам (Risk 1/5 из исходного плана) намертво.

---

## 6. Страница «Админ» (что видит РОП)

Гейт: `if st.user.email not in ADMIN_EMAILS: st.stop()`.

**Таб 1 — Прайс.**
Загрузка валидированного CSV/XLSX → проверка обязательных колонок →
предпросмотр строк → кнопка «Сделать активным» (создаёт новую `price_lists`
со `status=active`, старую → `archived`).
Diff-отчёт и откат — отдельный шаг позже, не в первом проходе.

**Таб 2 — Настройки цен.**
Форма из `pricing_settings`, поля рендерятся по `value_type`:
- глобальные: НДС, max_coeff, min_coeff_b, synthetic_dealer_factor
- множители: Орион, автовесы, … (number, дефолт 1.0)
- кнопка «Добавить множитель» (выбор scope: category / item_type / item + значение)
Сохранение → запись в `pricing_settings` + `audit.log("settings_changed")`.

**Таб 3 — Журнал.**
Read-only лента `audit_log` (последние N, фильтр по action/дате).

**Таб 4 — Качество данных.**
Read-only проверки-предупреждения:
- нет активного прайса
- модель есть в справочнике, но нет в активном прайсе
- прайс просрочен (`valid_from` старый)
- опция без категории/описания
- активный прайс отсутствует

РОП **не трогает**: модели/ТТХ (только импорт), шаблоны (git), роли (их нет).

---

## 7. Порядок реализации

Это и есть «осталось закодить». Каждый шаг самостоятелен и тестируется.

### Шаг 0 — надёжность (без UI, ничего не ломает)

- `0001_baseline.sql` — зафиксировать текущие `kps`/`contracts`
- настроить бэкап Supabase (расписание + проверка восстановления)
- `src/storage/documents.py` — store/fetch через Supabase Storage
- `src/checks/docx_validate.py` — leak-check `{{ }}` + сверка итогов
- подключить `docx_validate` в текущий путь генерации КП/договора

Можно запускать **сейчас**, не дожидаясь стабилизации v2.1.

### Шаг 1 — прайс в БД

- таблицы `price_lists`, `price_items` (миграция `0002`)
- `src/pricing/price_repo.py` — `get_active()` из БД, fallback на `data/prices.json`
- `price_list_id` в snapshot КП (миграция `0003` — alter `kps`)
- Таб «Прайс»: загрузка → активна (без diff)
- скрипт миграции текущего `data/prices.json` → первая запись `price_lists`

### Шаг 2 — engine + настройки (самый рискованный)

- таблица `pricing_settings` (миграция `0004`) + сид из `config.py`
- `src/pricing/engine.py` + `src/pricing/settings.py`
- перевести ценовые виджеты на engine **по одному**, не большим взрывом
- тесты на каждый класс: A / B / C / UNKNOWN / on_request + множитель
- тесты на приоритет множителей (item > category > item_type > global)
- Таб «Настройки цен»

⚠️ Pricing трогает весь UI (помним конфликт ключа `platform_width_m`).
Только инкрементально: тесты пишутся ДО миграции каждого виджета.

### Шаг 3 — заморозка + аудит

- `settings_snapshot` в `kps` (миграция `0005`)
- `snapshot_builder` пишет резолвнутые значения коридора по строкам
- `from_kp` читает только замороженные значения
- `src/storage/audit.py` + таблица `audit_log` (миграция `0006`)
- логировать: ручная цена, смена прайса, смена настроек, генерация КП/договора
- обязательный comment при `selected` вне recommended
- Табы «Журнал» и «Качество данных»

---

## 8. Что сознательно НЕ делаем в v1

| Отложено | Когда вернуться |
|---|---|
| Роли / RBAC | если появятся пользователи с разными правами |
| Approval workflow | если бизнесу понадобится формальное согласование |
| Rules engine (правила в БД) | сейчас правила = коэффициенты в `pricing_settings`, хватает |
| Версионирование шаблонов | git версионирует; берём только leak-check |
| Нормализация позиций КП | держим JSONB-snapshot |
| Diff/rollback прайса | после стабилизации Таба «Прайс» |
| Мультикомпания | этап продуктизации |
| FastAPI/React | только при доказанном упоре в Streamlit |

---

## 9. Открытые вопросы

- **Supabase Auth на Streamlit Cloud** — проверить, как именно прокидывается
  `st.user.email` (нативный OIDC Streamlit vs Supabase Auth). От этого зависит
  источник `actor` для аудита и гейт админки. Решается на Шаге 0/1.
- **Класс C и множитель** — в v1 множитель к ручному диапазону НЕ применяется.
  Если РОП захочет иначе — отдельная настройка, не дефолт.
- **Формат прайса для импорта** — зафиксировать обязательные колонки CSV/XLSX
  до Шага 1 (отдельный мини-спек).
