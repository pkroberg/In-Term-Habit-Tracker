"""Braille line chart per day of the month: deep work hours, or (toggled
with `g`) the number of habits completed that day."""

from __future__ import annotations

import math
from datetime import date

from rich.text import Text
from textual.app import RenderResult
from textual_plotext import PlotextPlot

from ..models import MonthData

WHITE = (255, 255, 255)
GRAY = (174, 182, 194)  # keep in sync with $gray in app.tcss


DEEP_WORK = "deep work"
HABITS = "habits done"
MODES = (DEEP_WORK, HABITS)


class DeepWorkChart(PlotextPlot):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.mode = DEEP_WORK
        self.xs: list[int] = []
        self.ys: list[float] = []
        self.num_days = 31
        self.num_habits = 1

    def refresh_data(self, md: MonthData, today: date) -> None:
        self.num_days = md.num_days
        last_day = md.num_days
        if md.key == (today.year, today.month):
            last_day = today.day
        elif md.key > (today.year, today.month):
            last_day = 0
        self.xs = list(range(1, last_day + 1))
        self.num_habits = max(len(md.habits), 1)
        if self.mode == HABITS:
            self.ys = [float(done_count(md, d)) for d in self.xs]
        else:
            self.ys = [md.days[d].deep_work if d in md.days else 0.0 for d in self.xs]
        self.refresh()

    def render(self) -> RenderResult:
        """Draw with transparent backgrounds (so the terminal's own background
        shows through) instead of PlotextPlot's app-theme colours."""
        plt = self.plt
        plt.clear_figure()
        plt.plotsize(self.size.width, self.size.height)
        plt._set_size(self.size.width, self.size.height)
        plt.theme("clear")
        plt.canvas_color("default")
        plt.axes_color("default")
        plt.ticks_color(GRAY)

        if len(self.xs) == 1:
            plt.scatter(self.xs, self.ys, marker="braille", color=WHITE)
        elif self.xs:
            plt.plot(self.xs, self.ys, marker="braille", color=WHITE)

        plot_rows = self.size.height - 2
        if self.mode == HABITS:
            # Top of the axis is exactly the number of habits tracked this month.
            top = self.num_habits
            step = 1 if top + 1 <= max(2, plot_rows // 2) else 2
            unit = ""
        else:
            step, top = self._y_scale(max([4.0, *self.ys]), plot_rows=plot_rows)
            unit = "h"
        plt.xlim(1, self.num_days)
        plt.ylim(0, top)
        ticks = sorted({1, *range(5, self.num_days + 1, 5), self.num_days})
        plt.xticks(ticks, [str(t) for t in ticks])
        yticks = [float(v) for v in range(0, top + 1, step)]
        plt.yticks(yticks, [f"{v:g}{unit}" for v in yticks])
        plt.frame(False)
        plt.xaxes(True, False)
        plt.yaxes(True, False)
        return Text.from_ansi(plt.build())

    def toggle_mode(self) -> str:
        self.mode = MODES[(MODES.index(self.mode) + 1) % len(MODES)]
        return self.mode

    @staticmethod
    def _y_scale(peak: float, plot_rows: int) -> tuple[int, int]:
        """Pick a whole-hour tick step so labels sit at least 2 rows apart
        (short charts would otherwise bunch them up), and a top just above
        the peak that lands on a tick."""
        max_ticks = max(2, plot_rows // 2)
        for step in (1, 2, 3, 4, 5, 10):
            n = math.ceil((peak + 0.5) / step)
            if n + 1 <= max_ticks:
                break
        return step, n * step


def done_count(md: MonthData, day: int) -> int:
    """How many of the month's habits were checked on `day`."""
    entry = md.days.get(day)
    if entry is None:
        return 0
    return sum(1 for name in md.habits if entry.checks.get(name))
