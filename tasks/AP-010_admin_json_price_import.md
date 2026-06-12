# AP-010 — Validate + diff + download загруженного прайса

- **task_id:** AP-010
- **Status:** planned
- **Phase:** 2 (Minimal admin UI)
- **Size:** medium
- **Depends on:** AP-004, AP-013, AP-008
- **Agent safety level:** `requires_human_review_after`

> Изменено в ревью: было «импорт JSON в draft price list в БД» (зависело от
> storage AP-005). Переописано как **semi-manual file-based** сценарий: загрузить
> → валидировать → показать diff → отдать проверенный файл на скачивание. БД нет.
> Запись в `data/` НЕ выполняется — файл в git кладёт человек руками.
> Гейт: Фаза 2 (UI), после v2.1.

## Goal

Дать в админке безопасный сценарий подготовки нового прайса без БД и без
авто-записи: пользователь загружает подготовленный JSON, система валидирует его
(AP-004), показывает diff с текущим `data/prices.json` (AP-013) и предлагает
скачать проверенный файл.

## Business value

Это и есть первый практический результат админки: безопасно проверить и сравнить
новый прайс, ничего не сломав. Человек сам решает, заменить ли
`data/prices.json` (через git). Никакого риска авто-перезаписи или рассинхрона с
расчётом.

## Context

- Текущий прайс — `data/prices.json` (`src/data_loader.load_prices()`).
- Валидатор — `src/admin/price_validator.py` (AP-004).
- Diff — `src/admin/price_diff.py` (AP-013).
- Нормализатор — `src/admin/price_normalizer.py` (AP-003).
- Страница-хост — `src/pages/3_Админка.py` (AP-008).
- Streamlit: `st.file_uploader` для загрузки, `st.download_button` для отдачи
  проверенного файла.

## Affected files

- `src/pages/3_Админка.py` (подключить раздел)
- `docs/admin_panel_status.md`

## New files

- `src/admin/price_upload_view.py` (render + сервисная логика сценария)
- `tests/admin/test_price_upload_view.py`
- фикстуры: валидная и невалидная копии прайса (в `tests/admin/fixtures/`)

## Allowed changes

- Создать раздел загрузки/валидации/diff/скачивания и тесты.
- Подключить раздел на страницу админки.
- Обновить статус AP-010.

## Forbidden changes

- НЕ писать в `data/prices.json` и любые `data/`-файлы.
- НЕ писать в БД (storage прайсов появится в Фазе 3).
- НЕ менять расчёт цен, snapshot, КП, Договор.
- НЕ активировать ничего автоматически.

## Implementation steps

1. Раздел: `file_uploader` → распарсить JSON → нормализовать (AP-003) →
   валидировать (AP-004).
2. Если есть error — показать список ошибок (item/field/message), download
   заблокировать.
3. Если ошибок нет — показать diff с текущим `data/prices.json` (AP-013:
   added/removed/changed) и `download_button` с проверенным JSON.
4. Явная подпись: «файл не сохраняется автоматически; чтобы применить — положите
   его в `data/prices.json` через git».
5. Сервисную логику вынести из render так, чтобы её можно было тестировать без
   Streamlit-рантайма.
6. Тесты: валидная фикстура → есть diff + разрешён download; невалидная →
   структурированные ошибки, download заблокирован; копия текущего прайса →
   пустой diff.
7. Обновить статус AP-010 (`human_review: pending`).

## Tests

- `rtk python -m pytest tests/admin/test_price_upload_view.py -q`.
- `rtk python -m pytest tests/ -q` — зелёный.

## Manual verification

- Открыть «Админка» → загрузить копию `data/prices.json` → diff пустой, download
  доступен. Загрузить испорченную копию → видны ошибки, download заблокирован.
- Подтвердить, что `data/prices.json` на диске не изменился.

## Done criteria

- Импорт никогда не пишет в `data/` и БД.
- Невалидный прайс не даёт скачать/применить.
- Diff с текущим прайсом виден; проверенный файл скачивается.
- В UI явно сказано, что применение — ручное (git).

## Stop condition

Один commit (`feat: безопасная проверка и сравнение загруженного прайса`),
пометить `human_review: pending`, краткий отчёт, **стоп**. Фаза 3 (БД) — только по
команде пользователя и после закрытия v2.1.

## Risks

- Большой JSON/кодировка в uploader — показывать понятную ошибку парсинга.
- Соблазн «сразу сохранять» — запрещено: запись в `data/` только человеком.
