# NEXT_TASK → AP-003

Следующая задача для реализации: **AP-003 — Canonical model + normalizer прайса**.
Полное описание: `tasks/AP-003_price_contracts_normalizer.md`.

- **Phase:** 1 (Foundation)
- **Agent safety level:** `safe_for_autonomous_agent` (можно автономно/ночью)
- **Depends on:** AP-000
- **Размер:** medium

## Почему именно она первая

- AP-000 завершена: формат `data/prices.json` описан в `docs/price_format.md`.
- Нормализатор даёт единый плоский формат для следующих задач Фазы 1:
  валидатора, diff и read-only диагностики.
- Задача остаётся локальной и безопасной: без БД, UI, расчёта цен и записи в
  `data/`.

## Что сделать (кратко)

Добавить canonical-модели price item и нормализатор `data/prices.json` в плоский
список без потери исходных полей. Покрыть unit-тестами counts и распределение
классов.

Полные шаги, allowed/forbidden changes, tests, done criteria и stop condition —
в `tasks/AP-003_price_contracts_normalizer.md`.

## После AP-003

По текущей инструкции пользователя в этом запуске можно перейти к следующей
задаче Фазы 1 только после успешных тестов и отдельного commit.

Порядок Фазы 1:
`AP-000 → AP-003 → AP-004 → AP-013 → AP-009`.
