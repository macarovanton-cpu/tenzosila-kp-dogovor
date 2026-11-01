"""Д14 (N17): падение fill_spec_v2 не откатывается на шаблон v1.

Полный проход генерации через AppTest непрактичен (нужны валидный договор,
реквизиты и клик по кнопке с вложенным состоянием), поэтому — страж по
исходнику страницы: в обработчике `except Exception as exc_v2` есть st.error и
st.stop(), нет отката на v1, записи трассировки и выставления generated.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = (Path(__file__).resolve().parent.parent / "src" / "app_pages" / "2_Договор.py").read_text(encoding="utf-8")


def _handler() -> str:
    m = re.search(r"except Exception as exc_v2:\n(.*?)\n\s*attachments = ", SRC, re.S)
    assert m, "обработчик exc_v2 не найден"
    return m.group(1)


def test_exc_v2_handler_errors_and_stops():
    h = _handler()
    assert "st.error(" in h and "st.stop()" in h


def test_exc_v2_handler_has_no_v1_fallback_or_traceback_dump():
    h = _handler()
    for bad in ("fill_template", "fill_spec_with_items", "SPEC_TEMPLATE", "traceback_", 'cs["generated"]'):
        assert bad not in h, bad
