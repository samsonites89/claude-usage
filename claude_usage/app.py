from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Label, Static
from textual.containers import Container, Horizontal, Vertical

from claude_usage import parser


REFRESH_INTERVAL = 30  # seconds


def _bar(value: int, max_value: int, width: int = 20) -> str:
    if max_value == 0:
        return " " * width
    filled = round(value / max_value * width)
    return "█" * filled + "░" * (width - filled)


def _fmt(n: int) -> str:
    return f"{n:,}"


def _fmt_cost(cost: float) -> str:
    return f"~${cost:.4f}"


class SummaryPanel(Static):
    DEFAULT_CSS = """
    SummaryPanel {
        width: 30;
        height: 100%;
        border: solid $primary;
        padding: 1 2;
    }
    """

    totals: reactive[parser.Totals] = reactive(parser.Totals, recompose=True)

    def render(self) -> str:
        t = self.totals
        lines = [
            "[bold]SUMMARY[/bold]",
            "",
            f"[dim]Input[/dim]",
            f"  {_fmt(t.input_tokens)}",
            "",
            f"[dim]Output[/dim]",
            f"  {_fmt(t.output_tokens)}",
            "",
            f"[dim]Cache write[/dim]",
            f"  {_fmt(t.cache_creation_tokens)}",
            "",
            f"[dim]Cache read[/dim]",
            f"  {_fmt(t.cache_read_tokens)}",
            "",
            "─" * 20,
            f"[bold]Total[/bold]",
            f"  {_fmt(t.total_tokens)}",
            "",
            f"[dim]Est. cost[/dim]",
            f"  [green]{_fmt_cost(t.estimated_cost)}[/green]",
            "",
            f"[dim]Requests[/dim]",
            f"  {_fmt(t.record_count)}",
        ]
        return "\n".join(lines)


class DailyChart(Static):
    DEFAULT_CSS = """
    DailyChart {
        height: 1fr;
        border: solid $primary;
        padding: 1 2;
        overflow-y: auto;
    }
    """

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
            bar = _bar(t.total_tokens, max_tokens, width=18)
            label = d.strftime("%b %d") + (" [green]today[/green]" if d == today else "")
            lines.append(f"{label}  [cyan]{bar}[/cyan]  {_fmt(t.total_tokens)}")

        return "\n".join(lines)


class SessionsTable(Static):
    DEFAULT_CSS = """
    SessionsTable {
        height: 1fr;
        border: solid $primary;
        padding: 1 2;
        overflow-y: auto;
    }
    """

    session_data: reactive[list] = reactive(list, recompose=True)

    def render(self) -> str:
        rows = self.session_data
        if not rows:
            return "[bold]RECENT SESSIONS[/bold]\n\n[dim]No sessions found.[/dim]"

        lines = ["[bold]RECENT SESSIONS[/bold] (last 20)", ""]
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


class ClaudeUsageApp(App):
    TITLE = "Claude Token Usage"
    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        layout: horizontal;
        height: 1fr;
    }
    #right {
        layout: vertical;
        width: 1fr;
        height: 100%;
    }
    """
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            yield SummaryPanel()
            with Vertical(id="right"):
                yield DailyChart()
                yield SessionsTable()
        yield Footer()

    def on_mount(self) -> None:
        self._load_data()
        self.set_interval(REFRESH_INTERVAL, self._load_data)

    def _load_data(self) -> None:
        records = parser.load_records()
        all_totals = parser.totals(records)
        daily = parser.by_day(records)
        sessions = parser.by_session(records)
        last_seen = parser.session_last_seen(records)

        sorted_sessions = sorted(
            [(sid, t, last_seen[sid]) for sid, t in sessions.items()],
            key=lambda x: x[2],
            reverse=True,
        )[:20]

        self.query_one(SummaryPanel).totals = all_totals
        self.query_one(DailyChart).day_data = daily
        self.query_one(SessionsTable).session_data = sorted_sessions

    def action_refresh(self) -> None:
        self._load_data()

    def action_quit(self) -> None:
        self.exit()
