from __future__ import annotations

from datetime import datetime, timezone

from textual.reactive import reactive
from textual.widgets import Static

from claude_usage.utils import _fmt, _fmt_cost


class DailyChart(Static):
    day_data: reactive[dict] = reactive(dict, recompose=True)

    def render(self) -> str:
        data = self.day_data
        if not data:
            return "[bold]DAILY USAGE[/bold]\n\n[dim]No data yet.[/dim]"

        today = datetime.now(tz=timezone.utc).astimezone().date()
        days = sorted(data.keys(), reverse=True)[:14]
        max_tokens = max((data[d].total_tokens for d in days), default=1)

        lines = ["[bold]DAILY USAGE[/bold] (last 14 days)", ""]
        for d in days:
            t = data[d]
            filled = min(round(t.total_tokens / max_tokens * 18), 18)
            bar = "[cyan]" + "█" * filled + "[/cyan]" + "░" * (18 - filled)
            label = d.strftime("%b %d") + (" [green]today[/green]  " if d == today else "        ")
            lines.append(f"{label}  {bar}  {_fmt(t.total_tokens)}  [dim]{_fmt_cost(t.estimated_cost)}[/dim]")

        return "\n".join(lines)
