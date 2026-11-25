"""Plain data model for one month of habit tracking."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field

MAX_HABITS = 5
MAX_NOTE = 120
MAX_DEEP_WORK = 16.0
DEEP_WORK_STEP = 0.5
DEFAULT_HABITS = ["No Snooze", "Diet", "Started Deepwork", "Read", "Wind Down"]


def clamp_deep_work(hours: float) -> float:
    """Round to the nearest half hour and clamp to 0..MAX_DEEP_WORK."""
    rounded = round(float(hours) / DEEP_WORK_STEP) * DEEP_WORK_STEP
    return max(0.0, min(MAX_DEEP_WORK, rounded))


def clean_note(text: str) -> str:
    """Collapse a note to a single trimmed line of at most MAX_NOTE chars."""
    one_line = " ".join(str(text).split())
    return one_line[:MAX_NOTE]


def prev_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


@dataclass
class DayEntry:
    checks: dict[str, bool] = field(default_factory=dict)
    deep_work: float = 0.0
    note: str = ""

    def is_empty(self) -> bool:
        return not any(self.checks.values()) and self.deep_work == 0 and not self.note

    def to_dict(self) -> dict:
        return {
            "checks": {name: True for name, done in self.checks.items() if done},
            "deep_work": self.deep_work,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DayEntry:
        return cls(
            checks={str(k): bool(v) for k, v in dict(data.get("checks", {})).items() if v},
            deep_work=clamp_deep_work(data.get("deep_work", 0.0)),
            note=clean_note(data.get("note", "")),
        )


@dataclass
class MonthData:
    year: int
    month: int
    habits: list[str]
    days: dict[int, DayEntry] = field(default_factory=dict)

    @property
    def num_days(self) -> int:
        return calendar.monthrange(self.year, self.month)[1]

    @property
    def key(self) -> tuple[int, int]:
        return (self.year, self.month)

    def day(self, day: int) -> DayEntry:
        """Return the entry for `day`, creating an empty one if needed."""
        if not 1 <= day <= self.num_days:
            raise ValueError(f"day {day} out of range for {self.year}-{self.month:02d}")
        return self.days.setdefault(day, DayEntry())

    def set_habits(self, habits: list[str], renames: dict[str, str] | None = None) -> None:
        """Replace the habit list, moving checks for renamed habits and
        dropping checks for habits that no longer exist."""
        renames = renames or {}
        self.habits = list(habits)
        keep = set(self.habits)
        for entry in self.days.values():
            moved = {renames.get(name, name): done for name, done in entry.checks.items()}
            entry.checks = {name: done for name, done in moved.items() if name in keep}

    def checks_for(self, habit: str) -> int:
        return sum(1 for e in self.days.values() if e.checks.get(habit))

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "month": self.month,
            "habits": list(self.habits),
            "days": {
                str(d): e.to_dict() for d, e in sorted(self.days.items()) if not e.is_empty()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> MonthData:
        md = cls(
            year=int(data["year"]),
            month=int(data["month"]),
            habits=[str(h) for h in data.get("habits", [])][:MAX_HABITS],
        )
        for day_str, entry in dict(data.get("days", {})).items():
            day = int(day_str)
            if 1 <= day <= md.num_days:
                md.days[day] = DayEntry.from_dict(entry)
        return md


def diff_habits(old: list[str], slots: list[str]) -> tuple[list[str], dict[str, str], list[str]]:
    """Compare the old habit list with edited setup slots (slot i initially
    held old[i]).

    Returns (new_habits, renames, removed):
    - a habit whose name still appears anywhere in the new list keeps its data;
    - otherwise, if its slot now holds a brand-new name, it is a rename;
    - otherwise it was removed.
    """
    cleaned = [s.strip() for s in slots]
    new_habits = [s for s in cleaned if s]
    old_set = set(old)
    new_set = set(new_habits)
    renames: dict[str, str] = {}
    removed: list[str] = []
    for i, name in enumerate(old):
        if name in new_set:
            continue
        replacement = cleaned[i] if i < len(cleaned) else ""
        if replacement and replacement not in old_set and replacement not in renames.values():
            renames[name] = replacement
        else:
            removed.append(name)
    return new_habits, renames, removed
