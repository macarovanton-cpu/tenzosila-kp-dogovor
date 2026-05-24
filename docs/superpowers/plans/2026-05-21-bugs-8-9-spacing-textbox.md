# Баги 8-9: лишний отступ + текстбокс Приложения — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Убрать лишние пустые параграфы между ТХ и п.15 (баг 8) и заменить плейсхолдеры в text box Приложения (баг 9).

**Architecture:** Баг 8 — добавить удаление двух body-параграфов в `patch_spec_template.py` (idempotent, сохраняет один для отступа). Баг 9 — добавить `_replace_textbox_placeholders()` в `filler.py` вызываемую после `doc.save()` через zipfile-замену. Оба фикса независимы.

**Tech Stack:** Python 3.11, python-docx, zipfile (stdlib), pytest

---

## Структура файлов

- Modify: `scripts/patch_spec_template.py` — добавить удаление 2 из 3 пустых параграфов между TABLE[1] и п.15
- Modify: `src/contracts/filler.py` — добавить `_replace_textbox_placeholders()` + вызов после save
- Modify: `tests/contracts/test_templates.py` — 1 новый тест (баг 8)
- Modify: `tests/contracts/test_filler.py` — 1 новый тест (баг 9)

---

## Task 1: Тест и фикс бага 8 — лишние пустые параграфы

**Контекст:** Между `doc.tables[1]` (ТХ, 11 строк) и заголовком п.15 «Комплект поставки» в шаблоне 3 пустых body-параграфа. Из-за них контент не влезает на одну страницу несмотря на правильную цепочку keepNext. Нужно оставить 1 для отступа.

В `patch_spec_template.py` блок «Цепочка keepNext: параграфы [55-57]» уже находит эти параграфы через `intermediates = all_bp[p14_i + 2 : p15_i]`. Нужно добавить удаление `intermediates[:-1]` (все кроме последнего) сразу после цикла keepNext.

**Files:**
- Modify: `tests/contracts/test_templates.py`
- Modify: `scripts/patch_spec_template.py`

- [ ] **Step 1: Написать падающий тест**

  Добавить в конец `tests/contracts/test_templates.py`:

  ```python
  
  
  def test_spec_max_empty_paras_between_th_and_kompl():
      """Между таблицей ТХ и заголовком п.15 не более 1 пустого параграфа."""
      doc = Document(CONTRACTS / "spec_foundation_install.docx")
      body_paras = _body_paras(doc)
      p14_idx = next(
          i for i, p in enumerate(body_paras) if "Технические характеристики" in p.text
      )
      p15_idx = next(
          i for i, p in enumerate(body_paras) if "Комплект поставки" in p.text
      )
      # p14_idx+2 .. p15_idx — параграфы после p.14 и его empty-пары до заголовка п.15
      between = body_paras[p14_idx + 2 : p15_idx]
      assert len(between) <= 1, (
          f"Между таблицей ТХ и заголовком п.15 должно быть не более 1 пустого параграфа, "
          f"найдено {len(between)}"
      )
  ```

- [ ] **Step 2: Проверить что тест FAIL**

  ```bash
  pytest tests/contracts/test_templates.py::test_spec_max_empty_paras_between_th_and_kompl -v
  ```

  Ожидание: FAIL с «найдено 3».

- [ ] **Step 3: Добавить удаление параграфов в patch_spec_template.py**

  В блоке «Цепочка keepNext: параграфы [55-57]» (строки 125–133) добавить 2 строки после цикла keepNext. Заменить:

  ```python
      # Цепочка keepNext: параграфы [55-57] между TABLE[1] и п.15
      if len(doc.tables) > 1 and p14 and p15:
          all_bp = _body_paras(doc)
          p14_i = next(i for i, p in enumerate(all_bp) if p._p is p14._p)
          p15_i = next(i for i, p in enumerate(all_bp) if p._p is p15._p)
          intermediates = all_bp[p14_i + 2 : p15_i]
          for p in intermediates:
              set_keep_with_next(p)
          print(f"Параграфы между TABLE[1] и п.15: keepNext на {len(intermediates)} параграфах")
  ```

  На:

  ```python
      # Цепочка keepNext: параграфы [55-57] между TABLE[1] и п.15; удаляем лишние 2 из 3
      if len(doc.tables) > 1 and p14 and p15:
          all_bp = _body_paras(doc)
          p14_i = next(i for i, p in enumerate(all_bp) if p._p is p14._p)
          p15_i = next(i for i, p in enumerate(all_bp) if p._p is p15._p)
          intermediates = all_bp[p14_i + 2 : p15_i]
          for p in intermediates:
              set_keep_with_next(p)
          print(f"Параграфы между TABLE[1] и п.15: keepNext на {len(intermediates)} параграфах")
          # Оставляем 1 пустой параграф для отступа, удаляем остальные
          for p in intermediates[:-1]:
              p._p.getparent().remove(p._p)
          print(f"Удалено {len(intermediates[:-1])} лишних пустых параграфов между TABLE[1] и п.15")
  ```

- [ ] **Step 4: Запустить скрипт**

  ```bash
  python scripts/patch_spec_template.py
  ```

  Ожидание в выводе:
  ```
  Параграфы между TABLE[1] и п.15: keepNext на 3 параграфах
  Удалено 2 лишних пустых параграфов между TABLE[1] и п.15
  ```

- [ ] **Step 5: Проверить что тест проходит**

  ```bash
  pytest tests/contracts/test_templates.py -v
  ```

  Ожидание: **13 PASSED** (было 12, добавили 1).

- [ ] **Step 6: Коммит**

  ```bash
  git add scripts/patch_spec_template.py tests/contracts/test_templates.py templates/contracts/spec_foundation_install.docx templates/contracts/backup/spec_foundation_install.docx
  git commit -m "fix(templates/spec): баг 8 — удаление 2 лишних пустых параграфов между ТХ и п.15"
  ```

---

## Task 2: Тест и фикс бага 9 — плейсхолдеры в text box

**Контекст:** `docxtpl` не рендерит плейсхолдеры внутри `w:txbxContent` (Word text box). В шаблоне `spec_foundation_install.docx` в Приложении №1 есть текстбокс с `{{ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ}}`. После `fill_template` плейсхолдер остаётся нетронутым.

Фикс: добавить в `filler.py` функцию `_replace_textbox_placeholders()` и вызвать её после `doc.save(output_path)`. Функция итерирует по XML-файлам внутри DOCX и делает string replace для каждого ключа из `data`.

**Files:**
- Modify: `tests/contracts/test_filler.py`
- Modify: `src/contracts/filler.py`

- [ ] **Step 7: Написать падающий тест**

  Добавить в конец `tests/contracts/test_filler.py`:

  ```python
  
  
  def test_filler_replaces_textbox_placeholders(tmp_path):
      """fill_template заменяет {{ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ}} в text box Приложения."""
      import zipfile
  
      template = os.path.normpath(SPEC_TEMPLATE_PATH)
      output = str(tmp_path / "spec_textbox.docx")
  
      fill_template(template, SPEC_MOCK_DATA, output)
  
      with zipfile.ZipFile(output) as z:
          content = z.read("word/document.xml").decode("utf-8")
  
      assert "{{ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ}}" not in content, (
          "Плейсхолдер {{ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ}} не был заменён в text box Приложения"
      )
  ```

- [ ] **Step 8: Проверить что тест FAIL**

  ```bash
  pytest tests/contracts/test_filler.py::test_filler_replaces_textbox_placeholders -v
  ```

  Ожидание: FAIL — плейсхолдер остаётся в XML.

- [ ] **Step 9: Добавить `_replace_textbox_placeholders` и вызов в filler.py**

  В `src/contracts/filler.py` добавить функцию перед `fill_template` (после `replace_in_paragraph`, строка ~57):

  ```python
  
  def _replace_textbox_placeholders(docx_path: str, data: dict) -> None:
      """Заменяет {{KEY}} в text box-ах (w:txbxContent), которые docxtpl/python-docx пропускают."""
      import zipfile
      import shutil
  
      tmp = docx_path + '.tmp'
      with zipfile.ZipFile(docx_path, 'r') as zin:
          with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
              for item in zin.infolist():
                  data_bytes = zin.read(item.filename)
                  if item.filename.endswith('.xml'):
                      text = data_bytes.decode('utf-8')
                      for key, value in data.items():
                          placeholder = '{{' + key + '}}'
                          if placeholder in text:
                              text = text.replace(placeholder, str(value) if value else '')
                      data_bytes = text.encode('utf-8')
                  zout.writestr(item, data_bytes)
      shutil.move(tmp, docx_path)
  ```

  Затем в `fill_template`, после `doc.save(output_path)` (строка 108), добавить вызов:

  ```python
      doc.save(output_path)
      _replace_textbox_placeholders(output_path, data)
  ```

  Итоговый конец функции `fill_template` (строки 98–109):

  ```python
      # Удаляем пустые нумерованные параграфы (СПЕЦ_ОПЛАТА_П5/П6 без значения → «2.5 »)
      _NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
      _body_tag = f'{{{_NS}}}body'
      for para in list(doc.paragraphs):
          if para.text.strip() == '':
              p_el = para._element
              if (p_el.getparent().tag == _body_tag
                      and p_el.find(f'.//{{{_NS}}}numPr') is not None):
                  p_el.getparent().remove(p_el)

      doc.save(output_path)
      _replace_textbox_placeholders(output_path, data)
  ```

- [ ] **Step 10: Проверить что тест проходит**

  ```bash
  pytest tests/contracts/test_filler.py -v
  ```

  Ожидание: **5 PASSED** (было 4, добавили 1).

- [ ] **Step 11: Коммит**

  ```bash
  git add src/contracts/filler.py tests/contracts/test_filler.py
  git commit -m "fix(contracts/filler): баг 9 — замена плейсхолдеров в text box через zipfile"
  ```

---

## Task 3: Регрессия и STATUS

- [ ] **Step 12: Прогон всех тестов**

  ```bash
  pytest tests/ -v 2>&1 | tail -15
  ```

  Ожидание: ≥288 PASSED (286 было + 2 новых), 0 FAILED (кроме ожидаемых синтетических e2e).

- [ ] **Step 13: Обновить STATUS.md**

  В `docs/STATUS.md` в таблицу добавить:

  ```
  | 8b | Лишний вертикальный отступ — п.15 съезжает на новую страницу (3 пустых параграфа → 1) | ✅ Закрыт |
  | 9b | Плейсхолдер ИНИЦИАЛЫ не рендерится в text box Приложения (docxtpl обходит txbxContent) | ✅ Закрыт |
  ```

  В раздел «Что выполнено» добавить:

  ```
  ### Промт E ✅ — баги 8b и 9b шаблона спецификации
  - patch_spec_template.py: удаление 2 из 3 пустых параграфов между TABLE[1] и п.15
  - filler.py: _replace_textbox_placeholders() — замена {{KEY}} в txbxContent через zipfile
  - +2 теста (13 в test_templates.py, 5 в test_filler.py)
  ```

- [ ] **Step 14: Коммит STATUS**

  ```bash
  git add docs/STATUS.md
  git commit -m "docs: закрыты баги 8b и 9b, обновлён статус"
  ```
