# NEXT_TASK → HUMAN_REVIEW_BEFORE_PHASE_2

Фаза 1 (Foundation) завершена:

- AP-000 — документация формата прайса;
- AP-003 — canonical model + normalizer прайса;
- AP-004 — валидатор формата прайса;
- AP-013 — diff двух версий прайса;
- AP-009 — read-only диагностика прайса.

## Что дальше

Перед стартом Фазы 2 нужен human review результатов Фазы 1.

Первая задача Фазы 2 после review и с учётом гейта v2.1:
**AP-008 — Shell страницы админки**.
Полное описание: `tasks/AP-008_admin_page_shell.md`.

## Почему не стартовать AP-008 автоматически

- Фаза 2 впервые добавляет Streamlit-UI.
- По `docs/admin_panel_agent_rules.md` UI-задачи требуют human review after.
- По `docs/admin_panel_task_breakdown.md` Фаза 2 желательно начинается после
  закрытия v2.1; в `docs/STATUS.md` v2.1 ещё открыт.

## Для human review

Проверить:

- `docs/price_format.md`;
- `src/admin/price_models.py`;
- `src/admin/price_normalizer.py`;
- `src/admin/price_validator.py`;
- `src/admin/price_diff.py`;
- `src/admin/price_diagnostics.py`;
- `tests/admin/`.

CLI-проверка диагностики:

```bash
rtk python -m src.admin.price_diagnostics
```
