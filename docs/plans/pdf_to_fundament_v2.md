# План: `scripts/pdf_to_fundament_docx.py` — конвертер PDF-чертежей фундаментов в DOCX-приложения

## Context

Блок 3 (фундаменты) требует библиотеку из ~13 DOCX-приложений к спецификации. Сейчас они
собираются вручную (1 из 13 готов: `data/fundament/build_task/пандусный_С_Ф_3 скц.docx`).
Нужен скрипт, который из PDF-чертежа (несколько листов А3 горизонтальных) собирает DOCX-приложение,
оформленное **точно как эталон** `templates/contracts/spec_v2.docx` (параграфы 39–45): default header
с «Договор № …», шапка «Приложение №… / Строительное задание на фундамент Весов», картинка чертежа
на страницу и плавающий TextBox «Утверждаю / {{ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ}}» поверх картинки.
Плейсхолдеры `{{…}}` остаются для последующей подстановки через docxtpl.

Предыдущая реализация провалилась на размерах (картинки вылезали за страницу, текст наползал).
Эта версия калибрована по реальным EMU-значениям эталона.

## Что выяснено из эталона (геометрия — основа реализации)

Замеры из `word/document.xml` / `word/header1.xml` / `sectPr`:

- **Страница** (`sectPr`): `pgSz` 11906×16838 twips = **A4 portrait 210×297мм**.
  `pgMar` top=567 (10мм) right=424 (7.5мм) bottom=0 left=1418 (25мм). → **полезная ширина = 177.5мм**.
- **Default header** (`header1.xml`, pStyle `a6`): «Договор № {{ДОГОВОР_НОМЕР}} от {{ДОГОВОР_ДАТА_ПОЛНАЯ}}г.»,
  привязан через `sectPr/headerReference rId9`.
- **Блок шапки приложения** — top-level параграфы (0-индекс):
  - P[39] «Приложение №{{ПРИЛОЖЕНИЕ_НОМЕР}} к Спецификации №{{СПЕЦ_НОМЕР}} от {{ДОГОВОР_ДАТА_ПОЛНАЯ}} г.» (jc=right, style Normal)
  - P[40], P[41] — пустые (jc=right)
  - P[42] «Строительное задание на фундамент Весов» (jc=center)
  - P[43] «{{APPENDIX_FOUNDATION_CHECK}}» — **НЕ копировать**
  - P[44] — пустой
  - → в результат идут **P[39],P[40],P[41],P[42],P[44]** (5 параграфов).
- **P[45]** — параграф картинки (pStyle `a7` = Title, jc=left), содержит два run-а:
  1. run с floating TextBox (`mc:AlternateContent` → `mc:Choice/w:drawing` с `wps:wsp/wps:txbx`):
     anchor `positionH` 642620 EMU (**17.85мм**, relativeFrom=column), `positionV` 4172585 EMU (**115.9мм**, relativeFrom=paragraph),
     `extent` 1933575×561975 EMU (**53.7×15.6мм**), `wrapNone`, `behindDoc=0`, `allowOverlap=1`.
     Текст: «Утверждаю» + «____________ {{ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ}}».
  2. run с inline-картинкой: `wp:inline/wp:extent` 6390640×4522470 EMU (**177.5×125.6мм**), `r:embed=rId8`.
- **Соответствие aspect:** 177.5/125.6 = 1.413 ≈ A3 landscape 420/297 = 1.414. То есть при масштабе картинки
  на полную полезную ширину 177.5мм горизонтальный А3-лист даёт высоту ≈125.6мм — **ровно как в эталоне**.

Подтверждено окружение: **PyMuPDF 1.27.2** и **python-docx 1.2.0** установлены. LibreOffice — нет.

## Подход к сборке DOCX (ключевое решение)

Чтобы получить **точные стили** (`a6`, `a7`, Normal, Title), header и параметры страницы — не строить
документ с нуля, а **открыть эталон через `Document(reference_path)`** (он тянет styles.xml, header1.xml,
footers, sectPr) и заменить только тело:

1. До очистки тела — `copy.deepcopy` нужных XML-элементов:
   - `header_block` = клоны P[39],P[40],P[41],P[42],P[44];
   - `img_ppr` = `pPr` из P[45] (pStyle a7, jc left);
   - `textbox_drawing` = `mc:Choice/w:drawing` из TextBox-run P[45] (берём только Choice c `wps`,
     **отбрасываем `mc:Fallback`/VML** — современный Word и LibreOffice рендерят wps; так уходит
     морока с уникальностью VML `o:spid`/shapetype. Это осознанное упрощение, `wps:txbx` сохраняется).
2. Удалить из `body` все `w:p`/`w:tbl`, **оставив `w:sectPr`** (с ним сохраняются header/footers).
3. Рендер PDF → PNG (fitz, DPI 200), без поворота (`page.get_pixmap(dpi=200)`; ориентация как в исходнике).
4. Для каждой страницы вставлять новые параграфы перед `sectPr` (`sectPr.addprevious(p)`):
   - **стр. 1:** клоны `header_block` (5 параграфов), затем параграф картинки;
   - **стр. 2+:** параграф картинки с page-break (`<w:br w:type="page"/>` первым run-ом);
   - параграф картинки = клон `img_ppr` + run с TextBox (deepcopy `textbox_drawing`, уникальные id)
     + run с картинкой через `run.add_picture(BytesIO(png), width, height)` (python-docx сам заводит
     media-часть, rels и content-type).

### Размеры картинки (где провалилась прошлая версия)

- `USABLE_W_EMU = 6390640` (177.5мм — берём константу эталона, не пересчитываем).
- Доступная высота: стр.1 `H1 = (297-10-35)мм` (резерв 35мм под шапку из 5 строк),
  стр.2+ `H = (297-10-5)мм` (резерв 5мм снизу). В EMU.
- `target_w = USABLE_W_EMU`, `target_h = target_w / aspect` (aspect = px_w/px_h из pixmap).
- Если `target_h > H_avail`: масштабировать по высоте — `target_h = H_avail`, `target_w = target_h*aspect`.
- Для А3-landscape связывает ширина → 177.5×125.6мм, совпадает с эталоном. Кэп по высоте — защита от
  нестандартных/портретных листов (картинка гарантированно не вылезет).
- TextBox оставляем на эталонных оффсетах (17.85/115.9мм) — при высоте картинки ≥125мм он лежит
  в её нижне-левом углу, как в эталоне (это штамп «Утверждаю», он там и должен перекрывать чертёж).

### Уникальность TextBox на каждой странице

В каждом клоне `textbox_drawing` проставить уникальные:
- `wp:docPr/@id` — из выделенного диапазона (напр. `500000 + page_idx`), чтобы не конфликтовать с
  авто-id картинок от python-docx;
- `wp:anchor/@wp14:anchorId` — уникальный 8-hex (напр. `f"{0x47FCA4F2 + page_idx:08X}"`).

## Структура скрипта

Стиль — как у соседних утилит в `scripts/` (хардкод путей-констант, `sys.stdout.reconfigure(encoding="utf-8")`,
type hints, комментарии на русском). Файл ≤200 строк; при разрастании вынести рендер-хелперы.

```
ROOT = Path(__file__).parent.parent
REFERENCE = ROOT / "templates" / "contracts" / "spec_v2.docx"
SRC_DIR   = ROOT / "data" / "fundament" / "pdf_source"
OUT_DIR   = ROOT / "data" / "fundament" / "build_task"
CS_SRC    = SRC_DIR / "control_sheet"          # подпапка контрольных листов
CS_OUT    = ROOT / "data" / "fundament" / "control_sheet"
DPI = 200
NS = {...}  # w, wp, wp14, a, pic, mc, wps, r

# --- извлечение шаблонных кусков из эталона ---
def _load_reference_parts(doc) -> tuple[list, ppr, drawing]: ...
# --- рендер ---
def _render_pages(pdf_path) -> list[bytes]:   # fitz → список PNG-байтов
def _clone_textbox(drawing, page_idx): ...    # deepcopy + уникальные id
def _image_emu(px_w, px_h, page_idx) -> tuple[int,int]: ...  # размеры с кэпом
# --- сборка ---
def convert(pdf_path: Path, out_path: Path) -> None:
    # Document(REFERENCE) → extract parts → clear body → per-page build → save
# --- CLI ---
def _iter_batch() -> list[tuple[Path, Path]]:  # SRC_DIR/*.pdf→OUT_DIR ; CS_SRC/*→CS_OUT
def main():  # argparse: positional pdf | --all ; per-file try/except, прогресс, продолжать при ошибке
```

CLI:
- `python scripts/pdf_to_fundament_docx.py path/to/file.pdf` → `data/fundament/build_task/<stem>.docx`.
- `python scripts/pdf_to_fundament_docx.py --all` → `pdf_source/*.{pdf,PDF}` → `build_task/`,
  `pdf_source/control_sheet/*.{pdf,PDF}` → `data/fundament/control_sheet/` (если подпапка есть).
- По каждому файлу — строка прогресса `[i/N] имя … OK/ERROR`. Ошибка одного файла логируется,
  пакет продолжается (`try/except` вокруг `convert`). Кириллица в путях — pathlib + `fitz.open(str(p))`,
  UTF-8 stdout.
- `OUT_DIR`/`CS_OUT` создаются при необходимости (`mkdir(parents=True, exist_ok=True)`).

## Файлы

- **Новый:** `scripts/pdf_to_fundament_docx.py`.
- **Новый:** `tests/contracts/test_pdf_to_fundament_docx.py`.
- **Правка:** `requirements.txt` — добавить `pymupdf>=1.27` (одобрено). Pillow не нужен.
- Возможно `data/fundament/control_sheet/` создаётся скриптом при первом запуске (не в гите пустой).

## Тесты (`tests/contracts/test_pdf_to_fundament_docx.py`)

Стиль — как `tests/contracts/test_fill_spec_v2.py` (helper `_all_text`, `tmp_path`, `Document`).
Фикстура — синтетический A3-landscape PDF на 2 страницы, сгенерированный через fitz в `tmp_path`
(быстро, без зависимости от 3.7МБ реального файла):

1. **Структура шапки (стр.1):** в тексте есть «Приложение», «к Спецификации», «Строительное задание
   на фундамент Весов»; **нет** `APPENDIX_FOUNDATION_CHECK`.
2. **Header сохранён:** в пакете есть `word/header1.xml` и `sectPr/headerReference`; в шапке плейсхолдеры
   `{{ДОГОВОР_НОМЕР}}`, `{{ДОГОВОР_ДАТА_ПОЛНАЯ}}`.
3. **Параметры страницы:** `pgSz` 11906×16838, `pgMar` left=1418/right=424/top=567/bottom=0 — скопированы.
4. **Картинки:** число inline-картинок == числу страниц PDF; для каждой `wp:extent cx ≤ USABLE_W_EMU`
   и `cy ≤ доступной высоты` (не вылезает за страницу).
5. **TextBox на каждой странице:** число `wps:txbx` == числу страниц; `docPr id` и `wp14:anchorId`
   уникальны между страницами; внутри плейсхолдер `{{ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ}}` сохранён;
   anchor offsets = 642620 / 4172585 EMU.
6. **Page-break:** на стр.2+ присутствует `w:br w:type="page"`; число разрывов == N-1.
7. **Пакетный режим:** положить 2 синтетических PDF в tmp SRC_DIR (monkeypatch путей или параметризуемая
   функция `_iter_batch`), прогнать, проверить что для каждого создан DOCX; битый PDF не валит пакет.

`pytest tests/` должен пройти целиком до коммита (правило CLAUDE.md).

## Верификация (выбрано: программно + ручной просмотр)

1. `pytest tests/contracts/test_pdf_to_fundament_docx.py -v` — зелёный.
2. Прогон на **реальном** файле: `python scripts/pdf_to_fundament_docx.py "data/fundament/pdf_source/пандусный_С_Ф_3 скц.PDF"`
   → DOCX в `build_task/`. Программно (мини-скрипт/в логе) распечатать EMU-размеры каждой картинки и
   подтвердить ≤ полезной области; сравнить с эталонными 6390640×4522470.
3. Если `soffice` всё же найдётся в PATH на момент прогона — опционально сконвертировать в PDF
   (`soffice --headless --convert-to pdf`) и приложить как доказательство; иначе — **Антон открывает
   готовый DOCX в Word глазами** (картинки влезают, шапка и TextBox не наползают на чертёж нечитаемо).
4. Сверка с существующим ручным `build_task/пандусный_С_Ф_3 скц.docx` как референсом ожидаемого вида.

## Коммит

Один коммит после зелёных тестов: `feat(contracts): конвертер PDF-чертежей фундаментов в DOCX-приложения`.
Затем (по правилам STATUS.md) — обновить «Активную задачу»/лог отдельным `docs:`-коммитом, если этот
шаг там заведён. Push — только по явной просьбе.
