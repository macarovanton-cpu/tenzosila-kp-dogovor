"""Storage layer: Supabase tables kps и contracts."""
from __future__ import annotations

import functools
import logging
import os
from datetime import date, datetime, timezone
from typing import Any

from supabase import Client, create_client

logger = logging.getLogger(__name__)

_KPS_TABLE = "kps"
_CONTRACTS_TABLE = "contracts"


class StorageError(Exception):
    """Любая ошибка операции с Supabase."""


@functools.lru_cache(maxsize=1)
def _get_client() -> Client:
    try:
        import streamlit as st
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise StorageError("SUPABASE_URL / SUPABASE_KEY не заданы")
    return create_client(url, key)


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
            "updated_at": datetime.now(timezone.utc).isoformat(),
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
