"""Modal screens: habit setup, yes/no confirmation, key help."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static

from ..models import MAX_HABITS


class HabitSetupScreen(ModalScreen[list[str] | None]):
    """Edit up to five habits. Dismisses with the five slot values
    (empty strings for unused slots), or None when cancelled."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, title: str, habits: list[str], first_time: bool) -> None:
        super().__init__()
        self.title_text = title
        self.initial = (list(habits) + [""] * MAX_HABITS)[:MAX_HABITS]
        self.first_time = first_time

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-dialog", classes="dialog"):
            yield Static(self.title_text, classes="dialog-title")
            hint = (
                "New month! Pick up to 5 habits to track (prefilled from your last month)."
                if self.first_time
                else "Rename, add or clear habits. Renamed habits keep their checkmarks."
            )
            yield Static(hint, classes="dialog-hint")
            for i, name in enumerate(self.initial, start=1):
                with Horizontal(classes="setup-slot"):
                    yield Label(f"{i}.", classes="slot-num")
                    yield Input(
                        value=name,
                        placeholder="(unused)",
                        select_on_focus=False,
                        id=f"habit-{i}",
                    )
            yield Static("", id="setup-error", classes="error")
            yield Static(
                "[b]enter[/b] next  ·  [b]ctrl+s[/b] save  ·  [b]esc[/b] cancel",
                classes="dialog-keys",
            )

    def on_mount(self) -> None:
        self.query_one("#habit-1", Input).focus()

    def slots(self) -> list[str]:
        return [self.query_one(f"#habit-{i}", Input).value.strip() for i in range(1, MAX_HABITS + 1)]

    def validate(self, slots: list[str]) -> str | None:
        names = [s for s in slots if s]
        if not names:
            return "Track at least one habit."
        lowered = [n.lower() for n in names]
        dupes = sorted({n for n in names if lowered.count(n.lower()) > 1})
        if dupes:
            return f"Duplicate habit: {', '.join(dupes)}"
        return None

    def action_save(self) -> None:
        slots = self.slots()
        error = self.validate(slots)
        if error:
            self.query_one("#setup-error", Static).update(error)
            return
        self.dismiss(slots)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        idx = int(event.input.id.split("-")[1])
        if idx < MAX_HABITS:
            self.query_one(f"#habit-{idx + 1}", Input).focus()
        else:
            self.action_save()


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("y", "answer(True)", "Yes"),
        Binding("n,escape", "answer(False)", "No"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static(self.message, classes="dialog-hint")
            yield Static("[b]y[/b] yes  ·  [b]n[/b] no", classes="dialog-keys")

    def action_answer(self, value: bool) -> None:
        self.dismiss(value)



HELP_TEXT = """\
[b]Days[/b]
  ↑ ↓ / j k       move between days
  1 – 5           toggle habit N
  + / -           deep work ± 0.5h
  e / enter       write the day's sentence (enter / esc to finish)
  t               jump to today
  g               switch graph: deep work / habits done

[b]Months[/b]
  ← → / \\[ ]       previous / next month
  h               edit this month's habits

[b]App[/b]
  ?               this help
  q               quit

Data lives in ~/.habit-tracker/YYYY-MM.json (one file per month)."""


class HelpScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape,question_mark,q", "close", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static("keys", classes="dialog-title")
            yield Static(HELP_TEXT)

    def action_close(self) -> None:
        self.dismiss(None)

    def on_click(self) -> None:
        self.dismiss(None)
