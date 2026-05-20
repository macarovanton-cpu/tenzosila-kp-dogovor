# STATUS — AI-конфигуратор КП и договоров

Последнее обновление: 2026-05-20
Текущая фаза: 2.x — Шаг 10, прогон синтетики + тег

---

## Что работает сейчас

### Конфигуратор КП (стабильно)
- Streamlit на Cloud, 234 теста зелёные (216 KП + 18 storage)
- Полный цикл: выбор модели → опции → цена → схема оплаты → DOCX
- Все линейки С/СЛ/Ф/ФЛ/П/М, двухдиапазонные
- 7 пресетов оплаты, 3 модели оплаты (V1/V2/V3), параллельные сроки

### Модуль договоров (рабочий MVP)
- src/contracts/{extractor, filler, utils, state}.py + 30 тестов
- pages/2_Договор.py — текущий путь: PDF КП + карточка → AI → форма → DOCX
- AI: OpenRouter, пул Qwen3-235b-07-25 → Qwen3-235b → Llama 3.3 70B
- Шаблоны: contract.docx + spec_foundation_install.docx
- Тег: v0.7

### Storage модуль Supabase (новый)
- src/storage/supabase_client.py создан
- Таблицы: kps + contracts (UUID PK, RLS отключён)
- Тестовые таблицы: kps_test + contracts_test
- 18 тестов зелёные (save/get/upsert/list/search/delete/contracts)
- Supabase: hwrbwfjjctppeofakuja.supabase.co, Frankfurt

---

## Что выполнено

### Шаг 6.5 ✅ — Рефакторинг namespace страницы Договор
- src/contracts/state.py создан
- 42 ключа ЗАКАЗЧИК_*/СПЕЦ_* изолированы под st.session_state["contract"]
- 12 новых тестов, все зелёные

### Шаг 7 ✅ — Storage модуль Supabase
- src/storage/supabase_client.py: save_kp, get_kp_by_number, list_recent_kps,
  search_kps_by_contractor, delete_kp, save_contract, get_contracts_by_kp_id
- StorageError кастомный класс, try/except на всех функциях
- 18 тестов зелёные на реальном Supabase
- Схема таблиц пересоздана с английскими именами колонок (UUID, not BIGSERIAL)

### Шаг 9 ✅ — Двухрежимный UI договора
- Режим A: selectbox/text_input → get_kp_by_number → build_specification_from_kp_snapshot
- Режим B: extract_kp_data_legacy (алиас extract_from_files), без изменений
- extract_card_data: только 19 ЗАКАЗЧИК_* через extract_card_data.txt
- set_specification, set_requisites, is_extracted обновлён для режима A
- src/contracts/from_kp.py: маппинг JSONB снапшота → СПЕЦ_* плейсхолдеры
- Шаблоны: contract.docx и spec_foundation_install.docx — хардкод убран
- Баги A2/A3/P1.3 закрыты; P1.4 неактуален (шаблон использует ИНИЦИАЛЫ)
- +49 тестов (итого 270 PASS, 1 skipped)

### Шаг 8 ✅ — Интеграция save_kp в страницу КП
- src/storage/snapshot_builder.py: build_kp_snapshot(state) → JSONB по §6.2
- sidebar.py: download_button-click guard + _save_kp_to_storage
- Ошибки Supabase не блокируют генерацию DOCX (st.warning)
- 5 новых unit-тестов (tests/test_snapshot_builder.py), итого 221 зелёных без сети

---

## Что делаем дальше

### Шаг 9 ✅ — Двухрежимный UI договора (выполнен)

### Шаг 10 — Прогон синтетики + тег (Code, ~15 мин) ← ТЕКУЩИЙ
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

## Открытые баги (не блокируют Шаг 8)

### Шаблоны
- P1.1: строка «Ограждение» не добавляется в таблицу спеки (в режиме A агрегируется в П1)
- P1.2: ТТХ статичны → Этап 3

### Синтетика (legacy-режим, ожидаемо)
- B1: арифметика 3/5 → закроется в режиме A
- B3: парсер теста не справляется с многострочными суммами
- C5: AI дропает поверку когда позиций >5

---

## Технический долг
- Git-конфликт дом↔Codespaces (backup-ветка → force-push)
- data_loader: дублирование equipment_specs.json ↔ models.json
- vMerge слияние ячеек в таблице спецификации DOCX
- Удаление legacy ключа payment_percents из state