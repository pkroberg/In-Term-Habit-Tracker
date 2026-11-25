"""One JSON file per month in ~/.habit-tracker (override with HABIT_TRACKER_DIR)."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from .models import MonthData

_FILE_RE = re.compile(r"^(\d{4})-(\d{2})\.json$")


class StorageError(Exception):
    pass


def data_dir() -> Path:
    return Path(os.environ.get("HABIT_TRACKER_DIR", "~/.habit-tracker")).expanduser()


def path_for(year: int, month: int) -> Path:
    return data_dir() / f"{year:04d}-{month:02d}.json"


def exists(year: int, month: int) -> bool:
    return path_for(year, month).is_file()


def load(year: int, month: int) -> MonthData | None:
    """Load a month, or return None if it has never been set up."""
    path = path_for(year, month)
    if not path.is_file():
        return None
    try:
        return MonthData.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise StorageError(f"Could not read {path}: {exc}") from exc


def save(md: MonthData) -> Path:
    """Atomically write a month to disk (temp file + rename)."""
    path = path_for(md.year, md.month)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(md.to_dict(), fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path


def saved_months() -> list[tuple[int, int]]:
    directory = data_dir()
    if not directory.is_dir():
        return []
    months = []
    for p in directory.iterdir():
        m = _FILE_RE.match(p.name)
        if m and 1 <= int(m.group(2)) <= 12:
            months.append((int(m.group(1)), int(m.group(2))))
    return sorted(months)


def nearest_habits(year: int, month: int) -> list[str] | None:
    """Habits from the closest earlier month on disk (or, failing that, the
    closest later one) to prefill a new month's setup."""
    months = [k for k in saved_months() if k != (year, month)]
    earlier = [k for k in months if k < (year, month)]
    later = [k for k in months if k > (year, month)]
    for key in list(reversed(earlier)) + later:
        try:
            md = load(*key)
        except StorageError:
            continue
        if md and md.habits:
            return md.habits
    return None
