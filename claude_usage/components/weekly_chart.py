from __future__ import annotations

from datetime import datetime, timedelta, timezone

from textual.reactive import reactive
from textual.widgets import Static

from claude_usage.utils import _fmt, _fmt_cost


class WeeklyChart(Static):
    week_data: reactive[dict] = reactive(dict, recompose=True)

    def render(self) -> str:
        data = self.week_data
        if not data:
            return "[bold]WEEKLY USAGE[/bold]\n\n[dim]No data yet.[/dim]"

        today = datetime.now(tz=timezone.utc).astimezone().date()
        this_week_monday = today - timedelta(days=today.weekday())
        weeks = sorted(data.keys(), reverse=True)[:8]
        max_tokens = max((data[w].total_tokens for w in weeks), default=1)

        lines = ["[bold]WEEKLY USAGE[/bold] (last 8 weeks)", ""]
        for w in weeks:
            t = data[w]
            filled = min(round(t.total_tokens / max_tokens * 18), 18)
            bar = "[magenta]" + "█" * filled + "[/magenta]" + "░" * (18 - filled)
            week_end = w + timedelta(days=6)
            label = f"{w.strftime('%b %d')}–{week_end.strftime('%d')}"
            suffix = " [green]this week[/green]" if w == this_week_monday else ""
            lines.append(f"{label}{suffix:<18}  {bar}  {_fmt(t.total_tokens)}  [dim]{_fmt_cost(t.estimated_cost)}[/dim]")

        return "\n".join(lines)
