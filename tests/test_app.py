import json
from datetime import date

import pytest

from habit_tracker import storage
from habit_tracker.app import HabitApp
from habit_tracker.models import DEFAULT_HABITS, MonthData
from habit_tracker.screens.habit_setup import ConfirmScreen, HabitSetupScreen
from habit_tracker.screens.month_screen import MonthScreen
from habit_tracker.widgets import DayRow, DeepWorkChart, NoteInput

TODAY = date(2026, 11, 24)
SIZE = (104, 51)


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HABIT_TRACKER_DIR", str(tmp_path))
    return tmp_path


def read(data_dir, name="2026-11.json"):
    return json.loads((data_dir / name).read_text())


def month_screen(app) -> MonthScreen:
    return next(s for s in app.screen_stack if isinstance(s, MonthScreen))


async def test_first_launch_setup_creates_file(data_dir):
    app = HabitApp(today=TODAY)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, HabitSetupScreen)
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert isinstance(app.screen, MonthScreen)
        assert read(data_dir)["habits"] == DEFAULT_HABITS
        assert len(app.screen.query(DayRow)) == 30
        assert isinstance(app.focused, DayRow) and app.focused.day == 24


async def test_cancel_first_setup_exits():
    app = HabitApp(today=TODAY)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert app.return_code == 0


async def test_toggle_deep_work_and_note_persist(data_dir):
    storage.save(MonthData(2026, 11, ["Gym", "Read", "Med"]))
    app = HabitApp(today=TODAY)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("2")
        assert read(data_dir)["days"]["24"]["checks"] == {"Read": True}
        await pilot.press("plus", "plus", "plus", "minus", "equals_sign")
        assert read(data_dir)["days"]["24"]["deep_work"] == 1.5
        chart = app.screen.query_one(DeepWorkChart)
        assert chart.xs[-1] == 24 and chart.ys[-1] == 1.5
        await pilot.press("e", *"Hiked", "space", *"up", "enter")
        assert isinstance(app.focused, DayRow)
        # keys typed into the note must not toggle habits or change months
        await pilot.press("e", "1", "left_square_bracket", "escape")
        assert isinstance(app.focused, DayRow)
        assert month_screen(app).month_data.key == (2026, 11)
        await pilot.press("up", "1")
        await pilot.pause()

    saved = read(data_dir)
    assert saved["days"]["24"]["note"] == "Hiked up1["
    assert saved["days"]["24"]["checks"] == {"Read": True}
    assert saved["days"]["23"]["checks"] == {"Gym": True}

    app2 = HabitApp(today=TODAY)
    async with app2.run_test(size=SIZE) as pilot:
        await pilot.pause()
        row = app2.focused
        assert row.day == 24
        assert row.query_one(NoteInput).value == "Hiked up1["


async def test_month_navigation(data_dir):
    storage.save(MonthData(2026, 11, ["Gym"]))
    app = HabitApp(today=TODAY)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("right_square_bracket")  # future: blocked
        await pilot.pause()
        assert month_screen(app).month_data.key == (2026, 11)

        await pilot.press("left_square_bracket")  # October: never set up
        await pilot.pause()
        assert isinstance(app.screen, HabitSetupScreen)
        await pilot.press("escape")  # cancel: stay on November
        await pilot.pause()
        assert month_screen(app).month_data.key == (2026, 11)

        await pilot.press("left")
        await pilot.pause()
        await pilot.press("ctrl+s")  # prefilled from November
        await pilot.pause()
        ms = month_screen(app)
        assert ms.month_data.key == (2026, 10)
        assert len(ms.query(DayRow)) == 31
        assert app.focused.day == 1
        assert read(data_dir, "2026-10.json")["habits"] == ["Gym"]

        await pilot.press("t")
        await pilot.pause()
        assert month_screen(app).month_data.key == (2026, 11)
        assert app.focused.day == 24


async def test_edit_habits_rename_and_remove(data_dir):
    md = MonthData(2026, 11, ["Gym", "Read"])
    md.day(5).checks = {"Gym": True, "Read": True}
    storage.save(md)
    app = HabitApp(today=TODAY)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        setup = app.screen
        assert isinstance(setup, HabitSetupScreen)
        setup.query_one("#habit-1").value = "Run"
        setup.query_one("#habit-2").value = ""
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)  # Read had a checkmark
        await pilot.press("y")
        await pilot.pause()
        assert read(data_dir)["habits"] == ["Run"]
        assert read(data_dir)["days"]["5"]["checks"] == {"Run": True}
        assert app.focused.day == 24


async def test_setup_rejects_duplicates_and_empty():
    storage.save(MonthData(2026, 11, ["Gym"]))
    app = HabitApp(today=TODAY)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        setup = app.screen
        setup.query_one("#habit-2").value = "gym"
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert app.screen is setup
        setup.query_one("#habit-1").value = ""
        setup.query_one("#habit-2").value = ""
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert app.screen is setup


async def test_long_habit_names_fit_104x51(data_dir):
    names = [
        "Exercise for at least thirty minutes before work",
        "Read twenty pages of a book",
        "No phone in the bedroom after 10pm",
        "Meditate",
        "Write in the journal before bed",
    ]
    storage.save(MonthData(2026, 10, names))
    app = HabitApp(today=date(2026, 10, 31))
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        screen = app.screen
        legend = str(screen.query_one("#legend").render())
        for name in names:
            assert name in legend.replace("\n", " ")
        assert "4 Meditate 0%" in legend  # items (with their %) never split across lines
        # all 31 days visible on screen and the chart keeps a usable height
        rows = list(screen.query(DayRow))
        assert len(rows) == 31
        assert all(r.region.bottom <= 51 for r in rows)
        assert rows[-1].region.height == 1
        assert screen.query_one(DeepWorkChart).size.height >= 10
        await pilot.press("5")
        assert read(data_dir, "2026-10.json")["days"]["31"]["checks"] == {names[4]: True}


async def test_long_note_scrolls_back_to_start_after_enter(data_dir):
    storage.save(MonthData(2026, 11, ["Gym"]))
    app = HabitApp(today=TODAY)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        note = app.focused.query_one(NoteInput)
        long_text = "Spent the whole afternoon hiking up the ridge trail and watched the sunset over the bay"
        await pilot.press("e", *["space" if c == " " else c for c in long_text])
        await pilot.pause()
        assert note.scroll_offset.x > 0  # scrolled to the end while typing
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.focused, DayRow)
        assert note.cursor_position == 0
        assert note.scroll_offset.x == 0
        assert read(data_dir)["days"]["24"]["note"] == long_text
        assert "dw_hrs" in str(app.screen.query_one("#table-head").query(".col-dw").first().render())


async def test_graph_toggles_to_habits_done(data_dir):
    md = MonthData(2026, 11, ["A", "B", "C", "D"])
    md.day(1).checks = {"A": True, "B": True, "C": True, "D": True}
    md.day(2).checks = {"B": True}
    md.day(2).deep_work = 3.0
    storage.save(md)
    app = HabitApp(today=TODAY)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        chart = app.screen.query_one(DeepWorkChart)
        box = app.screen.query_one("#chart-box")
        assert chart.mode == "deep work" and chart.ys[1] == 3.0
        await pilot.press("g")
        await pilot.pause()
        assert chart.mode == "habits done"
        assert "habits done" in str(box.border_title)
        assert "1[/] perfect day" in str(box.border_subtitle) or "perfect day" in str(box.border_subtitle)
        assert chart.ys[:3] == [4.0, 1.0, 0.0]
        assert chart.num_habits == 4  # y-axis tops out at the month's habit count
        await pilot.press("1")  # toggling a habit updates the habits graph live
        await pilot.pause()
        assert chart.ys[23] == 1.0
        await pilot.press("g")
        await pilot.pause()
        assert chart.mode == "deep work" and chart.ys[1] == 3.0
