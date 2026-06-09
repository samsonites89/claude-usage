from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

from claude_usage import parser
from claude_usage.utils import _fmt, _fmt_cost, _bar


class WorkspaceTable(Static):
    workspace_data: reactive[list[tuple[str, parser.Totals]]] = reactive(list, recompose=True)

    def render(self) -> str:
        rows = self.workspace_data
        if not rows:
            return "[bold darkorange]▶[/bold darkorange] [bold]WORKSPACES[/bold]\n\n[dim]No data found.[/dim]"

        total_cost = sum(t.estimated_cost for _, t in rows)
        lines = ["[bold darkorange]▶[/bold darkorange] [bold]WORKSPACES[/bold]", ""]

        col_name = 28
        col_cost = 10
        col_tok = 10
        col_bar = 14
        header = (
            f"{'Workspace':<{col_name}}  {'Est. cost':>{col_cost}}  "
            f"{'Tokens':>{col_tok}}  {'Share':<{col_bar}}"
        )
        lines.append(f"[dim]{header}[/dim]")
        lines.append("─" * (col_name + col_cost + col_tok + col_bar + 6))

        for workspace, t in rows:
            short = workspace if len(workspace) <= col_name else "…" + workspace[-(col_name - 1):]
            bar = _bar(t.estimated_cost, total_cost, width=col_bar) if total_cost > 0 else "░" * col_bar
            lines.append(
                f"{short:<{col_name}}  [green]{_fmt_cost(t.estimated_cost):>{col_cost}}[/green]  "
                f"{_fmt(t.total_tokens):>{col_tok}}  {bar}"
            )

        return "\n".join(lines)
