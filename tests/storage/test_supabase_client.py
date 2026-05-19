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
