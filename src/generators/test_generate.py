#!/usr/bin/env python
"""
test_generate.py — генерирует тестовые КП из шаблона для ручной проверки.

Кейсы:
  1. Гипсобетон — ВЕСТА-С-80-18, 5.93 млн, 6 позиций, оплата 50/50
  2. Кирова     — ВЕСТА-ФЛ-80-18, 3.475 млн, 4 позиции, расщеплённая оплата
  3. Стресс-тест — 12 позиций, максимальная нагрузка

Запуск:
    python src/generators/test_generate.py

Результаты сохраняются в output/
"""
import os
from docxtpl import DocxTemplate

BASE     = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
TEMPLATE = os.path.join(BASE, "templates/kp_template.docx")
OUT_DIR  = os.path.join(BASE, "output")


CASES = [
    {
        "_name": "gipsobeton",
        # Шапка
        "client_name": "АО Гипсобетон",
        "kp_number":   "47141",
        "kp_date":     "22.04.2026",
        # Технические характеристики
        "warranty_text":          "36 месяцев",
        "division_info":          (
            "Весы автомобильные ВЕСТА-С-80-18, max 80т, "
            "размеры платформы 18х3м; "
            "Ограждение НОРМА; Датчики Zemic DHM9B 30t 8шт; "
            "Терминал цифровой ТИТАН 3ЦС 1шт"
        ),
        "platform_size":          "18×3",
        "max_load_t":             "80",
        "construction_description": (
            "Конструкция сплошная 09Г2С: Двутавр 30Б1 8 шт., "
            "швеллер 12 2шт, Лист настила 10мм рифлёный, нижний подшив 4мм"
        ),
        "main_scale_label":       "20 до 60т / 50 от 60т до 80т",
        # Спецификация (динамический список)
        "spec_items": [
            {"name": "Весы автомобильные ВЕСТА-С-80-18, max 80т, р-р платформы 18х3м",
             "price": "2 450 000", "term_days": "45"},
            {"name": "Фундамент под ВЕСТА-С/Ф, 18м, «под ключ»",
             "price": "1 900 000", "term_days": "30"},
            {"name": "ПАК ОРИОН Стандарт+",
             "price": "1 200 000", "term_days": "21"},
            {"name": "Монтаж автовесов",
             "price": "250 000",   "term_days": "5"},
            {"name": "Доставка",
             "price": "70 000",    "term_days": "7"},
            {"name": "Поверка",
             "price": "60 000",    "term_days": "3"},
        ],
        "total_price":     "5 930 000",
        "total_term_days": "35",
        "vat_percent": "22",
        # Условия оплаты
        "payment_line_1": "Предоплата: 50% от стоимости проекта",
        "payment_line_2": "Доплата: 50% по завершении проекта",
    },
    {
        "_name": "kirova",
        # Шапка
        "client_name": "АО Совхоз имени Кирова",
        "kp_number":   "47215",
        "kp_date":     "22.04.2026",
        # Технические характеристики
        "warranty_text":          "24 месяца",
        "division_info":          (
            "Весы автомобильные ВЕСТА-ФЛ-80-18, max 80т, "
            "размеры платформы 18х3м"
        ),
        "platform_size":          "18×3",
        "max_load_t":             "80",
        "construction_description": (
            "Конструкция колейная: Двутавр 25Б1 8 шт., "
            "Лист настила 8мм рифлёный, нижний подшив 3мм"
        ),
        "main_scale_label":       "50",
        # Спецификация (4 позиции, поверка — силами заказчика)
        "spec_items": [
            {"name": "Весы автомобильные ВЕСТА-ФЛ-80-18, max 80т, р-р платформы 18х3м",
             "price": "1 800 000", "term_days": "45"},
            {"name": "Фундамент пандусный «Стандарт» под ВЕСТА-СЛ/ФЛ, 18м",
             "price": "1 400 000", "term_days": "30"},
            {"name": "Монтаж автовесов",
             "price": "200 000",   "term_days": "5"},
            {"name": "Доставка",
             "price": "75 000",    "term_days": "7"},
        ],
        "total_price":     "3 475 000",
        "total_term_days": "30",
        "vat_percent": "22",
        # Условия оплаты (расщеплённая)
        "payment_line_1": (
            "Предоплата: 50% стоимости весов + 50% стоимости фундамента"
        ),
        "payment_line_2": (
            "Доплата: по уведомлению о готовности весов к отгрузке "
            "и по факту готовности фундамента — "
            "50% стоимости весов + 50% стоимости фундамента + "
            "100% стоимости доставки. "
            "За монтаж: по факту выполнения — 100% стоимости монтажа."
        ),
    },
    {
        "_name": "stress_max",
        # Шапка
        "client_name": "ООО «Стресс-тест Макс»",
        "kp_number":   "99999",
        "kp_date":     "23.04.2026",
        # Технические характеристики
        "warranty_text":          "36 месяцев",
        "division_info":          (
            "Весы автомобильные ВЕСТА-С-100-24, max 100т, "
            "размеры платформы 24х3м; "
            "Ограждение НОРМА; Датчики Zemic DHM9B 50t 10шт; "
            "Терминал цифровой ТИТАН 3ЦС 1шт"
        ),
        "platform_size":          "24×3",
        "max_load_t":             "100",
        "construction_description": (
            "Конструкция сплошная 09Г2С: Двутавр 35Б1 10 шт., "
            "швеллер 14 2шт, Лист настила 12мм рифлёный, нижний подшив 5мм"
        ),
        "main_scale_label":       "50 до 100т",
        # Спецификация (12 позиций — стресс-тест масштабирования)
        "spec_items": [
            {"name": "Весы автомобильные ВЕСТА-С-100-24, max 100т, р-р платформы 24х3м",
             "price": "3 200 000", "term_days": "60"},
            {"name": "Фундамент монолитный под ВЕСТА-С/Ф, 24м",
             "price": "2 800 000", "term_days": "45"},
            {"name": "Пандусы подъездные, 2 шт.",
             "price": "320 000",   "term_days": "30"},
            {"name": "Рама монтажная усиленная",
             "price": "180 000",   "term_days": "20"},
            {"name": "Ограждение НОРМА, комплект",
             "price": "95 000",    "term_days": "14"},
            {"name": "Люки обслуживания, 2 шт.",
             "price": "60 000",    "term_days": "14"},
            {"name": "ПАК ОРИОН Автоматика+",
             "price": "1 850 000", "term_days": "30"},
            {"name": "Навес металлический под ключ, 30м²",
             "price": "750 000",   "term_days": "25"},
            {"name": "Монтаж автовесов с наладкой",
             "price": "380 000",   "term_days": "7"},
            {"name": "Доставка (до 1000 км)",
             "price": "90 000",    "term_days": "3"},
            {"name": "Поверка государственная",
             "price": "70 000",    "term_days": "3"},
            {"name": "ЗИП комплект (расходники 1 год)",
             "price": "150 000",   "term_days": "14"},
        ],
        "total_price":     "9 945 000",
        "total_term_days": "60",
        "vat_percent":  "22",
        # Условия оплаты
        "payment_line_1": "Предоплата: 50% стоимости весов + 50% стоимости фундамента",
        "payment_line_2": (
            "Доплата: по факту готовности весов к отгрузке "
            "и по факту готовности фундамента — остаток суммы"
        ),
    },
]


def _get_para_text(para):
    return "".join(r.text or "" for r in para.runs)


def generate(case: dict) -> str:
    name = case["_name"]
    data = {k: v for k, v in case.items() if not k.startswith("_")}
    tpl  = DocxTemplate(TEMPLATE)
    tpl.render(data)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"КП_тест_{name}.docx")
    tpl.save(out_path)

    # --- автопроверки ---
    from docx import Document
    doc = Document(out_path)
    all_text = " ".join("".join(r.text or "" for r in p.runs) for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_text += " " + "".join(
                    "".join(r.text or "" for r in p.runs) for p in cell.paragraphs
                )

    # 1. Нет незаполненных jinja-тегов
    assert "{{" not in all_text, (
        f"[{name}] В документе остались незаполненные плейсхолдеры {{{{ }}}}"
    )
    assert "{%" not in all_text, (
        f"[{name}] В документе остались незаполненные теги {{%}}"
    )

    # 2. Количество строк в таблице спецификации
    spec_tbl = next(
        (t for t in doc.tables
         if t.rows and "Наименование" in "".join(
             _get_para_text(p) for p in t.rows[0].cells[0].paragraphs
         )),
        None,
    )
    assert spec_tbl is not None, f"[{name}] Таблица спецификации не найдена в output"
    # header + N items + ИТОГО; endfor-строка удалена docxtpl
    expected_rows = 2 + len(data["spec_items"])
    assert len(spec_tbl.rows) == expected_rows, (
        f"[{name}] Строк в таблице спецификации: {len(spec_tbl.rows)}, "
        f"ожидалось {expected_rows} (1 заголовок + {len(data['spec_items'])} позиций + 1 ИТОГО)"
    )

    # 3. total_price и total_term_days присутствуют в тексте
    assert data["total_price"] in all_text, (
        f"[{name}] Не найден total_price={data['total_price']!r}"
    )
    assert data["total_term_days"] in all_text, (
        f"[{name}] Не найден total_term_days={data['total_term_days']!r}"
    )

    return out_path


def main():
    print(f"Шаблон : {TEMPLATE}")
    for case in CASES:
        out = generate(case)
        print(f"  Сохранён: {out} [{len(case['spec_items'])} позиций]")
    print("Готово. Откройте файлы в output/ для ручной проверки.")


if __name__ == "__main__":
    main()
