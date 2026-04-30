# Tech Debt Audit — Предрелизный

**Дата:** 2026-04-30  
**Фаза:** Phase 1 Production Trial (95%)  
**Кодовая база:** 4 328 строк Python в 23 файлах src/

---

## 1. Захардкоженные значения

### Централизованные константы (src/config.py) ✅
| Константа | Значение | Строка |
|-----------|----------|--------|
| VAT_RATE | 0.22 | config.py:16 |
| SYNTHETIC_DEALER_FACTOR | 0.92 | config.py:23 |
| MAX_COEFF | 1.4 | config.py:24 |
| MIN_COEFF_B | 0.6 | config.py:25 |
| DEFAULT_KP_VALID_DAYS | 15 | config.py:20 |

Все расчётные функции импортируют из config — единая точка правды.

### Требуют внимания ⚠️

| Что | Где | Severity | Комментарий |
|-----|-----|----------|-------------|
| Строки "22%" в UI | model_section.py:177, options_section.py:178,180, make_template.py:482,484,594,598 | MEDIUM | Display-строки, не расчёт. При смене ставки — 6 мест ручной правки |
| Толщина настила 6/8 мм | filters.py:11 | LOW | Задокументировано в docstring, бизнес-правило простое |
| `100 - prepay_pct` | payment_renderer.py:98,110 | — | Стандартная арифметика процентов |

---

## 2. Расчётные функции без тестов

**Покрытие:** 36 из 43 функций = 83.7%

| Приоритет | Функция | Файл:строка | Комментарий |
|-----------|---------|-------------|-------------|
| CRITICAL | `calc_default_deck_mm` | filters.py:9 | Бизнес-правило ≤60→6мм, >60→8мм |
| HIGH | `fmt_rub` | utils/format.py:11 | Форматирование денег (UI + DOCX) |
| HIGH | `fmt_int_spaces` | utils/format.py:16 | Форматирование чисел (DOCX) |
| HIGH | `pluralize` | utils/format.py:24 | Русское склонение (день/дня/дней) |
| — | `percent_to_retail` | pricing.py:188 | Используется в model_section/options_section. Тест добавлен. ✅ |
| LOW | `encode_term_days_marker` | generators/spec_vmerge.py:30 | Тестируется косвенно через apply_spec_vmerge |

### Полностью покрытые модули (100%)
- spec_builder.py — 8/8 функций
- term_days.py — 8/8 функций
- validation.py — 5/5 функций
- payment_renderer.py — 8/8 функций

---

## 3. Мёртвый код и неиспользуемые импорты

- **Неиспользуемые импорты:** 0 ✅
- **Мёртвый код:** не найдено. `percent_to_retail()` используется в model_section.py и options_section.py — ошибка аудита исправлена.
- **Dead code в UI/генераторах:** не обнаружено

---

## 4. TODO / FIXME / HACK

| Файл | Строки | Текст | Статус |
|------|--------|-------|--------|
| data/build_models.py | 97 | `# TODO уточнить` (platform_height для П) | Данные отсутствуют, `data_incomplete: true` |
| data/build_models.py | 98 | `# TODO уточнить` (deck_sheathing для П) | Данные отсутствуют, `data_incomplete: true` |
| data/build_models.py | 99 | `# TODO уточнить для Сибири` (warranty для П) | Региональные варианты |

**FIXME:** 0 | **HACK:** 0

---

## 5. Секреты и чувствительные данные

| Что | Где | Оценка |
|-----|-----|--------|
| Контакт менеджера (ФИО, телефон, email) | data/managers.json | OK — внутренний инструмент |
| Путь LibreOffice `C:\Program Files\...` | tests/e2e/helpers/docx_to_png.py:22 | OK — fallback в тестах, после env var и shutil.which() |
| API-ключи, пароли, токены | — | Не найдено ✅ |

---

## 6. Размер файлов (лимит ≤200 строк)

| Файл | Строк | Статус |
|------|-------|--------|
| generators/make_template.py | 772 | ⚠️ Утилита генерации шаблона |
| generators/test_generate.py | 283 | ⚠️ Тестовая утилита |
| ui/payment_section.py | 267 | ⚠️ |
| generators/kp_generator.py | 264 | ⚠️ |
| spec_builder.py | 249 | ⚠️ |
| ui/options_section.py | 233 | ⚠️ |
| term_days.py | 212 | ⚠️ |
| pricing.py | 205 | ⚠️ |
| Остальные 15 файлов | ≤194 | ✅ |

---

## 7. Рекомендации

| # | Действие | Приоритет | Усилие |
|---|----------|-----------|--------|
| 1 | Тесты: `calc_default_deck_mm`, `fmt_rub`, `fmt_int_spaces`, `pluralize` | HIGH | 30 мин |
| 2 | ~~`percent_to_retail` — удалить или покрыть тестом~~ | ~~MEDIUM~~ | ✅ Тест добавлен |
| 3 | Строки "22%" → `f"{VAT_RATE*100:.0f}%"` (6 мест) | LOW | 15 мин |
| 4 | spec_builder.py (249 строк) — рассмотреть разбивку | LOW | 20 мин |

---

## Итог

| Категория | Результат |
|-----------|-----------|
| Захардкоженные значения | ✅ Централизованы в config.py |
| Тестовое покрытие | ⚠️ 83.7% (7 функций без тестов) |
| Мёртвый код | ✅ 0 (ошибка аудита исправлена) |
| TODO/FIXME/HACK | ✅ 3 TODO в data/, 0 в коде |
| Секреты | ✅ Не найдено |
| Импорты | ✅ Чистые |
| Безопасность | ✅ Нет уязвимостей |

**Статус: готов к Production Trial.** Критических блокеров нет. Рекомендации #1-2 желательно закрыть до начала пробной эксплуатации.
