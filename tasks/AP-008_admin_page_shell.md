# AP-008 — Shell страницы админки

- **task_id:** AP-008
- **Status:** planned
- **Phase:** 2 (Minimal admin UI)
- **Size:** small
- **Depends on:** AP-000
- **Agent safety level:** `requires_human_review_after`

> Гейт: задача из Фазы 2 (Streamlit-UI). Не начинать до закрытия v2.1
> (см. `docs/STATUS.md`).

## Goal

Добавить третью Streamlit-страницу «Админка» — безопасную read-only заглушку с
местом под будущие разделы, не трогая КП и договор.

## Business value

Каркас навигации, на котором дальше маленькими шагами растёт read-only админка
(AP-015) и безопасный сценарий проверки прайса (AP-010). Сам по себе ничего не
меняет в расчётах.

## Context

- Роутер — `src/app.py`; сейчас две страницы:
  `src/pages/1_Коммерческое_предложение.py`, `src/pages/2_Договор.py`.
- Streamlit multipage: файл в `src/pages/` автоматически попадает в навигацию.
- Ролей/авторизации в проекте нет — страница будет видна всем. Для read-only
  заглушки это допустимо и должно быть явно отмечено на странице.

## Affected files

- `src/app.py` (только если требуется регистрация/навигация; не менять логику КП)
- `docs/admin_panel_status.md`

## New files

- `src/pages/3_Админка.py`
- `src/admin/__init__.py` (если ещё не создан в AP-003)
- `tests/test_admin_page.py` (AppTest smoke)

## Allowed changes

- Создать страницу-заглушку и smoke-тест.
- Минимально тронуть `src/app.py`, только если без этого страница не появляется.

## Forbidden changes

- НЕ менять `src/pages/1_Коммерческое_предложение.py` и
  `src/pages/2_Договор.py`.
- НЕ менять расчёт КП, snapshot, генерацию.
- НЕ добавлять mutable-операции (никаких записей в `data/`/БД).

## Implementation steps

1. Создать `src/pages/3_Админка.py`: заголовок, явное предупреждение «read-only,
   mutable-функции появятся позже», заготовка под разделы.
2. Убедиться, что КП и Договор остаются в навигации.
3. AppTest smoke: приложение стартует, страница админки доступна.
4. Обновить статус AP-008 (`human_review: pending`).

## Tests

- `rtk python -m pytest tests/test_admin_page.py -q`.
- `rtk python -m pytest tests/ -q` — зелёный.

## Manual verification

- `streamlit run src/app.py` → открыть «Админка», увидеть заглушку; КП и Договор
  открываются как раньше.

## Done criteria

- Страница «Админка» видна и read-only.
- На странице есть предупреждение про будущие mutable-функции и отсутствие ролей.
- КП и Договор не затронуты.

## Stop condition

Один commit (`feat: добавить страницу-заглушку админки`), пометить
`human_review: pending`, краткий отчёт, **стоп**. AP-015 не начинать.

## Risks

- Без ролей страница видна всем — допустимо только для read-only заглушки, явно
  отметить на странице и в `notes`.
