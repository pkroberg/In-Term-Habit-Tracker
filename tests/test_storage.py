import json

import pytest

from habit_tracker import storage
from habit_tracker.models import (
    DayEntry,
    MonthData,
    clamp_deep_work,
    clean_note,
    diff_habits,
)


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HABIT_TRACKER_DIR", str(tmp_path))
    return tmp_path


def test_round_trip(data_dir):
    md = MonthData(2026, 11, ["Gym", "Read"])
    md.day(3).checks["Gym"] = True
    md.day(3).deep_work = 2.5
    md.day(3).note = "Hiked with Sam"
    md.day(4)  # empty day is not written
    storage.save(md)

    raw = json.loads((data_dir / "2026-11.json").read_text())
    assert list(raw["days"]) == ["3"]
    loaded = storage.load(2026, 11)
    assert loaded.habits == ["Gym", "Read"]
    assert loaded.days[3] == DayEntry({"Gym": True}, 2.5, "Hiked with Sam")


def test_load_missing_returns_none():
    assert storage.load(2026, 1) is None


def test_corrupt_file_raises(data_dir):
    (data_dir / "2026-11.json").write_text("{not json")
    with pytest.raises(storage.StorageError):
        storage.load(2026, 11)


def test_save_is_atomic_and_leaves_no_temp_files(data_dir):
    md = MonthData(2026, 11, ["Gym"])
    storage.save(md)
    storage.save(md)
    assert sorted(p.name for p in data_dir.iterdir()) == ["2026-11.json"]


def test_nearest_habits_prefers_earlier_and_skips_gaps():
    storage.save(MonthData(2026, 6, ["June"]))
    storage.save(MonthData(2026, 9, ["Sept"]))
    storage.save(MonthData(2027, 1, ["Jan"]))
    assert storage.nearest_habits(2026, 11) == ["Sept"]
    assert storage.nearest_habits(2026, 7) == ["June"]
    assert storage.nearest_habits(2026, 1) == ["June"]  # nothing earlier: use later
    assert storage.nearest_habits(2026, 9) == ["June"]  # ignores the month itself


def test_nearest_habits_none_when_empty():
    assert storage.nearest_habits(2026, 11) is None


def test_clamping():
    assert clamp_deep_work(-1) == 0
    assert clamp_deep_work(2.3) == 2.5
    assert clamp_deep_work(99) == 16
    assert clean_note("  hello\nworld \t ") == "hello world"
    assert len(clean_note("x" * 500)) == 120


def test_from_dict_ignores_out_of_range_days():
    md = MonthData.from_dict(
        {"year": 2026, "month": 2, "habits": ["A"], "days": {"30": {"deep_work": 1}, "2": {"deep_work": 1}}}
    )
    assert list(md.days) == [2]


def test_diff_habits_rename_remove_add_and_reorder():
    old = ["Gym", "Read", "Meditate", "Water"]
    slots = ["Run", "Water", "Meditate", "", "Journal"]
    new, renames, removed = diff_habits(old, slots)
    assert new == ["Run", "Water", "Meditate", "Journal"]
    assert renames == {"Gym": "Run"}
    assert removed == ["Read"]  # its slot now holds an existing habit (Water)


def test_set_habits_moves_and_drops_checks():
    md = MonthData(2026, 11, ["Gym", "Read"])
    md.day(1).checks = {"Gym": True, "Read": True}
    md.set_habits(["Run"], {"Gym": "Run"})
    assert md.days[1].checks == {"Run": True}


def test_set_habits_swap_names():
    md = MonthData(2026, 11, ["A", "B"])
    md.day(1).checks = {"A": True}
    new, renames, _ = diff_habits(["A", "B"], ["B", "A", "", "", ""])
    md.set_habits(new, renames)
    assert renames == {}  # both names still exist: identity kept by name
    assert md.days[1].checks == {"A": True}
