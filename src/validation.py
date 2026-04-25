"""Валидация состояния КП: жёсткие errors (блокируют кнопку) и мягкие warnings."""
from __future__ import annotations

from typing import Any

from src.data_loader import get_manager_by_id, get_model_by_id, get_price_by_model_id


def _get_preset(payment_terms: dict, preset_id: str) -> dict | None:
    for preset in payment_terms.get("presets", []):
        if preset.get("id") == preset_id:
            return preset
    return None


def _has_enabled_option(state: dict, predicate) -> bool:
    for key, opt in state.get("options", {}).items():
        if opt.get("enabled") and predicate(key, opt):
            return True
    return False


def validate(
    state: dict[str, Any],
    prices: dict,
    models_json: dict,
    payment_terms: dict,
    managers: dict,
) -> tuple[list[str], list[str]]:
    """Вернуть (errors, warnings). errors блокируют кнопку «Сгенерировать КП»."""
    errors: list[str] = []
    warnings: list[str] = []

    # --- ERRORS ---
    if not str(state.get("kp_number", "")).strip():
        errors.append("Не указан номер КП")
    if not str(state.get("client_name", "")).strip():
        errors.append("Не указан клиент")

    manager_id = str(state.get("manager_id", "")).strip()
    if not manager_id or get_manager_by_id(managers, manager_id) is None:
        errors.append("Менеджер не выбран")

    model_id = state.get("model_id", "")
    price_entry = get_price_by_model_id(prices, model_id)
    if price_entry is None:
        errors.append(f"Модель «{model_id}» отсутствует в прайсе")
    else:
        model_price = state.get("model_price")
        dealer = int(price_entry.get("dealer_ru", 0) or 0)
        if model_price is not None and int(model_price) < dealer:
            errors.append("Цена модели ниже дилерской — проверьте слайдер")

    # Опции "под запрос"
    for key, opt in state.get("options", {}).items():
        if opt.get("enabled") and opt.get("is_on_request"):
            errors.append(
                f"Опция «{key}» помечена «под запрос» — "
                f"запросите цену у производства"
            )

    # Оплата
    preset_id = state.get("payment_preset_id", "")
    preset = _get_preset(payment_terms, preset_id)
    if preset is not None:
        if preset.get("is_split"):
            for group in preset.get("groups", []):
                group_id = group["id"]
                if not _split_group_active(group_id, state):
                    continue
                vals = state.get("payment_split_state", {}).get(group_id, {})
                prepay = int(vals.get("prepay", group["default_percents"]["prepay"]))
                postpay = int(vals.get("postpay", group["default_percents"]["postpay"]))
                if prepay + postpay != 100:
                    errors.append(
                        f"Сумма процентов в группе «{group['label']}» "
                        f"не равна 100 ({prepay} + {postpay})"
                    )
        elif preset.get("id") == "custom":
            if not str(state.get("payment_custom_text", "")).strip():
                errors.append("Для индивидуальных условий оплаты укажите текст")
        else:
            keys = preset.get("editable_percent_keys", [])
            total = 0
            for k in keys:
                total += int(
                    state.get("payment_percents", {}).get(
                        k, preset["default_percents"].get(k, 0)
                    )
                )
            if keys and total != 100:
                errors.append(
                    f"Сумма процентов в условиях оплаты не равна 100 (сейчас {total})"
                )

    # --- WARNINGS ---
    model = get_model_by_id(models_json, model_id)
    if model and model.get("data_incomplete"):
        warnings.append(
            f"Модель «{model_id}»: данные неполные — уточните ТХ у производства"
        )

    for key, opt in state.get("options", {}).items():
        if not opt.get("enabled"):
            continue
        if key.endswith("_22"):
            warnings.append(
                f"Опция «{key}» для 22 м — цена рассчитана как среднее "
                f"между 20 и 24 м, дилерская — оценка"
            )
        if opt.get("dealer_is_synthetic"):
            # Уже покрыто _22 warning-ом, но на случай других UNKNOWN — оставим
            pass

    line = state.get("model_line", "")
    if _has_enabled_option(state, lambda k, o: k == "ramp_set_f_s") and line == "П":
        warnings.append(
            "Для линейки П рекомендуются усиленные пандусы — "
            "уточните возможность у производства"
        )

    return errors, warnings


def _split_group_active(group_id: str, state: dict) -> bool:
    """Определяет, активна ли группа оплаты split_by_items по содержимому state.options."""
    if group_id == "scales":
        return True
    options: dict = state.get("options", {})
    if group_id == "foundation":
        prefixes = ("foundation_lite_", "foundation_std_", "foundation_s_f_")
        for k, opt in options.items():
            if opt.get("enabled") and k.startswith(prefixes):
                return True
        return False
    if group_id == "delivery":
        opt = options.get("delivery_default", {})
        return bool(opt.get("enabled"))
    if group_id == "installation_and_verification":
        inst = options.get("install_default", {})
        if inst.get("enabled"):
            return True
        ver = options.get("verification_default", {})
        if ver.get("enabled") and not ver.get("customer_side"):
            return True
        return False
    return False
