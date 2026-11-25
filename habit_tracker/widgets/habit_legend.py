"""Full habit names (keyed by their column number) with completion %."""

from __future__ import annotations

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

GAP = "   "
WHITE = "#ffffff"
GRAY = "#aeb6c2"  # $gray in app.tcss


class HabitLegend(Widget):
    """Packs "1 Name 55%   2 Name 40% ..." into as few lines as the width
    allows, breaking only between habits (a name longer than a whole line
    still wraps). Grows taller for long names; the chart above gives up rows."""

    DEFAULT_CSS = "HabitLegend { height: auto; }"

    items: reactive[list[tuple[str, str]]] = reactive(list, layout=True)

    def render(self) -> Text:
        width = max(self.content_size.width, 1)
        out = Text(no_wrap=False)
        line_len = 0
        for i, (name, pct) in enumerate(self.items, start=1):
            item_len = len(f"{i} {name} {pct}")
            if line_len:
                if line_len + len(GAP) + item_len > width:
                    out.append("\n")
                    line_len = 0
                else:
                    out.append(GAP)
                    line_len += len(GAP)
            out.append(f"{i} ", style=f"bold {WHITE}")
            out.append(name, style=GRAY)
            out.append(f" {pct}", style=WHITE)
            line_len += item_len
        return out
