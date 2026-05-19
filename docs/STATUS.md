# STATUS — AI-конфигуратор КП и договоров

Последнее обновление: 2026-05-19
Текущая фаза: 2.x — Шаг 7, storage модуль Supabase

---

## Что работает сейчас

### Конфигуратор КП (стабильно)
- Streamlit на Cloud, 216 тестов зелёные
- Полный цикл: выбор модели → опции → цена → схема оплаты → DOCX
- Все линейки С/СЛ/Ф/ФЛ/П/М, двухдиапазонные
- 7 пресетов оплаты, 3 модели оплаты (V1/V2/V3), параллельные сроки

### Модуль договоров (рабочий MVP)
- src/contracts/{extractor, filler, utils, state}.py + 30 тестов
- pages/2_Договор.py — текущий путь: PDF КП + карточка → AI → форма → DOCX
- AI: OpenRouter, пул Qwen3-235b-07-25 → Qwen3-235b → Llama 3.3 70B
- Шаблоны: contract.docx + spec_foundation_install.docx
- Тег: v0.7

---

## Что выполнено

### Шаг 6.5 ✅ — Рефакторинг namespace страницы Договор
- src/contracts/state.py создан
- 42 ключа ЗАКАЗЧИК_*/СПЕЦ_* изолированы под st.session_state["contract"]
  Структура: contract.requisites / contract.specification / contract.manual
- 12 новых тестов, все зелёные
- 216 тестов суммарно зелёные
- Закоммичено: feat(contracts): шаг 6.5 — изоляция namespace

### Supabase готов к интеграции ✅
- Проект: tenzosila-kp-dogovor, регион Frankfurt
- URL: https://hwrbwfjjctppeofakuja.supabase.co
- Таблица kps создана (RLS отключён для MVP)
- Подключение из Python протестировано, anon-ключ в secrets.toml
- Архитектура: две таблицы — kps + contracts (FK → kps.id)
- Вся структура JSONB задокументирована в docs/session_state_audit.md

---

## Что делаем дальше

### Шаг 7 — Storage модуль Supabase (Code, ~3.5 ч) ← ТЕКУЩИЙ
Создать src/storage/supabase_client.py.

Функции для таблицы kps:
- save_kp(номер_кп, дата_кп, контрагент, модель, сумма_итого, автор, данные)
- get_kp_by_number(номер_кп) → dict | None
- list_recent_kps(limit=50) → list[dict]  (без поля данные)
- search_kps_by_contractor(query, limit=20) → list[dict]
- delete_kp(номер_кп) → bool

Функции для таблицы contracts:
- Сначала создать таблицу contracts в Supabase SQL Editor
- save_contract(kp_id, contract_number, contract_date, object_address, spec_number, requisites, specification)
- get_contracts_by_kp_id(kp_id) → list[dict]

Тесты: tests/storage/test_supabase_client.py
- Тестовая таблица kps_test (отдельная, TRUNCATE перед каждым тестом)
- test_save_and_retrieve, test_upsert, test_list_recent, test_search, test_delete
- Обработка StorageError

Требования:
- supabase>=2.0 в requirements.txt
- st.secrets["SUPABASE_URL"] и st.secrets["SUPABASE_KEY"]
- UPSERT по номер_кп (не INSERT — один КП может сохраняться повторно)

### Шаг 8 — Интеграция в страницу КП (Code, ~1 ч)
- После генерации DOCX → save_kp с полным снапшотом state
- st.success / st.warning в UI
- НЕ блокировать генерацию если Supabase упал

### Шаг 9 — Двухрежимный UI договора (Code, ~2.5 ч)
- Разделить extractor.py: extract_card_data (новый) + extract_kp_data_legacy
- prompts/extract_card_data.txt — только 16 полей карточки
- st.radio в pages/2_Договор.py: «Из базы» / «Из PDF файла»
- Режим A: поиск по номеру/контрагенту → данные из Supabase + AI для карточки
- Режим B: текущий legacy-путь без изменений
- Правка шаблонов: убрать «29.05.2026», «Компания Тензосила»

### Шаг 10 — Прогон синтетики + тег (Code, ~15 мин)
- test_e2e_synthetic.py на новой архитектуре
- Обновить тесты B1/C5 под П6
- findings: «Сессия 4 — после двухрежимного UI»
- Тег v0.8

### Шаг 11 — Деплой на Streamlit Cloud (ты, ~10 мин)
- SUPABASE_URL и SUPABASE_KEY в Cloud Secrets
- Push в main

### Шаг 12 — Миграция старых КП (опционально, ~30 мин)
- scripts/migrate_old_kps.py — прогон архива PDF → save_kp

---

## После итерации Supabase → Этап 3

- Вынос ТТХ в плейсхолдеры из JSON-справочников КП
- 9 шаблонов спецификаций по сценариям комплектации
- Селектор шаблона в UI

---

## Открытые баги (не блокируют Шаг 7)

### Шаблоны (закроются в Шаге 9)
- A2: «29.05.2026» зашита в contract.docx
- A3: «Компания Тензосила» в spec_foundation_install.docx
- P1.1: строка «Ограждение» не добавляется в таблицу спеки
- P1.3: хвост «110/2026 от 29.05.2026г» в спеке
- P1.4: незамещённый {{ЗАКАЗЧИК_ДИРЕКТОР_ФИО_КРАТКОЕ}}
- P1.2: ТТХ статичны → Этап 3

### Синтетика (legacy-режим)
- B1: арифметика 3/5 (закроется в режиме A — данные из state)
- B3: парсер теста не справляется с многострочными суммами
- C5: AI дропает поверку когда позиций >5

---

## Технический долг
- Git-конфликт дом↔Codespaces (backup-ветка → force-push)
- data_loader: дублирование equipment_specs.json ↔ models.json
- vMerge слияние ячеек в таблице спецификации DOCX
- Удаление legacy ключа payment_percents из state