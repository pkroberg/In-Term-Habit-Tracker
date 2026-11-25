# Habit Tracker (in-terminal)

A monthly habit tracker for the terminal, built with [Textual](https://textual.textualize.io/).

- One month on screen at a time; step between months with `[` / `]` (or ← / →).
- Per day: up to 5 habit checkboxes, hours of deep work, and one sentence for the day's memorable moment.
- A line chart of deep work hours for each day of the month.
- The first time you open a month, you pick its habits (prefilled from your most recent month). Press `h` to change them later. Renamed habits keep their checkmarks.

## Install & run

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/habit                # or: .venv/bin/python -m habit_tracker
```

To run it from anywhere (including `~` in a fresh terminal), link the launcher into a folder on your PATH:

```bash
ln -s "$PWD/.venv/bin/habit" ~/.local/bin/habit
habit
```

The layout is built for a **104×51** terminal (JetBrains Mono): all 31 days, the habit legend and the chart fit on one screen without scrolling. The month name, totals and key hints sit in the box borders to leave the chart as much height as possible. Colours are white and one dim gray on a transparent background, so the terminal's own background shows through.

## Keys

| Key | Action |
|---|---|
| ↑ ↓ / j k | move between days |
| 1 – 5 | toggle habit N on the selected day |
| + / - | deep work ± 0.5h |
| e / enter | write the day's sentence (enter or esc to finish) |
| [ ] / ← → | previous / next month |
| t | jump to today |
| g | switch the graph between deep work hours and habits done per day |
| h | edit this month's habits |
| ? | help |
| q | quit |

The mouse works too: click a checkbox to toggle it, or click a sentence to edit it.

## Data

Each month is saved as a readable JSON file at `~/.habit-tracker/YYYY-MM.json`. Changes are written right away, and each save is atomic. Set `HABIT_TRACKER_DIR` to keep the files somewhere else, such as a synced folder.

## Tests

```bash
.venv/bin/pytest
```
