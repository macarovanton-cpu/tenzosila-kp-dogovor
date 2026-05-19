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
