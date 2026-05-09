from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static
from textual.containers import Horizontal, Vertical
from textual.worker import Worker, WorkerState

from claude_usage import parser


REFRESH_INTERVAL = 30  # seconds


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


class SummaryPanel(Static):
    DEFAULT_CSS = """
    SummaryPanel {
        width: 36;
        height: 100%;
        border: solid $primary;
        padding: 1 2;
    }
    """

    totals: reactive[parser.Totals] = reactive(parser.Totals, recompose=True)
    daily: reactive[parser.Totals] = reactive(parser.Totals, recompose=True)
    weekly: reactive[parser.Totals] = reactive(parser.Totals, recompose=True)
    daily_limit: reactive[float | None] = reactive(None, recompose=True)
    weekly_limit: reactive[float | None] = reactive(None, recompose=True)
    plan_config: reactive[parser.PlanConfig | None] = reactive(None, recompose=True)
    rate_limits: reactive[parser.RateLimits | None] = reactive(None, recompose=True)
    fetching: reactive[bool] = reactive(False, recompose=True)

    def compose(self) -> ComposeResult:
        plan = self.plan_config
        rl = self.rate_limits

        plan_label = f"[dim]{plan.label}[/dim]" if plan else "[dim]Pro[/dim]"
        yield Static(f"[bold]SUMMARY[/bold]  {plan_label}")
        yield Static("─" * 30)

        # --- Live rate limits (from API) ---
        if rl:
            fetched_ago = int((datetime.now(tz=timezone.utc) - rl.fetched_at).total_seconds() / 60)
            ago_str = f"{fetched_ago}m ago" if fetched_ago > 0 else "just now"
            yield Static(f"[bold]SESSION[/bold]  [dim]5-hour window ({ago_str})[/dim]")
            yield Static(f"  {_bar_pct(rl.session_pct, width=20)} {rl.session_pct:.1f}%")
            yield Static(f"  [dim]{_fmt_reset(rl.session_reset_at)}[/dim]")
            yield Static("")
            yield Static(f"[bold]WEEK[/bold]  [dim]7-day window[/dim]")
            yield Static(f"  {_bar_pct(rl.weekly_pct, width=20)} {rl.weekly_pct:.1f}%")
            yield Static(f"  [dim]{_fmt_reset(rl.weekly_reset_at)}[/dim]")
        elif self.fetching:
            yield Static("[dim]Fetching limits...[/dim]")
        else:
            yield Static("[dim]Press [bold]L[/bold] to fetch live limits[/dim]")

        yield Static("─" * 30)

        # --- Today (last 24h, vs inferred daily limit or plan budget) ---
        limit_source = "[dim]~24h est.[/dim]" if rl else "[dim]plan budget[/dim]"
        yield Static(f"[bold]Today[/bold]  {limit_source if self.daily_limit else ''}")
        if self.daily_limit:
            yield Static(f"  {_bar(self.daily.estimated_cost, self.daily_limit, width=20)} {_pct(self.daily.estimated_cost, self.daily_limit)}")
            yield Static(f"  {_fmt_cost(self.daily.estimated_cost)} / ${self.daily_limit:.2f}")
        else:
            yield Static(f"  {_fmt_cost(self.daily.estimated_cost)}")
        yield Static(f"  [dim]{_fmt(self.daily.total_tokens)} tokens ({_fmt(self.daily.record_count)} req)[/dim]")
        yield Static("")

        # --- This week (7d API window, vs inferred weekly limit or plan budget) ---
        week_source = "[dim]7d window[/dim]" if rl else "[dim]plan budget[/dim]"
        yield Static(f"[bold]This week[/bold]  {week_source if self.weekly_limit else ''}")
        if self.weekly_limit:
            yield Static(f"  {_bar(self.weekly.estimated_cost, self.weekly_limit, width=20)} {_pct(self.weekly.estimated_cost, self.weekly_limit)}")
            yield Static(f"  {_fmt_cost(self.weekly.estimated_cost)} / ${self.weekly_limit:.2f}")
        else:
            yield Static(f"  {_fmt_cost(self.weekly.estimated_cost)}")
        yield Static(f"  [dim]{_fmt(self.weekly.total_tokens)} tokens ({_fmt(self.weekly.record_count)} req)[/dim]")

        yield Static("─" * 30)
        yield Static(
            f"[dim]All time[/dim]\n"
            f"  {_fmt_cost(self.totals.estimated_cost)}\n"
            f"  [dim]{_fmt(self.totals.input_tokens)} in / {_fmt(self.totals.output_tokens)} out[/dim]\n"
            f"  [dim]cache wr {_fmt(self.totals.cache_creation_tokens)} / rd {_fmt(self.totals.cache_read_tokens)}[/dim]\n"
            f"  [dim]{_fmt(self.totals.record_count)} requests total[/dim]"
        )


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
            filled = min(round(t.total_tokens / max_tokens * 18), 18)
            bar = "[cyan]" + "█" * filled + "[/cyan]" + "░" * (18 - filled)
            label = d.strftime("%b %d") + (" [green]today[/green]  " if d == today else "        ")
            lines.append(f"{label}  {bar}  {_fmt(t.total_tokens)}  [dim]{_fmt_cost(t.estimated_cost)}[/dim]")

        return "\n".join(lines)


class WeeklyChart(Static):
    DEFAULT_CSS = """
    WeeklyChart {
        height: 1fr;
        border: solid $primary;
        padding: 1 2;
        overflow-y: auto;
    }
    """

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
    #charts {
        layout: horizontal;
        height: 1fr;
    }
    """
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("r", "refresh", "Refresh"),
        Binding("l", "fetch_limits", "Fetch limits"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            yield SummaryPanel()
            with Vertical(id="right"):
                with Horizontal(id="charts"):
                    yield DailyChart()
                    yield WeeklyChart()
                yield SessionsTable()
        yield Footer()

    def on_mount(self) -> None:
        self._load_data()
        self.set_interval(REFRESH_INTERVAL, self._load_data)
        # Load cached limits on startup without making a network call
        cached = parser.load_rate_limits_cache()
        if cached:
            self.query_one(SummaryPanel).rate_limits = cached

    def _load_data(self) -> None:
        records = parser.load_records()
        now = datetime.now(tz=timezone.utc)
        all_totals = parser.totals(records)
        daily = parser.by_day(records)
        weekly = parser.by_week(records)
        sessions = parser.by_session(records)
        last_seen = parser.session_last_seen(records)
        plan_config = parser.load_plan_config()
        rl = parser.load_rate_limits_cache()

        # Compute window-based totals if rate limits are cached
        if rl:
            session_start = rl.session_reset_at - timedelta(hours=5)
            session_window = parser.window_totals(records, session_start, now)
            weekly_start = rl.weekly_reset_at - timedelta(days=7)
            weekly_window = parser.window_totals(records, weekly_start, now)

            # Infer absolute limits: actual_cost / utilization = limit
            if rl.session_utilization > 0:
                session_limit_cost = session_window.estimated_cost / rl.session_utilization
                daily_limit_cost = session_limit_cost * (24 / 5)
            else:
                daily_limit_cost = None

            if rl.weekly_utilization > 0:
                weekly_limit_cost = weekly_window.estimated_cost / rl.weekly_utilization
            else:
                weekly_limit_cost = None

            # Today = last 24h from JSONL
            daily_total = parser.window_totals(records, now - timedelta(hours=24), now)
            # This week = the 7-day API window
            weekly_total = weekly_window
        else:
            daily_total = parser.today_totals(records)
            weekly_total = parser.week_totals(records)
            daily_limit_cost = plan_config.daily_budget if plan_config else None
            weekly_limit_cost = plan_config.weekly_budget if plan_config else None

        sorted_sessions = sorted(
            [(sid, t, last_seen[sid]) for sid, t in sessions.items()],
            key=lambda x: x[2],
            reverse=True,
        )[:20]

        panel = self.query_one(SummaryPanel)
        panel.totals = all_totals
        panel.daily = daily_total
        panel.weekly = weekly_total
        panel.daily_limit = daily_limit_cost
        panel.weekly_limit = weekly_limit_cost
        panel.plan_config = plan_config

        self.query_one(DailyChart).day_data = daily
        self.query_one(WeeklyChart).week_data = weekly
        self.query_one(SessionsTable).session_data = sorted_sessions

    def action_refresh(self) -> None:
        self._load_data()

    def action_fetch_limits(self) -> None:
        panel = self.query_one(SummaryPanel)
        panel.fetching = True
        self.run_worker(self._do_fetch_limits, exclusive=True)

    async def _do_fetch_limits(self) -> None:
        import asyncio
        limits = await asyncio.get_event_loop().run_in_executor(None, parser.fetch_rate_limits)
        panel = self.query_one(SummaryPanel)
        panel.fetching = False
        if limits:
            panel.rate_limits = limits

    def action_quit(self) -> None:
        self.exit()
