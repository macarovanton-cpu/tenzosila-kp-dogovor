# Review Фазы 1 админ-панели прайса

Статус: **review пройден, R1 resolved отдельным fix-commit.** Можно переходить
к Фазе 2 (AP-008) с учётом гейта v2.1.

Дата: 2026-06-12. Ветка: `feature/admin-panel-phase-1`.
Ревьюер: senior engineer (Claude).

## Итог

Фаза 1 (AP-000, AP-003, AP-004, AP-013, AP-009) выполнена корректно и
безопасно. Весь код в `src/admin/` — read-only, изолирован от рантайма
(ни `app.py`, ни pricing, ни генерация КП, ни договор, ни Supabase его не
импортируют — проверено grep'ом, импорты только внутри `src/admin/`).
Документация формата совпадает с реальным `data/prices.json`. Тесты зелёные.

Явных ошибок, требующих правки кода, **не найдено**. После review отдельно
закрыт риск R1 по семантике срока действия прайса.

## Что проверено

### 1. Документация формата (`docs/price_format.md`) vs `data/prices.json`
Сверено фактически (версия прайса `0.4`):

| Параметр | Документация | Реальные данные | Совпало |
|---|---|---|---|
| models | 45 | 45 | да |
| options | 65 | 65 | да |
| `A_retail_and_dealer` | 20 | 20 | да |
| `B_retail_only` | 36 | 36 | да |
| `C_manual_range` | 4 | 4 | да |
| `UNKNOWN` (нет `price_class`) | 5 | 5 | да |
| `on_request: true` | 1 | 1 (`canopy_turnkey_24`, класс B) | да |
| `data_incomplete` | 4 модели линейки П-80 | `vesta-п-80-{18,20,22,24}` | да |
| НДС | 22% | `_meta.vat_note` = «Все цены с НДС 22%…» | да |
| дилер РФ | retail × 0.92 (для UNKNOWN — синтетика) | `vat_note`: «Дилер РФ = розница × 0.92» | да |

Состав `_meta`, поля моделей/опций и классы цен описаны точно. У моделей нет
поля `label` — документация этого и не утверждает, нормализатор корректно
подставляет `model_id`.

### 2. Нормализатор (`price_normalizer.py`)
Плоский `PriceItem`, модели и опции в едином формате. Корректно: `None`-цены,
кириллические ключи, `raw_payload` сохраняется целиком, отсутствующий
`price_class` → `UNKNOWN`. Замечаний нет.

### 3. Валидатор (`price_validator.py`)
Структурные issue без short-circuit, уровни error/warning. По классам:
A требует retail+dealer, B — retail, C — range_min/max и порядок границ,
UNKNOWN — retail (под синтетическую дилерскую границу), `on_request`
пропускается, `data_incomplete` → warning. На реальном прайсе: **0 errors,
4 warnings** (4 модели П-80) — совпадает с заявленным.

### 4. Diff версий (`price_diff.py`)
Идентичность по `(item_type, key)`; added/removed/changed; значимые поля —
`price_retail`, `price_dealer_ru`, `price_class`, `range_min`, `range_max`,
`on_request`. Несущественные (label, applies_to, raw_payload) игнорируются.
Логика корректна. Ограничения — см. R2.

### 5. Read-only диагностика (`price_diagnostics.py`)
CLI `python -m src.admin.price_diagnostics` отрабатывает, ничего не пишет.
Считает counts по классам, on_request, валидацию, нулевые цены, модели без
цены, `valid_from`/`valid_until`/expired. После R1-fix на реальном прайсе:
errors 0, warnings 5, expired no, zero_price_items 0, models_without_price 0.

### 6. Тесты (`tests/admin/`)
21 тест, все проходят (`pytest tests/admin -q` → 21 passed). Покрыты:
нормализация (counts, классы, маппинг моделей/опций, manual_range/unknown,
on_request), валидатор (нет ошибок на проде, сбор ошибок без short-circuit,
on_request, data_incomplete warning, UNKNOWN), diff (равенство, add/remove,
изменения значимых/несущественных полей), диагностика (counts, expiry semantics,
нулевые цены, модели без цены, формат). Фикстура `prices` грузит реальный
`data/prices.json`. Покрытие для Фазы 1 — достаточное.

## Найденные риски

### R1 — RESOLVED: семантика `is_expired` без `valid_until` (medium)
`valid_from` — это дата **начала** действия, а не окончания. Бизнес-решение
принято: если в `_meta` нет `valid_until`, диагностика не имеет права считать
прайс просроченным.

Реализовано отдельным fix-commit:

- `is_expired` считается только от `_meta.valid_until`;
- если `valid_until` отсутствует, `is_expired = false`;
- отсутствие `valid_until` добавляет warning `valid_until_missing`;
- если `valid_until < today`, `is_expired = true`;
- если `valid_until >= today`, `is_expired = false`.

На текущем `data/prices.json` (`valid_from = 2026-03-01`, `valid_until`
отсутствует): `expired: no`, errors 0, warnings 5 (4 `data_incomplete` +
1 `valid_until_missing`).

### R2 — diff не отслеживает `discount_pct` и `label` (low)
`discount_pct` не входит в `SIGNIFICANT_FIELDS`: смена дилерской скидки
(например 8 → 10 %) в diff не покажется. Денежный эффект частично ловится через
`price_dealer_ru`, который отслеживается. Изменение `label` тоже не видно.
Приемлемо для Фазы 1; учесть при доработке diff в Фазе 2, если потребуется.

### R3 — валидатор не отвергает неизвестный/опечатанный `price_class` (low)
Опечатка в классе (например `B_retail_only`) попадёт в fallback-ветку и будет
проверена как UNKNOWN (только retail), без сигнала. Для read-only Фазы 1
безопасно; добавить явную проверку допустимых классов можно в Фазе 2.

## Скрытый риск для текущего КП/договора
**Не обнаружен.** `src/admin/` не импортируется рантаймом, `data/prices.json`
не изменялся, в БД ничего не писалось, миграции не применялись. Фаза 1 не может
повлиять на расчёт цены, генерацию КП или договор.

## Нужны ли правки
R1 закрыт. R2/R3 — некритичные заметки на будущее.

## Можно ли переходить к Фазе 2
**Да**, при двух условиях:
1. Соблюдён гейт v2.1: по `docs/STATUS.md` v2.1 ещё открыт, а Фаза 2 желательно
   стартует после его закрытия.
2. AP-008/AP-015 остаются UI-задачами с `requires_human_review_after`.

## Что обязательно проверить человеку перед AP-008
1. **Гейт v2.1** — подтвердить, что v2.1 закрыт (или осознанно стартовать Фазу 2
   параллельно).
2. **Изоляция UI** — AP-008 впервые добавляет Streamlit-страницу; убедиться, что
   она не трогает существующие экраны КП/договора и не пишет в `data/`/БД
   (по `docs/admin_panel_agent_rules.md` — read-only, human review after).
3. **Источник прайса для UI** — AP-015/AP-010 должны читать тот же
   `data/prices.json` через существующий loader, без второго пути загрузки.

## Ограничения для Фазы 2
- UI строго read-only: validate / diff / download, **без записи** в `data/` и БД.
- Не трогать pricing logic, генерацию КП, договор, Supabase, миграции.
- Не убирать JSON-источник прайса; не плодить второй путь загрузки.
- Новая страница не должна влиять на существующие экраны (изоляция роутинга).
- Переиспользовать `src/admin/` как есть; менять — только вместе с тестами и
  под human review.
