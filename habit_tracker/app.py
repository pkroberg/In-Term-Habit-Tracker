"""Textual app entry point."""

from __future__ import annotations

from datetime import date

from textual.app import App

from .screens.month_screen import MonthScreen


class HabitApp(App):
    TITLE = "Habit Tracker"
    CSS_PATH = "app.tcss"
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, today: date | None = None) -> None:
        super().__init__()
        self.today = today or date.today()
        # Native ANSI mode: backgrounds stay transparent so the terminal's own
        # background shows through; all foreground colours come from app.tcss.
        self.theme = "ansi-dark"

    def on_mount(self) -> None:
        self.push_screen(MonthScreen(self.today))


def main() -> None:
    HabitApp().run()


if __name__ == "__main__":
    main()
