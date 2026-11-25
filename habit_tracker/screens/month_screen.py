"""The main screen: one month of habits, notes and deep work."""

from __future__ import annotations

import calendar
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from .. import storage
from ..models import DEFAULT_HABITS, DayEntry, MonthData, diff_habits, next_month, prev_month
from ..widgets import DayRow, DeepWorkChart, HabitLegend
from .habit_setup import ConfirmScreen, HabitSetupScreen, HelpScreen


class MonthScreen(Screen):
    BINDINGS = [
        Binding("left,left_square_bracket", "prev_month", "Prev month"),
        Binding("right,right_square_bracket", "next_month", "Next month"),
        Binding("t", "today", "Today"),
        Binding("h", "edit_habits", "Habits"),
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    HINTS = " · ".join(
        f"[b]{key}[/b] {label}"
        for key, label in [
            ("1-5", "habit"),
            ("+/-", "deep"),
            ("e", "note"),
            ("←→", "month"),
            ("t", "today"),
            ("h", "habits"),
            ("?", "help"),
            ("q", "quit"),
        ]
    )
    """Shown in the table box's bottom border; the full list is in the ? help."""

    def __init__(self, today: date) -> None:
        super().__init__()
        self.today = today
        self.month_data: MonthData | None = None

    # -- layout ------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="chart-box"):
            yield DeepWorkChart(id="chart")
        with Vertical(id="table-box"):
            yield Horizontal(id="table-head", classes="table-line")
            yield VerticalScroll(id="days")
            yield HabitLegend(id="legend")

    def on_mount(self) -> None:
        self.query_one("#table-box").border_subtitle = self.HINTS
        self.open_month(self.today.year, self.today.month)

    # -- month loading -----------------------------------------------------

    def open_month(self, year: int, month: int) -> None:
        if (year, month) > (self.today.year, self.today.month):
            self.notify("That month hasn't started yet.", severity="warning", timeout=2)
            return
        try:
            md = storage.load(year, month)
        except storage.StorageError as exc:
            self.notify(str(exc), title="Can't open month", severity="error", timeout=8)
            if self.month_data is None:
                self.app.exit(message=str(exc))
            return
        if md is not None:
            self.call_next(self.show_month, md)
            return

        prefill = storage.nearest_habits(year, month) or DEFAULT_HABITS
        title = f"Habits for {calendar.month_name[month]} {year}"

        def on_setup(slots: list[str] | None) -> None:
            if slots is None:
                if self.month_data is None:
                    self.app.exit()
                return
            new = MonthData(year, month, [s for s in slots if s])
            storage.save(new)
            self.call_next(self.show_month, new)

        self.app.push_screen(HabitSetupScreen(title, prefill, first_time=True), on_setup)

    async def show_month(self, md: MonthData, focus_day: int | None = None) -> None:
        self.month_data = md
        is_current = md.key == (self.today.year, self.today.month)

        self.query_one("#chart-box").border_title = (
            f"◀ [b #ffffff]{calendar.month_name[md.month]} {md.year}[/] ▶  ·  deep work"
        )

        head = self.query_one("#table-head", Horizontal)
        await head.remove_children()
        numbers = [str(i) for i in range(1, len(md.habits) + 1)]
        await head.mount_all(self._table_line("", "day", numbers, "dw_hrs", "memorable moment"))

        days = self.query_one("#days", VerticalScroll)
        await days.remove_children()
        rows = [
            DayRow(
                date(md.year, md.month, d),
                md.habits,
                md.days.get(d) or DayEntry(),
                self.today,
            )
            for d in range(1, md.num_days + 1)
        ]
        await days.mount_all(rows)

        self.refresh_stats(chart=True)
        if focus_day is None:
            focus_day = self.today.day if is_current else 1
        self.focus_day(focus_day)

    def focus_day(self, day: int) -> None:
        rows = list(self.query_one("#days").query_children(DayRow))
        if not rows:
            return
        row = rows[max(0, min(len(rows), day) - 1)]
        row.focus()
        self.call_after_refresh(row.scroll_visible, animate=False, top=False)

    # -- stats ---------------------------------------------------------------

    def refresh_stats(self, chart: bool) -> None:
        md = self.month_data
        if md is None:
            return
        if chart:
            self.query_one(DeepWorkChart).refresh_data(md, self.today)
        if md.key == (self.today.year, self.today.month):
            elapsed = self.today.day
        else:
            elapsed = md.num_days
        elapsed = max(elapsed, 1)
        total = sum(e.deep_work for e in md.days.values())
        notes = sum(1 for e in md.days.values() if e.note)
        self.query_one("#chart-box").border_subtitle = (
            f"[b #ffffff]{total:g}h[/] total  ·  [b #ffffff]{total / elapsed:.1f}h[/] avg/day"
            f"  ·  [b #ffffff]{notes}[/] moments"
        )
        self.query_one(HabitLegend).items = [
            (name, f"{round(100 * md.checks_for(name) / elapsed)}%") for name in md.habits
        ]

    @staticmethod
    def _table_line(cursor: str, day: str, habits: list[str], dw: str, note: str) -> list[Static]:
        cells = [Static(cursor, classes="col-cursor"), Static(day, classes="col-day")]
        cells += [Static(text, classes="col-habit") for text in habits]
        cells += [Static(dw, classes="col-dw"), Static(note, classes="col-note-head")]
        return cells

    # -- events --------------------------------------------------------------

    def on_day_row_changed(self, event: DayRow.Changed) -> None:
        md = self.month_data
        if md is None:
            return
        md.days[event.row.day] = event.row.entry
        try:
            storage.save(md)
        except OSError as exc:
            self.notify(f"Save failed: {exc}", severity="error")
        self.refresh_stats(chart=event.deep_work_changed)

    # -- actions -------------------------------------------------------------

    def _focused_day(self) -> int | None:
        node = self.focused
        while node is not None and not isinstance(node, DayRow):
            node = node.parent
        return node.day if isinstance(node, DayRow) else None

    def action_prev_month(self) -> None:
        if self.month_data:
            self.open_month(*prev_month(*self.month_data.key))

    def action_next_month(self) -> None:
        if self.month_data:
            self.open_month(*next_month(*self.month_data.key))

    def action_today(self) -> None:
        if self.month_data and self.month_data.key == (self.today.year, self.today.month):
            self.focus_day(self.today.day)
        else:
            self.open_month(self.today.year, self.today.month)

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_quit(self) -> None:
        self.app.exit()

    def action_edit_habits(self) -> None:
        md = self.month_data
        if md is None:
            return
        focus_day = self._focused_day()
        title = f"Habits for {calendar.month_name[md.month]} {md.year}"

        def apply(new_habits: list[str], renames: dict[str, str]) -> None:
            md.set_habits(new_habits, renames)
            storage.save(md)
            self.call_next(self.show_month, md, focus_day)

        def on_setup(slots: list[str] | None) -> None:
            if slots is None:
                return
            new_habits, renames, removed = diff_habits(md.habits, slots)
            losing = [name for name in removed if md.checks_for(name)]
            if not losing:
                apply(new_habits, renames)
                return
            detail = ", ".join(f"{n} ({md.checks_for(n)} days)" for n in losing)
            self.app.push_screen(
                ConfirmScreen(f"Remove {detail}?\nTheir checkmarks for this month will be deleted."),
                lambda ok: apply(new_habits, renames) if ok else None,
            )

        self.app.push_screen(HabitSetupScreen(title, md.habits, first_time=False), on_setup)

