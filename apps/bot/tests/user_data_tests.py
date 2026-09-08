"""Round-trip tests for the FSM payloads.

aiogram's RedisStorage stores data as JSON, so every payload the bot keeps
between steps has to survive to_dict -> json -> from_dict unchanged.
"""

import json

from apps.bot.user_data import DefectData, EmployeeRef, MeasurementEntry


def _json_round_trip(payload: dict) -> dict:
    return json.loads(json.dumps(payload))


class TestEmployeeRef:
    def test_carries_the_three_attributes_the_flow_reads(self):
        ref = EmployeeRef(id=7, first_name="Ivan", last_name="Petrov")

        assert ref.id == 7
        assert f"{ref.first_name} {ref.last_name}" == "Ivan Petrov"

    def test_builds_from_an_employee_like_object(self):
        class Employee:
            id = 3
            first_name = "Anna"
            last_name = "Sidorova"

        ref = EmployeeRef.from_employee(Employee())

        assert ref == EmployeeRef(id=3, first_name="Anna", last_name="Sidorova")

    def test_treats_missing_names_as_empty(self):
        class Employee:
            id = 4
            first_name = None
            last_name = None

        ref = EmployeeRef.from_employee(Employee())

        assert ref.first_name == ""
        assert ref.last_name == ""

    def test_survives_a_json_round_trip(self):
        ref = EmployeeRef(id=7, first_name="Ivan", last_name="Petrov")

        assert EmployeeRef.from_dict(_json_round_trip(ref.to_dict())) == ref

    def test_is_hashable_so_it_can_live_in_a_set(self):
        assert len({EmployeeRef(id=1), EmployeeRef(id=1)}) == 1


class TestMeasurementEntry:
    def test_survives_a_json_round_trip_with_floats(self):
        entry = MeasurementEntry(
            dimension="thickness",
            dimension_label="Thickness",
            value=12.5,
            norm_value=14.0,
            unit="mm",
        )

        restored = MeasurementEntry.from_dict(_json_round_trip(entry.to_dict()))

        assert restored == entry
        assert isinstance(restored.value, float)

    def test_keeps_none_apart_from_zero(self):
        entry = MeasurementEntry(value=0.0, norm_value=None)

        restored = MeasurementEntry.from_dict(_json_round_trip(entry.to_dict()))

        assert restored.value == 0.0
        assert restored.norm_value is None


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
                MeasurementEntry(dimension="thickness", value=12.5, norm_value=14.0),
                MeasurementEntry(dimension="length", value=3.0, unit="mm"),
            ],
            photo_file_ids=["AgACAgIAAx", "AgACAgIAAy"],
            defect_id="d1",
            current_measurement=MeasurementEntry(dimension="width", value=1.25),
            responsible_employee_id=7,
            responsible_employee_label="Ivan Petrov",
        )

        restored = DefectData.from_dict(_json_round_trip(defect.to_dict()))

        assert restored == defect

    def test_rebuilds_nested_entries_as_dataclasses_not_dicts(self):
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

    def test_ignores_keys_the_dataclass_no_longer_declares(self):
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
        defect = DefectData(photo_file_ids=["a"])

        defect.to_dict()["photo_file_ids"].append("b")

        assert defect.photo_file_ids == ["a"]
