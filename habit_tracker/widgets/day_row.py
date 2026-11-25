"""A single day in the month table: cursor | date | habit checks | deep work | note."""

from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Static

from ..models import DEEP_WORK_STEP, MAX_NOTE, DayEntry, clamp_deep_work, clean_note

CHECKED = "●"
UNCHECKED = "○"
CURSOR = "▸"


class HabitCell(Static):
    """A clickable ● / ○ cell."""

    checked: reactive[bool] = reactive(False)

    class Clicked(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    def __init__(self, index: int, checked: bool) -> None:
        super().__init__(classes="col-habit habit-cell")
        self.index = index
        self.set_reactive(HabitCell.checked, checked)
        self._paint(checked)

    def watch_checked(self, checked: bool) -> None:
        self._paint(checked)

    def _paint(self, checked: bool) -> None:
        self.set_class(checked, "-checked")
        self.update(CHECKED if checked else UNCHECKED)

    def on_click(self) -> None:
        self.post_message(self.Clicked(self.index))


class NoteInput(Input):
    """Sentence input; Enter or Escape hands focus back to the row."""

    BINDINGS = [Binding("escape", "leave", "Done", show=False)]

    def on_blur(self) -> None:
        # After editing a long sentence, show its beginning again, not the end.
        self.cursor_position = 0
        self.scroll_to(x=0, animate=False)

    def action_leave(self) -> None:
        row = self.parent
        if isinstance(row, DayRow):
            row.focus()


class DayRow(Horizontal, can_focus=True):
    BINDINGS = [
        Binding("up,k", "move(-1)", "Prev day", show=False),
        Binding("down,j", "move(1)", "Next day", show=False),
        *[Binding(str(i), f"toggle({i - 1})", f"Habit {i}", show=False) for i in range(1, 6)],
        Binding("plus,equals_sign", "deep_work(1)", "+0.5h", show=False),
        Binding("minus", "deep_work(-1)", "-0.5h", show=False),
        Binding("e,enter", "edit_note", "Edit sentence", show=False),
    ]

    class Changed(Message):
        """Something on this day changed and should be saved."""

        def __init__(self, row: DayRow, deep_work_changed: bool) -> None:
            super().__init__()
            self.row = row
            self.deep_work_changed = deep_work_changed

    def __init__(self, day_date: date, habits: list[str], entry: DayEntry, today: date) -> None:
        super().__init__(classes="day-row")
        self.day_date = day_date
        self.habits = habits
        self.entry = entry
        self.is_today = day_date == today
        self.is_future = day_date > today
        self.set_class(self.is_today, "-today")
        self.set_class(self.is_future, "-future")
        self._update_empty()

    @property
    def day(self) -> int:
        return self.day_date.day

    def compose(self) -> ComposeResult:
        yield Static("", classes="col-cursor")
        yield Static(self.day_date.strftime("%a %d"), classes="col-day")
        for i, name in enumerate(self.habits):
            yield HabitCell(i, bool(self.entry.checks.get(name)))
        yield Static(self._deep_work_text(), classes="col-dw")
        yield NoteInput(
            value=self.entry.note,
            placeholder="what made today memorable?" if self.is_today else "",
            max_length=MAX_NOTE,
            select_on_focus=False,
            compact=True,
            classes="col-note",
        )

    def _deep_work_text(self) -> str:
        hours = self.entry.deep_work
        return f"{hours:g}h" if hours else "[#aeb6c2]·[/]"  # $gray

    def _update_empty(self) -> None:
        self.set_class(self.entry.is_empty(), "-empty")

    def _changed(self, deep_work_changed: bool) -> None:
        self._update_empty()
        self.post_message(self.Changed(self, deep_work_changed))

    # -- cursor --------------------------------------------------------------

    def _set_cursor(self, on: bool) -> None:
        self.set_class(on, "-cursor")
        self.query_one(".col-cursor", Static).update(CURSOR if on else "")

    def on_descendant_focus(self) -> None:
        self._set_cursor(True)

    def on_descendant_blur(self) -> None:
        self._set_cursor(self.has_focus)

    def on_focus(self) -> None:
        self._set_cursor(True)

    def on_blur(self) -> None:
        self._set_cursor(self.has_focus_within)

    # -- actions -------------------------------------------------------------

    def action_move(self, delta: int) -> None:
        rows = list(self.parent.query_children(DayRow)) if self.parent else []
        if self not in rows:
            return
        idx = max(0, min(len(rows) - 1, rows.index(self) + delta))
        rows[idx].focus()
        rows[idx].scroll_visible()

    def action_toggle(self, index: int) -> None:
        if index >= len(self.habits):
            return
        cell = self.query(HabitCell)[index]
        cell.checked = not cell.checked
        if cell.checked:
            self.entry.checks[self.habits[index]] = True
        else:
            self.entry.checks.pop(self.habits[index], None)
        self._changed(deep_work_changed=False)

    def action_deep_work(self, direction: int) -> None:
        new = clamp_deep_work(self.entry.deep_work + direction * DEEP_WORK_STEP)
        if new == self.entry.deep_work:
            return
        self.entry.deep_work = new
        self.query_one(".col-dw", Static).update(self._deep_work_text())
        self._changed(deep_work_changed=True)

    def action_edit_note(self) -> None:
        note = self.query_one(NoteInput)
        note.focus()
        note.cursor_position = len(note.value)

    # -- events --------------------------------------------------------------

    def on_habit_cell_clicked(self, event: HabitCell.Clicked) -> None:
        event.stop()
        self.action_toggle(event.index)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        note = clean_note(event.value)
        if note == self.entry.note:
            return
        self.entry.note = note
        self._changed(deep_work_changed=False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.focus()
