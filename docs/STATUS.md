# STATUS — Tenzosila KP & Dogovor

Последнее обновление: 2026-05-23

---

## Где мы сейчас

**Архитектура v2 договоров, Шаг 7 — внедрение clauses library. Задача 5 в процессе (spec_v2.docx).**

Последний тег: **v0.9** (массив позиций спецификации, data_editor с пересчётом total).

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

**Шаг 7 архитектуры v2 — задача 5 (В ПРОЦЕССЕ):**
- Создан `templates/contracts/spec_v2.docx` — шаблон с маркерами {{CLAUSE_SECTION_*}}
- Создан `src/contracts/spec_v2_filler.py` — fill_spec_v2()
- Создан `scripts/create_spec_v2_template.py`
- Создан `tests/contracts/test_fill_spec_v2.py` — 10 тестов (но проверяют len, не контент ячеек)
- Найден баг: ячейки таблицы позиций пустые (`_set_cell_text` не создаёт w:t при их отсутствии)
- Найдено: ТТХ зашиты под ВЕСТА-СЛ-80-18-Ц, кит зашит, оплата 6 слотов, сроки 3 строки, год 2026 хардкод, лишняя кавычка в «Тензосила»

---

## Открытая работа: план Code сохранён

**Файл:** `docs/spec-v2-docx-curious-kite.md` (план Code на 7 атомарных коммитов).

**Что ждёт выполнения:**

| # | Коммит | Файлы |
|---|---|---|
| 1 | `fix(contracts): _set_cell_text — создание w:t + тесты контента` | filler.py, test_fill_spec_v2.py |
| 2 | `refactor(template): патч spec_v2.docx — маркеры, кавычки, год` | scripts/patch_spec_v2_template.py |
| 3 | `feat(contracts): terms_renderer — динамические сроки` | terms_renderer.py + тесты |
| 4 | `feat(contracts): tth_context — ТТХ плейсхолдеры` | tth_context.py + тесты |
| 5 | `feat(contracts): kit_renderer — комплект из модели` | kit_renderer.py + тесты |
| 6 | `feat(contracts): spec_v2_filler payment/terms/kit/appendix` | spec_v2_filler.py |
| 7 | `feat(contracts): build_spec_v2_data + integration + 3 DOCX` | from_kp.py, integration tests |

**Решения зафиксированы в плане:**
- `_set_cell_text` фикс: при отсутствии w:t создавать через OxmlElement
- ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА — константа «не более 50 м»
- ТТХ_ТЕМПЕРАТУРА — формула `_format_temp` со знаком
- Нумерация приложений v1.0 — фиксированная: №1=Строительное задание, №2=Контрольный лист; ОРИОН, материалы в backlog v1.1
- Контент контрольного листа из `docs/contract_templates_v1/Автовесы_монтаж_gemini.md:85-101`
- 3 примера DOCX для верификации: ВЕСТА-СЛ-40-18 / ВЕСТА-С-80-18 / ВЕСТА-С-100-24

**После коммита 1 — обязательный полный `pytest tests/ -v` (320+ тестов), не только test_fill_spec_v2.**

**После коммита 7 — стоп, ручная проверка DOCX в Word, потом задача 6.**

---

## Следующие задачи (после задачи 5)

### Задача 6, 7, 8 архитектуры v2 — промт для Code (модель: sonnet, после ack задачи 5)
Задачи 6, 7, 8. Модель: sonnet. Subagent-Driven.
Задача 5 одобрена. spec_v2.docx + fill_spec_v2 работают.
═══════════════════════════════════════════════════════════════
Задача 6 — UI override-флаги (src/pages/2_Договор.py)
═══════════════════════════════════════════════════════════════
В странице договора, после блока загрузки КП, перед таблицей items:
st.subheader("Особые условия")

st.checkbox "Зимний период (бетонные работы при +5 °C и ниже)"
→ session_state["contract"]["flags"]["winter_concrete"] (default False)

with st.expander("Override-флаги (для нестандартных случаев)", expanded=False):
st.caption("По умолчанию scope вычисляется из позиций спецификации.
Здесь можно вручную переопределить.")

st.selectbox "Тип фундамента"
options: ["Авто (из позиций)", "Заказчик строит", "Подрядчик строит",
"Подрядчик с материалами Заказчика", "Рама", "Без фундамента"]
маппинг на: None | "customer_builds" | "contractor_full"
| "contractor_with_materials" | "rama" | "none"
→ scope_overrides["foundation_scope"]
st.selectbox "Тип монтажа"
options: ["Авто (из позиций)", "Полный монтаж", "Шеф-монтаж", "Без монтажа"]
маппинг: None | "full" | "shefmontazh" | "none"
→ scope_overrides["installation_scope"]
st.selectbox "Поверку организует"
options: ["Авто (из позиций)", "Подрядчик", "Заказчик", "Без поверки"]
маппинг: None | "supplier" | "customer" | "none"
→ scope_overrides["verification_scope"]
st.selectbox "Опоры ПАК ОРИОН"
(показывать только если has_orion=True по контексту)
options: ["Авто (из позиций)", "Заказчик", "Подрядчик"]
маппинг: None | "by_customer" | "by_contractor"
→ scope_overrides["orion_poles_scope"]

ПРЕДПРОСМОТР CLAUSES:
with st.expander("Предпросмотр пунктов договора", expanded=False):
deal = собрать из текущего session_state
clauses_by_section = build_contract_clauses(deal)
для каждой секции:
st.markdown(f"{section.title} (раздел {section.section_number})")
для каждого clause в секции:
st.text(f"  {clause.auto_number}. {clause.text[:60]}...")
st.caption(f"Всего пунктов: {total_count}")
ТЕСТЫ:

tests/contracts/test_page_dogovor_overrides.py:

winter_concrete=True → preview содержит "winter_concrete_surcharge"
foundation_scope override="rama" → preview содержит "flat_area_for_rama"
verification_scope override="customer" → preview содержит "customer_organizes_verification"



═══════════════════════════════════════════════════════════════
Задача 7 — переключение генерации на v2 + fallback
═══════════════════════════════════════════════════════════════
Кнопка "Скачать спецификацию" в src/pages/2_Договор.py:
try:
output = fill_spec_v2(spec_v2_template_path, data, items, deal, output_path)
except Exception as e:
st.warning(f"Не удалось сгенерировать v2-спецификацию: {e}. Использую старый шаблон.")
output = fill_template(старый путь...)
Кнопка "Скачать договор" — БЕЗ ИЗМЕНЕНИЙ.
Старый spec_foundation_install.docx остаётся в репо как fallback.
Не удалять.
═══════════════════════════════════════════════════════════════
Задача 8 — финальная верификация
═══════════════════════════════════════════════════════════════

Полный pytest -v зелёный (включая новые тесты задач 6 и 7)
Streamlit smoke:

страница "Договор" открывается
чекбокс зимний период работает
expander override-флаги открывается, selectbox-ы работают
preview clauses обновляется реактивно
кнопка "Скачать спецификацию" даёт корректный DOCX


docs/STATUS.md → Шаг 7 ✅, v1.0 готов, обновить раздел "Текущее состояние"
docs/architecture/contracts_v2.md → пометить план миграции как реализованный
git tag v1.0
финальный коммит chore(release): v1.0 — clauses library + override UI

ОБЩИЕ ТРЕБОВАНИЯ:

Subagent-Driven: после каждой задачи pytest + отчёт + ack.
НЕ трогать payment_renderer, term_days, snapshot_builder, supabase_client.
НЕ удалять старый шаблон spec_foundation_install.docx.

Покажи план до правок.

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
- `v1.0` (план) — clauses library, override UI, единый spec_v2.docx