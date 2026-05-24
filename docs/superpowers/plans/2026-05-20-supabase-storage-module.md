# Supabase Storage Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `src/storage/supabase_client.py` — a thin storage layer over two Supabase tables (`kps` and `contracts`) with real integration tests.

**Architecture:** Module-level singleton `_get_client()` via `functools.lru_cache`; all public functions wrap every Supabase call in try/except and re-raise as `StorageError`. Production table names live in module-level variables (`_KPS_TABLE`, `_CONTRACTS_TABLE`) so tests can monkeypatch them to `kps_test` / `contracts_test`.

**Tech Stack:** Python 3.11+, supabase-py ≥ 2.0, pytest, tomllib (stdlib).

---

## ⚠️ Pre-work: Run these SQL statements in Supabase SQL Editor

### SQL Block 1 — Create `contracts` table

```sql
CREATE TABLE contracts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kp_id uuid REFERENCES kps(id) ON DELETE SET NULL,
  contract_number text,
  contract_date date,
  object_address text,
  spec_number text,
  requisites jsonb,
  specification jsonb,
  created_at timestamptz DEFAULT now()
);
```

### SQL Block 2 — Create `kps_test` and `contracts_test` tables (for integration tests)

```sql
-- Mirror of kps for integration tests (no production data)
CREATE TABLE kps_test (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kp_number text UNIQUE NOT NULL,
  kp_date date NOT NULL,
  client_name text NOT NULL,
  model_id text NOT NULL,
  total_price integer NOT NULL,
  manager_id text NOT NULL,
  data jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Mirror of contracts for integration tests
CREATE TABLE contracts_test (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kp_id uuid,
  contract_number text,
  contract_date date,
  object_address text,
  spec_number text,
  requisites jsonb,
  specification jsonb,
  created_at timestamptz DEFAULT now()
);
```

### SQL Block 3 — Ensure `kp_number` is UNIQUE on production `kps` table

```sql
-- Safe to run even if constraint already exists
CREATE UNIQUE INDEX IF NOT EXISTS idx_kps_kp_number ON kps(kp_number);
```

---

## Design Decisions

### Module structure: public API

```
src/storage/supabase_client.py
  StorageError             — raised by all public functions on any Supabase failure
  _get_client() → Client   — lru_cache(1) singleton; tries st.secrets, falls back to os.environ
  _KPS_TABLE = "kps"       — monkeypatched to "kps_test" in integration tests
  _CONTRACTS_TABLE = "contracts"

  # kps
  save_kp(kp_number, kp_date, client_name, model_id, total_price, manager_id, data) → dict
  get_kp_by_number(kp_number) → dict | None
  list_recent_kps(limit=50) → list[dict]          # no `data` column
  search_kps_by_contractor(query, limit=20) → list[dict]
  delete_kp(kp_number) → bool

  # contracts
  save_contract(kp_id, contract_number, contract_date, object_address, spec_number,
                requisites, specification) → dict
  get_contracts_by_kp_id(kp_id) → list[dict]
```

### UPSERT conflict target

`save_kp` uses `ON CONFLICT (kp_number)` — the column is UNIQUE (see SQL Block 3). `updated_at` is set manually in the upsert payload so it reflects the actual update time.

`save_contract` uses plain INSERT (no natural unique key; one KP can have multiple contracts).

### How tests connect to Supabase

`_get_client()` first tries `st.secrets["SUPABASE_URL"]` / `st.secrets["SUPABASE_KEY"]`, then falls back to `os.environ["SUPABASE_URL"]` / `os.environ["SUPABASE_KEY"]`.

`tests/storage/conftest.py` hooks `pytest_configure` to read `.streamlit/secrets.toml` (via stdlib `tomllib`) and populate env vars before any import. This means:
- **Locally**: credentials come from the existing `secrets.toml` — zero setup for developers.
- **CI**: `SUPABASE_URL` and `SUPABASE_KEY` are set as repository secrets / env vars.

---

## File Structure

**New files:**
- `src/storage/__init__.py`
- `src/storage/supabase_client.py`
- `tests/storage/__init__.py`
- `tests/storage/conftest.py`
- `tests/storage/test_supabase_client.py`

**Modified files:**
- `requirements.txt` — add `supabase>=2.0`

---

## Task 1: Requirements + empty packages

**Files:**
- Modify: `requirements.txt`
- Create: `src/storage/__init__.py`
- Create: `tests/storage/__init__.py`

- [ ] **Step 1: Add supabase to requirements.txt**

Add one line after `openai>=1.0`:
```
supabase>=2.0
```

- [ ] **Step 2: Create empty package files**

`src/storage/__init__.py` — empty file.
`tests/storage/__init__.py` — empty file.

- [ ] **Step 3: Verify install**

```bash
pip install -r requirements.txt
python -c "import supabase; print(supabase.__version__)"
```
Expected: version ≥ 2.0.x printed, no errors.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt src/storage/__init__.py tests/storage/__init__.py
git commit -m "chore: добавить supabase>=2.0, создать пакеты storage"
```

---

## Task 2: Test fixtures + module skeleton

**Files:**
- Create: `tests/storage/conftest.py`
- Create: `src/storage/supabase_client.py` (skeleton only)

- [ ] **Step 1: Write `tests/storage/conftest.py`**

```python
"""Fixtures для integration-тестов storage."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


def pytest_configure(config) -> None:
    """Загрузить Supabase credentials из secrets.toml до первого теста."""
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        return
    secrets_file = ROOT / ".streamlit" / "secrets.toml"
    if not secrets_file.exists():
        return
    with open(secrets_file, "rb") as f:
        secrets = tomllib.load(f)
    os.environ.setdefault("SUPABASE_URL", secrets.get("SUPABASE_URL", ""))
    os.environ.setdefault("SUPABASE_KEY", secrets.get("SUPABASE_KEY", ""))


@pytest.fixture(scope="session")
def supabase_client():
    from src.storage.supabase_client import _get_client
    _get_client.cache_clear()
    return _get_client()


@pytest.fixture(autouse=True)
def use_test_tables(monkeypatch):
    """Перенаправить все функции на тестовые таблицы."""
    import src.storage.supabase_client as sc
    monkeypatch.setattr(sc, "_KPS_TABLE", "kps_test")
    monkeypatch.setattr(sc, "_CONTRACTS_TABLE", "contracts_test")


@pytest.fixture(autouse=True)
def truncate_tables(supabase_client):
    """TRUNCATE тестовых таблиц перед каждым тестом."""
    supabase_client.table("kps_test").delete().gte("created_at", "1900-01-01").execute()
    supabase_client.table("contracts_test").delete().gte("created_at", "1900-01-01").execute()
    yield
```

- [ ] **Step 2: Write `src/storage/supabase_client.py` skeleton**

```python
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
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)
```

- [ ] **Step 3: Verify import**

```bash
python -c "from src.storage.supabase_client import StorageError, _get_client; print('OK')"
```
Expected: `OK`.

- [ ] **Step 4: Commit skeleton**

```bash
git add src/storage/supabase_client.py tests/storage/conftest.py
git commit -m "feat(storage): скелет модуля, StorageError, _get_client, fixtures"
```

---

## Task 3: kps CRUD — TDD

**Files:**
- Create: `tests/storage/test_supabase_client.py`
- Modify: `src/storage/supabase_client.py`

- [ ] **Step 1: Write failing tests for kps**

Create `tests/storage/test_supabase_client.py`:

```python
"""Integration-тесты storage.supabase_client — реальные вызовы к Supabase."""
from __future__ import annotations

from datetime import date

import pytest

import src.storage.supabase_client as sc

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _kp(suffix: str = "001") -> dict:
    return dict(
        kp_number=f"КП-2026-{suffix}",
        kp_date=date(2026, 5, 20),
        client_name="ООО Ромашка",
        model_id="vesta-с-60-18",
        total_price=2_450_000,
        manager_id="ivanov",
        data={"metadata": {"kp_valid_days": 15}, "model": {"line": "С"}},
    )


# ---------------------------------------------------------------------------
# test_save_and_retrieve
# ---------------------------------------------------------------------------

class TestSaveAndRetrieve:
    def test_save_returns_row_with_id(self):
        row = sc.save_kp(**_kp())
        assert row["kp_number"] == "КП-2026-001"
        assert "id" in row

    def test_get_kp_by_number_returns_saved_row(self):
        sc.save_kp(**_kp())
        row = sc.get_kp_by_number("КП-2026-001")
        assert row is not None
        assert row["client_name"] == "ООО Ромашка"
        assert row["total_price"] == 2_450_000
        assert row["data"]["metadata"]["kp_valid_days"] == 15

    def test_get_kp_by_number_missing_returns_none(self):
        result = sc.get_kp_by_number("КП-НЕТУ-999")
        assert result is None


# ---------------------------------------------------------------------------
# test_upsert_overwrites
# ---------------------------------------------------------------------------

class TestUpsertOverwrites:
    def test_second_save_updates_fields(self):
        sc.save_kp(**_kp())
        updated = dict(_kp(), total_price=3_000_000, client_name="ЗАО Новое")
        sc.save_kp(**updated)
        row = sc.get_kp_by_number("КП-2026-001")
        assert row["total_price"] == 3_000_000
        assert row["client_name"] == "ЗАО Новое"

    def test_upsert_does_not_duplicate(self):
        sc.save_kp(**_kp())
        sc.save_kp(**_kp())
        rows = sc.list_recent_kps(limit=10)
        numbers = [r["kp_number"] for r in rows]
        assert numbers.count("КП-2026-001") == 1


# ---------------------------------------------------------------------------
# test_list_recent
# ---------------------------------------------------------------------------

class TestListRecent:
    def test_returns_saved_rows(self):
        sc.save_kp(**_kp("001"))
        sc.save_kp(**_kp("002"))
        rows = sc.list_recent_kps(limit=10)
        numbers = {r["kp_number"] for r in rows}
        assert "КП-2026-001" in numbers
        assert "КП-2026-002" in numbers

    def test_no_data_column(self):
        sc.save_kp(**_kp())
        rows = sc.list_recent_kps(limit=5)
        for row in rows:
            assert "data" not in row

    def test_limit_respected(self):
        for i in range(5):
            sc.save_kp(**_kp(f"{i:03d}"))
        rows = sc.list_recent_kps(limit=3)
        assert len(rows) <= 3


# ---------------------------------------------------------------------------
# test_search_by_contractor
# ---------------------------------------------------------------------------

class TestSearchByContractor:
    def test_finds_by_partial_name(self):
        sc.save_kp(**_kp("001"))
        kp2 = dict(_kp("002"), client_name="ОАО Вектор")
        sc.save_kp(**kp2)
        rows = sc.search_kps_by_contractor("Ромашка")
        assert any(r["kp_number"] == "КП-2026-001" for r in rows)
        assert all(r["kp_number"] != "КП-2026-002" for r in rows)

    def test_case_insensitive(self):
        sc.save_kp(**_kp())
        rows = sc.search_kps_by_contractor("ромашка")
        assert len(rows) >= 1

    def test_no_data_column(self):
        sc.save_kp(**_kp())
        rows = sc.search_kps_by_contractor("Ромашка")
        for row in rows:
            assert "data" not in row


# ---------------------------------------------------------------------------
# test_delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_existing_returns_true(self):
        sc.save_kp(**_kp())
        result = sc.delete_kp("КП-2026-001")
        assert result is True
        assert sc.get_kp_by_number("КП-2026-001") is None

    def test_delete_missing_returns_false(self):
        result = sc.delete_kp("КП-НЕТУ-888")
        assert result is False


# ---------------------------------------------------------------------------
# test_storage_error_handling
# ---------------------------------------------------------------------------

class TestStorageErrorHandling:
    def test_raises_storage_error_on_bad_table(self, monkeypatch):
        monkeypatch.setattr(sc, "_KPS_TABLE", "kps_table_does_not_exist_xyz")
        with pytest.raises(sc.StorageError):
            sc.get_kp_by_number("КП-2026-001")
```

- [ ] **Step 2: Run tests — expect failures**

```bash
pytest tests/storage/test_supabase_client.py -v 2>&1 | head -40
```
Expected: `AttributeError: module ... has no attribute 'save_kp'` or similar — functions not yet defined.

- [ ] **Step 3: Implement kps functions in `src/storage/supabase_client.py`**

Append after `_get_client()`:

```python
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
            .order("created_at", desc=True)
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
```

- [ ] **Step 4: Run kps tests — expect green**

```bash
pytest tests/storage/test_supabase_client.py -v -k "not Contract"
```
Expected: all `TestSaveAndRetrieve`, `TestUpsertOverwrites`, `TestListRecent`, `TestSearchByContractor`, `TestDelete`, `TestStorageErrorHandling` pass.

- [ ] **Step 5: Run full suite — check no regressions**

```bash
pytest tests/ -v --ignore=tests/storage 2>&1 | tail -5
```
Expected: same pass count as before (216 tests green).

- [ ] **Step 6: Commit**

```bash
git add src/storage/supabase_client.py tests/storage/test_supabase_client.py
git commit -m "feat(storage): kps CRUD — save_kp, get_kp_by_number, list_recent, search, delete"
```

---

## Task 4: contracts CRUD — TDD

**Files:**
- Modify: `tests/storage/test_supabase_client.py`
- Modify: `src/storage/supabase_client.py`

- [ ] **Step 1: Add contract tests to the test file**

Append to `tests/storage/test_supabase_client.py`:

```python
# ---------------------------------------------------------------------------
# contract helpers
# ---------------------------------------------------------------------------

_REQUISITES = {
    "ЗАКАЗЧИК_ИНН": "7701234567",
    "ЗАКАЗЧИК_КПП": "770101001",
    "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": "ООО Ромашка",
}

_SPECIFICATION = {
    "СПЕЦ_НДС": "22",
    "СПЕЦ_ИТОГО": "2 450 000",
    "СПЕЦ_П1_НАИМЕНОВАНИЕ": "Автовесы ВЕСТА-С-60-18",
}


# ---------------------------------------------------------------------------
# test_contracts
# ---------------------------------------------------------------------------

class TestContracts:
    def _saved_kp_id(self) -> str:
        row = sc.save_kp(**_kp())
        return row["id"]

    def test_save_contract_returns_row_with_id(self):
        kp_id = self._saved_kp_id()
        row = sc.save_contract(
            kp_id=kp_id,
            contract_number="1-2026",
            contract_date=date(2026, 5, 20),
            object_address="г. Москва, ул. Ленина, 1",
            spec_number="1",
            requisites=_REQUISITES,
            specification=_SPECIFICATION,
        )
        assert "id" in row
        assert row["contract_number"] == "1-2026"

    def test_get_contracts_by_kp_id_returns_saved(self):
        kp_id = self._saved_kp_id()
        sc.save_contract(
            kp_id=kp_id,
            contract_number="1-2026",
            contract_date=date(2026, 5, 20),
            object_address="г. Москва, ул. Ленина, 1",
            spec_number="1",
            requisites=_REQUISITES,
            specification=_SPECIFICATION,
        )
        rows = sc.get_contracts_by_kp_id(kp_id)
        assert len(rows) == 1
        assert rows[0]["requisites"]["ЗАКАЗЧИК_ИНН"] == "7701234567"
        assert rows[0]["specification"]["СПЕЦ_НДС"] == "22"

    def test_get_contracts_by_kp_id_empty(self):
        rows = sc.get_contracts_by_kp_id("00000000-0000-0000-0000-000000000000")
        assert rows == []

    def test_multiple_contracts_for_one_kp(self):
        kp_id = self._saved_kp_id()
        for i in range(3):
            sc.save_contract(
                kp_id=kp_id,
                contract_number=f"{i}-2026",
                contract_date=date(2026, 5, 20),
                object_address="Адрес",
                spec_number=str(i),
                requisites=_REQUISITES,
                specification=_SPECIFICATION,
            )
        rows = sc.get_contracts_by_kp_id(kp_id)
        assert len(rows) == 3
```

- [ ] **Step 2: Run contract tests — expect failures**

```bash
pytest tests/storage/test_supabase_client.py::TestContracts -v
```
Expected: `AttributeError: module ... has no attribute 'save_contract'`.

- [ ] **Step 3: Implement contracts functions in `src/storage/supabase_client.py`**

Append after `delete_kp`:

```python
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
```

- [ ] **Step 4: Run all storage tests — expect green**

```bash
pytest tests/storage/test_supabase_client.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Run full test suite — check no regressions**

```bash
pytest tests/ -v 2>&1 | tail -10
```
Expected: 216+ tests green (previous 216 + new storage tests).

- [ ] **Step 6: Commit**

```bash
git add src/storage/supabase_client.py tests/storage/test_supabase_client.py
git commit -m "feat(storage): contracts CRUD — save_contract, get_contracts_by_kp_id"
```

---

## Self-review

**Spec coverage check:**
- ✅ `save_kp` with full snapshot
- ✅ `get_kp_by_number`
- ✅ `list_recent_kps(limit=50)` without `data` column
- ✅ `search_kps_by_contractor(query, limit=20)`
- ✅ `delete_kp`
- ✅ UPSERT on `kp_number`
- ✅ `save_contract`
- ✅ `get_contracts_by_kp_id`
- ✅ `StorageError` on all failures
- ✅ `supabase>=2.0` in requirements.txt
- ✅ `lru_cache` singleton
- ✅ `st.secrets` with env var fallback
- ✅ Real Supabase calls (no mocks) for main tests
- ✅ `kps_test` + `contracts_test` tables with TRUNCATE fixture
- ✅ SQL for `contracts` table
- ✅ SQL for `kps_test` table

**Placeholder scan:** None found.

**Type consistency:** `save_kp` returns `dict`, `get_kp_by_number` returns `dict | None`, list functions return `list[dict]` — consistent across tasks.
