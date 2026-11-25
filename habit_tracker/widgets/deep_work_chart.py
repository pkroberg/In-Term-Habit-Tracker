"""Braille line chart of deep work hours per day of the month."""

from __future__ import annotations

import math
from datetime import date

from rich.text import Text
from textual.app import RenderResult
from textual_plotext import PlotextPlot

from ..models import MonthData

WHITE = (255, 255, 255)
GRAY = (174, 182, 194)  # keep in sync with $gray in app.tcss


class DeepWorkChart(PlotextPlot):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.xs: list[int] = []
        self.ys: list[float] = []
        self.num_days = 31

    def refresh_data(self, md: MonthData, today: date) -> None:
        self.num_days = md.num_days
        last_day = md.num_days
        if md.key == (today.year, today.month):
            last_day = today.day
        elif md.key > (today.year, today.month):
            last_day = 0
        self.xs = list(range(1, last_day + 1))
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

        step, top = self._y_scale(max([4.0, *self.ys]), plot_rows=self.size.height - 2)
        plt.xlim(1, self.num_days)
        plt.ylim(0, top)
        ticks = sorted({1, *range(5, self.num_days + 1, 5), self.num_days})
        plt.xticks(ticks, [str(t) for t in ticks])
        yticks = [float(v) for v in range(0, top + 1, step)]
        plt.yticks(yticks, [f"{v:g}h" for v in yticks])
        plt.frame(False)
        plt.xaxes(True, False)
        plt.yaxes(True, False)
        return Text.from_ansi(plt.build())

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
