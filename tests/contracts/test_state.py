"""Тесты для src/contracts/state.py — namespace договора в session_state."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_session_state():
    """Мокаем st.session_state как обычный dict."""
    state: dict = {}
    with patch("src.contracts.state.st") as mock_st:
        mock_st.session_state = state
        yield state


# ------------------------------------------------------------------
# init_contract_state
# ------------------------------------------------------------------

class TestInitContractState:
    def test_creates_namespace(self, mock_session_state):
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        assert "requisites" in cs
        assert "specification" in cs
        assert "manual" in cs
        assert "uploads" in cs
        assert cs["ai_raw"] is None

    def test_idempotent(self, mock_session_state):
        from src.contracts.state import init_contract_state
        init_contract_state()
        mock_session_state["contract"]["requisites"]["ЗАКАЗЧИК_ИНН"] = "123"
        init_contract_state()
        assert mock_session_state["contract"]["requisites"]["ЗАКАЗЧИК_ИНН"] == "123"

    def test_manual_defaults(self, mock_session_state):
        from src.contracts.state import init_contract_state
        init_contract_state()
        manual = mock_session_state["contract"]["manual"]
        assert manual["contract_number"] == ""
        assert manual["contract_date"] is None
        assert manual["spec_number"] == "1"

    def test_winter_surcharge_defaults(self, mock_session_state):
        from src.contracts.state import init_contract_state
        init_contract_state()
        flags = mock_session_state["contract"]["flags"]
        assert flags["winter_surcharge"] is False
        assert flags["winter_surcharge_amount"] == 200000

    def test_attachment_defaults(self, mock_session_state):
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        assert cs["kp_snapshot"] == {}
        assert cs["attachments"]["build_task_path"] == ""
        assert cs["attachments"]["build_task_source"] == "auto"
        assert cs["attachments"]["control_sheet_path"] == ""
        assert cs["attachments"]["include_control_sheet"] is False

    def test_winter_surcharge_flags_backfilled_for_existing_state(self, mock_session_state):
        from src.contracts.state import init_contract_state
        mock_session_state["contract"] = {"flags": {"winter_concrete": True}}

        init_contract_state()

        flags = mock_session_state["contract"]["flags"]
        assert flags["winter_surcharge"] is True
        assert flags["winter_surcharge_amount"] == 200000


# ------------------------------------------------------------------
# set_extracted_data
# ------------------------------------------------------------------

class TestSetExtractedData:
    def test_writes_to_namespace(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_extracted_data
        init_contract_state()
        raw = {
            "requisites": {"ЗАКАЗЧИК_ИНН": "7701234567"},
            "specification": {"СПЕЦ_НДС": "22"},
        }
        set_extracted_data(raw)
        cs = mock_session_state["contract"]
        assert cs["requisites"]["ЗАКАЗЧИК_ИНН"] == "7701234567"
        assert cs["specification"]["СПЕЦ_НДС"] == "22"
        assert cs["ai_raw"] is raw

    def test_pushes_widget_keys(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_extracted_data
        init_contract_state()
        raw = {
            "requisites": {"ЗАКАЗЧИК_ИНН": "7701234567"},
            "specification": {"СПЕЦ_ИТОГО": "1 000 000"},
        }
        set_extracted_data(raw)
        assert mock_session_state["w_ЗАКАЗЧИК_ИНН"] == "7701234567"
        assert mock_session_state["w_СПЕЦ_ИТОГО"] == "1 000 000"

    def test_none_values_become_empty_string(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_extracted_data
        init_contract_state()
        raw = {"requisites": {"ЗАКАЗЧИК_EMAIL": None}, "specification": {}}
        set_extracted_data(raw)
        assert mock_session_state["contract"]["requisites"]["ЗАКАЗЧИК_EMAIL"] == ""


# ------------------------------------------------------------------
# sync_field
# ------------------------------------------------------------------

class TestSyncField:
    def test_widget_to_namespace(self, mock_session_state):
        from src.contracts.state import init_contract_state, sync_field
        init_contract_state()
        mock_session_state["contract"]["requisites"]["ЗАКАЗЧИК_ИНН"] = ""
        mock_session_state["w_ЗАКАЗЧИК_ИНН"] = "9999999999"
        sync_field("requisites", "ЗАКАЗЧИК_ИНН")
        assert mock_session_state["contract"]["requisites"]["ЗАКАЗЧИК_ИНН"] == "9999999999"


# ------------------------------------------------------------------
# sync_manual_field
# ------------------------------------------------------------------

class TestSyncManualField:
    def test_widget_to_manual(self, mock_session_state):
        from src.contracts.state import init_contract_state, sync_manual_field
        init_contract_state()
        mock_session_state["w_contract_number"] = "42-2026"
        sync_manual_field("contract_number")
        assert mock_session_state["contract"]["manual"]["contract_number"] == "42-2026"


# ------------------------------------------------------------------
# collect_for_template
# ------------------------------------------------------------------

class TestCollectForTemplate:
    def test_flat_merge(self, mock_session_state):
        from src.contracts.state import init_contract_state, collect_for_template
        init_contract_state()
        cs = mock_session_state["contract"]
        cs["requisites"] = {"ЗАКАЗЧИК_ИНН": "123", "ЗАКАЗЧИК_КПП": "456"}
        cs["specification"] = {"СПЕЦ_НДС": "22", "СПЕЦ_ИТОГО": "100"}
        data = collect_for_template()
        assert data == {
            "ЗАКАЗЧИК_ИНН": "123",
            "ЗАКАЗЧИК_КПП": "456",
            "СПЕЦ_НДС": "22",
            "СПЕЦ_ИТОГО": "100",
        }

    def test_includes_all_ai_keys(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_extracted_data, collect_for_template
        init_contract_state()
        raw = {
            "requisites": {"ЗАКАЗЧИК_ИНН": "1"},
            "specification": {"СПЕЦ_П6_НАИМЕНОВАНИЕ": "Поверка", "СПЕЦ_П6_СУММА": "50000"},
        }
        set_extracted_data(raw)
        data = collect_for_template()
        assert "СПЕЦ_П6_НАИМЕНОВАНИЕ" in data
        assert "СПЕЦ_П6_СУММА" in data


# ------------------------------------------------------------------
# is_extracted
# ------------------------------------------------------------------

class TestIsExtracted:
    def test_false_initially(self, mock_session_state):
        from src.contracts.state import init_contract_state, is_extracted
        init_contract_state()
        assert is_extracted() is False

    def test_true_after_extraction(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_extracted_data, is_extracted
        init_contract_state()
        set_extracted_data({"requisites": {}, "specification": {}})
        assert is_extracted() is True


# ------------------------------------------------------------------
# is_extracted — режим A (specification populated)
# ------------------------------------------------------------------

class TestIsExtractedModeA:
    def test_true_when_specification_populated(self, mock_session_state):
        """Mode A: is_extracted() → True когда specification заполнена."""
        from src.contracts.state import init_contract_state, is_extracted
        init_contract_state()
        mock_session_state["contract"]["specification"]["СПЕЦ_НДС"] = "22"
        assert is_extracted() is True

    def test_false_when_specification_empty_dict(self, mock_session_state):
        """is_extracted() → False если specification = {} (пустой)."""
        from src.contracts.state import init_contract_state, is_extracted
        init_contract_state()
        assert is_extracted() is False


# ------------------------------------------------------------------
# set_specification
# ------------------------------------------------------------------

class TestSetSpecification:
    def test_writes_spec_to_namespace(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_specification
        init_contract_state()
        spec = {"СПЕЦ_НДС": "22", "СПЕЦ_ИТОГО": "1000000"}
        set_specification(spec)
        cs = mock_session_state["contract"]
        assert cs["specification"]["СПЕЦ_НДС"] == "22"
        assert cs["specification"]["СПЕЦ_ИТОГО"] == "1000000"

    def test_pushes_widget_keys(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_specification
        init_contract_state()
        set_specification({"СПЕЦ_НДС": "22"})
        assert mock_session_state.get("w_СПЕЦ_НДС") == "22"

    def test_none_becomes_empty_string(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_specification
        init_contract_state()
        set_specification({"СПЕЦ_ИТОГО": None})
        assert mock_session_state["contract"]["specification"]["СПЕЦ_ИТОГО"] == ""


# ------------------------------------------------------------------
# set_requisites
# ------------------------------------------------------------------

class TestSetRequisites:
    def test_writes_requisites_to_namespace(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_requisites
        init_contract_state()
        reqs = {"ЗАКАЗЧИК_ИНН": "7701234567"}
        set_requisites(reqs)
        cs = mock_session_state["contract"]
        assert cs["requisites"]["ЗАКАЗЧИК_ИНН"] == "7701234567"

    def test_pushes_widget_keys(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_requisites
        init_contract_state()
        set_requisites({"ЗАКАЗЧИК_ИНН": "7701234567"})
        assert mock_session_state.get("w_ЗАКАЗЧИК_ИНН") == "7701234567"


# ------------------------------------------------------------------
# generated key
# ------------------------------------------------------------------

class TestGeneratedKey:
    def test_init_creates_generated_none(self, mock_session_state):
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        assert "generated" in cs
        assert cs["generated"] is None

    def test_idempotent_does_not_clear_generated(self, mock_session_state):
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        cs["generated"] = {"contract_bytes": b"x", "spec_bytes": b"y"}
        init_contract_state()
        assert cs["generated"] is not None
        assert cs["generated"]["contract_bytes"] == b"x"

    def test_clear_generated_sets_none(self, mock_session_state):
        from src.contracts.state import init_contract_state, clear_generated
        init_contract_state()
        mock_session_state["contract"]["generated"] = {
            "contract_bytes": b"x",
            "contract_filename": "a.docx",
            "spec_bytes": b"y",
            "spec_filename": "b.docx",
        }
        clear_generated()
        assert mock_session_state["contract"]["generated"] is None


# ------------------------------------------------------------------
# set_spec_items / get_spec_items
# ------------------------------------------------------------------

class TestSetGetSpecItems:
    def test_set_and_get_items(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_spec_items, get_spec_items
        init_contract_state()
        items = [{"id": "weights", "name": "Весы", "unit": "компл",
                  "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
                  "payment_group": None, "is_custom": False,
                  "source": "preset", "metadata": {}}]
        set_spec_items(items)
        assert get_spec_items() == items

    def test_get_items_empty_by_default(self, mock_session_state):
        from src.contracts.state import init_contract_state, get_spec_items
        init_contract_state()
        assert get_spec_items() == []

    def test_items_stored_in_specification(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_spec_items
        init_contract_state()
        set_spec_items([{"id": "x"}])
        assert mock_session_state["contract"]["specification"]["items"] == [{"id": "x"}]


class TestCollectForTemplateExcludesItems:
    def test_items_key_excluded(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_spec_items, collect_for_template
        init_contract_state()
        mock_session_state["contract"]["specification"]["СПЕЦ_НДС"] = "22"
        set_spec_items([{"id": "weights"}])
        data = collect_for_template()
        assert "items" not in data
        assert "СПЕЦ_НДС" in data


class TestIsExtractedWithItems:
    def test_false_when_only_items_set(self, mock_session_state):
        """is_extracted() → False если specification содержит только items=[]."""
        from src.contracts.state import init_contract_state, is_extracted, set_spec_items
        init_contract_state()
        set_spec_items([])
        assert is_extracted() is False

    def test_true_when_spec_fields_present(self, mock_session_state):
        from src.contracts.state import init_contract_state, is_extracted, set_spec_items
        init_contract_state()
        mock_session_state["contract"]["specification"]["СПЕЦ_НДС"] = "22"
        set_spec_items([{"id": "weights"}])
        assert is_extracted() is True


# ------------------------------------------------------------------
# merge_requisites
# ------------------------------------------------------------------

class TestMergeRequisites:
    def test_updates_only_passed_keys(self, mock_session_state):
        """merge_requisites обновляет только переданные ключи, не трогает остальные."""
        from src.contracts.state import init_contract_state, merge_requisites
        init_contract_state()
        cs = mock_session_state["contract"]
        cs["requisites"]["ЗАКАЗЧИК_ИНН"] = "existing"
        cs["requisites"]["ЗАКАЗЧИК_КПП"] = "keep_me"
        merge_requisites({"ЗАКАЗЧИК_ИНН": "new_value"})
        assert cs["requisites"]["ЗАКАЗЧИК_ИНН"] == "new_value"
        assert cs["requisites"]["ЗАКАЗЧИК_КПП"] == "keep_me"  # не снесён

    def test_pushes_widget_keys(self, mock_session_state):
        from src.contracts.state import init_contract_state, merge_requisites
        init_contract_state()
        merge_requisites({"ЗАКАЗЧИК_EMAIL": "test@example.com"})
        assert mock_session_state.get("w_ЗАКАЗЧИК_EMAIL") == "test@example.com"

    def test_none_value_becomes_empty_string(self, mock_session_state):
        from src.contracts.state import init_contract_state, merge_requisites
        init_contract_state()
        merge_requisites({"ЗАКАЗЧИК_ТЕЛЕФОН": None})
        cs = mock_session_state["contract"]
        assert cs["requisites"]["ЗАКАЗЧИК_ТЕЛЕФОН"] == ""

    def test_collect_for_template_unaffected(self, mock_session_state):
        """Регресс: collect_for_template возвращает тот же dict после merge."""
        from src.contracts.state import (
            init_contract_state, merge_requisites,
            set_specification, collect_for_template,
        )
        init_contract_state()
        set_specification({"СПЕЦ_НДС": "22", "СПЕЦ_ИТОГО": "1000000"})
        merge_requisites({"ЗАКАЗЧИК_ИНН": "7707083893", "ЗАКАЗЧИК_КПП": "770701001"})
        data = collect_for_template()
        assert data["ЗАКАЗЧИК_ИНН"] == "7707083893"
        assert data["ЗАКАЗЧИК_КПП"] == "770701001"
        assert data["СПЕЦ_НДС"] == "22"
        assert data["СПЕЦ_ИТОГО"] == "1000000"
