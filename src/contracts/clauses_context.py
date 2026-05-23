"""clauses_context.py — вычисление контекста переменных для applies_when."""
from __future__ import annotations

# Маппинг внутренних значений scope из from_kp.py → clauses DSL
_FOUNDATION_SCOPE_MAP: dict[str, str] = {
    "fundament_jb": "contractor_full",
    "pandus_lite": "contractor_full",
    "pandus_std": "contractor_full",
    "contractor_full": "contractor_full",
    "contractor_with_materials": "contractor_with_materials",
    "customer_builds": "customer_builds",
}


def build_clauses_context(deal: dict) -> dict:
    """Вычислить 6 переменных DSL-контекста из объекта сделки.

    deal:
      items: list[dict]          — SpecItem list
      scope_overrides: dict      — переопределения (применяются если items не содержат значения)
      flags: dict                — {"winter_concrete": bool}
    """
    items: list[dict] = deal.get("items", []) or []
    overrides: dict = deal.get("scope_overrides", {}) or {}
    flags: dict = deal.get("flags", {}) or {}

    items_by_id = {item["id"]: item for item in items}

    # --- foundation_scope ---
    if "foundation" in items_by_id:
        raw = items_by_id["foundation"].get("metadata", {}).get("scope", "contractor_full")
        foundation_scope = _FOUNDATION_SCOPE_MAP.get(raw, "contractor_full")
    elif "rama" in items_by_id:
        foundation_scope = "rama"
    elif "foundation_scope" in overrides:
        foundation_scope = overrides["foundation_scope"]
    else:
        foundation_scope = "none"

    # --- installation_scope ---
    if "installation" in items_by_id:
        raw = items_by_id["installation"].get("metadata", {}).get("scope", "full")
        if raw in ("fundament", "rama"):
            installation_scope = "full"
        elif raw in ("shefmontazh", "full"):
            installation_scope = raw
        else:
            installation_scope = "full"
    elif "installation_scope" in overrides:
        installation_scope = overrides["installation_scope"]
    else:
        installation_scope = "none"

    # --- verification_scope ---
    if "verification" in items_by_id:
        meta = items_by_id["verification"].get("metadata", {})
        verification_scope = "customer" if meta.get("customer_side") else "supplier"
    elif "verification_scope" in overrides:
        verification_scope = overrides["verification_scope"]
    else:
        verification_scope = "none"

    # --- has_orion ---
    has_orion = "orion" in items_by_id

    # --- orion_poles_scope ---
    if has_orion:
        if "orion_install" in items_by_id:
            orion_poles_scope = "by_contractor"
        elif "orion_poles_scope" in overrides:
            orion_poles_scope = overrides["orion_poles_scope"]
        else:
            orion_poles_scope = "by_customer"
    else:
        orion_poles_scope = "none"

    # --- winter_concrete — ТОЛЬКО из явного флага ---
    winter_concrete = bool(flags.get("winter_concrete", False))

    return {
        "foundation_scope": foundation_scope,
        "installation_scope": installation_scope,
        "verification_scope": verification_scope,
        "has_orion": has_orion,
        "orion_poles_scope": orion_poles_scope,
        "winter_concrete": winter_concrete,
    }
