# NEXT_TASK → AP-010_AFTER_HUMAN_REVIEW_AP-015

AP-015 выполнена: в read-only админку добавлена панель диагностики текущего
прайса и правил ценовых классов A/B/C/UNKNOWN/on_request.

## Перед следующей задачей

Нужен human review AP-015, потому что это Streamlit-UI с уровнем безопасности
`requires_human_review_after`.

Проверить вручную:

- `streamlit run src/app.py`;
- открыть страницу «Админка»;
- убедиться, что видны counts, metadata, errors, warnings и правила классов;
- сверить НДС 22%, `MAX_COEFF`, `MIN_COEFF_B`,
  `SYNTHETIC_DEALER_FACTOR` с `src/config.py`;
- убедиться, что страница read-only и не предлагает запись в `data/` или БД;
- убедиться, что «Коммерческое предложение» и «Договор» открываются как раньше.

## Следующая задача после review

**AP-010 — Validate + diff + download загруженного прайса.**
Полное описание: `tasks/AP-010_admin_json_price_import.md`.

Не реализовывать AP-010 без отдельной команды пользователя.
