"""Строит JSONB-снапшот session_state КП для сохранения в Supabase."""
from __future__ import annotations

from typing import Any

# Маппинг длины платформы → количество секций (из models.json, детерминировано)
_LENGTH_TO_SECTIONS: dict[int, int] = {18: 3, 20: 4, 22: 4, 24: 4}
_FOUNDATION_EXECUTION_CHOICES: frozenset[str] = frozenset({
    "пандусный",
    "приямок",
    "монолитная_плита",
})
_DEFAULT_FOUNDATION_EXECUTION = "пандусный"


def _has_manager_selected_foundation(enabled_options: dict[str, Any]) -> bool:
    return any(
        key.startswith(("foundation_s_f_", "foundation_lite_", "foundation_std_"))
        or key == "foundation_supervision"
        or key.startswith("construction_works_")
        for key in enabled_options
    )


def _resolve_foundation_execution(
    enabled_options: dict[str, Any], selected_execution: Any
) -> str | None:
    """Определить тип исполнения фундамента по включённым опциям.

    Возвращает значение для поля foundation_execution в snapshot:
    - выбранный менеджером тип — для фундаментных вариантов 1-3
    - "rama_concrete" — бетонное основание на раме
    - "rama_road_slabs" — укладка дорожных плит
    - "rama_pag_slabs" — укладка плит ПАГ
    - None — фундамент не выбран
    """
    for key in enabled_options:
        if key == "concrete_base_on_frame":
            return "rama_concrete"
        if key.startswith("road_slabs_"):
            return "rama_road_slabs"
        if key.startswith("pag_slabs_"):
            return "rama_pag_slabs"
    if _has_manager_selected_foundation(enabled_options):
        if selected_execution in _FOUNDATION_EXECUTION_CHOICES:
            return str(selected_execution)
        return _DEFAULT_FOUNDATION_EXECUTION
    return None


def _resolve_foundation_sections(
    enabled_options: dict[str, Any], length: int | None
) -> int | None:
    """Количество секций платформы для строительного задания.

    Возвращает None если нет фундаментной опции (курирование и стройработы
    без материалов не требуют строительного задания).
    """
    has_sectioned_foundation = any(
        key.startswith((
            "foundation_s_f_",
            "foundation_lite_",
            "foundation_std_",
            "construction_works_",
        ))
        or key == "concrete_base_on_frame"
        for key in enabled_options
    )
    if not has_sectioned_foundation or length is None:
        return None
    return _LENGTH_TO_SECTIONS.get(int(length))


def _build_enabled_options(opts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Собрать compact payload включённых опций для snapshot."""
    enabled_options: dict[str, dict[str, Any]] = {}
    for key, opt in opts.items():
        if not opt.get("enabled", False):
            continue
        payload = {
            "price": opt.get("price", 0),
            "qty": opt.get("qty", 1),
            "customer_side": opt.get("customer_side", False),
            "retail": opt.get("retail", 0),
            "dealer_is_synthetic": opt.get("dealer_is_synthetic", False),
        }
        if key == "bytovka_weigh_room":
            dimensions = str(opt.get("dimensions") or "").strip()
            if dimensions:
                payload["dimensions"] = dimensions
        enabled_options[key] = payload
    return enabled_options


def _build_custom_items(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Отдать в snapshot только валидные произвольные позиции без UI-id."""
    from src.contracts.custom_work_types import DEFAULT_WORK_TYPE

    result: list[dict[str, Any]] = []
    for item in state.get("custom_items") or []:
        name = str(item.get("name") or "").strip()
        price = int(item.get("price") or 0)
        if not name or price <= 0:
            continue
        entry: dict[str, Any] = {"name": name, "price": price}
        # scope пишем только для не-дефолтного типа: «Прочее» сериализуется как
        # раньше {name, price} → старые снапшоты байт-идентичны при пересейве.
        scope = item.get("scope")
        if scope and scope != DEFAULT_WORK_TYPE:
            entry["scope"] = scope
        result.append(entry)
    return result


def _resolve_installation_scope(
    enabled_options: dict[str, Any], state: dict[str, Any]
) -> str | None:
    """Тип монтажа для договора; без включённого монтажа остаётся null."""
    if "install_default" not in enabled_options:
        return None
    if state.get("is_shefmontazh"):
        return "shefmontazh"
    return "full"


def build_kp_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Возвращает data-блок для колонки kps.data.

    Включает только ключи из §6.2 session_state_audit.md.
    Виджетные ключи (opt_*, split_*), вычисляемые (spec_items, totals)
    и legacy (payment_percents) исключены.
    Для options хранятся только enabled=True записи с полями
    price/qty/customer_side/retail/dealer_is_synthetic.
    """
    opts = state.get("options") or {}
    enabled_options = _build_enabled_options(opts)

    line = state.get("model_line", "")
    max_t = state.get("model_max", "")
    length = state.get("model_length")

    return {
        "metadata": {
            "kp_valid_days": state.get("kp_valid_days"),
            "warranty_months": state.get("warranty_months"),
            # Срок исполнения проекта: сохраняем факт. значение + флаг ручной
            # правки, чтобы при переоткрытии КП срок не пересчитался дефолтом.
            "total_term_days": state.get("total_term_days"),
            "total_term_days_user_set": bool(state.get("total_term_days_user_set")),
        },
        "model": {
            "line": line,
            "max": max_t,
            "length": length,
            "width": float(state.get("platform_width_m", 3.0) or 3.0),
            "price": state.get("model_price"),
            "qty": int(state.get("model_qty", 1) or 1),
        },
        # Контракт snapshot КП→Договор (HANDOFF.md §6)
        "foundation_execution": _resolve_foundation_execution(
            enabled_options, state.get("foundation_execution")
        ),
        "foundation_sections": _resolve_foundation_sections(enabled_options, length),
        "model_code": f"ВЕСТА-{line}-{max_t}-{length}" if line and max_t and length else None,
        "installation_scope": _resolve_installation_scope(enabled_options, state),
        "equipment": {
            "sensor_id": state.get("sensor_id"),
            "indicator_id": state.get("indicator_id"),
            "cable_m": state.get("cable_m"),
        },
        "construction": {
            "beam": state.get("construction_beam"),
            "beam_count": state.get("construction_beam_count"),
            "center_beam": state.get("construction_center_beam"),
            "center_beam_count": state.get("construction_center_beam_count"),
            "deck_mm": state.get("construction_deck_mm"),
            "underlining_mm": state.get("construction_underlining_mm"),
        },
        "metrology": {
            "is_dual_range": state.get("is_dual_range"),
        },
        "options": enabled_options,
        "custom_items": _build_custom_items(state),
        "spec_overrides": state.get("spec_items_overrides") or {},
        "payment": {
            "preset_id": state.get("payment_preset_id"),
            "days": state.get("payment_days"),
            "custom_text": state.get("payment_custom_text", ""),
            "split_state": state.get("payment_split_state") or {},
            "v1_prepay": state.get("payment_v1_prepay"),
            "v2_prepay": state.get("payment_v2_prepay"),
            "v2_preship": state.get("payment_v2_preship"),
            "v3_days": state.get("payment_v3_days"),
            "v3_trigger_id": state.get("payment_v3_trigger_id"),
        },
    }
