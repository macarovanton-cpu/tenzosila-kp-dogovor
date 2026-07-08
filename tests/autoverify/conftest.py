"""Session-фикстуры autoverify: один прогон раннера на каждую JSON-фикстуру."""
from __future__ import annotations

import pytest

from tests.autoverify.fixtures import list_fixture_ids, load_fixture
from tests.autoverify.runner import GeneratedSet, generate_all


@pytest.fixture(scope="session", params=list_fixture_ids())
def generated(request, tmp_path_factory) -> GeneratedSet:
    """Результат headless-прогона фикстуры (кэш на сессию pytest)."""
    out = tmp_path_factory.mktemp(f"gen_{request.param}")
    return generate_all(load_fixture(request.param), out)


@pytest.fixture(scope="session")
def generated_again(generated, tmp_path_factory) -> GeneratedSet:
    """Второй независимый прогон той же фикстуры — для проверки детерминизма."""
    out = tmp_path_factory.mktemp(f"gen2_{generated.fixture_id}")
    return generate_all(load_fixture(generated.fixture_id), out)
