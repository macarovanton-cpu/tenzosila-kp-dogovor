"""Storage layer: Supabase tables kps и contracts."""
from __future__ import annotations

import functools
import logging
from datetime import UTC, date, datetime
from typing import Any

from supabase import Client, ClientOptions, create_client

from core.settings import get_secret

logger = logging.getLogger(__name__)

_KPS_TABLE = "kps"
_CONTRACTS_TABLE = "contracts"


class StorageError(Exception):
    """Любая ошибка операции с Supabase."""


@functools.lru_cache(maxsize=1)
def _get_client() -> Client:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    options = ClientOptions(postgrest_client_timeout=10)
    return create_client(url, key, options=options)


_KP_LIST_COLS = "id,kp_number,kp_date,client_name,model_id,total_price,manager_id,created_at,updated_at"


def save_kp(
    kp_number: str,
    kp_date: date,
    client_name: str,
    model_id: str,
    total_price: int,
    manager_id: str,
    data: dict[str, Any],
) -> dict:
    try:
        row = {
            "kp_number": kp_number,
            "kp_date": kp_date.isoformat(),
            "client_name": client_name,
            "model_id": model_id,
            "total_price": total_price,
            "manager_id": manager_id,
            "data": data,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        _get_client().table(_KPS_TABLE).upsert(row, on_conflict="kp_number").execute()
        result = _get_client().table(_KPS_TABLE).select("*").eq("kp_number", kp_number).execute()
        if not result.data:
            raise StorageError(f"save_kp: строка не найдена после upsert (kp_number={kp_number})")
        return result.data[0]
    except Exception as e:
        logger.error("save_kp failed: %s", e)
        raise StorageError(f"save_kp: {e}") from e


def get_kp_by_number(kp_number: str) -> dict | None:
    try:
        result = (
            _get_client().table(_KPS_TABLE).select("*").eq("kp_number", kp_number).execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("get_kp_by_number failed: %s", e)
        raise StorageError(f"get_kp_by_number: {e}") from e


def list_recent_kps(limit: int = 50) -> list[dict]:
    try:
        result = (
            _get_client()
            .table(_KPS_TABLE)
            .select(_KP_LIST_COLS)
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("list_recent_kps failed: %s", e)
        raise StorageError(f"list_recent_kps: {e}") from e


def search_kps_by_contractor(query: str, limit: int = 20) -> list[dict]:
    try:
        result = (
            _get_client()
            .table(_KPS_TABLE)
            .select(_KP_LIST_COLS)
            .ilike("client_name", f"%{query}%")
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("search_kps_by_contractor failed: %s", e)
        raise StorageError(f"search_kps_by_contractor: {e}") from e


def delete_kp(kp_number: str) -> bool:
    try:
        result = (
            _get_client().table(_KPS_TABLE).delete().eq("kp_number", kp_number).execute()
        )
        return bool(result.data)
    except Exception as e:
        logger.error("delete_kp failed: %s", e)
        raise StorageError(f"delete_kp: {e}") from e


def save_contract(
    kp_id: str,
    contract_number: str,
    contract_date: date,
    object_address: str,
    spec_number: str,
    requisites: dict[str, Any],
    specification: dict[str, Any],
) -> dict:
    try:
        row = {
            "kp_id": kp_id,
            "contract_number": contract_number,
            "contract_date": contract_date.isoformat(),
            "object_address": object_address,
            "spec_number": spec_number,
            "requisites": requisites,
            "specification": specification,
        }
        result = _get_client().table(_CONTRACTS_TABLE).insert(row).execute()
        if not result.data:
            raise StorageError("save_contract: INSERT вернул пустой результат")
        return result.data[0]
    except Exception as e:
        logger.error("save_contract failed: %s", e)
        raise StorageError(f"save_contract: {e}") from e


def get_contracts_by_kp_id(kp_id: str) -> list[dict]:
    try:
        result = (
            _get_client().table(_CONTRACTS_TABLE).select("*").eq("kp_id", kp_id).execute()
        )
        return result.data
    except Exception as e:
        logger.error("get_contracts_by_kp_id failed: %s", e)
        raise StorageError(f"get_contracts_by_kp_id: {e}") from e
