"""Round-trip tests for the FSM payloads.

aiogram's RedisStorage stores data as JSON, so every payload the bot keeps
between steps has to survive to_dict -> json -> from_dict unchanged.
"""

import json

from apps.bot.user_data import (
    STATE_SCHEMA_VERSION,
    DefectData,
    MeasurementEntry,
    PhotoEntry,
    is_current_schema,
)


def _json_round_trip(payload: dict) -> dict:
    return json.loads(json.dumps(payload))


def _from_another_deploy(payload: dict) -> dict:
    return payload | {"_schema": STATE_SCHEMA_VERSION + 1}


class TestMeasurementEntry:
    def test_survives_a_json_round_trip_with_floats(self):
        entry = MeasurementEntry(
            dimension="thickness",
            dimension_label="Thickness",
            value=12.5,
            unit="mm",
        )

        restored = MeasurementEntry.model_validate(
            _json_round_trip(entry.model_dump(mode="json"))
        )

        assert restored == entry
        assert isinstance(restored.value, float)

    def test_keeps_none_apart_from_zero(self):
        zero, unset = (
            MeasurementEntry.model_validate(
                _json_round_trip(entry.model_dump(mode="json"))
            )
            for entry in (MeasurementEntry(value=0.0), MeasurementEntry())
        )

        assert zero.value == 0.0
        assert unset.value is None


class TestDefectData:
    def test_empty_instance_survives_a_json_round_trip(self):
        defect = DefectData()

        assert DefectData.from_dict(_json_round_trip(defect.to_dict())) == defect

    def test_fully_populated_instance_survives_a_json_round_trip(self):
        defect = DefectData(
            wagon_id=12,
            wagon_number="60123456",
            department="coupler_brake",
            department_label="Coupler and brake",
            node="uncoupling_lever",
            node_label="Uncoupling lever",
            part_number="PN-99",
            defect_type="human_factor",
            defect_type_label="Human factor",
            severity="critical",
            severity_label="Critical",
            description="Cracked weld",
            measurements=[
                MeasurementEntry(dimension="thickness", value=12.5),
                MeasurementEntry(dimension="length", value=3.0, unit="mm"),
            ],
            photos=[
                PhotoEntry(file_id="AgACAgIAAx", message_id=10),
                PhotoEntry(file_id="AgACAgIAAy", message_id=11),
            ],
            defect_id="d1",
            current_measurement=MeasurementEntry(dimension="width", value=1.25),
            responsible_employee_id=7,
            responsible_employee_label="Ivan Petrov",
        )

        restored = DefectData.from_dict(_json_round_trip(defect.to_dict()))

        assert restored == defect

    def test_rebuilds_nested_entries_as_models_not_dicts(self):
        defect = DefectData(
            measurements=[MeasurementEntry(dimension="thickness", value=1.0)],
            current_measurement=MeasurementEntry(dimension="width"),
        )

        restored = DefectData.from_dict(_json_round_trip(defect.to_dict()))

        assert isinstance(restored.measurements[0], MeasurementEntry)
        assert isinstance(restored.current_measurement, MeasurementEntry)
        assert restored.measurements[0].value == 1.0

    def test_absent_current_measurement_stays_none(self):
        restored = DefectData.from_dict(DefectData().to_dict())

        assert restored.current_measurement is None
        assert restored.measurements == []

    def test_ignores_keys_the_model_no_longer_declares(self):
        stored = DefectData(wagon_number="60123456").to_dict()
        stored["removed_in_a_later_deploy"] = "stale"

        restored = DefectData.from_dict(stored)

        assert restored.wagon_number == "60123456"

    def test_tolerates_keys_a_later_deploy_added(self):
        stored = DefectData(wagon_number="60123456").to_dict()
        del stored["severity"]

        restored = DefectData.from_dict(stored)

        assert restored.severity is None

    def test_to_dict_does_not_alias_the_original_lists(self):
        defect = DefectData(photos=[PhotoEntry(file_id="a", message_id=1)])

        defect.to_dict()["photos"].append({"file_id": "b", "message_id": 2})

        assert [p.file_id for p in defect.photos] == ["a"]


class TestSchemaVersion:
    """A field that changes type is not caught by extra="ignore".

    Dropping a key is absorbed, and so is adding one, because every field has a
    default. A type change is not: from_dict validates nothing, so a str would
    land in an int field and reach the ORM. The stamp is what makes that case
    fail closed, at the cost of discarding a form the deploy interrupted.
    """

    def test_a_defect_from_another_deploy_is_discarded(self):
        stored = _from_another_deploy(DefectData(wagon_number="60123456").to_dict())

        assert DefectData.from_dict(stored) is None

    def test_an_unstamped_blob_predates_the_stamp_and_is_discarded(self):
        stored = DefectData(wagon_number="60123456").to_dict()
        del stored["_schema"]

        assert DefectData.from_dict(stored) is None

    def test_this_builds_own_output_survives_the_check(self):
        assert is_current_schema(DefectData().to_dict())

    def test_the_stamp_is_not_mistaken_for_a_field(self):
        """extra="ignore" drops it, so it never reaches a field."""
        restored = DefectData.from_dict(DefectData(wagon_number="1").to_dict())

        assert restored == DefectData(wagon_number="1")

    def test_nested_measurements_are_covered_by_the_parent_stamp(self):
        defect = DefectData(measurements=[MeasurementEntry(dimension="width")])

        stored = _json_round_trip(defect.to_dict())

        assert "_schema" not in stored["measurements"][0]
        assert DefectData.from_dict(stored) == defect
