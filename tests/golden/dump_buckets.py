"""Секция BUCKETS: payment_group по позициям спецификации (видимость B9/B12).

Дописывается СНАРУЖИ dump_docx() (см. freeze.py/test_golden.py) — сам
DOCX-дамп остаётся чистой функцией байты->текст.
"""
from __future__ import annotations

from src.payment_wording import _iv_kind, iv_guard_triggered

_GROUPS = ("scales", "foundation", "delivery", "installation_and_verification")


def buckets_section(items: list[dict]) -> str:
    """Секция BUCKETS: payment_group по позициям, состав бакетов, iv-флаги."""
    lines = ["", "--- BUCKETS ---", "", "[ITEMS]"]
    for it in items:
        item_id = it.get("item_key") or it.get("id") or ""
        row = f"{item_id} | {it.get('name', '')} | {it.get('payment_group')}"
        if "custom_scope" in it:
            row += f" | custom_scope={it.get('custom_scope')}"
        lines.append(row)

    lines += ["", "[GROUPS]"]
    for group in _GROUPS:
        members = [
            it.get("item_key") or it.get("id") or ""
            for it in items
            if it.get("payment_group") == group
        ]
        lines.append(f"{group}: {', '.join(members) if members else '(пусто)'}")

    iv_items = [it for it in items if it.get("payment_group") == "installation_and_verification"]
    guard_triggered = iv_guard_triggered(iv_items)
    kinds = [_iv_kind(it) for it in iv_items]
    has_install = any(k[0] for k in kinds)
    has_verification = any(k[1] for k in kinds)
    has_orion_install = any(k[2] for k in kinds)
    lines += [
        "",
        "[IV]",
        f"has_install={has_install} has_verification={has_verification} "
        f"has_orion_install={has_orion_install}",
        f"guard_triggered={guard_triggered}",
    ]

    return "\n".join(lines) + "\n"
