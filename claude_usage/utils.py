from __future__ import annotations

from datetime import datetime, timezone


def _bar(value: float, max_value: float, width: int = 20) -> str:
    if max_value == 0:
        return "░" * width
    filled = min(round(value / max_value * width), width)
    color = "red" if filled >= width else "yellow" if filled >= width * 0.8 else "cyan"
    return f"[{color}]{'█' * filled}[/{color}]" + "░" * (width - filled)


def _bar_pct(pct: float, width: int = 20) -> str:
    filled = min(round(pct / 100 * width), width)
    color = "red" if pct >= 95 else "yellow" if pct >= 80 else "green"
    return f"[{color}]{'█' * filled}[/{color}]" + "░" * (width - filled)


def _fmt(n: int) -> str:
    return f"{n:,}"


def _fmt_cost(cost: float) -> str:
    return f"~${cost:.4f}"


def _pct(value: float, limit: float) -> str:
    if limit == 0:
        return ""
    return f"{value / limit * 100:.1f}%"


def _fmt_reset(dt: datetime) -> str:
    local = dt.astimezone()
    now = datetime.now(tz=timezone.utc).astimezone()
    diff = dt - datetime.now(tz=timezone.utc)
    hours = int(diff.total_seconds() / 3600)
    mins = int((diff.total_seconds() % 3600) / 60)
    if diff.total_seconds() < 0:
        return "reset past"
    if hours >= 24:
        return local.strftime("resets %b %d %H:%M")
    if hours > 0:
        return f"resets in {hours}h {mins}m"
    return f"resets in {mins}m"
