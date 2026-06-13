# Редизайн определения foundation_scope + связка clauses

**Дата:** 2026-06-13
**Статус:** спецификация, к реализации (opus-plan сессия)
**Закрывает:** P1 contractor_supervised, P2 items-vs-override, P2 зимний чекбокс,
P2 ОРИОН-опоры, баг «нет фундамента → пустые обязательства»

---

## Принцип

Отсутствие позиции «Фундамент» в КП — НЕ «ноль обязательств». Весы всегда
стоят на основании. Если его не строит Тензосила — его готовит Заказчик.
Дефолт при отсутствии сигнала = `customer_builds`, не `none`.

Пандусы есть в КП почти всегда — для определения scope НЕ используются.

---

## Определение scope (приоритет сверху вниз)

1. Позиция «Фундамент» (стройка Тензосилой) → `contractor_full` /
   `contractor_with_materials` (по наличию позиции материалов заказчика).
2. Позиция «Курирование строительства фундамента» → `contractor_supervised`.
3. Позиция «Рама» → `rama` (Заказчик готовит основание под раму).
4. Ничего из 1–3 → выбор менеджера, дефолт `customer_builds`.

---

## Видимый выбор (выпадающий список) — только в случае 4

Список реально работает (override побеждает), значения:
- **Заказчик строит фундамент** (дефолт) → `customer_builds`
- **Готовый фундамент Заказчика** → `existing_foundation` (новый scope, ноль
  обязательств по фундаменту + оговорка в договоре)

Список скрыт / неактивен если scope определён автоматически (случаи 1–3).

---

## Гард (противоречие)

Позиция «Фундамент» в КП + ручной выбор «Заказчик строит» = противоречие
(нельзя одновременно продавать стройку и отдать её заказчику).
→ warning на странице Договор, генерацию не блокировать жёстко, но
предупредить явно.

---

## Изменения в clauses.yaml

### contractor_supervised — НЕ дублировать клозы заказчика

Расширить `applies_when` существующих `customer_builds`-клозов:
- `customer_builds_foundation_per_spec`:
  `foundation_scope in ("customer_builds", "contractor_supervised")`
- `customer_provides_foundation_photos`: то же

Заказчик в обоих случаях строит сам по Приложению №1 — тексты идентичны,
дублирование не нужно.

### Новый supplier-клоз курирования

```yaml
- id: supplier_supervises_foundation_construction
  section: obligations_supplier
  order: 15
  applies_when: 'foundation_scope == "contractor_supervised"'
  text: |
    Подрядчик направляет специалиста строительной бригады для выполнения
    работ по курированию строительства фундамента Весов (Приложение №1 к
    настоящей Спецификации) в течение 15 (пятнадцати) рабочих дней с момента
    поступления предоплаты в соответствии с п.2.1 настоящей Спецификации, по
    предварительному письменному согласованию Сторон.
```

Источник формулировки: реальная спецификация из корпуса combined_1.md.

### Новый scope existing_foundation + оговорка

```yaml
- id: scales_for_existing_foundation
  section: special_conditions
  order: 5
  applies_when: 'foundation_scope == "existing_foundation"'
  text: |
    Весы изготавливаются под существующий фундамент Заказчика. Размеры
    фундамента согласованы Сторонами до начала производства Весов.
    Обязательства по устройству фундамента у Сторон не возникают.
```

### ОРИОН-опоры by_contractor без стройки фундамента

Сейчас `supplier_dispatches_construction_team_with_orion_poles` требует
`foundation_scope in ("contractor_full", "contractor_with_materials")`.
При `rama` или `customer_builds` + `orion_poles_scope == "by_contractor"`
обязательство по опорам выпадает — оплаченная работа без клоза в договоре.

Решение: добавить отдельный supplier-клоз для случая «опоры by_contractor
без фундамента Тензосилы». Точный `applies_when` и текст уточнить в
реализации по коду (возможно объединить с существующим через расширение
условия).

---

## Зимний чекбокс (2_Договор.py)

Гейтить по `foundation_scope`:
- Виден и активен только при `foundation_scope in ("contractor_full", "contractor_with_materials")`
- Иначе скрыт полностью

Бетон льёт только Тензосила → надбавка осмысленна только тогда.

---

## Обновление DSL-шапки clauses.yaml

Добавить в комментарий-шапку два новых значения:
```
#   foundation_scope:    "none" | "customer_builds" | "contractor_full"
#                      | "contractor_with_materials" | "rama"
#                      | "contractor_supervised" | "existing_foundation"
```

---

## Тесты (добавить в реализацию)

Параметризованный перебор scope → assert:

| Комбинация | Проверка |
|---|---|
| `contractor_supervised` | supplier-клоз курирования присутствует + customer-клозы стройки присутствуют |
| `existing_foundation` | оговорка присутствует, customer_builds-клозов нет |
| `customer_builds` | customer-клозы стройки присутствуют, оговорки нет |
| зимний флаг при F ∉ {cf, cwm} | UI не позволяет выставить (скрыт) |
| ОРИОН опоры by_contractor + любой F | supplier-клоз по опорам присутствует |
| оплаченная позиция (фундамент/курирование) | ≥1 соответствующий клоз в договоре |

---

## Файлы которые затронет реализация

- `data/clauses.yaml` — новые клозы, расширение applies_when
- `src/contracts/clauses_context.py` — логика определения scope, дефолт customer_builds
- `src/contracts/from_kp.py` — маппинг contractor_supervised (уже есть), existing_foundation (новый)
- `src/pages/2_Договор.py` — видимый список (только при F=auto), гард, зимний гейт
- `tests/contracts/` — параметризованный тест-перебор
