# Инвентаризация Streamlit-проекта перед переписыванием (FastAPI + Next.js)

Снято с `main` на коммите `9098052`, 2026-10-25. Ссылки `файл:строка` даны на этот коммит. «Не установлено» — сведений нет в репозитории или нужна проверка вживую.

## 1. Сценарии

Роутер: три страницы — `src/app.py:8-15`.

### 1.1 «Коммерческое предложение» (`src/app_pages/1_Коммерческое_предложение.py`)

Порядок рендера: `init_state` → применение отложенного восстановления КП → блок «Открыть прошлый КП» → шапка → модель/оборудование/конструкция (левая колонка) → опции (правая) → спецификация → оплата → валидация → сайдбар (`…предложение.py:47-112`).

| Блок | Что вводит менеджер | Виджет / ограничения | Ссылка |
|---|---|---|---|
| Открыть прошлый КП | поиск по контрагенту (пусто — последние 50) → «Показать»; выбор → «Загрузить выбранный»; или номер → «Найти» | сеть только по кнопке; восстановление применяется на следующем run до виджетов | `src/ui/load_kp_section.py:72-122`, `…предложение.py:61-64`, `src/storage/kp_restore.py:243-252` |
| Предупреждение о перезаписи | — | если номер КП совпадает с загруженным: «Смените номер … иначе оригинал будет перезаписан» | `src/ui/load_kp_section.py:61-69` |
| Шапка | номер КП, дата КП, срок действия КП (1–90 дн., дефолт 15), срок исполнения (min..120 раб. дн.), менеджер (select из managers.json), название клиента | срок исполнения по умолчанию = сумма дефолтов ролей; ручная правка ставит флаг `total_term_days_user_set`; если состав изменился и ручное значение < минимума — поднимается до минимума | `src/ui/header.py:17-98` |
| Модель | линейка (С/СЛ/Ф/ФЛ/П), макс. нагрузка, длина — каскад, варианты только из ключей prices.json; ширина 3.0/3.5/4.0 м; чекбокс «Двухдиапазонные весы» (недоступен, если у модели нет `dual_range`); цена модели (number_input); количество весов 1–20 | смена линейки/нагрузки/длины сбрасывает опции, цену, конструкцию, ручные правки спецификации, диапазон, ручной срок; смена ширины сбрасывает только цену модели и её price-override | `src/ui/model_section.py:27-225`, `src/state.py:118-158`, `src/filters.py:23-61` |
| Карточка ТХ | — (read-only) | тип платформы, секции, датчики, масса, балка, настил, мин. нагрузка, e, осевые нагрузки; предупреждение `data_incomplete` | `src/ui/model_section.py:144-171` |
| Оборудование | гарантия (12/18/24/36/48/60 мес., дефолт из line_defaults), длина кабеля 5–100 м шаг 5, датчик, индикатор (из `equipment_defaults.*.alternatives`) | — | `src/ui/equipment_section.py:13-73` |
| Конструкция | профиль, кол-во профилей, центральная балка и их кол-во (недоступны для колейной), настил 6/8/10, подшивка 3/4/5 | на цену не влияет, только текст ТХ в КП; дефолты из модели/линейки | `src/ui/construction_section.py:10-106` |
| Опции и услуги | по 11 блокам (`OPTION_BLOCKS_ORDER`): чекбокс включения; цена (number_input в коридоре класса); количество 1–20 только для пандусов и блока фундамента; для фундаментов 1–3 и курирования/стройработ — «Тип фундамента» (пандусный/приямок/монолитная_плита); для бытовки — «Габариты»; для монтажа — чекбокс «Шеф-монтаж»; для поверки — радио «Подрядчик/Заказчик» (Заказчик → цена 0) | опция `on_request` показывается заблокированной; пакеты ОРИОН взаимоисключающие (включение одного снимает остальные); выключение опции чистит её override и сиротский `orion_install` | `src/ui/options_section.py:77-252`, `src/config.py:43-116` |
| Произвольные позиции | «+ добавить позицию» → название, тип работ (Прочее/Монтаж), цена 0–100 000 000 шаг 1000, «×» удалить | подсказка, если имя похоже на монтаж, а тип «Прочее»; позиция с пустым именем или ценой 0 не попадает в спецификацию | `src/ui/options_section.py:254-325`, `src/spec_builder.py:189-201` |
| Спецификация | правка «Кол-во» (≥1) и «Цена» по каждой строке | правка пишется в `spec_items_overrides[item_key]`, строка помечается ✏️; движение виджета цены чистит price-override | `src/ui/specification_section.py:10-111`, `src/ui/options_section.py:355-363` |
| Условия оплаты | пресет (6 шт.) и его параметры: v1 — предоплата 1–99 %, срок аванса 1–30; v2 — предоплата 1–98, перед отгрузкой 0–99, срок; v3 — срок 1–90, точка отсчёта; prepay_100 — срок; split_by_items — предоплата/постоплата по активным группам (доставка: предоплата заморожена 0) и срок; custom — свободный текст | превью под блоком и в сайдбаре | `src/ui/payment_section.py:18-255` |
| Сайдбар | — | ИТОГО с НДС / без НДС / НДС 22 %; при qty>1 — цена за 1 шт; «Действует до»; «Срок изготовления … раб. дн.»; ошибки и предупреждения; превью оплаты; кнопка «Сгенерировать КП» | `src/ui/sidebar.py:17-101` |

| Действие | Условие | Результат | Ссылка |
|---|---|---|---|
| «Сгенерировать КП» | нет errors валидации и спецификация непуста; DOCX строится на каждом рендере сайдбара | `st.download_button` с DOCX; имя `{номер}_{клиент}_{модель}_{ГГГГ-ММ-ДД}.docx` (ОПФ и запрещённые символы вырезаются) | `src/ui/sidebar.py:121-190`, `src/generators/kp_generator.py:283-317` |
| Сохранение КП в базу | только при клике на скачивание; ошибка базы — warning, генерацию не блокирует | upsert в `kps` по `kp_number` | `src/ui/sidebar.py:104-118`, `:163-164` |
| Срок меньше минимума | `TermDaysTooSmallError` | кнопка заблокирована, текст с разбивкой минимума | `src/ui/sidebar.py:165-181` |

Валидация КП (`src/validation.py:23-152`): errors — пустой номер КП, пустой клиент, менеджер не выбран/не найден, модели нет в прайсе, цена модели < `dealer_ru`, включённая опция «под запрос», для split — сумма % в активной группе ≠ 100, custom без текста, v1 предоплата вне 1–99 или срок < 1, v2 предоплата < 1 / перед отгрузкой < 0 / сумма > 99 / срок < 1, v3 срок < 1, prepay_100 срок < 1. Warnings — `data_incomplete` модели, опция с ключом `*_22` (цена — среднее 20/24 м), пандусы `ramp_set_f_s` на линейке П.

### 1.2 «Договор» (`src/app_pages/2_Договор.py`)

| Шаг | Что вводит менеджер | Что происходит | Ссылка |
|---|---|---|---|
| Источник данных | радио «Из базы (по номеру)» / «Из PDF файла (старый КП)» | — | `:438-447` |
| A. КП из базы | выбор из 50 последних КП (метка: номер — клиент — модель — сумма) или номер + «Найти» (кнопка заблокирована, пока выбран пункт дропдауна) | полный снапшот догружается отдельно, кэш по (номер, updated_at); загрузка коммитится в state только целиком и только для нового `номер:updated_at`; сразу засеваются строки оплаты по пресету КП; при недоборе оплаты (страж A9) — `st.error`, генерация останется заблокирована | `:455-566`, `:303-313`, `src/contracts/kp_load.py:12-33` |
| B. Старый КП из PDF | PDF КП + карточка контрагента (PDF/DOCX) → «Извлечь данные через AI» | LLM-извлечение (раздел 7), производные поля директора дописываются только в пустые; скан без текста → ошибка | `:568-602` |
| Реквизиты из файла/текста | файл DOCX/PDF → «Распознать из файла»; или вставка текста → «Распознать»; «Очистить реквизиты» | regex-парсер (раздел 7); поля, правленные вручную, повторное распознавание не перетирает; производные (полное наименование, инициалы, РП) перезаписывают непустое значение только при изменении первичного поля | `:612-712`, `src/contracts/state.py:153-169` |
| Реквизиты заказчика | 19 полей `ЗАКАЗЧИК_*` + пол директора (male/female; дефолт по отчеству) | пол → «действующего/действующей» | `:87-107`, `:714-746` |
| Особые условия (только после загрузки данных) | основание под весы: при фундаменте/раме в позициях — только метка; при монтаже без фундамента — выбор «Заказчик строит фундамент» / «Готовый фундамент Заказчика»; без монтажа — ничего | предупреждение «Опоры ОРИОН без фундамента» + рекомендуемый текст | `:750-819`, `src/contracts/recommendations.py` |
| Зимний период | чекбокс (только если бетон льёт Подрядчик) + сумма удорожания (дефолт 200 000, шаг 1000) | при скрытии флаги сбрасываются | `:821-846` |
| Override-флаги | тип монтажа (Авто/Полный/Шеф/Без), кто организует поверку (Авто/Подрядчик/Заказчик/Без), опоры ОРИОН (Авто/Заказчик/Подрядчик — только при ОРИОН) | пишутся в `scope_overrides` | `:848-868` |
| Предпросмотр пунктов | — | первые 60 символов каждого пункта по разделам, общее число | `:870-883` |
| Позиции спецификации | таблица с добавлением/удалением строк: наименование, бакет (Оборудование/Фундамент/Монтаж и поверка), ед., кол-во, цена с НДС; «+ Добавить позицию» | сумма = кол-во × цена; бакет «Оборудование» → `scales` или `delivery`, если имя начинается с «доставка»; ошибка «позиции без бакета»; предупреждение, если имя похоже на монтаж/фундамент/поверку, а бакет «Оборудование» | `:886-946`, `:215-292` |
| Поля спецификации (режим B без позиций) | `СПЕЦ_*` из LLM, правятся вручную | — | `:109-139`, `:948-949` |
| Условия оплаты | «Заполнить по умолчанию»; таблица строк: тип, %, основа, объект, база, сумма (read-only), событие, дней, ед. дней | сумма пересчитывается из % и базы; текст пункта «2.N» показывается под таблицей | `src/ui/payment_lines_editor.py:265-334` |
| Приложения по фундаменту | «Авто-подбор» / «Без приложения» / конкретный файл строительного задания; чекбокс «Добавить контрольный лист (Приложение №2)», если лист существует | выбор пишется в `contract.attachments` | `:365-429`, `:955` |
| Параметры договора | тип документа «Спецификация»/«Поставка» (дефолт — автоопределение, пере-seed только при смене КП или авто-типа); номер договора; дата; адрес объекта монтажа; номер спецификации (дефолт «1»); «Срок действия договора до» — только для «Поставка» | — | `:963-1030`, `src/contracts/state.py:11-17` |
| «Сгенерировать договор и спецификацию» | — | заблокирована, если: нет данных спецификации или реквизитов, пуст номер договора, пуст адрес, есть errors реквизитов, нет строк оплаты (при наличии `specification`) | `:1038-1076` |
| Результат «Поставка» | — | один DOCX `Договор_поставки_{номер}_{заказчик}.docx` | `:1135-1160` |
| Результат «Спецификация» | — | два DOCX `Договор_{номер}_{заказчик}.docx` и `Спецификация_{номер}_{заказчик}.docx`; к Спецификации приклеиваются приложения; warning, если Спецификация ссылается на Приложение №1, а файл не приложен | `:1161-1227` |
| Скачивание / «Сгенерировать заново» | — | кнопки скачивания; сброс `generated` | `:1229-1256` |

Ошибки реквизитов и «Не заполнены условия оплаты» выводятся в сайдбар (`:1047-1068`). Генерация пишет файлы в `output/contracts/` (`:78`, `:1085`).

### 1.3 «Админка» (`src/app_pages/3_Админка.py`)

| Блок | Что делает | Ссылка |
|---|---|---|
| Баннер | «Разграничение прав доступа пока не реализовано — страница видна всем» | `3_Админка.py:16-20` |
| Битый prices.json | ошибка + кнопка отката из `prices.backup.json` | `:22-34` |
| Состояние прайса | метаданные, структура, проблемы цен, правила классов (read-only) | `:36`, `src/admin/price_overview_view.py:68-288` |
| «Откатить на предыдущую версию» | подтверждение → копия бэкапа в prices.json, сброс черновика обновления, сброс кэша `load_prices` | `:38-64`, `src/admin/price_write_service.py:76-92` |
| Проверка загруженного prices.json | загрузка JSON → валидация + diff → «Скачать проверенный JSON» (запись не делает) | `:66`, `src/admin/price_upload_view.py:14-56` |
| Обновление прайса | «Загрузить из PDF» (дилерский + розничный PDF → «Прочитать прайс») или «Редактировать текущий» → таблица → «Проверить» → блокеры/предупреждения + «Что изменится» → «Применить новый прайс» (бэкап → three-way merge → атомарная запись → сброс кэша) | `src/admin/price_update_view.py:173-433`, `src/admin/price_write_service.py:46-130` |
| Удаление строк | не применяется: предупреждение «позиции, отсутствующие в снимке, переносятся из текущего прайса» | `src/admin/price_update_view.py:332-338` |

## 2. Справочники

| Файл | Назначение | Структура | Пример записи | Кто читает |
|---|---|---|---|---|
| `data/models.json` | ТХ моделей ВЕСТА, оборудование по умолчанию, дефолты линеек | `_meta`, `equipment_defaults{sensor,indicator}` (`default`, `default_temp_range_c`, `alternatives[{id,label,temp_range_c,is_default}]`), `line_defaults{С,СЛ,Ф,ФЛ,П}`, `models[73]` | `models[0]` (`data/models.json:283`): `id "vesta-с-40-18"`, `full_name`, `line`, `max_load_t 40`, `length_m 18`, `width_m 3`, `sections 3`, `sensors_count 8`, `mass_kg`, `beam_profile`, `deck_default_mm`, `min_load_t`, `verification_division_kg`, `n_intervals`, `axle_loads_t{single,double,triple,quad}`, `data_incomplete`, `notes`, `dual_range{w1,w2:{max_load_t,min_load_t,e_kg,n}}`. `line_defaults.С` (`:164`): `platform_type`, `default_warranty_months`, `default_sensor`, `default_indicator`, `default_cable_length_m`, `underlining_mm(_min/_max)`, `center_reinforcement`, `longitudinal_beams_count`, `default_construction_type`, `default_center_beam_count` | `src/data_loader.py:23-26` → страница КП, `src/state.py:155`, `src/generators/kp_generator.py:126`, `2_Договор.py:522`; напрямую по относительному пути `src/contracts/spec_v2_filler.py:219` (ТТХ/комплект договора) |
| `data/prices.json` | розничные и дилерские цены моделей и опций, класс цены | `_meta`, `models{53}` (`retail`, `dealer_ru`, `dealer_discount_pct`, у 4 — `data_incomplete`), `options{89}`: `label`, `applies_to_lines`, `applies_to_lengths`, `price_retail`, `price_dealer_ru`, `discount_pct`, `price_class`, опц. `range_min/range_max` (12), `components{equipment,shef_montazh}` (10), `on_request` (1), `allow_customer_value` (1), `notes`, `dealer_note` | модель `vesta-фл-60-12` (`data/prices.json:26`): `retail 1140296, dealer_ru 1049072, dealer_discount_pct 8`. Опция `ramp_set_fl_sl` (`:297`): `label`, `applies_to_lines [ФЛ,СЛ]`, `applies_to_lengths [12..24]`, `price_retail 280000`, `price_dealer_ru 257600`, `price_class A_retail_and_dealer` | `src/data_loader.py:29-32` (кэш 1 ч) → КП, договор, админка; `src/admin/price_pdf_merge.py:15` (напрямую); запись — `src/admin/price_write_service.py:46-72` |
| `data/payment_terms.json` | пресеты оплаты, дефолтные %, тексты КП | `_meta`, `default_preset_id "split_by_items"`, `presets[6]`: `id`, `name`, `description`, `is_split`, `variant`, `default_percents`, `default_days`, `editable_days`, `body_template`; у split — `groups[4]{id,label,default_percents,editable_percent_keys,postpay_trigger,always_shown,shown_if}`; у v3 — `trigger_options[3]{id,label,text}`, `default_trigger_id`; у custom — `is_freeform`, `freeform_placeholder` | `v1_prepay_postpay` (`data/payment_terms.json:24-34`): `default_percents {prepay:50}`, `default_days 5`, `body_template "— Предоплата {prepay}% общей стоимости при подписании Договора ({days_phrase}).\n— Доплата {postpay}% …"` | `src/data_loader.py:35-38`; `src/payment_wording.py:32-35` (свой lru_cache, без сброса) |
| `data/options.json` | описания пакетов ОРИОН и фундаментов для UI | `_meta`, `pak_orion_packages[5]{id,name,description,components[],price_equipment,price_installation}`, `foundation_options[8]{id,name,applies_to_lines,description,prices_by_length}`, `delivery{note,is_negotiable}`, `verification{name,note,default_price,is_negotiable}` | `pak_orion_packages[0]` (`data/options.json:11`): `id orion_lite`, `components [ПО UniServer…, камеры, коммутатор]`, `price_equipment 135000`, `price_installation 110000` | только подпись под опцией в UI: `src/ui/options_section.py:409-438`. Цены отсюда не используются (`_meta.notes`) |
| `data/equipment_specs.json` | паспортные данные датчиков и терминалов для ТТХ/комплекта договора | `sensors[9]` (`manufacturer`, `model`, `registration_number`, `type`, `accuracy_class`, `n_max`, `max_load_options_t`, `temperature_min_c/max_c`, `ip_rating`, …, `additional_specs`), `terminals[4]` (`manufacturer`, `model`, `registration_number`, `max_sensors_count`, питание, `ip_rating`, `interfaces`, …), `extracted_at`, `source`, `source_count` | `sensors[0]` (`data/equipment_specs.json:2`): `Zemic DHM9B`, рег. № `55634-19`, `C3`, `-30…+40` | `src/contracts/spec_v2_filler.py:220`, `src/contracts/from_kp.py:454-469` |
| `data/managers.json` | менеджеры для шапки и колонтитула КП | `_meta`, `default_manager_id "makarov_av"`, `managers[]{id,full_name,position,phone,email,is_default}` | `data/managers.json:10-16` | `src/data_loader.py:47-50`, `src/ui/header.py:17-98`, `src/generators/kp_generator.py:127` |
| `data/clauses.yaml` | библиотека пунктов Спецификации (обязательства, особые условия) | комментарий-шапка с перечнем переменных DSL, `sections[4]{id,title,section_number}`, `clauses[35]{id,section,order,applies_when,text}` | `supplier_prepares_docs` (`data/clauses.yaml:43-48`): `applies_when 'verification_scope == "supplier"'` | `src/contracts/clauses_renderer.py:16`, `src/contracts/clauses_loader.py` (подробно — раздел 8) |
| `data/fundament/build_task/*.docx`, `data/fundament/control_sheet/*.docx` | строительные задания и контрольные листы — приложения к Спецификации | список и правило выбора — раздел 4 | — | `src/contracts/fundament_lookup.py` |
| `src/config.py` | константы | пути к справочникам (`:8-13`), `VAT_RATE 0.22` (`:16`), `DEFAULT_KP_VALID_DAYS 15` (`:20`), коэффициенты коридоров (`:23-30`), `LINES` (`:35`), `LENGTHS [18,20,22,24]` (`:36`, не используется), `OPTION_BLOCKS_ORDER` (`:43-55`), `BLOCK_LABELS` (`:58-70`), `BLOCK_KEY_PREFIXES` (`:73-108`), `QTY_ENABLED_BLOCKS` (`:111`), `UNIT_BY_BLOCK` (`:114-117`) | — | весь `src/` |
| `src/contracts/supplier.py` | реквизиты поставщика ООО «ТПК «Тензосила» | `SUPPLIER{ПОСТАВЩИК_*}` | `:8-23` | только `src/contracts/supply_filler.py:24`; в spec-шаблонах те же реквизиты статичным текстом (`supplier.py:3-5`) |
| `src/contracts/custom_work_types.py` | типы работ произвольных позиций | `WorkType(label, spec_id, scope, payment_group)`; активны `other`, `installation`; `foundation/verification/orion` закомментированы | `:21-33` | UI опций, `spec_builder`, `from_kp`, `snapshot_builder` |
| `src/contracts/prompts/*.txt` | системные промпты LLM | раздел 7 | — | `src/contracts/extractor.py:16-17` |
| `src/term_days.py` (константы) | дефолтные сроки ролей | `TERM_DAYS_DEFAULTS`: scales 20, orion 5, foundation 10, canopy 25, install 3, delivery 1, verification 1 | `:28-36` | КП, договор |
| `.streamlit/config.toml` | тема и шрифты Streamlit | `[server] headless`, `[theme]`, `[theme.light/dark(.sidebar)]` | — | Streamlit |
| `core/settings.py` | секреты только из окружения | `get_secret(name)` → RuntimeError, если пусто | `:10-15` | `supabase_client.py:25-26` (`SUPABASE_URL`, `SUPABASE_KEY`), `extractor.py:95` (`OPENROUTER_API_KEY`) |

Расхождения справочников:

| Что | Где |
|---|---|
| В models.json 73 модели, в prices.json 53; 20 моделей (все 40 т и 60 т-24 м для С/СЛ/Ф/ФЛ) без цены скрыты каскадом | `src/filters.py:23-39` |
| 5 опций 22 м (`frame_22`, `fence_light_22`, `fence_norma_22`, `hatches_fl_22`, `hatches_f_22`) без `price_class` → класс UNKNOWN | `src/pricing.py:102-104` |
| `foundation_options[].id` в options.json без суффикса длины (`foundation_lite_sl_fl`), ключи prices.json — с суффиксом (`foundation_lite_sl_fl_18`) → подпись для фундаментов не находится | `data/options.json:88`, `src/ui/options_section.py:429-437` |
| `_LENGTH_TO_SECTIONS` дублирует `models[].sections` | `src/storage/snapshot_builder.py:7` (TECH_DEBT B20) |

## 3. Правила расчёта

### 3.1 Цена модели

| Шаг | Формула | Ссылка |
|---|---|---|
| Масштаб ширины | `retail_W = round(retail × W / 3.0)`, `dealer_W = round(dealer_ru × W / 3.0)` | `src/pricing.py:55-57`, `:165-167` |
| Потолок | `coeff = 2.0 × (1.2, если W ≠ 3.0, иначе 1)` → 2.0 или 2.4 | `src/pricing.py:168`, `src/config.py:30` |
| Коридор | `min = ceil1000(dealer_W)`, `max = floor1000(retail_W × coeff)`, `default = clamp(round1000(retail_W), min, max)` | `src/pricing.py:169-171`, `:43-52` |
| Шаг ввода | `max > 1 000 000 → 10 000`; `> 100 000 → 5 000`; иначе 1 000 | `src/pricing.py:31-40` |
| Значение | `model_price = state.model_price`, если задано, иначе `default`; записывается в state на каждом рендере | `src/ui/model_section.py:194-205` |
| В спецификации | если `model_price` None → `retail` (без масштаба); затем override `spec_items_overrides[model_id]` по qty/price | `src/spec_builder.py:378-384` |
| Цвет-метка | ≥ retail 🟢; < dealer 🔴; иначе 🟡 | `src/pricing.py:185-191` |
| Валидация | error, если `model_price < dealer_ru` (немасштабированный) | `src/validation.py:49-52` |
| Сбросы | смена модели → `model_price=None` + сброс опций/overrides; смена ширины → `model_price=None` + снятие price-override модели | `src/state.py:118-158` |

### 3.2 Цена опций — классы

| Класс | Кол-во ключей | min | max | default | Дилерская в подписи | Ссылка |
|---|---|---|---|---|---|---|
| `A_retail_and_dealer` | 20 | `ceil1000(price_dealer_ru)` | `floor1000(retail × 1.4)` | `clamp(round1000(retail))` | реальная | `src/pricing.py:122-137` |
| `B_retail_only` | 52 | `ceil1000(retail × 0.6)` | `floor1000(min × 4.5)` (≈ retail × 2.7) | `clamp(round1000(retail))` | нет | `src/pricing.py:139-155`, `src/config.py:25-29` |
| `C_manual_range` | 12 | `ceil1000(range_min)` | `floor1000(range_max)` | `clamp(round1000(price_retail))` | нет; `allow_customer_value` только у поверки | `src/pricing.py:106-120` |
| нет класса / неизвестный → UNKNOWN | 5 | `ceil1000(retail × 0.92)` | `floor1000(retail × 1.4)` | `clamp(round1000(retail))` | синтетическая (`dealer_is_synthetic`) = min | `src/pricing.py:64-80`, `:102-104`, `:157-158` |
| `on_request: true` | 1 (`canopy_turnkey_24`) | 0 | 0 | 0 | — опция заблокирована, включённая — error | `src/pricing.py:83-96`, `src/validation.py:55-60` |

Строка спецификации КП по опции (`src/spec_builder.py:411-441`): видимость по `applies_to_lines/lengths` и префиксу блока (`src/filters.py:68-99`); `customer_side` → цена 0 (`:421-424`); `total = price × qty` (`:435`); затем override qty/price (`:425-427`, `:204-217`). Произвольная позиция — qty 1, цена из UI, тоже с override (`:443-465`).

Бандл ОРИОН (5 пакетов с `components.shef_montazh > 0`): строка делится на ПАК и `orion_install`; `montazh = round(price × shef / (equip + shef))`, `equipment = price − montazh`; имя монтажа зависит от наличия фундамента; два бандла в сделке → `MultipleOrionBundlesError` (`src/spec_builder.py:287-361`).

Имена позиций КП: модель «Весы автомобильные {full_name}» + «Размер платформы …» при W≠3 (`src/spec_builder.py:76-98`); фундамент «Фундамент железобетонный {пандусный|в приямок|монолитная плита} под весы ВЕСТА-…, Nм» (`:141-160`); подстановка линейки в лейблы рам/пандусов/фундаментов (`:101-138`); «Шеф-монтаж и пусконаладка» при шеф-монтаже; «(силами Заказчика)» при `customer_side` (`:163-186`).

### 3.3 Итоги и НДС

| Что | Правило | Ссылка |
|---|---|---|
| Ставка | `VAT_RATE = 0.22`; цены прайса уже с НДС | `src/config.py:15-16` |
| Итог КП | `with_vat = Σ total × model_qty`; `vat = round(with_vat × 0.22 / 1.22)`; `without_vat = with_vat − vat` | `src/pricing.py:200-214` |
| КП-документ | строки per-unit, `subtotal_per_1 = Σ total`, `subtotal_n = subtotal_per_1 × qty`; при qty>1 строка ИТОГО делится на «за 1 весы» и «за N весов»; `vat_percent = "22"` | `src/generators/kp_generator.py:160-164`, `:228`, `:248-262`, `:280-288` |
| `kps.total_price` | `calc_totals(spec_items, model_qty)["with_vat"]` — с НДС, за всё количество | `src/ui/sidebar.py:152-154` |
| Договор, `СПЕЦ_НДС` | из снапшота всегда `"22"` | `src/contracts/from_kp.py:278` |
| Замена «20»→«22» | при генерации: если `СПЕЦ_НДС` пусто или содержит подстроку «20» → `nds.replace("20","22")`, пусто → «22» (нужно для режима B: промпт разрешает модели вернуть 20) | `src/app_pages/2_Договор.py:1096-1098`, `src/contracts/prompts/extract_contract_data.txt:28` |
| Текст строки оплаты | «…, в т.ч. НДС 22%, …» — литерал, не из `VAT_RATE` | `src/contracts/payment_line.py:85`, `:92` |
| Статичные «22%» в шаблонах | раздел 8 | — |

### 3.4 Оплата в КП (lite-регистр, без сумм)

| Пресет | Строки | Ссылка |
|---|---|---|
| v1 | `postpay = 100 − prepay`; `body_template.format(prepay, postpay, days_phrase)` | `src/generators/payment_renderer.py:152-160` |
| v2 | `postpay = 100 − prepay − preship` | `:163-173` |
| v3 | 100 % + текст выбранного триггера | `:176-189` |
| prepay_100 | `p1 = 100` | `:192-197` |
| custom | свободный текст или «—» | `:210-211` |
| split_by_items | строка 1: предоплата весов [+ фундамента]; при равных % — один % и объекты через «и», иначе через « + »; строка 2: доплата фундамента по Акту (с опорами ОРИОН — расширенный объект и триггер); строка 3: доплата весов [+ доставки] по готовности к отгрузке; строка 4: «Монтаж/Шеф-монтаж и поверка: предоплата X % …, доплата Y % …»; фаза с 0 % не печатается; слово «оплата», если ненулевая только одна фаза | `:49-149`, `src/payment_wording.py:79-87` |
| Срок | `days_brief(n)` → «5 дней»; сноска «Сроки указаны в банковских днях.» | `src/payment_wording.py:59-64`, `payment_renderer.py:26`, `:227-228` |
| Активность групп в документе | по `payment_group` позиций спецификации | `payment_renderer.py:29-39`, `src/spec_builder.py:220-239` |
| Активность групп в UI и валидации | по ключам `state.options` (другой предикат) | `src/validation.py:155-190`, `src/ui/payment_section.py:196` |

Бакеты (`resolve_payment_group`, `src/spec_builder.py:220-239`): `foundation_*`, `construction_works_*`, `concrete_base*`, `road_slabs_*`, `pag_slabs_*`, `orion_cable_poles` → foundation; `delivery_default` → delivery; `install_default`, `verification_default`, `orion_install` → installation_and_verification; остальное (модель, ОРИОН-ПАК, рамы, пандусы, ограждения, люки, навес, мелочи) → scales. Произвольная позиция: тег типа работ, иначе по имени: «доставка…» → delivery, `^монтаж|^поверка|^шеф.?монтаж` → iv, `^фундамент|^строительство фундамента|^бетонное основание|укладка.+плит|опор и кабель-трасс` → foundation, иначе scales (`:244-275`).

### 3.5 Оплата в договоре (full-регистр, с суммами)

| Правило | Формула | Ссылка |
|---|---|---|
| Не-split (v1/v2/v3/prepay_100) | фазы: v1 предоплата/SPEC_SIGNED + доплата/WORK_ACT; v2 + доплата/SHIPMENT_READY; v3 одна «оплата» с триггером DELIVERED или WORK_ACT; prepay_100 «оплата»/SPEC_SIGNED_INVOICE. База `total = Σ total позиций × model_qty`; `amount = round(total × pct / 100)`, последняя фаза = `total − уже распределено`; фазы с 0 % и строки с 0 ₽ пропускаются; объект «от общей цены договора» | `src/contracts/payment_line.py:115-205` |
| custom | строк нет → генерация заблокирована, пока менеджер не заполнит таблицу | `payment_line.py:162-163`, `2_Договор.py:1064-1076` |
| Split L1 | `round(scales_total × s_prepay%)` [+ `round(foundation_total × f_prepay%)`]; при разных % весов и фундамента % не печатается (плоская сумма) | `payment_line.py:352-372` |
| Split L2 | доплата фундамента `round(foundation_total × f_post%)`, триггер FOUNDATION_ACT или FOUNDATION_ACT_POLES | `:374-387` |
| Split L3 | `round(scales_total × s_post%)` [+ `round(delivery_total × d_post%)`]; при разных % — плоская сумма | `:389-413` |
| Split L4/L5 | монтаж/поверка: предоплата BRIGADE_READY и доплата WORK_ACT, объект по составу бакета | `:415-440`, `src/payment_wording.py:163-251` |
| Остаток в split | не добирается: каждая сумма округляется отдельно | `payment_line.py:262-264` |
| Страж покрытия | `|Σ строк − ожидаемое| > max(число строк, 1)` → `PaymentCoverageError`; split сверяется с суммой 4 бакетов, не-split — с полным ИТОГО; вызывается только при автозасеве/«Заполнить по умолчанию» | `:267-299`, `:445-447` |
| Количество весов | все бакеты × `model_qty` | `:334-337` |
| Редактор | `amount = round(% / 100 × база)`, пустая база = ИТОГО; если Σ% группы (база + объект) = 100 ± 0,01 → последняя строка группы = база − остальные; строки без % не пересчитываются | `src/ui/payment_lines_editor.py:170-195` |
| Проверки редактора | Σ% по группе > 100 → error (выводится, но генерацию не блокирует); база > ИТОГО, перебор и недобор > max(строк,1) ₽ → warnings | `payment_lines_editor.py:202-240`, `:324-330` |
| Текст пункта | «{N}. {Тип} {pct}% {основа} {объект} в размере {сумма} ({пропись}) {рубль/рубля/рублей}, в т.ч. НДС 22%, в течение {N (прописью) банковских дней} с момента {триггер}.»; без % — без части «pct основа объект»; нумерация «2.N» в Спецификации, «4.2.N» в договоре поставки | `payment_line.py:63-95`, `2_Договор.py:1170-1173`, `src/contracts/supply_filler.py:332-335` |
| Тексты триггеров | full/lite-словарь; для договора поставки — переопределения «подписания настоящего Договора», «поставки Весов Покупателю» | `src/payment_wording.py:260-297` |

### 3.6 Сроки

| Правило | Формула | Ссылка |
|---|---|---|
| Роль позиции | `vesta-*` → scales; по префиксам → install/verification/delivery/foundation/canopy/orion; рамы, ограждения и пр. → None (сливаются с весами по vMerge) | `src/term_days.py:48-74` |
| Активность | сервисные роли (install/delivery/verification) не учитываются при `customer_side` | `src/term_days.py:93-107` |
| Дефолт проекта | `T = Σ дефолтов уникальных активных ролей` | `src/term_days.py:139-147` |
| Ручной срок | фиксированные роли без изменений; вариативные: `max(1, round(default × (T − T_fix) / Σ default_var))`, дельта округления — первой активной из scales/orion/foundation/canopy | `src/term_days.py:148-183` |
| Минимум | `T_fix + число активных вариативных ролей`; меньше → `TermDaysTooSmallError` | `src/term_days.py:150-167`, `:206-214` |
| В КП | колонка «Срок» по позициям, строка ИТОГО — общий срок | `src/generators/kp_generator.py:136-158`, `:227` |
| В договоре | позиции договора не несут `item_key` → все роли None → сроки берутся из `TERM_DAYS_DEFAULTS` (поставка 20, фундамент 10, монтаж 3, доставка 1); ручной срок КП не передаётся (`total_term_days: None`) | `src/term_days.py:102-103`, `src/contracts/from_kp.py:188`, `:574-585`, `src/contracts/terms_renderer.py:13-40`, `src/contracts/supply_filler.py:194-204`, `:302-304` |
| Формат | договор: «N (прописью) рабочих дней» (`terms_renderer.py:26-27`); оплата: «N (прописью) банковских/рабочих/календарных дн[я|ей]» с согласованием по числу (`src/contracts/utils.py:152-172`); КП: «N день/дня/дней» (`src/utils/format.py:24-34`) | — |
| Срок действия КП | `kp_date + kp_valid_days` | `src/ui/header.py:51`, `src/ui/sidebar.py:52-54` |

### 3.7 Округления и форматы

| Что | Правило | Ссылка |
|---|---|---|
| Границы и дефолт цены | `ceil/floor/round` до 1000 ₽ | `src/pricing.py:43-52` |
| НДС в КП | `round()` до рубля | `src/pricing.py:208` |
| Суммы оплаты | `round()` до рубля, Python-округление «к чётному» на .5 | `src/contracts/payment_line.py:189`, `:262-264`, `src/ui/payment_lines_editor.py:183` |
| Доля ОРИОН | `round()`, остаток — в ПАК | `src/spec_builder.py:347-348` |
| Деньги в DOCX | обычный пробел разделителем тысяч | `src/utils/format.py:16-21`, `payment_line.py:74` |
| Деньги в UI | неразрывный пробел + «₽» | `src/utils/format.py:11-13` |
| Пропись | `number_to_words` — миллионы/тысячи/единицы, миллиардов нет; «рубль/рубля/рублей» по числу | `src/contracts/utils.py:72-127` |
| Цены позиций договора | `float`; `price_per_unit = price / qty` | `src/contracts/from_kp.py:500`, `:531`, `:572` |

## 4. Документы

### 4.0. Классы выходных документов и точка выбора

| Класс | Файлы на выходе | Шаблоны | Кто собирает | Условие |
|---|---|---|---|---|
| КП | `НомерКП_Клиент_Модель_Дата.docx` (`src/generators/kp_generator.py:302-317`) | `templates/kp_template.docx` (docxtpl) | `generate_kp` `src/generators/kp_generator.py:256-291`; контекст `build_template_context` `:124-235` | всегда со страницы КП; один шаблон на все сценарии |
| Договор поставки | один файл `Договор_поставки_<№>_<клиент>.docx` (`src/app_pages/2_Договор.py:1140`) | `templates/contracts/supply_contract.docx` + `supply_appendix_1.docx` + `supply_appendix_2.docx`, склейка docxcompose | `build_supply_context` `src/contracts/supply_filler.py:263`; `compose_supply` `src/contracts/compose.py:22-103` | радио «Тип документа» = «Поставка» (`src/app_pages/2_Договор.py:1135`) |
| Договор + Спецификация v2 | два файла `Договор_…docx`, `Спецификация_…docx` (`src/app_pages/2_Договор.py:1112-1113`) | `templates/contracts/contract.docx` + `templates/contracts/spec_v2.docx` (+ приложения из `data/fundament/`) | `fill_template` `src/app_pages/2_Договор.py:1166`; `fill_spec_v2` `:1175`; `compose_spec_with_attachments` `:1199` | радио = «Спецификация» и в спецификации есть items (`src/app_pages/2_Договор.py:1167`) |
| Договор + Спецификация v1 (fallback) | те же два файла | `contract.docx` + `templates/contracts/spec_foundation_install.docx` (статичный текст под фундамент+монтаж+поверку) | `fill_spec_with_items` `src/app_pages/2_Договор.py:1196` или `fill_template` `:1211` | (а) `fill_spec_v2` упал не-Lite исключением (`:1182-1196`); (б) items пусты — режим «Из PDF файла», где AI-экстракт кладёт плоский `specification` без items (`src/contracts/state.py:68`, `src/contracts/prompts/extract_contract_data.txt:122-127`) → `:1210-1211` |

Автовыбор радио: `decide_contract_type` → `"supply"`, если `installation_scope=="none"` И `foundation_scope ∈ {none, existing_foundation, rama}` И нет ОРИОН, иначе `"spec"` (`src/contracts/supply_filler.py:170-187`); вызывается на `src/app_pages/2_Договор.py:974-978`; менеджер может переключить вручную, выбор переживает reruns до смены КП/авто-типа (`:983-991`). Поверка в условии не участвует (`src/contracts/supply_filler.py:181-185`).

Контекст сценария (`build_clauses_context`, `src/contracts/clauses_context.py:39-122`) — все поля вычисляются из items, override из `contract.scope_overrides` применяется только при отсутствии соответствующей позиции:

| Поле | Значения | Источник |
|---|---|---|
| `installation_scope` | none / full / shefmontazh | item `installation`.metadata.scope (`:54-61`); scope «fundament»/«rama» → full; иначе override (`:62-63`); иначе none |
| `foundation_scope` | none / customer_builds / contractor_full / contractor_with_materials / contractor_supervised / rama / existing_foundation | item `foundation` через `_FOUNDATION_SCOPE_MAP` (`:5-17`, `:69-71`); item `rama` → rama (`:72-73`); override (`:74-75`); иначе customer_builds при монтаже, none без (`:80`) |
| `verification_scope` | none / supplier / customer | item `verification`, `customer_side` → customer (`:85-87`); override (`:88-89`) |
| `has_orion` | bool | item `orion` (`:94`) |
| `orion_poles_scope` | none / by_contractor / by_customer | item `orion_install` → by_contractor (`:98-99`); override (`:100-101`); иначе by_customer |
| `winter_concrete`, `winter_surcharge` | bool | только флаги `contract.flags` (`:108-111`) |

Откуда scope позиций (опции КП → `metadata.scope`): `install_default` → scope = `installation_scope` снапшота (full/shefmontazh), иначе fundament/rama (`src/contracts/from_kp.py:546-551`); `foundation_lite_*` → pandus_lite, `foundation_std_*` → pandus_std, `construction_works_*` → contractor_with_materials, `concrete_base_on_frame` → rama_concrete, `road_slabs_*` → rama_road_slabs, `pag_slabs_*` → rama_pag_slabs, `foundation_supervision` → contractor_supervised, прочие `foundation_*` (s_f) → fundament_jb (`src/contracts/from_kp.py:552-568`); id позиции — `_option_key_to_spec_id` (`src/contracts/spec_items.py:50-86`); `frame_*`/`ramp_set_*` → id rama/pandus (`:82-85`). Шеф-монтаж — флаг КП `is_shefmontazh` → `installation_scope="shefmontazh"` в снапшоте (`src/storage/snapshot_builder.py:115-123`). Ручная позиция с типом «Монтаж» продвигается до id `installation`, scope full (`src/contracts/custom_work_types.py:23-25`, `src/contracts/from_kp.py:588-604`); остальные типы (фундамент/поверка/ОРИОН) закомментированы (`src/contracts/custom_work_types.py:26-32`). ОРИОН-бандл КП всегда расщепляется на ПАК (`orion`) + `orion_install` (`src/contracts/from_kp.py:89-111`, `src/spec_builder.py:315-355`).

Ручные корректировки на странице Договора: тип основания «Заказчик строит / Готовый фундамент» — только если нет позиции фундамента/рамы и есть монтаж (`src/app_pages/2_Договор.py:173-177`, `:793-807`); без монтажа override фундамента сбрасывается (`:808-812`); чекбокс «Зимний период» и сумма (дефолт 200 000) — только при `foundation_scope ∈ {contractor_full, contractor_with_materials}` (`:822-845`, `src/contracts/clauses_context.py:28-36`), иначе флаги принудительно false (`src/app_pages/2_Договор.py:843-846`); override монтажа/поверки/опор ОРИОН (`:848-868`).

### 4.1. Сколько видов: расхождение с «8» владельца

| Счёт | Что считается | Источник |
|---|---|---|
| 9 исходных шаблонов юристов | 1 договор поставки + 8 спецификаций (монтаж; монтаж ОРИОН; рама монтаж; рама шеф-монтаж; стройка с материалом Заказчика; фундамент монтаж; фундамент монтаж зима; фундамент монтаж ОРИОН) | `docs/contract_templates_v1/*.md` |
| «8» владельца | не установлено: откуда счёт; совпадает по числу с 8 спецификационными шаблонами юристов (без поставки) | — |
| Реально в коде | **15 видов**: 1 договор поставки + 13 вариантов «Договор + Спецификация v2» + 1 fallback v1. Фиксированного списка видов в коде нет: спецификация v2 одна (`templates/contracts/spec_v2.docx`), вид = комбинация scope-полей, пункты фильтруются `applies_when` (`src/contracts/clauses_renderer.py:57-69`). Ниже — виды, различающиеся набором пунктов `data/clauses.yaml`; 8 видов юристов покрыты (С1–С8), 5 видов сверх юристов (С9–С13) и fallback v1 программа тоже выдаёт | `docs/architecture/contracts_v2.md:30-31` (принцип «один шаблон»), расчёт наборов клауз — прогон `build_contract_clauses` на синтетических deal (скрипт `kinds.py` в scratchpad, код не менялся) |

### 4.2. Таблица видов

Общее для всех видов «Договор + Спецификация v2»: `contract.docx` статичен (одинаков для всех видов, только реквизиты/дата/номер/НДС) (`templates/contracts/contract.docx`, филлер `src/contracts/filler.py:119`); в спецификации меняются таблица позиций (`src/contracts/filler.py:284-362`), строки оплаты 2.N (`src/app_pages/2_Договор.py:1168-1173`), блок сроков (`src/contracts/terms_renderer.py:30-84`), набор/нумерация пунктов с 4 (`src/contracts/clauses_renderer.py:73`), ТТХ и комплект (`src/contracts/spec_v2_filler.py:303-359`). Всегда срабатывают `cross_reference_to_contract`, `delivery_address` (`data/clauses.yaml:272-284`). Подстановки: `install_site_label` = «месту установки» для rama, иначе «фундаменту» (`src/contracts/clauses_renderer.py:111`); `scales_or_with_orion` (`:110`); срок стройки Заказчиком дефолт 60 дн. (`:102-106`).

| Вид | Условие выбора (state/снапшот → контекст) | Шаблон DOCX и правила `data/clauses.yaml` | Что меняется в документе | Эталон |
|---|---|---|---|---|
| Д1. Договор поставки | авто: install=none, foundation ∈ {none, existing_foundation, rama}, без ОРИОН (`src/contracts/supply_filler.py:181-186`) — напр. только весы/доставка/рама без монтажа; или ручной выбор «Поставка» | `supply_contract.docx` + `supply_appendix_1.docx` + `supply_appendix_2.docx` (`src/contracts/compose.py:36`, `:64`, `:84`); clauses.yaml не используется | Спецификация (прил.1): одна строка «весы» = сумма всех позиций кроме бакетов installation_and_verification и foundation (рама/пандусы/ОРИОН-оборудование агрегируются в неё) + строка «Доставка» (`src/contracts/supply_filler.py:231-256`); при qty>1 — две строки ИТОГО (`src/contracts/compose.py:74-81`); оплата 4.2.N (`src/contracts/supply_filler.py:332`); сроки производства/доставки, срок действия, ТТХ+комплект в прил.2 (`:303-366`). Риск: позиции бакетов foundation/installation_and_verification молча выпадают — бетонное основание/плиты под раму без монтажа (`src/spec_builder.py:230-231`), поверка без монтажа (авто-тип = supply), всё, что осталось при ручном «Поставка» | G-04, G-08 |
| Д2. Fallback: Договор + Спецификация v1 | items пусты (режим PDF) или исключение в `fill_spec_v2` (`src/app_pages/2_Договор.py:1182-1196`, `:1210-1211`) | `contract.docx` + `spec_foundation_install.docx`; clauses.yaml не используется | Жёсткий текст фундамент+монтаж+поверка (пункты 4-11, «Приложение №2», «п.п.7–11»), слоты СПЕЦ_П1..П5 и СПЕЦ_ОПЛАТА_П1..П6, статичные ТТХ 18×3 и комплект DHM9B/КБТ-8-Ц, встроенный лист «Строительное задание» (`templates/contracts/spec_foundation_install.docx`, дамп текста в scratchpad `tpl.txt`) | нет (runner fallback не реплицирует — `tests/autoverify/runner.py:11-12`) |
| С1. Фундамент Подрядчика + монтаж | item foundation со scope fundament_jb/pandus_lite/pandus_std → contractor_full; install full | `spec_v2.docx`; `supplier_dispatches_construction_team` (`data/clauses.yaml:57-62`), `customer_unable_to_accept_team_delays_work` (`:96-101`), `customer_provides_flat_area_for_construction` (`:124-129`), `customer_provides_scales_near_install_site` (`:145-150`), `customer_provides_crane` (`:152-157`), `additional_work_during_construction` (`:254-259`); при поверке Подрядчика + `supplier_prepares_docs` (`:43-48`), `customer_provides_test_vehicle` (`:159-164`) | Сроки: строка «строительство фундамента», в поставке «п.2.1 и п.2.2», бригады «строительной и монтажной» (`src/contracts/terms_renderer.py:43-82`); «монтаж Весов и поверка Весов» только при поверке Подрядчика, иначе «монтаж Весов» (`:71-74`); прил.№1 стройзадание (авто-подбор, §4.3) | G-01, G-06, G-09, G-10, G-11 |
| С2. С1 + зимний бетон | foundation contractor_full/with_materials И флаг `winter_surcharge` (чекбокс, `src/app_pages/2_Договор.py:824-842`) | С1 + `winter_foundation_surcharge` (сумма из `winter_surcharge_amount`), `winter_foundation_surcharge_payment`, `winter_concrete_heating_option` (`data/clauses.yaml:71-90`) | +3 пункта у Подрядчика; блок сроков без зимнего варианта (в `terms_renderer.py` ветки нет, `src/contracts/terms_renderer.py:48-54` — фикс. «выше +5 °С») | нет (G-03 заявляет зиму, но rama → клаузы не срабатывают, см. §9) |
| С3. Фундамент Подрядчика + ОРИОН | С1 + опция-бандл ОРИОН (→ items orion + orion_install) [+ `orion_cable_poles` → item orion_poles] | С1, но вместо `supplier_dispatches_construction_team` — `…_with_orion_poles` (условие: orion_install есть, `data/clauses.yaml:64-69`); + `customer_provides_power_220V` (`:166-171`), `customer_installs_high_cameras_supervised` (`:229-234`), `customer_provides_pc_for_orion` (Прил.№4, `:236-241`), `orion_oversized_vehicle` (`:261-266`) | Позиции ПАК/монтаж ОРИОН/опоры; клауза про опоры срабатывает по наличию orion_install, а не позиции опор (`src/contracts/clauses_context.py:98-99`). Ветка «опоры готовит Заказчик» (`customer_prepares_orion_poles`, `customer_prepares_cable_routes`, `data/clauses.yaml:215-227`) из КП недостижима: бандл всегда даёт orion_install, override игнорируется при его наличии (`src/contracts/clauses_context.py:98-101`) | G-05 |
| С4. Стройка силами Подрядчика, материалы Заказчика + монтаж | опция `construction_works_*` → contractor_with_materials | С1 + `customer_provides_construction_materials` (Прил.№3, `data/clauses.yaml:131-136`); зима доступна | как С1 + обязанность Заказчика по материалам; Прил.№3 программа не формирует | нет |
| С5. Заказчик строит фундамент + монтаж | нет позиции foundation/rama, install full, override не «готовый» → customer_builds (`src/contracts/clauses_context.py:80`) | `customer_builds_foundation_per_spec` (Прил.№1, срок дефолт 60 дн., `data/clauses.yaml:103-108`), `customer_provides_foundation_photos` (контрольный лист Прил.№2, `:110-115`) + монтажные клаузы С1 без стройки | Сроки без строки фундамента; стройзадание авто не подбирается (нет фундаментной опции → `foundation_execution` None, `src/storage/snapshot_builder.py:25-48`) → предупреждение при генерации (`src/app_pages/2_Договор.py:1200-1209`), выбор вручную | нет |
| С6. С5 + ОРИОН | как С5 + бандл ОРИОН | С5 + ОРИОН-клаузы С3 (без `…with_orion_poles`, т.к. нет стройки Подрядчика) | Позиции ПАК + монтаж ОРИОН; клаузы «Заказчик готовит опоры (Прил.№3)» не срабатывают (orion_install → by_contractor), хотя в шаблоне юристов есть (`docs/contract_templates_v1/Автовесы_монтаж_ОРИОН_gemini.md:54`) | нет (autoverify `montazh_orion`) |
| С7. Рама + монтаж | item rama (`frame_*`) или foundation со scope rama_concrete/rama_road_slabs/rama_pag_slabs → rama; install full | `customer_provides_flat_area_for_rama` (30×4 м, `data/clauses.yaml:117-122`), `customer_provides_power_220V` (`:169`), монтажные клаузы С1 без стройки | `install_site_label` = «месту установки»; сроки без строки фундамента; стройзадание rama_* (только concrete — авто, §4.3) | G-03, G-07 (обе — concrete_base_on_frame) |
| С8. Рама + шеф-монтаж | rama + `is_shefmontazh` (install shefmontazh) | С7 + `customer_sends_pre_install_photos` (`data/clauses.yaml:138-143`), `customer_organizes_specialist_logistics` (`:173-178`), `customer_does_install_under_supervision` (`:180-185`), `customer_provides_tools_and_specialists` (`:187-206`) | имя позиции «Шеф-монтаж и пусконаладка» (`src/contracts/from_kp.py:30`, `:132-133`); оплата «шеф-монтажных работ» | G-02 |
| С9. Курирование + монтаж (нет у юристов) | опция `foundation_supervision` → contractor_supervised | `supplier_supervises_foundation_construction` (`data/clauses.yaml:50-55`) + клаузы С5 (`:103-115`) | стройзадание авто не подбирается (секции не считаются для курирования, `src/storage/snapshot_builder.py:51-71`) → предупреждение (`src/app_pages/2_Договор.py:1205`) | нет |
| С10. Готовый фундамент Заказчика + монтаж (нет у юристов) | ручной выбор «Готовый фундамент Заказчика» → override existing_foundation (`src/app_pages/2_Договор.py:176`, `:807`) | `scales_for_existing_foundation` (`data/clauses.yaml:247-252`) + монтажные клаузы без стройки | без приложений | нет |
| С11. Шеф-монтаж не на раме (нет у юристов) | `is_shefmontazh` + фундамент Подрядчика / customer_builds / existing | клаузы соответствующего фундамента + 4 шеф-клаузы С8 | комбинация С1/С5/С10 и С8 | нет |
| С12. Работы без монтажа весов (нет у юристов) | install=none, но foundation contractor_* или ОРИОН (→ spec по `decide_contract_type`) | фундамент: `supplier_dispatches_construction_team`, площадка, доп.работы (+поверка); только ОРИОН: 220В, камеры, ПК, длинный автомобиль | сроки без строки монтажа (`src/contracts/terms_renderer.py:64`); для «ОРИОН без фундамента» UI предупреждает о некорректной формулировке (`src/app_pages/2_Договор.py:770-777`) | нет |
| С13. Спецификация без работ (нет у юристов) | ручной выбор «Спецификация» при авто-supply сделке | только `cross_reference_to_contract`, `delivery_address` (+поверка, если есть) | договор подряда на чистую поставку | нет |

Модификаторы поверх видов (не отдельные виды): поверка Подрядчиком / Заказчиком (`customer_organizes_verification`, `data/clauses.yaml:208-213`; `supplier_prepares_docs` и `customer_provides_test_vehicle` пропадают) / без поверки (G-10); qty>1 — вторая строка ИТОГО во всех трёх документах (`src/contracts/filler.py:353-359`, `src/contracts/compose.py:74-81`, `src/generators/kp_generator.py:269-278`).

### 4.3. КП

| Аспект | Факт |
|---|---|
| Шаблон | `templates/kp_template.docx`, один на все сценарии (`src/generators/kp_generator.py:258-262`) |
| Что меняется | таблица позиций `{%tr for item in spec_items %}` с колонкой сроков и vMerge (`src/generators/kp_generator.py:149-160`, `:267`); блок оплаты `payment_terms_block` (`:184-185`, `:230`); двухдиапазонная цена деления (`:187-189`); ИТОГО за 1/за N (`:269-278`) |
| Расхождение документации | `templates/README.md:61-62` описывает `payment_line_1/2`; в коде и шаблоне — `payment_terms_block`, `model_full_name`, `kp_valid_days`, `manager_*` (`src/generators/kp_generator.py:201-235`) — README устарел |
| Эталоны | КП выпускается во всех G-01..G-11 (`tests/autoverify/runner.py:104-105`) |

### 4.4. Строительные задания и контрольные листы

Правило выбора стройзадания — `resolve_build_task(snapshot)` (`src/contracts/fundament_lookup.py:88-153`); вызывается из `_render_fundament_attachment_choice` (`src/app_pages/2_Договор.py:365-370`) и из `tests/autoverify/runner.py:196`. Контрольный лист — `resolve_control_sheet(execution, sections)` (`src/contracts/fundament_lookup.py:156-169`), вызов `src/app_pages/2_Договор.py:410`. Склейка — `compose_spec_with_attachments`, стройзадание всегда «Приложение №1», контрольный лист №2 (`src/contracts/compose.py:130-140`, `:172`).

| Шаг | Правило |
|---|---|
| execution | `snapshot.foundation_execution`: concrete_base_on_frame → rama_concrete; road_slabs_* → rama_road_slabs; pag_slabs_* → rama_pag_slabs; опции foundation_s_f/lite/std/supervision/construction_works → выбор менеджера (пандусный / приямок / монолитная_плита, дефолт пандусный); иначе None (`src/storage/snapshot_builder.py:25-48`, UI `src/ui/options_section.py:328-352`) |
| sections | длина → секции {12:2, 16:3, 18:3, 20:4, 22:4, 24:4} (`src/storage/snapshot_builder.py:7`), только при опциях foundation_s_f/lite/std/construction_works/concrete_base_on_frame (`:59-67`) |
| family | для пандусного: линия из `model_code` С/Ф/П → С_Ф, СЛ/ФЛ → СЛ_ФЛ (`src/contracts/fundament_lookup.py:24-30`, `:119-129`) |
| имя файла | пандусный: `пандусный_{family}_{N}скц.docx`; приямок/rama_*: `{execution}_{N}скц.docx` (`:129-133`) |
| нет файла | монолитная_плита/None → «приложение не подключается» (`:94-100`, `:201-204`); неизвестный тип, секции ∉ {2,3,4}, нет семейства, файла нет → path None + причина (`:102-144`) |
| контрольный лист | только execution ∈ {пандусный, приямок} и секции 2/3/4, файл `control_sheet_{execution}_{N}скц.docx` (`:23`, `:156-169`); берётся из авто-execution даже при ручном выборе стройзадания (`src/app_pages/2_Договор.py:410`); по умолчанию выключен, чекбокс (`:418-427`) |
| ручной выбор | селект «Авто-подбор / Без приложения / любой файл build_task» (`src/app_pages/2_Договор.py:381-403`) |

Файлы (sha256/media — скрипты `fund2.py`, `hash_fund.py` в scratchpad; текстовый слой всех файлов — только шапка «Приложение №{{ПРИЛОЖЕНИЕ_НОМЕР}} к Спецификации №{{СПЕЦ_НОМЕР}} от {{ДОГОВОР_ДАТА_ПОЛНАЯ}} г.» + заголовок, содержание — картинки):

| Файл `data/fundament/build_task/…` | Авто-подбор достижим | Примечание |
|---|---|---|
| `пандусный_С_Ф_2скц.docx`, `_3скц`, `_4скц` | да (С/Ф/П, 12/16-18/20-24 м) | 8/8/8 картинок, байты различны |
| `пандусный_С_Ф_3 скц.docx` (с пробелом) — **не в git**: каталог под `.gitignore:67`, отслеживаются только 18 файлов без пробела; существует лишь на этой машине | нет (имя не строится, `:129`); только ручной | байты и набор картинок отличаются от `…_3скц` (общие 4 из 7–8); в селекте подпись совпадает с `…_3скц` — «Пандусный фундамент 440 мм (С/Ф), 3 секции» (regex допускает пробел, `src/contracts/fundament_lookup.py:31`, `:64-85`); рядом PDF-источники `data/fundament/pdf_source/пандусный_С_Ф_3 скц.PDF` |
| `пандусный_СЛ_ФЛ_2скц.docx`, `_3скц`, `_4скц` | да (СЛ/ФЛ) | байты различны |
| `пандусный_СЛ_ФЛ_3 скц.docx` (с пробелом) — **не в git**, как и предыдущий | нет; только ручной | то же, что для С_Ф: отличается от `…_3скц` (общие 4 картинки), дубль подписи; PDF `data/fundament/pdf_source/пандусный_СЛ_ФЛ_3 скц.PDF` |
| `приямок_2скц.docx`, `_3скц`, `_4скц` | да | 14 картинок каждый, различны |
| `rama_concrete_2скц.docx`, `_3скц`, `_4скц` | да | 2 картинки (одна общая — логотип) |
| `rama_road_slabs_2скц.docx`, `_3скц`, `_4скц` | **нет**: road_slabs_* не входит в список «секционных» опций → sections None → «Не указано количество секций» (`src/storage/snapshot_builder.py:59-70`, `src/contracts/fundament_lookup.py:110-116`); только ручной | в TECH_DEBT B24 не отражено (там только concrete_base_on_frame) |
| `rama_pag_slabs_2скц.docx`, `_3скц`, `_4скц` | **нет**, по той же причине; только ручной | — |

| Файл `data/fundament/control_sheet/…` | Достижим | Примечание |
|---|---|---|
| `control_sheet_пандусный_2скц.docx`, `_3скц`, `_4скц` | да | один на С_Ф и СЛ_ФЛ (семейство не учитывается); 1 картинка, байты различны |
| `control_sheet_приямок_3скц.docx`, `_4скц` | да | — |
| `control_sheet_приямок_2скц.docx` | **отсутствует** → чекбокс скрыт для приямка 12 м (`src/app_pages/2_Договор.py:410-416`) | — |
| для rama_* / монолитной плиты | не предусмотрено (`src/contracts/fundament_lookup.py:23`) | — |

Наблюдение: текстовый заголовок всех 5 контрольных листов — «Строительное задание на фундамент Весов» (не «Контрольный лист»); содержимое — картинка; не установлено: что изображено на картинке.

Покрытие комбинаций:

| Комбинация | Покрыта |
|---|---|
| пандусный × {С_Ф, СЛ_ФЛ} × {2,3,4} | да, авто |
| приямок × {2,3,4} | да, авто; контрольный лист — без 2 |
| rama_concrete × {2,3,4} | да, авто; без контрольного листа |
| rama_road_slabs / rama_pag_slabs × {2,3,4} | файлы есть, авто нет |
| монолитная_плита | нет файлов by design (`src/contracts/fundament_lookup.py:203`) |
| курирование (contractor_supervised), customer_builds | авто нет (нет секций / нет execution), но клаузы ссылаются на «строительное задание (Приложение №1)» (`data/clauses.yaml:103-108`) — только ручной выбор, иначе предупреждение (`src/app_pages/2_Договор.py:1205-1209`); `docs/TECH_DEBT.md:924` утверждает «курирование не требует строительного задания» — противоречит клаузе |
| длины вне {12,16,18,20,22,24} | авто нет (`src/storage/snapshot_builder.py:71`) |
| рама `frame_*` без основания | execution None → без приложения |

Нумерация приложений vs текст клауз: стройзадание прикладывается как №1 (`src/contracts/compose.py:131-135`), но `supplier_dispatches_construction_team` ссылается на «Приложение №2» для стройки Подрядчиком (`data/clauses.yaml:62`; в выпуске — `tests/golden/expected/G-01_spec.dump.txt:122` против `:365`); Прил.№3 (материалы, схема ОРИОН) и №4 (ПК ОРИОН) упоминаются (`data/clauses.yaml:136`, `:220`, `:241`), но программой не формируются.

## 5. Генерация договора: входы

| Вход | Откуда | Куда идёт | Ссылка |
|---|---|---|---|
| `data.model.line/max/length/width/price` | снапшот `kps.data` | строка «Весы автомобильные ВЕСТА-{л}-{т}-{м}-Ц, max …т, размеры платформы …», цена, `metadata` позиции (по ней ищется модель для ТТХ) | `src/contracts/from_kp.py:494-523`, `src/contracts/spec_v2_filler.py:224-238` |
| `data.model.qty` | снапшот | количество весов: ИТОГО, суммы оплаты, «в количестве N шт.» | `src/contracts/state.py:138-142`, `2_Договор.py:1126` |
| `data.options.{key}.price/qty/customer_side/dimensions` | снапшот | позиции спецификации: id по ключу, имя, бакет, `metadata.scope` (тип фундамента/монтажа) | `from_kp.py:525-585`, `src/contracts/spec_items.py:50-86` |
| `data.custom_items[{name,price,scope}]` | снапшот | позиции; тег «Монтаж» продвигает id до `installation` | `from_kp.py:587-622` |
| `data.installation_scope` | снапшот | имя «Шеф-монтаж и пусконаладка», `metadata.scope` монтажа, объект оплаты монтажа | `from_kp.py:132-133`, `:546-551`, `2_Договор.py:548` |
| `data.payment.*` | снапшот | автозасев строк оплаты | `src/contracts/kp_load.py:32`, `2_Договор.py:545-549` |
| `data.foundation_execution`, `data.foundation_sections` | снапшот | автоподбор строительного задания и контрольного листа | `2_Договор.py:369-370`, `:410` (правило — раздел 4) |
| `data.spec_overrides` | снапшот | только в реконструкцию state для `СПЕЦ_СРОК_*`/`СПЕЦ_ОПЛАТА_*`; к позициям договора не применяется | `from_kp.py:187`, `:252` |
| `data.metadata`, `equipment`, `construction`, `metrology` | снапшот | в договоре не используются (датчик/индикатор/кабель — из `line_defaults`, двухдиапазонность — из `models.json`) | `src/contracts/spec_v2_filler.py:240-255`, `:356`, `src/contracts/tth_context.py:14-24` |
| `kp_number`, `updated_at` | колонки `kps` | подпись загрузки, кэш, сигнатура авто-типа документа | `2_Договор.py:500`, `:516`, `:535`, `:982` |
| `model_id` | колонка `kps` | бакет позиции весов | `from_kp.py:519` |
| `client_name`, `total_price` | колонки `kps` | только метка в дропдауне; в документ не идут | `2_Договор.py:468-469` |
| `prices.json` | справочник | имена опций (fallback на `label`), `components` для деления ОРИОН | `from_kp.py:147-150`, `:89-111` |
| `models.json`, `equipment_specs.json` | справочник | ТТХ, комплект поставки | `src/contracts/spec_v2_filler.py:210-260`, `src/contracts/supply_filler.py:315-327` |
| `payment_terms.json` | справочник | lite-слоты `СПЕЦ_ОПЛАТА_П1..6` (fallback шаблона), дефолтные % | `from_kp.py:273-289`, `src/payment_wording.py:46-72` |
| `clauses.yaml` | справочник | пункты Спецификации | `src/contracts/clauses_renderer.py:16` |
| `data/fundament/*` | файлы | приложения к Спецификации | `2_Договор.py:1198-1199` |
| `SUPPLIER` | код | реквизиты поставщика в договоре поставки | `src/contracts/supplier.py:8-23` |
| Реквизиты `ЗАКАЗЧИК_*` (19) + пол | ввод на странице / regex / LLM | плейсхолдеры, «действующего/действующей» | `2_Договор.py:87-107`, `:1093-1094` |
| Позиции (правка таблицы) | ввод на странице | имя, бакет, ед., кол-во, цена | `2_Договор.py:889-931`, `:1119-1123` |
| `scope_overrides` (фундамент/монтаж/поверка/опоры) | ввод на странице | контекст клауз, авто-тип документа | `2_Договор.py:780-868` |
| `flags.winter_surcharge(_amount)`, `winter_concrete` | ввод на странице | клаузы зимнего бетонирования | `2_Договор.py:821-846` |
| `payment_lines` | редактор оплаты | раздел оплаты «2.N» / «4.2.N» | `2_Договор.py:1133`, `:1168-1173` |
| `attachments` | ввод на странице | склейка приложений | `2_Договор.py:365-429`, `:1198-1199` |
| Тип документа | радио (дефолт `decide_contract_type`: поставка, если нет монтажа, фундамент ∈ {none, existing_foundation, rama} и нет ОРИОН) | ветка генерации | `2_Договор.py:967-991`, `src/contracts/supply_filler.py:170-187` |
| Номер, дата договора, адрес объекта, номер спецификации, срок действия | ввод на странице | плейсхолдеры; дата раскладывается на части | `2_Договор.py:993-1030`, `:1087-1092` |
| Город договора поставки | `manual.contract_city`, в UI не вводится → всегда «г. Воронеж» | `ДОГОВОР_ГОРОД` | `src/contracts/supply_filler.py:337` |
| Режим B: `requisites` + `specification` | ответ LLM | поля страницы, `fill_template` без позиций | `2_Договор.py:591-595`, `:1210-1211` |
| Вычисляемые при генерации | `ДИРЕКТОР_ПРИЧАСТИЕ`, части даты, `СПЕЦ_НДС`, `СПЕЦ_ИТОГО_ПРОПИСЬ`/`_РУБ` (если пусто), `ТЕКУЩИЙ_ГОД`, `ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА = «не более 50 м»` | — | `2_Договор.py:1087-1108`, `src/contracts/tth_context.py:43` |

## 6. Хранение

### 6.1 Supabase

DDL, типы колонок, индексы и RLS в репозитории отсутствуют — не установлено: нужен дамп схемы Supabase. Ниже — колонки, которые читает и пишет код.

| Таблица | Колонки | Операции | Ссылка |
|---|---|---|---|
| `kps` | `id`, `kp_number` (ключ upsert), `kp_date`, `client_name`, `model_id`, `total_price`, `manager_id`, `data` (JSONB), `created_at`, `updated_at` | `save_kp` — upsert по `kp_number` + перечитывание; `get_kp_by_number`; `list_recent_kps(50)` по `updated_at desc`; `search_kps_by_contractor` — `ilike client_name`; `delete_kp` (вызовов нет) | `src/storage/supabase_client.py:31-116` |
| `contracts` | `kp_id`, `contract_number`, `contract_date`, `object_address`, `spec_number`, `requisites`, `specification` | `save_contract`, `get_contracts_by_kp_id` — в `src/` не вызываются; договоры не сохраняются | `src/storage/supabase_client.py:119-155` |
| Клиент | `create_client(SUPABASE_URL, SUPABASE_KEY)`, таймаут postgrest 10 с, lru_cache | — | `src/storage/supabase_client.py:23-28` |

### 6.2 Ключи снапшота `kps.data` (`build_kp_snapshot`, `src/storage/snapshot_builder.py:126-196`)

| Ключ | Содержимое | Кто читает |
|---|---|---|
| `metadata.kp_valid_days`, `warranty_months`, `total_term_days`, `total_term_days_user_set` | шапка/сроки | `kp_restore.py:99-106` |
| `model.line/max/length/width/price/qty` | `price` = значение виджета (`state.model_price`), может быть None в старых снапшотах | `kp_restore.py:67-119`, `from_kp.py:155-198`, `:494-523` |
| `foundation_execution` | `rama_concrete`/`rama_road_slabs`/`rama_pag_slabs` по опциям основания на раме; иначе выбор менеджера (`пандусный`/`приямок`/`монолитная_плита`, дефолт `пандусный`) при фундаментных опциях; иначе None | `snapshot_builder.py:25-48` |
| `foundation_sections` | секции по длине `{12:2,16:3,18:3,20:4,22:4,24:4}` при опциях фундамента/стройработ/бетона на раме | `snapshot_builder.py:7`, `:51-71` |
| `model_code` | «ВЕСТА-{л}-{т}-{м}» | не установлено: читателей в `src/` не найдено |
| `installation_scope` | `shefmontazh`/`full`, если включён `install_default`, иначе None | `snapshot_builder.py:115-123` |
| `equipment.sensor_id/indicator_id/cable_m` | выбор менеджера | только `kp_restore.py:121-125` |
| `construction.*` (6 полей) | конструкция | только `kp_restore.py:127-137` |
| `metrology.is_dual_range` | режим диапазона | только `kp_restore.py:140` |
| `options.{key}` | только включённые: `price`, `qty`, `customer_side`, `retail`, `dealer_is_synthetic`, у бытовки `dimensions` | `snapshot_builder.py:74-92` |
| `custom_items[]` | `{name, price}` + `scope`, если не «other»; UI-id не сохраняется | `snapshot_builder.py:95-112` |
| `spec_overrides` | `spec_items_overrides` (ручные qty/price КП) | `kp_restore.py:190`, `from_kp.py:187` |
| `payment.preset_id/days/custom_text/split_state/v1_prepay/v2_prepay/v2_preship/v3_days/v3_trigger_id` | оплата | `kp_restore.py:207-216`, `kp_load.py:32` |

`kps.total_price` = итог с НДС за всё количество весов (`src/ui/sidebar.py:152-154`, `:112`). Версии схемы снапшота нет (`docs/AUDIT_2026-07.md:14`).

### 6.3 Что не сохраняется

| Что | Следствие | Ссылка |
|---|---|---|
| `price_class`, границы коридора, `label`, `block`, `is_on_request` опций | при восстановлении КП границы и имена берутся из текущего прайса | TECH_DEBT B27; `snapshot_builder.py:80-86` |
| Имена и суммы строк спецификации, текст оплаты, сгенерированные DOCX | при открытии договора всё пересобирается из снапшота и текущих справочников | `from_kp.py:122-152` |
| Версия prices.json / дата прайса | не установлено, по какому прайсу посчитан КП | — |
| `kp_number`, `client_name`, `manager_id`, `kp_date` внутри `data` | живут только в колонках | `kp_restore.py:90-97` |
| Состояние страницы «Договор» (реквизиты, правки позиций, строки оплаты, флаги, overrides, вложения, номер договора) | теряется с сессией; таблица `contracts` не используется | `src/contracts/state.py:8-44`; вызовов `save_contract` нет |
| `bytovka_dimensions` вне опции, `foundation_execution` без фундаментной опции | — | `snapshot_builder.py:87-91`, `:44-48` |
| Ключи `delivery_address`, `flags` | читаются `build_spec_v2_data`, но снапшот их не пишет (функция мёртвая, TECH_DEBT B17) | `from_kp.py:403-408` |

Прочее хранение: `prices.json` и `prices.backup.json` пишутся админкой в локальную ФС процесса (`src/admin/price_write_service.py:46-72`); договоры пишутся в `output/contracts/` (`2_Договор.py:78`); при падении `fill_spec_v2` трассировка пишется в `docs/v1.0_fillspec_traceback_*.txt` (`2_Договор.py:1184-1193`). Где развёрнут прод и сохраняется ли ФС между перезапусками — не установлено (в TECH_DEBT B25 упоминается Streamlit Cloud).

## 7. Модель (LLM)

| Пункт | Факт | Ссылка |
|---|---|---|
| Провайдер и модель | OpenRouter (`base_url https://openrouter.ai/api/v1`), `qwen/qwen3-235b-a22b`, ключ `OPENROUTER_API_KEY` | `src/contracts/extractor.py:93-109` |
| Где вызывается в проде | только режим B страницы «Договор» → `extract_kp_data_legacy(kp_path, card_path)` | `2_Договор.py:586-602`, `extractor.py:120-134` |
| Мёртвый вызов | `extract_card_data` (только карточка) — только в тестах | `extractor.py:137-168`, `tests/contracts/test_extractor.py:64` |
| Вход | текст PDF КП (pdfplumber, все страницы с маркерами «=== СТРАНИЦА N ===») + текст карточки (PDF через pdfplumber или DOCX: таблицы с дедупликацией объединённых ячеек + абзацы) | `extractor.py:34-82` |
| Проверка до вызова | меньше 50 непробельных символов в PDF → `NoTextLayerError`; для DOCX порог 1 | `extractor.py:20-31`, `src/contracts/requisites_extract.py:20` |
| Промпт | `prompts/extract_contract_data.txt` (135 строк): копировать дословно, ничего не пересчитывать; производные поля директора оставить пустыми; основание — в родительном падеже; НДС 22 или 20; номер/дата договора пустые; условия оплаты П1..П6 дословно; суммы цифрами с пробелами; ограждение — отдельной позицией; модель дословно; сроки — только число | `src/contracts/prompts/extract_contract_data.txt:1-69` |
| Что извлекает | `requisites` — 19 полей `ЗАКАЗЧИК_*`; `specification` — `ДОГОВОР_*`, `СПЕЦ_НОМЕР`, `СПЕЦ_П1..П6_НАИМЕНОВАНИЕ/СУММА/СРОК`, `СПЕЦ_ИТОГО(_ПРОПИСЬ)`, `СПЕЦ_НДС`, `СПЕЦ_ОПЛАТА_П1..П6`, `СПЕЦ_СРОК_ПОСТАВКИ/ФУНДАМЕНТ/МОНТАЖ`, `СПЕЦ_АДРЕС_ОБЪЕКТА`, `СПЕЦ_МОДЕЛЬ_КРАТКОЕ`, `СПЕЦ_МАКС_НАГРУЗКА` | `prompts/extract_contract_data.txt:70-135` |
| Проверка ответа | срезаются обёртки ```json, затем `json.loads`; схема, обязательные ключи и типы не проверяются; таймаута и повторов нет (не установлено: таймаут клиента `openai` по умолчанию); любое исключение → `st.error` | `extractor.py:103-117`, `2_Договор.py:599-602` |
| Постобработка | `fill_missing_derived`: полное наименование, пол, инициалы, должность и ФИО в РП дописываются только в пустые поля; warnings о неуверенном склонении | `src/contracts/requisites_transforms.py:210-220`, `2_Договор.py:594-597` |
| Валидация после | `validate_requisites` на каждом рендере: errors (пустые наименование/ИНН/р/с, контрольная сумма ИНН, длины р/с/к/с/БИК, ключ р/с с БИК, контрольная цифра ОГРН, согласование БИК↔к/с) блокируют генерацию; warnings — форма ИНН↔ОГРН, формат КПП, пустые БИК/к/с/банк/адрес/ФИО/основание | `src/contracts/requisites_validation.py:50-144`, `2_Договор.py:1043-1076` |
| Поле П6 | промпт возвращает `СПЕЦ_П6_*`, на странице редактируются только П1..П5; П6 уходит в `data` без показа | `2_Договор.py:109-139`, `src/contracts/state.py:97-104` |

Запасной путь без LLM (regex), доступен в обоих режимах:

| Шаг | Что делает | Ссылка |
|---|---|---|
| Текст из файла | DOCX — абзацы + таблицы (вложенные — один уровень); PDF — pymupdf, скан → `NoTextLayerError` | `src/contracts/requisites_extract.py:27-81` |
| Разбор | email и телефон → банк (сегмент забеливается) → наименование (ОПФ + кавычки или ИП + ФИО) → «ИНН/КПП» слитно → числа по длине и якорям (ИНН с контрольной суммой, 9 цифр БИК/КПП, 20 цифр р/с с префиксами 405–408 или к/с 301) → адреса по якорям «юрид/почт/факт» → ФИО и должность директора (консервативно) → основание. Возвращает только уверенно найденные поля | `src/contracts/requisites_parser.py:258-319` |
| Слияние | поля из `requisites_manual` (правленные вручную) не перетираются | `src/contracts/state.py:153-169` |
| Производные | полное наименование по ОПФ, пол по отчеству (по «Фамилия И.О.» не выводится), инициалы, должность в РП по словарю, ФИО в РП через petrovich (по инициалам — именительный + warning) | `src/contracts/requisites_transforms.py:223-288` |

## 8. DOCX-механика

Обозначения: «распаковка» — содержимое `word/document.xml` / `word/header1.xml` / `word/footer1.xml` шаблона, прочитанное zipfile + python-docx в scratchpad (оригиналы не менялись). Библиотеки в окружении: docxtpl 0.20.2, docxcompose 2.2.0; в `requirements.txt:3-4` пины `docxtpl>=0.18.0`, `docxcompose>=1.4.0`.

### 8.1 docxtpl и прочие механизмы подстановки

**8.1.1 Какой шаблон каким механизмом рендерится**

| Шаблон | Механизм | Точка вызова | Источник контекста |
|---|---|---|---|
| `templates/kp_template.docx` | docxtpl `DocxTemplate.render(context)`, без `jinja_env`/`autoescape` | `src/generators/kp_generator.py:261-263`; вызывается из `src/ui/sidebar.py:151` | `build_template_context` `src/generators/kp_generator.py:124-235` |
| `templates/contracts/supply_contract.docx` | docxtpl (1-й проход) + python-docx (2-й проход, `{{PAYMENT_SECTION}}`) | `src/contracts/compose.py:41-61` | `build_supply_context` `src/contracts/supply_filler.py:263-368`; ключи с `_` отфильтровываются `src/contracts/compose.py:31` |
| `templates/contracts/supply_appendix_1.docx` | docxtpl + пост-обработка строки ИТОГО | `src/contracts/compose.py:64-81` | тот же контекст |
| `templates/contracts/supply_appendix_2.docx` | docxtpl | `src/contracts/compose.py:84-90` | тот же контекст |
| `templates/contracts/contract.docx` | **НЕ docxtpl**: собственный заменитель `{{КЛЮЧ}}` на python-docx (`fill_template`) | `src/app_pages/2_Договор.py:1166` | `collect_for_template` `src/contracts/state.py:97-104` + дополнения `src/app_pages/2_Договор.py:1087-1108` |
| `templates/contracts/spec_v2.docx` | **НЕ docxtpl**: `fill_spec_v2` → `fill_spec_with_items` → `fill_template` + замена маркеров параграфами | `src/app_pages/2_Договор.py:1175` | тот же `data` + `deal` `src/app_pages/2_Договор.py:1127-1132` |
| `templates/contracts/spec_foundation_install.docx` (v1) | **НЕ docxtpl**: `fill_spec_with_items` (fallback, если `fill_spec_v2` упал) или `fill_template` (нет items) | `src/app_pages/2_Договор.py:1196`, `src/app_pages/2_Договор.py:1211` | тот же `data` |
| `data/fundament/build_task/*.docx`, `data/fundament/control_sheet/*.docx` | `fill_template` (не docxtpl) | `src/contracts/compose.py:170-174` | `data` + `ПРИЛОЖЕНИЕ_НОМЕР` |

**8.1.2 Плейсхолдеры в шаблонах (распаковка) и ключи контекста**

| Шаблон | Теги в шаблоне | Ключи контекста, которых нет в шаблоне |
|---|---|---|
| `templates/kp_template.docx` | body: `client_name, kp_number, kp_date, model_full_name, sensor_label, indicator_label, sensor_temp_range, indicator_temp_range, warranty_text, max_load_t, main_scale_label, platform_size, construction_description, {%tr for item in spec_items %}, item.name, item.price, item.term_days, {%tr endfor %}, total_price, total_term_days, vat_percent, payment_terms_block, kp_valid_days`; footer: `manager_full_name, manager_phone, manager_email` | `qty_scales, subtotal_per_1, subtotal_n` (`src/generators/kp_generator.py:224-226`) — используются только пост-обработкой (`src/generators/kp_generator.py:270-278`) |
| `supply_contract.docx` | `ДОГОВОР_НОМЕР, ДОГОВОР_ГОРОД, ДОГОВОР_ДАТА, ПОСТАВЩИК_*` (ЮР_АДРЕС, ИНН, КПП, ОГРН, БАНК, РС, КС, БИК, ДИРЕКТОР_ФИО, ДИРЕКТОР_ФИО_РП), `ПОКУПАТЕЛЬ_*` (НАИМЕНОВАНИЕ, ИМЕНУЕМ, ДИРЕКТОР_ДОЛЖНОСТЬ_РП, ДИРЕКТОР_ФИО_РП, ДЕЙСТВУЕТ, ОСНОВАНИЕ, ЮР_АДРЕС, ИНН, КПП, ОГРН, БАНК, РС, КС, БИК, ТЕЛЕФОН, EMAIL, ДИРЕКТОР_ДОЛЖНОСТЬ, ДИРЕКТОР_ФИО), `ТОВАР_НАИМЕНОВАНИЕ_КОЛВО, ТОВАР_НАИМЕНОВАНИЕ, СРОК_ПРОИЗВОДСТВА_ДН, СРОК_ДОСТАВКИ_ДН, АДРЕС_ПОСТАВКИ, СУММА_ЦИФРАМИ, СУММА_ПРОПИСЬЮ, СУММА_РУБ, PAYMENT_SECTION, СРОК_ДЕЙСТВИЯ_ДО, ТЕКУЩИЙ_ГОД`; управляющие: `{% if ПОКУПАТЕЛЬ_ДИРЕКТОР_ФИО_РП %}…{% endif %}`, `{% if ПОКУПАТЕЛЬ_КПП %}`, `{%p if ПОКУПАТЕЛЬ_ТЕЛЕФОН %}…{%p endif %}`; header: `ДОГОВОР_НОМЕР, ДОГОВОР_ДАТА` | ТТХ_*, `spec_rows`, `kit_rows`, `ПОСТАВЩИК_ДИРЕКТОР_ДОЛЖНОСТЬ` — нужны другим двум шаблонам (контекст общий на 3 шаблона, `src/contracts/compose.py:42,69,89`) |
| `supply_appendix_1.docx` | `ДОГОВОР_НОМЕР, ДОГОВОР_ДАТА, {%tr for row in spec_rows %}, row.name, row.sum, {%tr endfor %}, СУММА_ЦИФРАМИ, ПОСТАВЩИК_ДИРЕКТОР_ФИО, ТЕКУЩИЙ_ГОД, ПОКУПАТЕЛЬ_ДИРЕКТОР_ДОЛЖНОСТЬ, ПОКУПАТЕЛЬ_НАИМЕНОВАНИЕ, ПОКУПАТЕЛЬ_ДИРЕКТОР_ФИО` | — |
| `supply_appendix_2.docx` | `ДОГОВОР_НОМЕР, ДОГОВОР_ДАТА, ТОВАР_НАИМЕНОВАНИЕ, ТТХ_MAX, ТТХ_ОСЬ, ТТХ_РАССТОЯНИЕ_ТЕРМИНАЛ, ТТХ_ДИСКРЕТНОСТЬ, ТТХ_ГАБАРИТЫ, ТТХ_ТЕМПЕРАТУРА, ТТХ_СВЯЗЬ, ТТХ_ПИТАНИЕ, ТТХ_МОЩНОСТЬ, ТТХ_ГОСТ_СТРОКА, {%tr for item in kit_rows %}, item.name, item.qty, {%tr endfor %}` + подписи как в прил.1 | — |
| `contract.docx` | `ДОГОВОР_НОМЕР, ДОГОВОР_ДЕНЬ, ДОГОВОР_МЕСЯЦ, ДОГОВОР_ГОД, ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ, ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП, ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП, ДИРЕКТОР_ПРИЧАСТИЕ, ЗАКАЗЧИК_ОСНОВАНИЕ, СПЕЦ_НДС, ЗАКАЗЧИК_АДРЕС_ЮР, ЗАКАЗЧИК_АДРЕС_ПОЧТ, ЗАКАЗЧИК_ИНН, ЗАКАЗЧИК_КПП, ЗАКАЗЧИК_РС, ЗАКАЗЧИК_БАНК, ЗАКАЗЧИК_БИК, ЗАКАЗЧИК_КС, ЗАКАЗЧИК_ТЕЛЕФОН, ЗАКАЗЧИК_EMAIL, ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ, ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ`; header: `ДОГОВОР_НОМЕР, ДОГОВОР_ДАТА_ПОЛНАЯ` | не установлено: полный перечень ключей `data` (зависит от `requisites`/`specification` в state, `src/contracts/state.py:97-104`) |
| `spec_v2.docx` | `СПЕЦ_НОМЕР, ДОГОВОР_НОМЕР, ДОГОВОР_ДАТА_ПОЛНАЯ, ДОГОВОР_ДЕНЬ/МЕСЯЦ/ГОД, ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ, ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП, ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП, ДИРЕКТОР_ПРИЧАСТИЕ, ЗАКАЗЧИК_ОСНОВАНИЕ, СПЕЦ_П1..П5_НАИМЕНОВАНИЕ/СУММА, СПЕЦ_ИТОГО, СПЕЦ_ИТОГО_ПРОПИСЬ, СПЕЦ_ИТОГО_РУБ, СПЕЦ_НДС, PAYMENT_SECTION, TERMS_SECTION, CLAUSE_SECTION_{obligations_supplier, obligations_customer, special_conditions, final}, ТТХ_НОМЕР, СПЕЦ_МОДЕЛЬ_КРАТКОЕ, СПЕЦ_МАКС_НАГРУЗКА, ТТХ_НАГРУЗКА_НА_ОСЬ, ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА, ТТХ_ГРАНИЦА_1/2, ТТХ_ДИСКРЕТНОСТЬ_1/2, ТТХ_ГАБАРИТЫ, ТТХ_ТЕМПЕРАТУРА, КОМПЛЕКТ_НОМЕР, ТЕКУЩИЙ_ГОД, ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ, ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ`; header: `ДОГОВОР_НОМЕР, ДОГОВОР_ДАТА_ПОЛНАЯ` | — |
| `spec_foundation_install.docx` | как spec_v2, но вместо маркеров секций — `СПЕЦ_ОПЛАТА_П1..П6, СПЕЦ_СРОК_ПОСТАВКИ, СПЕЦ_СРОК_ФУНДАМЕНТ, СПЕЦ_СРОК_МОНТАЖ, СПЕЦ_АДРЕС_ОБЪЕКТА`; `ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ` (не КРАТКОЕ); ТТХ и комплект — статичный текст (см. 8.6) | — |
| `build_task/*.docx`, `control_sheet/*.docx` | `ПРИЛОЖЕНИЕ_НОМЕР, СПЕЦ_НОМЕР, ДОГОВОР_ДАТА_ПОЛНАЯ` (+ `ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ` в build_task, внутри text box); header: `ДОГОВОР_НОМЕР, ДОГОВОР_ДАТА_ПОЛНАЯ` | — |

**8.1.3 Jinja-окружение, фильтры, RichText/Listing**

| Аспект | Факт | Ссылка |
|---|---|---|
| Кастомные jinja-фильтры / `jinja_env` для docxtpl | Нет: `render` вызывается только с контекстом | `src/generators/kp_generator.py:263`, `src/contracts/compose.py:42`, `src/contracts/compose.py:69`, `src/contracts/compose.py:89` |
| `src/filters.py` | Не jinja-фильтры, а каскадная фильтрация моделей/опций (линейка → нагрузка → длина) | `src/filters.py:1`, `src/filters.py:23-99` (функции `available_max_loads`, `available_lengths`, `get_visible_options`) |
| autoescape | Не включён; у docxtpl 0.20.2 параметр `autoescape` по умолчанию False | вызовы выше; сигнатура `DocxTemplate.render` в site-packages (вне репо) |
| Отдельный jinja2 | Для текстов клауз: `jinja2.Environment(undefined=jinja2.Undefined)` — неизвестный параметр рендерится пустой строкой | `src/contracts/clauses_renderer.py:35-37` |
| jinja2 в зависимостях | Импортируется напрямую, но в `requirements.txt` не указан (приходит транзитивно) | `src/contracts/clauses_renderer.py:8`, `requirements.txt:1-13` |
| RichText | Многострочное имя позиции спецификации КП: 1-я строка — размер ячейки, остальные с `size=16` (half-points = 8pt). Докстринг говорит «9pt (size=18)» — расходится с константой | `src/generators/kp_generator.py:40`, `src/generators/kp_generator.py:84-96`, `src/generators/kp_generator.py:88`, `src/generators/kp_generator.py:150-155` |
| Listing (`\n` → `<w:br/>`) | `payment_terms_block` всегда; `main_scale_label` только если двухдиапазонный (есть `\n`) | `src/generators/kp_generator.py:117-121`, `src/generators/kp_generator.py:184-189` |
| Строка оплаты КП | `render_payment_block` отдаёт plain text: строки split-пресета начинаются с «— », в конце сноска «Сроки указаны в банковских днях.» | `src/generators/payment_renderer.py:26`, `src/generators/payment_renderer.py:100-103`, `src/generators/payment_renderer.py:200-229` |

**8.1.4 Пост-обработка после рендера / подстановки**

| Документ | Операция | Как найдена цель | Ссылка |
|---|---|---|---|
| КП | Маркеры `⟦MERGE:restart:N⟧` / `⟦MERGE:continue⟧` в колонке сроков → текст + `<w:vMerge>` (см. 8.3) | таблица с первой ячейкой «Наименование» | `src/generators/kp_generator.py:265-267` |
| КП | При `qty_scales > 1` строка ИТОГО → «ИТОГО за 1 весы» + клон «ИТОГО за N весов» | первая строка любой таблицы, где `cells[0].text.strip() == "ИТОГО"` | `src/generators/kp_generator.py:238-253`, `src/generators/kp_generator.py:269-278` |
| Договор поставки | Двупроход: в контексте `PAYMENT_SECTION = "{{PAYMENT_SECTION}}"` (docxtpl ставит сам маркер), затем python-docx заменяет параграф маркера строками `_payment_lines` (или удаляет его) | подстрока в `doc.paragraphs` | `src/contracts/supply_filler.py:357-360`, `src/contracts/compose.py:45-61` |
| Прил.1 поставки | При `_qty_scales > 1` последняя строка `Table[0]` → «за 1 весы» + «за N весов» | индекс таблицы 0, последняя строка | `src/contracts/compose.py:72-81`, `src/contracts/compose.py:106-127` |
| Все `fill_template`-документы | `merge_runs`: склейка соседних runs с побайтно одинаковым `rPr` (runs с `w:drawing` пропускаются), затем замена `{{КЛЮЧ}}` в runs | параграфы тела, ячеек, header/footer (только где есть `{{`) | `src/contracts/filler.py:18-52`, `src/contracts/filler.py:81-95`, `src/contracts/filler.py:143-165` |
| Все `fill_template`-документы | Нормализация кавычек в `ЗАКАЗЧИК_КРАТКОЕ/ПОЛНОЕ_НАИМЕНОВАНИЕ` | по ключу | `src/contracts/filler.py:15`, `src/contracts/filler.py:134-139` |
| Все `fill_template`-документы | В ячейке ТТХ, содержащей «78871-20», «ТПК «Тензосила»» → «Компания «Тензосила»» | подстрока текста ячейки | `src/contracts/filler.py:55-78`, `src/contracts/filler.py:154` |
| Все `fill_template`-документы | Удаление пустых параграфов тела, у которых есть `numPr` (недозаполненные пункты «2.5 ») | пустой текст + `numPr` | `src/contracts/filler.py:167-175` |
| Все `fill_template`-документы | Замена `{{КЛЮЧ}}` строковым replace по сырому XML всех `.xml` частей (для text box `w:txbxContent`) | сырая подстрока | `src/contracts/filler.py:98-116`, `src/contracts/filler.py:178` |
| Спецификация | Строки позиций `Table[0]` клонируются из строки 1, ИТОГО пересчитывается; клон ИТОГО при qty>1 | индекс таблицы 0 | `src/contracts/filler.py:284-362` |
| Спецификация v2 | Маркеры `{{PAYMENT_SECTION}}`, `{{TERMS_SECTION}}`, `{{CLAUSE_SECTION_*}}` → параграфы; таблица комплекта | см. 8.4, 8.6 | `src/contracts/spec_v2_filler.py:319-375` |

**8.1.5 НДС: где 20 → 22 и где ставка зашита**

| Место | Что | Ссылка |
|---|---|---|
| Генерация договора/спецификации | Если `СПЕЦ_НДС` пусто → «22»; если содержит подстроку «20» → все «20» заменяются на «22» (замена в значении, не в XML) | `src/app_pages/2_Договор.py:1096-1098` |
| Перенос из КП | `СПЕЦ_НДС` = «22» | `src/contracts/from_kp.py:278`, `src/contracts/from_kp.py:440` |
| КП | `vat_percent` из `VAT_RATE = 0.22` | `src/config.py:16`, `src/generators/kp_generator.py:228` |
| Строки оплаты договора | Литерал «в т.ч. НДС 22%» | `src/contracts/payment_line.py:85`, `src/contracts/payment_line.py:92` |
| Клауза зимнего удорожания | Литерал «в т.ч. НДС 22%» | `data/clauses.yaml:76` |
| Прил.1 поставки | Заголовок столбца «Цена, руб с НДС 22%» — статичный текст шаблона | распаковка `templates/contracts/supply_appendix_1.docx` |
| Пост-рендерная замена «20%»→«22%» в XML | Не найдена (grep `VAT`/`НДС`/`"22"` по `src/`) | — |

**8.1.6 Маркеры**

| Маркер | Где кодируется | Где декодируется | Примечание |
|---|---|---|---|
| `⟦MERGE:restart:<значение>⟧`, `⟦MERGE:continue⟧` | `encode_term_days_marker` — находится в `src/generators/spec_vmerge.py:30-41` (не в `payment_renderer.py`, как предполагал бриф); вызывается из `src/generators/kp_generator.py:65`, `:70`, `:80` | `src/generators/spec_vmerge.py:104-132` | `merge=None` → значение как есть |
| `{{PAYMENT_SECTION}}` | шаблоны supply_contract / spec_v2 | `src/contracts/compose.py:47-57`, `src/contracts/spec_v2_filler.py:319-332` | нет строк → параграф удаляется |
| `{{TERMS_SECTION}}` | spec_v2 | `src/contracts/spec_v2_filler.py:334-345` | |
| `{{CLAUSE_SECTION_<section_id>}}` | spec_v2 (вставлены `scripts/create_spec_v2_template.py:15-20`, `:57-66`) | `src/contracts/spec_v2_filler.py:361-375` | |
| `src/generators/payment_renderer.py` | маркеров не содержит, только plain text | `src/generators/payment_renderer.py:1-7` | |

### 8.2 docxcompose — склейка

| Сценарий | Функция | Порядок частей | Как каждая часть получена | Ссылка |
|---|---|---|---|---|
| Договор поставки (1 файл) | `compose_supply(context, output_path)` | supply_contract → supply_appendix_1 → supply_appendix_2 | каждый — docxtpl во временный файл; договор — второй проход PAYMENT_SECTION; прил.1 — разбиение ИТОГО | `src/contracts/compose.py:22-103` |
| Спецификация + приложения | `compose_spec_with_attachments(spec_path, attachments, data)` — перезаписывает spec на месте | Спецификация → Приложение №1 (строительное задание) → №2 (контрольный лист) | каждое приложение — `fill_template` с `ПРИЛОЖЕНИЕ_НОМЕР`, временный файл `_attach_{N}_{stem}.docx` рядом с выходом | `src/contracts/compose.py:150-183` |
| Договор + Спецификация (spec-флоу) | не склеиваются — два отдельных файла, две кнопки скачивания | — | — | `src/app_pages/2_Договор.py:1218-1224` |

| Аспект | Факт | Ссылка |
|---|---|---|
| Разрыв страниц | `page_break_before = True` на `doc.paragraphs[0]` каждого приложения перед `append` | `src/contracts/compose.py:97`, `src/contracts/compose.py:143-147`, `src/contracts/compose.py:177` |
| Нумерация приложений | Фиксированная: build_task → 1, control_sheet → 2 (control_sheet остаётся №2 даже без build_task) | `src/contracts/compose.py:130-140` |
| Условие включения | build_task: путь непуст и `build_task_source != "none"`; control_sheet: `include_control_sheet` и путь непуст | `src/contracts/compose.py:133-139` |
| Выбор файлов приложений | `resolve_build_task(snapshot)`, `resolve_control_sheet(execution, sections)`; имена `<исполнение>_<N>скц.docx`, regex допускает пробел перед «скц»; UI выбора (авто / без / вручную) | `src/contracts/fundament_lookup.py:10-31`, `src/contracts/fundament_lookup.py:88`, `src/contracts/fundament_lookup.py:156-167`, `src/app_pages/2_Договор.py:348-427` |
| Дубли файлов | Локально в `data/fundament/build_task/` есть пары `пандусный_С_Ф_3 скц.docx` / `пандусный_С_Ф_3скц.docx` и `пандусный_СЛ_ФЛ_3 скц.docx` / `…_3скц.docx`; файлы с пробелом не в git (`.gitignore:67`) — см. 4.4 | листинг каталога, `git status --ignored` |
| Предупреждение об отсутствии Прил.1 | если `foundation_scope` ∈ {customer_builds, contractor_supervised} и build_task не приложен | `src/app_pages/2_Договор.py:1200-1209` |
| Происхождение строительных заданий | DOCX сгенерированы из PDF скриптом: `pdf_source/` → `build_task/`, `pdf_source/control_sheet/` → `control_sheet/` | `scripts/pdf_to_fundament_core.py:19-24`, `scripts/pdf_to_fundament_docx.py:33-39` |
| Секции/колонтитулы | docxcompose пропускает body-level `sectPr` добавляемого документа и удаляет его header/footer-ссылки → на всех страницах колонтитул первого (главного) документа. Все шаблоны и приложения — одна секция A4 portrait, первый элемент тела — параграф (распаковка) | docxcompose 2.2.0 `composer.py:86-95`, `:105` (site-packages, вне репо) |
| Нумерация списков | `restart_numbering = True` по умолчанию — списки добавленного документа перезапускаются | docxcompose `composer.py:53` |
| Стили | `preserve_styles=False` по умолчанию; Composer создаётся без параметров | `src/contracts/compose.py:93`, `src/contracts/compose.py:165`; docxcompose `composer.py:49` |
| Конфликты одноимённых стилей между шаблонами | не установлено: нужна сверка styles.xml шаблонов и рендер склеенного файла | — |

### 8.3 vMerge-таблицы

| Аспект | Факт | Ссылка |
|---|---|---|
| Где применяется | Только КП, таблица спецификации; единственный вызов `apply_spec_vmerge` | `src/generators/kp_generator.py:267` (grep по `src/`) |
| Поиск таблицы | Первая таблица, у которой текст первой ячейки первой строки (runs всех параграфов, strip) == «Наименование» | `src/generators/spec_vmerge.py:89-101` |
| Колонка | Только 3-я `<w:tc>` строки (`tcs[2]`); строки с < 3 ячейками пропускаются | `src/generators/spec_vmerge.py:117-121` |
| Признак объединения | Роль позиции `resolve_term_role(item_key)`: `vesta-*` → scales → `restart` с числом дней, группа открыта; роль None (опции весов) → `continue`, если группа открыта, иначе пустая ячейка; прочие роли (orion, foundation, canopy, install, delivery, verification) → число без merge, группа закрывается; фиксированная роль (install/delivery/verification) с `customer_side` → пусто | `src/generators/kp_generator.py:43-81`, `src/term_days.py:41`, `src/term_days.py:48-74` |
| Запись результата | Текст ячейки заменяется: остаётся только первый run (его `rPr`), остальные runs удаляются; в `tcPr` ставится `<w:vMerge w:val="restart"/>` или `<w:vMerge/>`, прежний vMerge удаляется | `src/generators/spec_vmerge.py:49-86`, `src/generators/spec_vmerge.py:123-132` |
| Работа на уровне XML | Намеренно через `w:tr`/`w:tc`, т.к. `row.cells` после vMerge возвращает склеенные ячейки | `src/generators/spec_vmerge.py:104-111` |
| Ограничения | объединяется только группа «весы + следующие за ними опции»; маркер распознаётся только если весь текст ячейки ровно маркер (regex `^…$`) — иначе маркер остаётся в документе видимым; другие колонки не объединяются | `src/generators/spec_vmerge.py:26-27`, `src/generators/spec_vmerge.py:124-132` |
| Договорные документы | vMerge не используется; строки таблиц строятся клонированием строки-образца (`deepcopy`) | `src/contracts/filler.py:265-281`, `src/contracts/filler.py:330-351`, `src/contracts/spec_v2_filler.py:180-203` |

### 8.4 DSL клауз (`data/clauses.yaml`)

**8.4.1 Грамматика `applies_when`**

| Элемент | Разрешено | Ссылка |
|---|---|---|
| Разбор | `ast.parse(mode="eval")` + рекурсивная белая проверка узлов; иное → `ValueError` | `src/contracts/clauses_dsl.py:97-104`, `src/contracts/clauses_dsl.py:20-49` |
| Узлы | Constant, Name, BoolOp (`and`/`or`), UnaryOp (`not`), Compare, Tuple | `src/contracts/clauses_dsl.py:22-49` |
| Операторы сравнения | `==`, `!=`, `in`, `not in`; цепочки сравнений поддерживаются | `src/contracts/clauses_dsl.py:38-44`, `src/contracts/clauses_dsl.py:70-83` |
| Переменные (белый список) | `foundation_scope, installation_scope, verification_scope, has_orion, orion_poles_scope, winter_concrete, winter_surcharge`, литералы `true`/`false` | `src/contracts/clauses_dsl.py:7-17`, `src/contracts/clauses_dsl.py:57-60` |
| Переменная `base_type` | Вычисляется в контексте, но в белом списке её нет → в yaml недоступна | `src/contracts/clauses_context.py:82`, `src/contracts/clauses_context.py:115` |
| Отсутствующая в контексте переменная | `KeyError` → клауза пропускается с warning | `src/contracts/clauses_dsl.py:61-62`, `src/contracts/clauses_renderer.py:63-67` |
| Значения по документации yaml | foundation_scope: none / customer_builds / contractor_full / contractor_with_materials / rama / contractor_supervised / existing_foundation; installation_scope: none / full / shefmontazh; verification_scope: none / supplier / customer; orion_poles_scope: none / by_customer / by_contractor | `data/clauses.yaml:4-13` |

**8.4.2 Контекст DSL (`build_clauses_context(deal)`)**

| Переменная | Правило | Ссылка |
|---|---|---|
| installation_scope | есть item `installation`: metadata.scope fundament/rama/прочее → full, shefmontazh/full → как есть; иначе override; иначе none | `src/contracts/clauses_context.py:53-65` |
| foundation_scope | item `foundation` → маппинг scope (fundament_jb/pandus_* → contractor_full, rama_* → rama, …), неизвестное → contractor_full; item `rama` → rama; override; иначе customer_builds при монтаже, none без него. `existing_foundation` — только через override | `src/contracts/clauses_context.py:5-17`, `src/contracts/clauses_context.py:67-80` |
| verification_scope | item `verification`: customer_side → customer, иначе supplier; override; иначе none | `src/contracts/clauses_context.py:84-91` |
| has_orion | есть item `orion` | `src/contracts/clauses_context.py:94` |
| orion_poles_scope | при ОРИОН: item `orion_install` → by_contractor; override; иначе by_customer; без ОРИОН → none | `src/contracts/clauses_context.py:96-105` |
| winter_concrete, winter_surcharge | только из `deal.flags` | `src/contracts/clauses_context.py:107-111` |

**8.4.3 Загрузка и валидация yaml**

| Проверка | Факт | Ссылка |
|---|---|---|
| Парсер | strictyaml со схемой `Any()` — типы/структура схемой не проверяются | `src/contracts/clauses_loader.py:48` |
| Дубли id клауз | `ValueError` | `src/contracts/clauses_loader.py:63-66` |
| Неизвестная section | `ValueError` | `src/contracts/clauses_loader.py:68-70` |
| `applies_when` | парсится при загрузке, ошибка → `ValueError`; по умолчанию `"true"` | `src/contracts/clauses_loader.py:72-76` |
| jinja-параметры в `text` | только debug-лог, не проверяются | `src/contracts/clauses_loader.py:78-81` |
| `order` | по умолчанию 0 | `src/contracts/clauses_loader.py:86` |
| `section_number`, `title`, `related_to` | загружаются, в рендере/нумерации не используются (grep по `src/`) | `src/contracts/clauses_loader.py:54-58`, `src/contracts/clauses_loader.py:89` |
| Кэш | библиотека грузится один раз в глобал `_LIBRARY` — правка yaml требует перезапуска процесса | `src/contracts/clauses_renderer.py:15-16`, `src/contracts/clauses_renderer.py:28-32` |

**8.4.4 Рендер и попадание в документ**

| Шаг | Факт | Ссылка |
|---|---|---|
| Фильтр | по секциям в порядке списка `sections` yaml; внутри — сортировка по `order` (стабильная → при равных order порядок файла) | `src/contracts/clauses_renderer.py:55-69` |
| Нумерация | сквозная плоская, начиная с 4, по порядку секций yaml | `src/contracts/clauses_renderer.py:71-77` |
| `obligations_range` | номера клауз obligations_customer (кроме `customer_unable_to_accept_team_delays_work`) + special_conditions; «первый-последний» или один номер | `src/contracts/clauses_renderer.py:17`, `src/contracts/clauses_renderer.py:79-94` |
| jinja-параметры текста | `foundation_term_days_by_customer` (metadata foundation, дефолт 60), `scales_or_with_orion`, `install_site_label` (rama → «месту установки», иначе «фундаменту»), `obligations_range`, `delivery_address_text` (без хвостовой точки), `winter_surcharge_amount` (разделитель тысяч пробелом) | `src/contracts/clauses_renderer.py:96-115`, `data/clauses.yaml:15-21` |
| Вставка | для каждой секции из захардкоженного `_CLAUSE_SECTION_ORDER` ищется первый параграф тела, содержащий `{{CLAUSE_SECTION_<id>}}`; перед ним вставляются параграфы «`N. текст`» (выравнивание по ширине, без копирования rPr/pPr маркера), маркер удаляется; клауз нет → маркер удаляется; маркер не найден → молча (без warning) | `src/contracts/spec_v2_filler.py:34-39`, `src/contracts/spec_v2_filler.py:361-375` |
| Многострочный текст клаузы | один параграф, строки через `<w:br/>` | `src/contracts/spec_v2_filler.py:117-137` |
| Номера ТТХ и комплекта | `ТТХ_НОМЕР` = макс. номер клаузы + 1, `КОМПЛЕКТ_НОМЕР` = + 2 (нет клауз → 4 и 5) | `src/contracts/spec_v2_filler.py:293-304` |
| Оплата (spec) | строки «2.N. …» строит `format_payment_line` с индексом из страницы; вставка с наследованием rPr/pPr параграфа-маркера | `src/app_pages/2_Договор.py:1168-1173`, `src/contracts/payment_line.py:63-97`, `src/contracts/spec_v2_filler.py:140-168` |
| Оплата (supply) | строки «4.2.N. …» с текстами триггеров поставки | `src/contracts/supply_filler.py:329-334` |
| Страж A5 | fallback из `СПЕЦ_ОПЛАТА_П1..6` обязан начинаться с «цифра.цифра», иначе `PaymentLinesLiteError` → генерация останавливается | `src/contracts/spec_v2_filler.py:17-31`, `src/contracts/spec_v2_filler.py:206-208`, `src/contracts/spec_v2_filler.py:320-327`, `src/app_pages/2_Договор.py:1176-1180` |
| Сроки | строки «- …»: фундамент (если фундамент Подрядчика), поставка (всегда, ссылка «п.2.1» или «п.2.1 и п.2.2»), монтаж[+поверка] (если монтаж) | `src/contracts/terms_renderer.py:30-84` |
| Заголовки «2. Порядок оплаты», «3. Срок поставки» | литеральная нумерация в тексте шаблона, Word-`numPr` снят | `scripts/patch_spec_v2_headings_numpr.py:3-8` |

### 8.5 Генерация шаблонов скриптами

| Скрипт | Вход → выход | Что делает | Повторный прогон на текущих шаблонах |
|---|---|---|---|
| `src/generators/make_template.py` | `03_knowledge_base/sample_kps/Гипсобетон_ВЕСТА-С-80-18.docx` → `templates/kp_template.docx` | замена литералов эталона (клиент, номер, дата, «36 месяца», «18×3», имя/телефон/email менеджера и т.п.) на jinja-теги, ТХ-таблица по индексам строк `tables[2]` с проверкой подписей, преобразование спецификации в `{%tr%}`-цикл, удаление блока «Спецификация ПАК ОРИОН», замена стриков пустых параграфов на page break, sanity-check тегов, PT Sans, оранжевого D04514 | Каталога `03_knowledge_base` нет; эталон лежит в `knowledge_base/sample_kps/` → скрипт в текущем виде не запустится. Все коммиты `kp_template.docx`, кроме `57b36eb`, шли вместе с правкой скрипта (git log). Не установлено: воспроизводит ли скрипт текущий шаблон байт-в-байт (нужен прогон с исправленным SRC). README описывает устаревшие теги `division_info`, `payment_line_1/2` | `src/generators/make_template.py:21-22`, `:117-128`, `:166-197`, `:269-339`, `:434-694`, `:700-785`; `templates/README.md:23`, `:61-62`, `:66-81` |
| `scripts/create_spec_v2_template.py` | `spec_foundation_install.docx` → `spec_v2.docx` | удаляет параграфы между «Выезд строительной» и «Технические характеристики», вставляет 4 маркера `{{CLAUSE_SECTION_*}}` | перезапишет `spec_v2.docx` и уничтожит все последующие патчи | `scripts/create_spec_v2_template.py:12-13`, `:23-68` |
| `scripts/patch_spec_v2_template.py` | `spec_v2.docx` на месте | кавычки «Тензосила»», маркеры PAYMENT/TERMS, ТТХ-плейсхолдеры, комплект, «2026» → `{{ТЕКУЩИЙ_ГОД}}`, приложение; часть замен — строковым replace по сырому XML | заявлен идемпотентным | `scripts/patch_spec_v2_template.py:1-5`, `:54-189`, `:171`, `:273-284` |
| `scripts/patch_spec_v2_numbering.py` | `spec_v2.docx`, бэкап `*.docx.bak` | плейсхолдеры номеров заголовков ТТХ/комплекта, снятие numPr | «одноразовый»; объясняет `templates/contracts/*.docx.bak` (в git их нет) | `scripts/patch_spec_v2_numbering.py:1`, `:11-12`, `:36-60` |
| `scripts/patch_spec_v2_headings_numpr.py` | `spec_v2.docx` | A8: снять numPr с «Порядок оплаты»/«Срок поставки» | идемпотентен | `scripts/patch_spec_v2_headings_numpr.py:1-11`, `:28-32` |
| `scripts/patch_spec_ruble_word.py` | spec_v2, spec_foundation_install, supply_contract | A6: «рублей» → `{{СПЕЦ_ИТОГО_РУБ}}` / `{{СУММА_РУБ}}` | идемпотентен (0 целей → не пишет) | `scripts/patch_spec_ruble_word.py:1-14`, `:40` |
| `scripts/patch_spec_template.py` | spec_foundation_install | вёрстка (баги 5, 6): pageBreakBefore, keepWithNext, cantSplit; raw-XML replace | — | `scripts/patch_spec_template.py:1-9`, `:20`, `:74-88` |
| `scripts/patch_template.py` | contract, spec_foundation_install | правка строк колонтитула/ячеек | «одноразовый» | `scripts/patch_template.py:1`, `:47-83` |
| `scripts/patch_placeholder_names.py` | contract, spec_foundation_install | `ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ` → `ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ` | сейчас `contract.docx` и `spec_v2.docx` содержат КРАТКОЕ (распаковка) — замена была откатана (удалённый `patch_customer_short_name_templates.py`, коммит 61a4a18) → повторный прогон даст регресс | `scripts/patch_placeholder_names.py:20-26`, `:123-130` |
| `scripts/create_supply_templates.py` | `docs/source/Автовесы _Поставка.docx` → 3 supply-шаблона | обрезка тела по маркерам, замены по подстрокам/regex | после него шаблоны правились патчами и вручную (см. ниже) | `scripts/create_supply_templates.py:1-15`, `:24-114` |
| `scripts/patch_supply_appendix1_spec.py` | supply_appendix_1 | spec-таблица → 3-строчный `{%tr%}`-цикл (однострочный docxtpl рендерит с ошибкой) | «разовый» | `scripts/patch_supply_appendix1_spec.py:1-13` |
| `scripts/patch_supply_headers.py` | 3 supply-шаблона | header: литерал «№ 86/2026 от 26.04.2026 года» → `{{ДОГОВОР_НОМЕР}}`/`{{ДОГОВОР_ДАТА}}`; схлоп пробелов перед «п. 4.2» | «разовый» | `scripts/patch_supply_headers.py:1-9`, `:15-16` |
| `scripts/patch_supply_contract_qty.py` | supply_contract | в абзаце-якоре §1.1 `{{ТОВАР_НАИМЕНОВАНИЕ}}` → `{{ТОВАР_НАИМЕНОВАНИЕ_КОЛВО}}`; guard «ровно один абзац» | «разовый» | `scripts/patch_supply_contract_qty.py:1-21` |
| `scripts/verify_supply_templates.py` | 3 supply-шаблона → `docs/source/verify_templates.txt` | проверка ожидаемых/запрещённых строк (в т.ч. «86/2026», ФИО из образца) | только чтение шаблонов | `scripts/verify_supply_templates.py:7-51`, `:106` |
| `scripts/sanitize_template_namespaces.py` | contract, spec_v2 (`document.xml`) | лечит ns0-порчу от ElementTree: пересборка корня с каноническим nsmap из «здоровых» git-коммитов (`git show`), резерв — таблица стандартных префиксов; ассерты текста/структуры | идемпотентен; требует git-историю с коммитами 8795cca/0e16119 | `scripts/sanitize_template_namespaces.py:1-13`, `:28-31`, `:33-55`, `:58-72`, `:114-128`, `:131-144` |
| `tests/test_template_namespaces.py` | — | страж: корень `w:document` с префиксом `w`, все префиксы `mc:Ignorable` объявлены | охват `git ls-files templates/**/*.docx` = только 6 файлов `templates/contracts/*.docx` (проверено командой); `kp_template.docx` и приложения `data/fundament/` не проверяются; проверяется только `word/document.xml` (не header/footer) | `tests/test_template_namespaces.py:19-34` |
| Ручные правки в Word | коммит 974ce59 изменил 3 supply-шаблона без скриптов; b6f8ded создал `contract.docx` и `spec_foundation_install.docx` без скрипта | — | `git show --stat 974ce59`, `git show --stat b6f8ded` |
| **Вывод для переноса** | Шаблоны `templates/contracts/*.docx` — результат цепочки разовых патчей с якорями на уже изменённый текст + ручных правок; пересобрать их скриптами нельзя → переносить DOCX как есть. `kp_template.docx` скриптом теоретически воспроизводим, но SRC-путь сломан | — | см. строки выше |

### 8.6 Хрупкие места

| Что | Где | Почему хрупко | Что сломается при правке шаблона в Word |
|---|---|---|---|
| Таблица позиций спецификации по индексу | `src/contracts/filler.py:321-351` | `doc.tables[0]`; строка 1 — образец; последняя — ИТОГО; все строки между ними удаляются | Добавили таблицу выше — позиции запишутся не туда; добавили строку-примечание под ИТОГО — она станет «ИТОГО», настоящий ИТОГО удалится |
| Таблица комплекта по индексу | `src/contracts/spec_v2_filler.py:180-203` | `doc.tables[2]`, строка 1 — образец (удаляется) | Новая таблица перед комплектом → комплект запишется в чужую таблицу, без ошибки |
| ИТОГО прил.1 поставки | `src/contracts/compose.py:114-126` | `doc.tables[0]`, последняя строка; колонки 0/1 | Строка/таблица после ИТОГО → перепишется не та строка |
| ИТОГО КП по точному тексту | `src/generators/kp_generator.py:244-253` | `cells[0].text.strip() == "ИТОГО"`, колонки 0/1/2 | Переименование («Итого:», «ИТОГО с НДС») → строка «за N весов» молча не появится |
| Таблица vMerge по заголовку | `src/generators/spec_vmerge.py:89-101`, `:119-121` | текст первой ячейки == «Наименование»; колонка сроков — `tcs[2]` | Переименование заголовка или перестановка колонок → маркеры `⟦MERGE…⟧` останутся в КП видимым текстом |
| Маркеры секций только в теле | `src/contracts/spec_v2_filler.py:159-177`, `:365-375` | поиск в `doc.paragraphs` (без таблиц); заменяется весь параграф | Маркер перенесён в ячейку → не найден (PAYMENT/TERMS — warning в лог, CLAUSE — молча); текст рядом с маркером в том же параграфе удалится |
| Порядок нумерации vs порядок вставки клауз | `src/contracts/clauses_renderer.py:74-77`, `src/contracts/spec_v2_filler.py:34-39` | номера идут по порядку секций yaml, вставка — по захардкоженному списку | Переставили секции в yaml или маркеры в шаблоне → номера пунктов не по возрастанию |
| Жёсткие перекрёстные ссылки на структуру | `src/contracts/clauses_renderer.py:73`, `src/contracts/terms_renderer.py:56`, `data/clauses.yaml:108`, `data/clauses.yaml:277` | клаузы с 4; «п.2.1 и п.2.2»; «Приложение №1»; «п.п. 3.2-3.4 Договора» | Вставка/удаление раздела в шаблоне или договоре → ссылки укажут не туда |
| `merge_runs` требует одинаковый `rPr` | `src/contracts/filler.py:39-52`, `:86-95` | склейка только при побайтно равном `rPr`; сейчас 7 тегов spec_v2 разбиты на runs с одинаковым rPr (распаковка: CLAUSE_SECTION_×4, ДОГОВОР_ДАТА_ПОЛНАЯ, ТТХ_ГРАНИЦА_1/2) | Правка части тега в Word (другой lang/шрифт) → `{{КЛЮЧ}}` не заменится |
| Детектор незаполненных тегов неполный | `src/contracts/filler.py:181-201`; вызов `src/app_pages/2_Договор.py:1148-1150`, `:1213-1216` | сканирует только параграфы тела и ячейки; header/footer/text box — нет | Неподставленный тег в колонтитуле или text box уйдёт клиенту без предупреждения |
| docxtpl без autoescape | `src/generators/kp_generator.py:263`, `src/contracts/compose.py:42`, `:69`, `:89` | значения вставляются в XML без экранирования; проверка в scratchpad на docxtpl 0.20.2: «ООО «А&Б» <1>» → «ООО «А» 1>» — текст молча обрезается | Не зависит от шаблона: любой `&`/`<` в имени клиента, адресе, реквизитах (КП, договор поставки) теряет часть текста |
| Raw-XML replace без экранирования | `src/contracts/filler.py:98-116` | строковый replace по XML всех частей; значение не экранируется; не работает для тегов, разбитых на runs | Тег в text box (сейчас только `ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ` в spec_foundation_install и 20 build_task — распаковка) разбит Word-ом → не заменится; `&` в значении → битый DOCX |
| Удаление пустых нумерованных параграфов | `src/contracts/filler.py:167-175` | любой пустой параграф тела с `numPr` удаляется | Намеренно пустой пункт списка в шаблоне исчезнет |
| Пустые/нулевые значения | `src/contracts/filler.py:94`, `:113` | `str(value) if value else ''` | Значение 0 печатается пустым |
| Колонтитулы | `src/contracts/filler.py:159-165` | обрабатываются только параграфы с `{{` в тексте; таблицы колонтитулов — нет | Тег, перенесённый в таблицу колонтитула, не заполнится |
| Госреестр/юрлицо по литералам | `src/contracts/filler.py:55-78` | ищет «78871-20» и «ТПК «Тензосила»» в тексте ячейки | Смена номера/формулировки в шаблоне → замена на «Компания «Тензосила»» молча не произойдёт |
| НДС через подстроку «20» | `src/app_pages/2_Договор.py:1096-1098` | заменяются все вхождения «20» в значении `СПЕЦ_НДС` | Значение вроде «НДС 20% (2020)» → «НДС 22% (2222)» |
| Реквизиты поставщика в двух местах | `src/contracts/supplier.py:3-23` | `SUPPLIER` для supply-шаблонов + статичный текст в `contract.docx`/`spec_v2.docx` | Смена реквизитов в Word без правки кода (или наоборот) → расхождение между типами договоров |
| ТТХ/комплект продублированы | `src/contracts/supply_filler.py:53-61`, `src/contracts/kit_renderer.py:52-60` | константы связи/питания/мощности и наименования комплекта в коде; в spec_v2 строки 7-10 ТТХ — статичный текст (распаковка) | Правка значения в одном месте не попадёт в другой тип документа |
| Fallback на spec v1 со статичными ТТХ | `src/app_pages/2_Договор.py:1181-1196` | при любом исключении `fill_spec_v2` генерируется v1; в v1 ТТХ («11», «18×3», «От -30 до +40») и комплект (DHM9B, КБТ-8-Ц) — статичный текст (распаковка) | Документ уходит с ТТХ/комплектом другой модели; пользователю показывается только `st.error` |
| `pageBreakBefore` на первый параграф | `src/contracts/compose.py:143-147` | ставится на `doc.paragraphs[0]`, а не на первый элемент тела | Приложение, начинающееся с таблицы, → разрыв окажется после таблицы |
| Колонтитулы приложений теряются | docxcompose `composer.py:86-95`, `:105` | у добавленных документов sectPr и header-ссылки отбрасываются | Отдельный колонтитул, добавленный в шаблон приложения, в склейке не появится |
| `{%tr%}`-циклы | `scripts/patch_supply_appendix1_spec.py:7-10` | рабочая форма — 3 строки (for / данные / endfor) | Склейка строк цикла в одну в Word → ошибка рендера docxtpl |
| DSL: `in` со строкой | `src/contracts/clauses_dsl.py:78-81` | `x in ("a")` — не кортеж, а строка → проверка подстроки | Опечатка в yaml (кортеж из одного элемента без запятой) даёт ложные срабатывания клауз |
| make_template по литералам эталона | `src/generators/make_template.py:21`, `:126-128`, `:447-615`, `:619-635` | ищет конкретные тексты эталона и индексы строк `tables[2]`; SRC-путь не существует | Регенерация КП-шаблона невозможна без правки скрипта; ручная правка `kp_template.docx` разойдётся со скриптом |
| Страж ns-порчи с дырой | `tests/test_template_namespaces.py:19-34` | glob не захватывает `templates/kp_template.docx`; проверяется только `document.xml` | Порча КП-шаблона или колонтитулов после скриптовой правки не будет поймана тестом |
| Оглавление КП | `templates/README.md:120-123` | TOC не обновляется автоматически | Номера страниц в оглавлении КП устаревают, обновление вручную в Word |
| Зеркало генерации в тестах | `src/app_pages/2_Договор.py:1078-1079`, `tests/autoverify/runner.py:9-11` | блок генерации продублирован в autoverify-раннере (fallback на v1 там не реплицирован) | Изменение пайплайна в одном месте не отразится в другом |
| Мёртвый код | `src/contracts/filler.py:204-227` | `remove_empty_paragraphs` без вызовов в `src/` (grep) | — (не переносить) |

## 9. Эталоны

### 9.1. Механика сравнения

| Аспект | Факт |
|---|---|
| Фикстура | JSON: `meta{id,flow,comment}`, `kp_state` (плоский state КП, `kp_date` обязателен), `requisites`, `contract{date,number,spec_number,object_address,scope_overrides,flags,payment_rows,valid_until}` (`tests/golden/fixtures.py:47-52`, `:79-124`) |
| Генерация | `tests/autoverify/runner.py:96-219` — зеркало кнопки страницы: КП → снапшот → items → `decide_contract_type`; если ≠ `meta.flow` — AssertionError (`:157-161`); supply → `compose_supply`; spec → contract + `fill_spec_v2` + авто-стройзадание без контрольного листа (`:194-203`). Отличия от страницы: год пинуется, fallback v1 не реплицируется (`:7-12`); `payment_rows: null` → автосев из снапшота (`:84-92`) |
| Что сравнивается | для каждого DOCX: `dump_docx(path) + buckets_section(items)` == `tests/golden/expected/<имя>.dump.txt` построчно, точное равенство строк (`tests/golden/test_golden.py:17-28`); для КП items — от `build_spec_items` (КП-билдер), для остальных — от `build_specification_items` (`:22`) |
| Дамп | канонический текст `=== DOCX-DUMP v1 ===`: docDefaults, использованные стили по имени, нумерации по алиасам, sha1 картинок, тело P/R/TBL с явными свойствами, колонтитулы (`tests/golden/dump_docx.py:10-39`) |
| Игнорируется | rsid*, paraId/textId, proofErr, закладки, lang, noProof, szCs/bCs/iCs, границы fldChar, все rId, имена/порядок ZIP-частей, docProps, settings, theme, fontTable, mc:Fallback, w:del (`tests/golden/dump_docx.py:41-44`); соседние раны с одинаковой rPr склеиваются (`:30-31`) |
| BUCKETS | `[ITEMS]` id/имя/payment_group(+custom_scope), `[GROUPS]` 4 бакета, `[IV]` has_install/verification/orion_install + guard (`tests/golden/dump_buckets.py:13-46`) |
| Побайтово | нет: `expected/*.docx` лежат рядом, но тестом не читаются (`tests/golden/test_golden.py:23-25`) |
| Детерминизм | два прогона дают равные дампы (`tests/golden/test_freeze_determinism.py:8-19`) |
| Обновление | только `python -m tests.golden.freeze` (`tests/golden/freeze.py:25-34`) |

### 9.2. G-01..G-11

Общее для всех: модель `vesta-сл-60-18` (кроме G-05 — `vesta-с-60-18`), qty=1, `scope_overrides={}`.

| id | Вход (ключевые поля) | Документы | Вид §4 | Сравнение |
|---|---|---|---|---|
| G-01 | foundation_std_sl_fl_18, install_default, verification_default, delivery; пандусный; split_by_items (`tests/golden/fixtures/G-01.json:34-55`) | kp, dogovor, spec (+прил.№1 пандусный СЛ_ФЛ 3скц) | С1 | dump+BUCKETS ×3 |
| G-02 | frame_18, ramp_set_fl_sl, install_default, verification, delivery; `is_shefmontazh: true`; ИП, директор-женщина (`tests/golden/fixtures/G-02.json:5`, `:33-58`) | kp, dogovor, spec (без приложения) | С8 | dump+BUCKETS ×3; в дампе шеф-клаузы и площадка 30×4 (`tests/golden/expected/G-02_spec.dump.txt:105-122`) |
| G-03 | concrete_base_on_frame, install, verification, delivery; flags winter_concrete/winter_surcharge=true, 200000 (`tests/golden/fixtures/G-03.json:35-54`, `:93-95`) | kp, dogovor, spec (+прил.№1 rama_concrete 3скц, `tests/golden/expected/G-03_spec.dump.txt:355-359`) | С7. **Зима не покрыта**: comment обещает «ветки clauses по зиме» (`tests/golden/fixtures/G-03.json:5`), но foundation_scope=rama → зимние клаузы не срабатывают (`data/clauses.yaml:74`); в дампе 0 вхождений «зимн» | dump+BUCKETS ×3 |
| G-04 | frame_18, delivery; valid_until (`tests/golden/fixtures/G-04.json:35-46`) | kp, dogovor_postavki | Д1 (рама агрегирована в строку весов: 1 935 972, `tests/golden/expected/G-04_dogovor_postavki.dump.txt:254-257`) | dump+BUCKETS ×2 |
| G-05 | foundation_s_f_18 (приямок), install, verification, delivery, orion_standard, orion_cable_poles (`tests/golden/fixtures/G-05.json:34-63`) | kp, dogovor, spec (+прил.№1 приямок 3скц, `tests/golden/expected/G-05_spec.dump.txt:400-404`) | С3 (опоры by_contractor) | dump+BUCKETS ×3 |
| G-06 | как G-01 + custom_item «Антивандальная табличка» (тип other) + override цены поверки 55000 (`tests/golden/fixtures/G-06.json:53-57`) | kp, dogovor, spec | С1 (ручные позиции, 4 бакета — `tests/golden/expected/G-06_spec.dump.txt:473-477`) | dump+BUCKETS ×3 |
| G-07 | как G-03 без зимы, `is_dual_range: true` (`tests/golden/fixtures/G-07.json:31-54`) | kp, dogovor, spec (+rama_concrete 3скц) | С7 (двухдиапазонная метрология) | dump+BUCKETS ×3 |
| G-08 | без опций, prepay_100 (`tests/golden/fixtures/G-08.json:35-37`) | kp, dogovor_postavki | Д1 (минимальный) | dump+BUCKETS ×2 |
| G-09 | foundation_std, verification, delivery + custom «Монтаж и пусконаладка» scope=installation (`tests/golden/fixtures/G-09.json:36-53`) | kp, dogovor, spec | С1 (монтаж ручной позицией) | dump+BUCKETS ×3 |
| G-10 | foundation_std, install, delivery, без поверки (`tests/golden/fixtures/G-10.json:36-51`) | kp, dogovor, spec | С1 без поверки («монтаж Весов», `tests/golden/expected/G-10_spec.dump.txt:111`) | dump+BUCKETS ×3 |
| G-11 | как G-01, model_price 1800001, prepay_100 (ИТОГО 3 450 001) (`tests/golden/fixtures/G-11.json:5`, `:55`) | kp, dogovor, spec | С1 (склонение «рубль») | dump+BUCKETS ×3 |

### 9.3. Виды §4 без golden-эталона

- Д2 — fallback v1 (`spec_foundation_install.docx`), включая режим «Из PDF файла».
- С2 — фундамент + зимний бетон (G-03 не покрывает, см. выше).
- С4 — стройка с материалами Заказчика (`construction_works_*`).
- С5 — Заказчик строит фундамент + монтаж.
- С6 — Заказчик строит + ОРИОН.
- С9 — курирование.
- С10 — готовый фундамент (override; во всех G `scope_overrides={}`).
- С11 — шеф-монтаж не на раме.
- С12 — работы без монтажа весов (фундамент/ОРИОН без монтажа).
- С13 — ручной override типа документа (и обратный «Поставка» при spec-сделке).
- Внутри покрытых видов без эталона: С7 с `frame_*` + монтаж (обе G — concrete_base), rama_road_slabs/pag_slabs; С3 с опорами Заказчика; поверка Заказчиком (`customer_side`); qty>1 (все G qty=1); контрольный лист (runner всегда выключает, `tests/autoverify/runner.py:200-201`); ручной выбор стройзадания.

### 9.4. Вторичное покрытие: `tests/autoverify/fixtures/*.json`

| Фикстура | Вид §4 | Ссылка |
|---|---|---|
| fundament_montazh_poverka | С1 | `tests/autoverify/fixtures/fundament_montazh_poverka.json:6` |
| days_singular, ruble_declension | С1 (prepay_100, склонения) | `tests/autoverify/fixtures/days_singular.json:6`, `ruble_declension.json:6` |
| winter_concrete | **С2** (единственное покрытие зимы) | `tests/autoverify/fixtures/winter_concrete.json:6` |
| orion | С3 (без опции опор, клауза про опоры всё равно срабатывает — по orion_install) | `tests/autoverify/fixtures/orion.json:6` |
| orion_poles | С3 с опорами | `tests/autoverify/fixtures/orion_poles.json:6` |
| montazh_orion | **С6** | `tests/autoverify/fixtures/montazh_orion.json:6` |
| rama_montazh, rama_montazh_x2 | С7 (concrete), x2 — qty=2 | `tests/autoverify/fixtures/rama_montazh_x2.json:21` |
| rama_ploshadka_montazh | **С7 с frame_18** | `tests/autoverify/fixtures/rama_ploshadka_montazh.json:6` |
| rama_shefmontazh | С8 | `tests/autoverify/fixtures/rama_shefmontazh.json:6` |
| rama_bez_montazha, rama_bez_montazha_x2 | Д1 (x2 — qty=2) | `tests/autoverify/fixtures/rama_bez_montazha_x2.json:21` |

Не покрыты ни golden, ни autoverify: Д2, С4, С5, С9, С10, С11, С12, С13, контрольный лист, rama_road/pag_slabs, поверка Заказчиком.

## 10. Баги и подозрительное

### 10.1 Открытые записи `docs/TECH_DEBT.md`

| ID | Что | Где | Видит ли менеджер в документе | Риск |
|---|---|---|---|---|
| B1 | два семейства id позиций (ключи опций КП и канонические id договора), формулировки оплаты матчат оба | `src/payment_wording.py:108-123` | нет, пока не добавят новую позицию | средний при расширении каталога |
| B2 | не проверяется полная контрольная сумма р/с (проверяется только ключ с БИК, длины) | `src/contracts/requisites_validation.py:85-96` | да — неверный счёт в реквизитах | средний |
| B4 | `merge_runs` не защищает `w:pict`/`w:object`/поля | `src/contracts/filler.py:18-52` | да — порча картинок/полей | низкий |
| B5 | удаление позиций прайса через UI не работает | `src/admin/price_update_view.py:332-338` | нет | низкий |
| B6 | парсер реквизитов: OCR-символы, счета с пробелами, метка «Адрес:», «факт» → почтовый, два р/с, кавычки | `src/contracts/requisites_parser.py` | да — кривые реквизиты, если менеджер не поправит | средний |
| B9 | класс риска: тест/эталон может закреплять дефект как норму | `docs/TECH_DEBT.md:531-537` | — | средний при миграции на эталонах |
| B10 | страж покрытия оплаты агрегатный, не видит позиций без бакета, работает только при автозасеве; F2 держится на resync в `2_Договор.py` | `src/contracts/payment_line.py:267-299`, `src/app_pages/2_Договор.py:265-292` | да — недобор суммы в графике оплаты | высокий при переносе генерации |
| B13 | старые снапшоты с override на бандл ОРИОН после расщепления увеличивают ИТОГО | `src/storage/kp_restore.py:190`, `src/spec_builder.py:315-361` | да — ИТОГО больше на долю монтажа | низкий |
| B14 | name-fallback бакета: «Пусконаладочные работы», «Работы по монтажу» → scales; ручная «Поверка» без тега → общий текст | `src/spec_builder.py:244-275` | да — работы платятся по триггерам весов | средний |
| B16 | поверка «силами Заказчика» активирует iv-бакет в рендере, но не в валидации | `src/validation.py:182-189` | нет | низкий |
| B17 | `build_spec_v2_data` — мёртвая вторая реализация | `src/contracts/from_kp.py:370-451` | нет | низкий (не переносить) |
| B18 | `templates/contracts/backup/spec_v2.docx` испорчен ns0, не в git (сейчас каталога нет на диске) | — | нет | низкий |
| B19 | сторож сходимости редактора оплаты — немой вечный rerun при втором писателе | `src/ui/payment_lines_editor.py:310-315` | нет (зависание страницы) | средний |
| B20 | `_LENGTH_TO_SECTIONS` дублирует `sections` моделей; для линейки П выдумывает секции | `src/storage/snapshot_builder.py:7` | да — не то стройзадание или без Приложения №1 | средний |
| B22 | рамы/ограждения/люки 12/16 м — цена 18 м, дилерской нет | `data/prices.json` | да — цена в КП | средний (цена) |
| B23 | СЛ-100 есть в прайсе, нет в конфигураторе | `data/prices.json`, `data/models.json` | нет | бизнес-решение |
| B24 | предикат «выбран фундамент» в 4 копиях с разным составом | `src/ui/options_section.py:328-334`, `src/storage/kp_restore.py:28-35`, `src/storage/snapshot_builder.py:16-22`, `:59-68` | косвенно — приложения | средний |
| B25 | загруженные файлы клиента не удаляются из временной папки | `src/app_pages/2_Договор.py:295-300` | нет | высокий (персональные данные) |
| B26 | парсер пишет 200 символов реквизитов в лог | `src/contracts/requisites_parser.py` (warning «якорь тел/факс») | нет | средний (ПДн) |
| B27 | класс цены не заморожен в снапшоте | `src/storage/snapshot_builder.py:74-92` | косвенно — названия позиций из текущего прайса | средний |
| B28 | golden-харнесс импортирует денежную арифметику из Streamlit-модуля | `tests/autoverify/runner.py`, `src/ui/payment_lines_editor.py` | нет | высокий для миграции |
| C | расширение `CUSTOM_WORK_TYPES` (фундамент/поверка/ОРИОН) | `src/contracts/custom_work_types.py:26-32` | да — нет обязательств сторон для ручных работ | низкий |
| C | ручные копейки в редакторе оплаты; группировка % по тексту «Объект»; нет теста сумм v1/v2/v3 при qty>1 | `docs/TECH_DEBT.md:1111-1119` | да при ручном вводе | низкий |
| C | константа «не более 50 м»; `section_number` не используется | `src/contracts/tth_context.py:43`, `src/contracts/clauses_loader.py` | нет | низкий |
| C | P1-7 ОГРН в парсере (тестовый ОГРНИП невалиден), P1-6 статусы распознавания | `docs/TECH_DEBT.md:1186-1191` | нет | низкий |
| C | временный файл не удаляется при падении `fill_template` в `compose.py` | `src/contracts/compose.py:150-183` | нет | низкий |
| C | протухший `.venv/`; устаревший путь `SRC` в `make_template.py` | `src/generators/make_template.py:21-22` | нет | низкий |

### 10.2 Найдено при инвентаризации (в TECH_DEBT не записано)

| # | Что | Где | Видит ли менеджер в документе | Риск |
|---|---|---|---|---|
| N1 | Количество опции > 1 (пандусы, фундаментный блок) теряется в договоре: в КП `total = price × qty`, в договоре `total = price`, `price_per_unit = price / qty`. ИТОГО и оплата договора меньше КП; ни один эталон не берёт qty опции > 1 | `src/spec_builder.py:420-436` против `src/contracts/from_kp.py:525-580` | да — суммы Спецификации и договора поставки | высокий |
| N2 | Ручные правки цены/количества в таблице спецификации КП (`spec_overrides`, в т.ч. цена модели) не применяются к позициям договора: снапшот хранит цену виджета, override живёт отдельно | `src/storage/snapshot_builder.py:156`, `:184`; `src/contracts/from_kp.py:486-625` (override не читается) | да — суммы договора ≠ КП | высокий |
| N3 | Датчик, индикатор и длина кабеля в договоре — из `line_defaults`, а не выбор менеджера в КП | `src/contracts/spec_v2_filler.py:240-255`, `:356`; `src/contracts/supply_filler.py:315-327` | да — ТТХ и комплект поставки | высокий |
| N4 | ТТХ договора печатает двухдиапазонные значения по данным модели, флаг КП `is_dual_range` в договоре не читается (grep `is_dual_range` по `src/contracts` — 0); как шаблон печатает пустой/непустой `ТТХ_ДИСКРЕТНОСТЬ_2` — не установлено | `src/contracts/tth_context.py:14-24` | да (вероятно) | средний |
| N5 | Сроки в договоре всегда дефолтные (поставка 20, фундамент 10, монтаж 3, доставка 1): позиции договора без `item_key`, ручной срок КП не передаётся | `src/term_days.py:102-103`, `src/contracts/from_kp.py:188`, `src/contracts/terms_renderer.py:38-40`, `src/contracts/supply_filler.py:302-304` | да — сроки договора ≠ КП | высокий |
| N6 | Ширина платформы не учитывается при поиске модели для ТТХ (`ТТХ_ГАБАРИТЫ` = длина×ширина модели) | `src/contracts/spec_v2_filler.py:230-236`, `src/contracts/tth_context.py:26-28` | да — габариты 18×3 при ширине 3.5/4 | средний |
| N7 | docxtpl без autoescape: «&» и «<» в имени клиента/реквизитах обрезают текст в КП и договоре поставки; raw-XML replace в `fill_template` с «&» даёт битый DOCX | `src/generators/kp_generator.py:263`, `src/contracts/compose.py:42`, `src/contracts/filler.py:98-116` (раздел 8.6) | да | высокий |
| N8 | Ошибка редактора оплаты «Σ% по базе > 100» не блокирует генерацию | `src/ui/payment_lines_editor.py:217-218`, `:324-326` против `src/app_pages/2_Договор.py:1070-1076` | да — переплата в графике | средний |
| N9 | Удаление строки в таблице позиций договора сдвигает `id`/`metadata` последующих строк (сопоставление по индексу) → неверные клаузы | `src/app_pages/2_Договор.py:265-292` | да — набор пунктов | средний |
| N10 | Восстановление КП не чистит виджет-ключи `custom_N_scope` (regex: name/price/delete) → тип работ ручной позиции может взять старое значение | `src/storage/kp_restore.py:223-234`, `src/ui/options_section.py:286-292`; не установлено: воспроизведение в UI | косвенно — бакет и клаузы | низкий |
| N11 | Активность групп split-оплаты в UI (по `state.options`) ≠ в документе (по `payment_group`): опоры ОРИОН или ручные работы включают группу в документе с дефолтными %, которые менеджер не видит и не правит | `src/validation.py:155-190`, `src/ui/payment_section.py:196` против `src/generators/payment_renderer.py:29-39` | да — строка оплаты КП | средний |
| N12 | В договоре поставки молча выпадают позиции бакетов foundation и installation_and_verification (бетон/плиты под раму без монтажа, поверка без монтажа, ручной выбор «Поставка») | `src/contracts/supply_filler.py:231-256` | да — сумма договора меньше КП | высокий |
| N13 | Пункт «Подрядчик направляет строительную бригаду…» ссылается на «Приложение №2», стройзадание прикладывается как №1 | `data/clauses.yaml:62`, `src/contracts/compose.py:130-140` | да | средний |
| N14 | Стройзадания `rama_road_slabs_*`/`rama_pag_slabs_*` автоматически не подбираются (опции плит не дают секций) | `src/storage/snapshot_builder.py:59-70` | да — без Приложения №1, если не выбрать вручную | средний |
| N15 | Нет `control_sheet_приямок_2скц.docx` | `data/fundament/control_sheet/` | да — нельзя приложить лист для 12 м приямка | низкий |
| N16 | Зимний бетон не покрыт golden: G-03 обещает зиму, но это рама — зимние пункты не срабатывают; покрытие только autoverify `winter_concrete` | `tests/golden/fixtures/G-03.json:5`, `data/clauses.yaml:74` | нет | средний для миграции |
| N17 | Падение `fill_spec_v2` молча переключает на шаблон v1 со статичными ТТХ 18×3 и комплектом DHM9B; трассировка пишется в `docs/` | `src/app_pages/2_Договор.py:1181-1196` | да — ТТХ другой модели | высокий |
| N18 | Режим PDF: генерация заблокирована, пока нет строк оплаты, но путь без позиций (`fill_template` v1) их не печатает, печатает `СПЕЦ_ОПЛАТА_П*` из LLM; авто-тип без позиций — «Поставка» | `src/app_pages/2_Договор.py:1064-1076`, `:1210-1211` | да | средний |
| N19 | Таблица `contracts` не используется (`save_contract` без вызовов) — договоры не хранятся | `src/storage/supabase_client.py:119-155` | нет | средний (потеря истории) |
| N20 | Город договора поставки всегда «г. Воронеж» (поле не вводится) | `src/contracts/supply_filler.py:337` | да | низкий |
| N21 | Сохранение КП — upsert по номеру: КП, открытый на правку и сохранённый под тем же номером, перезаписывает оригинал (только предупреждение) | `src/storage/supabase_client.py:54`, `src/ui/load_kp_section.py:61-69` | нет | средний |
| N22 | DOCX КП строится на каждом рендере сайдбара; сохранение в базу — только по клику на скачивание | `src/ui/sidebar.py:150-164` | нет | низкий |
| N23 | Подсказка цены модели «розница +40 %», фактический потолок ×2.0/×2.4; текст ошибки «проверьте слайдер», слайдеров нет | `src/ui/model_section.py:203`, `src/validation.py:52` | нет (UI) | низкий |
| N24 | Описания фундаментов из options.json не находятся (id без длины) | `src/ui/options_section.py:429-437` | нет (UI) | низкий |
| N25 | `LENGTHS` в config устарел (нет 12/16) и не используется | `src/config.py:36` | нет | низкий |
| N26 | `number_to_words` без миллиардов | `src/contracts/utils.py:72-97` | да при суммах ≥ 1 млрд | низкий |
| N27 | «НДС 22%» в строках оплаты и клаузе зимы — литералы, не `VAT_RATE`; замена «20»→«22» по подстроке | `src/contracts/payment_line.py:85`, `data/clauses.yaml:76`, `src/app_pages/2_Договор.py:1096-1098` | да при смене ставки | низкий |
| N28 | Админка без прав доступа пишет prices.json в локальную ФС процесса | `src/app_pages/3_Админка.py:16-20`, `src/admin/price_write_service.py:46-72` | нет | средний (безопасность; судьба файла после перезапуска — не установлено) |
| N29 | `ИТОГО` КП ищется по тексту ячейки «ИТОГО», таблицы договора — по индексу; правка шаблона в Word молча ломает вывод | раздел 8.6 | да | средний |
| N30 | Новые позиции в таблице договора: неизвестный `payment_group` показывается как «equipment» (нет в списке бакетов) | `src/app_pages/2_Договор.py:255` | нет | низкий |
| N31 | `_items_to_rows`/LLM: поле `СПЕЦ_П6_*` из ответа модели не показывается на странице | `src/app_pages/2_Договор.py:109-139` | возможно | низкий |
| N32 | В локальном `data/fundament/build_task/` лежат 2 неотслеживаемых файла `пандусный_*_3 скц.docx` (каталог в `.gitignore:67`, 18 файлов добавлены принудительно); в UI они показываются с той же подписью, что `…_3скц` | `src/contracts/fundament_lookup.py:31`, `:64-85` | только локально | низкий |

## 11. Активы для переноса как есть

Ниже — все файлы, отслеживаемые git (`git ls-files`). Шаблоны договоров переносить как DOCX: пересобрать их скриптами нельзя (раздел 8.5).

| Группа | Пути |
|---|---|
| Справочники | `data/models.json`, `data/prices.json`, `data/options.json`, `data/payment_terms.json`, `data/managers.json`, `data/equipment_specs.json`, `data/clauses.yaml` |
| Константы в коде (перенести как данные) | `src/config.py` (коэффициенты, блоки опций), `src/term_days.py:28-62` (сроки ролей, правила ролей), `src/contracts/supplier.py` (реквизиты поставщика), `src/contracts/custom_work_types.py`, `src/payment_wording.py:129-160`, `:260-297` (словоформы и тексты триггеров), `src/contracts/from_kp.py:22-65` (имена позиций договора), `src/contracts/kit_renderer.py`, `src/contracts/supply_filler.py:53-61` (константы ТТХ/комплекта), `src/contracts/recommendations.py` |
| Промпты LLM | `src/contracts/prompts/extract_contract_data.txt`, `src/contracts/prompts/extract_card_data.txt` |
| Шаблоны DOCX | `templates/kp_template.docx`, `templates/contracts/contract.docx`, `templates/contracts/spec_v2.docx`, `templates/contracts/spec_foundation_install.docx`, `templates/contracts/supply_contract.docx`, `templates/contracts/supply_appendix_1.docx`, `templates/contracts/supply_appendix_2.docx`, `templates/README.md` |
| Строительные задания | `data/fundament/build_task/rama_concrete_2скц.docx`, `rama_concrete_3скц.docx`, `rama_concrete_4скц.docx`, `rama_pag_slabs_2скц.docx`, `rama_pag_slabs_3скц.docx`, `rama_pag_slabs_4скц.docx`, `rama_road_slabs_2скц.docx`, `rama_road_slabs_3скц.docx`, `rama_road_slabs_4скц.docx`, `пандусный_С_Ф_2скц.docx`, `пандусный_С_Ф_3скц.docx`, `пандусный_С_Ф_4скц.docx`, `пандусный_СЛ_ФЛ_2скц.docx`, `пандусный_СЛ_ФЛ_3скц.docx`, `пандусный_СЛ_ФЛ_4скц.docx`, `приямок_2скц.docx`, `приямок_3скц.docx`, `приямок_4скц.docx` |
| Контрольные листы | `data/fundament/control_sheet/control_sheet_пандусный_2скц.docx`, `control_sheet_пандусный_3скц.docx`, `control_sheet_пандусный_4скц.docx`, `control_sheet_приямок_3скц.docx`, `control_sheet_приямок_4скц.docx` |
| Не в git, только на этой машине | `data/fundament/pdf_source/` (PDF-источники стройзаданий, `.gitignore:66`), `data/fundament/build_task/пандусный_С_Ф_3 скц.docx`, `data/fundament/build_task/пандусный_СЛ_ФЛ_3 скц.docx`, `templates/contracts/*.docx.bak` (`.gitignore:60`) — решение владельца, переносить ли |
| Ассеты UI/КП | `assets/favicon.png`, `assets/tenzosila_logo.png`, `assets/tenzosila_logo_small.png` |
| Исходники шаблонов | `docs/source/Автовесы _Поставка.docx`, `docs/contract_templates_v1/*.md` (9 шаблонов юристов в Markdown), `knowledge_base/sample_kps/Гипсобетон_ВЕСТА-С-80-18.docx` (исходник `kp_template`), `knowledge_base/sample_kps/Совхоз им. Кирова_ВЕСТА-ФЛ-80-18.docx`, `knowledge_base/sample_kps/*.pdf` |
| Справочная база | `knowledge_base/spravochnik_vesta.md`, `knowledge_base/opisanie_tipa_VESTA.md`, `knowledge_base/2026_03_01_Прайс_дилер_экспорт.pdf`, `knowledge_base/2026_03_01_Прайс_розница_Tenzosila.pdf`, `tenzosila-raw/product-types-md/**` (источник `equipment_specs.json`) |
| Входы эталонов | `tests/golden/fixtures/G-01.json` … `G-11.json` (11 файлов) |
| Дампы и DOCX эталонов | `tests/golden/expected/G-{01,02,03,05,06,07,09,10,11}_{kp,dogovor,spec}.{docx,dump.txt}`, `tests/golden/expected/G-{04,08}_{kp,dogovor_postavki}.{docx,dump.txt}` (62 файла) |
| Харнесс эталонов | `tests/golden/{fixtures,freeze,dump_docx,dump_walker,dump_runs,dump_props,dump_styles,dump_buckets}.py`, `tests/golden/test_golden.py`, `tests/autoverify/runner.py` |
| Вторичные фикстуры | `tests/autoverify/fixtures/*.json` (13 файлов: `days_singular`, `fundament_montazh_poverka`, `montazh_orion`, `orion`, `orion_poles`, `rama_bez_montazha`, `rama_bez_montazha_x2`, `rama_montazh`, `rama_montazh_x2`, `rama_ploshadka_montazh`, `rama_shefmontazh`, `ruble_declension`, `winter_concrete`) |
| Визуальные эталоны КП | `tests/baseline/png/{gipsobeton,kirova_with_verification,kirova_without_verification,stress_max}/*.png` (64 файла) + `tests/baseline/README.md` |
| Фикстуры админки | `tests/admin/fixtures/2026_03_01_Прайс_дилер_экспорт.pdf`, `tests/admin/fixtures/2026_03_01_Прайс_розница_Tenzosila.pdf`, `tests/admin/fixtures/price_upload_*.json` |
| Спецификации поведения (документы) | `docs/PAYMENT_SPEC.md`, `docs/PAYMENT_MATRIX.md`, `docs/architecture/contracts_v2.md`, `docs/architecture/contracts_v2_1.md`, `docs/MIGRATION_PLAN.md`, `docs/MIGRATION_PLAN_DELTA.md` |
