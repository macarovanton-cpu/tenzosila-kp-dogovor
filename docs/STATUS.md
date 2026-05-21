# STATUS — AI-конфигуратор КП и договоров

Последнее обновление: 2026-05-21
Текущая фаза: 2.x — закрытие багов после ручной проверки КП→договор

---

## Что работает сейчас

### Конфигуратор КП (стабильно)
- Streamlit на Cloud, 234 теста зелёные (216 КП + 18 storage)
- Полный цикл: выбор модели → опции → цена → схема оплаты → DOCX
- Все линейки С/СЛ/Ф/ФЛ/П/М, двухдиапазонные
- 7 пресетов оплаты, 3 модели оплаты (V1/V2/V3), параллельные сроки

### Модуль договоров (рабочий MVP)
- src/contracts/{extractor, filler, utils, state, from_kp}.py + 30+ тестов
- pages/2_Договор.py — двухрежимный UI:
  - Режим A: данные из Supabase + AI только для карточки
  - Режим B: legacy, AI парсит PDF КП + карточку
- AI: OpenRouter, пул Qwen3-235b-07-25 → Qwen3-235b → Llama 3.3 70B
- Шаблоны: contract.docx + spec_foundation_install.docx (хардкод дат и «Компания Тензосила» убран)
- Тег: v0.7

### Storage модуль Supabase
- src/storage/supabase_client.py создан
- Таблицы: kps + contracts (UUID PK, RLS отключён)
- 18 тестов зелёные
- Supabase: hwrbwfjjctppeofakuja.supabase.co, Frankfurt
- save_kp интегрирован в страницу КП (Шаг 8)

---

## Что выполнено

### Шаг 6.5 ✅ — Рефакторинг namespace страницы Договор
- src/contracts/state.py создан, 42 ключа ЗАКАЗЧИК_*/СПЕЦ_* под st.session_state["contract"]
- 12 новых тестов

### Шаг 7 ✅ — Storage модуль Supabase
- supabase_client.py: save_kp, get_kp_by_number, list_recent_kps, search_kps_by_contractor, 
  delete_kp, save_contract, get_contracts_by_kp_id
- 18 тестов на реальном Supabase

### Шаг 8 ✅ — Интеграция save_kp в страницу КП
- src/storage/snapshot_builder.py: build_kp_snapshot(state) → JSONB
- sidebar.py: save после download, ошибки Supabase не блокируют
- 5 unit-тестов

### Шаг 9 ✅ — Двухрежимный UI договора
- Режим A: selectbox/text_input → get_kp_by_number → build_specification_from_kp_snapshot
- Режим B: legacy без изменений (alias extract_from_files = extract_kp_data_legacy)
- extract_card_data: только 19 ЗАКАЗЧИК_* через extract_card_data.txt
- src/contracts/from_kp.py: маппинг JSONB → СПЕЦ_*
- Баги A2/A3/P1.3 закрыты, P1.4 неактуален (шаблон использует ИНИЦИАЛЫ)
- +49 тестов (270 PASS, 1 skipped)

### Промт A ✅ — Баг 4 (rerun при скачивании)
- Байты документов сохраняются в st.session_state["contract"]["generated"]
- Кнопки скачивания не теряются при rerun
- Добавлена кнопка «Сгенерировать заново»

### Промт D-prep ✅ — баги 8 и 9 шаблона спецификации
- patch_spec_template.py: w:keepWithNext→w:keepNext (корень бага), цепочка через TABLE[1]+paras[55-57]+TABLE[2]+para[61]+TABLE[3]
- patch_spec_template.py: _replace_in_docx_xml — замена КРАТКОЕ→ИНИЦИАЛЫ в text box Приложения
- +3 теста (итого 12 в test_templates.py)

### Промт C-prep ✅ — вёрстка и нумерация страниц
- filler.py: guard `if '{{' in p.text` для header/footer (сохраняет поле PAGE)
- filler.py: удаление пустых нумерованных параграфов после подстановки (баг 1)
- patch_spec_template.py: cantSplit TABLE[1]/TABLE[2], keepWithNext-цепь через P[56]
- +4 теста (2 в test_filler.py, 2 в test_templates.py → итого 4 в filler, 9 в templates)

---

## Ручная проверка КП→договор (ООО «Вера»)

Обнаружены 6 багов, 4 закрыто, 1 снят. Полный список:

| # | Баг | Статус |
|---|-----|--------|
| 1 | Пустые строки 2.5/2.6 в оплате (filler.py удаляет пустые numPr параграфы) | ✅ Закрыт |
| 2 | Пустое наименование весов в КП | Снят — артефакт парсинга |
| 3 | «действующего» вместо «действующей» (род директора) | Открыт — Промт C |
| 4 | Rerun теряет второй документ | ✅ Закрыт |
| 5 | Пункт 14 спецификации не с новой страницы | ✅ Закрыт |
| 6 | Приложение №1 не с новой страницы | ✅ Закрыт |
| 8 | п.14/15 + подписи разрываются по страницам (keepNext-цепь, w:keepWithNext→w:keepNext) | ✅ Закрыт |
| 9 | Устаревший плейсхолдер ФИО_КРАТКОЕ в text box Приложения №1 | ✅ Закрыт |

---

## Что делаем дальше

### Промт B ✅ — вёрстка спецификации
- spec_foundation_install.docx: п.14 (ТХ) с новой страницы, п.14/15 keep-together
- Приложение №1 — page_break_before
- scripts/patch_spec_template.py — idempotent, можно повторить после замены шаблона
- +2 теста (6 в test_templates.py)

### Промт C (opus-plan → sonnet, ~1.5 ч) — род директора ← ТЕКУЩИЙ
- Решение: pymorphy3 / поле «пол» в карточке / гибрид
- Правка: extract_card_data.txt, форма Договор, шаблоны (плейсхолдеры по роду)

### Промт D (opus, ~2.5 ч) — jinja-цикл по строкам оплаты
- spec_foundation_install.docx: вместо фиксированных П1..П6 — цикл (пустые строки уже убраны через filler.py, цикл нужен для гибкости)
- from_kp.py: формат данных для цикла
- Проверка на всех 7 пресетах оплаты

### Шаг 10 — Прогон синтетики + тег (~15 мин)
- Только после закрытия багов
- Обновить тесты B1/C5 под П6
- Findings: «Сессия 4»
- Тег v0.8

### Шаг 11 — Деплой на Streamlit Cloud (ты, ~10 мин)
- SUPABASE_URL и SUPABASE_KEY в Cloud Secrets
- Push в main

### Шаг 12 — Миграция старых КП (опционально, ~30 мин)
- scripts/migrate_old_kps.py

---

## После итерации Supabase → Этап 3

- Вынос ТТХ в плейсхолдеры из JSON-справочников КП
- 9 шаблонов спецификаций по сценариям комплектации
- Селектор шаблона в UI

---

## Открытые баги шаблонов (не блокируют)
- P1.1: «Ограждение» отдельной строкой → в режиме A агрегируется в П1
- P1.2: ТТХ статичны → Этап 3

## Синтетика (legacy, ожидаемо падает)
- B1: арифметика 3/5 → закроется в режиме A
- B3: парсер теста не справляется с многострочными суммами
- C5: AI дропает поверку когда позиций >5

---

## Технический долг
- Git-конфликт дом↔Codespaces (backup-ветка → force-push)
- data_loader: дублирование equipment_specs.json ↔ models.json
- vMerge слияние ячеек в таблице спецификации DOCX
- Удаление legacy ключа payment_percents из state