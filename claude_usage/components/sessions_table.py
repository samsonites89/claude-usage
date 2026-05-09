from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

from claude_usage.utils import _fmt, _fmt_cost


class SessionsTable(Static):
    session_data: reactive[list] = reactive(list, recompose=True)

    def render(self) -> str:
        rows = self.session_data
        if not rows:
            return "[bold dark_orange]▶[/bold dark_orange] [bold]RECENT SESSIONS[/bold]\n\n[dim]No sessions found.[/dim]"

        lines = ["[bold dark_orange]▶[/bold dark_orange] [bold]RECENT SESSIONS[/bold] (last 20)", ""]
        col_id = 18
        col_tok = 10
        col_cost = 10
        col_time = 16
        header = (
            f"{'Session':<{col_id}}  {'Tokens':>{col_tok}}  "
            f"{'Est. cost':>{col_cost}}  {'Last active':<{col_time}}"
        )
        lines.append(f"[dim]{header}[/dim]")
        lines.append("─" * (col_id + col_tok + col_cost + col_time + 6))

        for sid, t, last_seen in rows:
            short_id = sid[:16] + ".."
            time_str = last_seen.astimezone().strftime("%b %d %H:%M")
            lines.append(
                f"{short_id:<{col_id}}  {_fmt(t.total_tokens):>{col_tok}}  "
                f"[green]{_fmt_cost(t.estimated_cost):>{col_cost}}[/green]  {time_str}"
            )

        return "\n".join(lines)
