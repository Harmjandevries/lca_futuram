import sys
from pathlib import Path

import pytest
import types

sys.path.append(str(Path(__file__).resolve().parents[1]))

sys.modules.setdefault("bw2data", types.SimpleNamespace(Database=object))

from code_folder.helpers.brightway_helpers import BrightwayHelpers
from code_folder.helpers.constants import ExternalDatabase


class DummyDatabase:
    def __init__(self, activities, name):
        self._activities = activities
        self.name = name

    def __iter__(self):
        return iter(self._activities)


def test_build_external_exchange_uses_reference_product_for_ambiguous_name_and_location():
    ecoinvent = DummyDatabase(
        [
            {"name": "battery treatment", "location": "RER", "code": "act-1", "reference product": "nickel"},
            {"name": "battery treatment", "location": "RER", "code": "act-2", "reference product": "cobalt"},
        ],
        name="ecoinvent-test",
    )

    exchange = BrightwayHelpers.build_external_exchange(
        database=ExternalDatabase.ECOINVENT,
        biosphere=DummyDatabase([], "biosphere"),
        ecoinvent=ecoinvent,
        process_name="battery treatment",
        amount=1.0,
        unit="kilogram",
        flow_direction="input",
        location="RER",
        categories=("air", "urban air"),
        reference_product="nickel",
    )

    assert exchange["input"] == (ecoinvent.name, "act-1")


def test_find_ecoinvent_key_by_name_requires_reference_product_when_ambiguous():
    ecoinvent = DummyDatabase(
        [
            {"name": "battery treatment", "location": "RER", "code": "act-1", "reference product": "nickel"},
            {"name": "battery treatment", "location": "RER", "code": "act-2", "reference product": "cobalt"},
        ],
        name="ecoinvent-test",
    )

    with pytest.raises(ValueError) as excinfo:
        BrightwayHelpers.find_ecoinvent_key_by_name(
            name="battery treatment",
            ecoinvent=ecoinvent,
            location="RER",
        )

    assert "Multiple processes found" in str(excinfo.value)


def test_find_ecoinvent_key_by_name_single_match():
    ecoinvent = DummyDatabase(
        [
            {"name": "battery treatment", "location": "RER", "code": "act-1", "reference product": "nickel"},
        ],
        name="ecoinvent-test",
    )

    result = BrightwayHelpers.find_ecoinvent_key_by_name(
        name="battery treatment",
        ecoinvent=ecoinvent,
        location="RER",
    )

    assert result == (ecoinvent.name, "act-1")
