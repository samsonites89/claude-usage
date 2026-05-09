from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header

from claude_usage import parser
from claude_usage.components import DailyChart, RefreshPopup, SessionsTable, SummaryPanel, WeeklyChart
from claude_usage.utils import _fmt, _fmt_cost


REFRESH_INTERVAL = int(os.environ.get("CLAUDE_USAGE_REFRESH_INTERVAL", 30))
LIMITS_REFRESH_INTERVAL = int(os.environ.get("CLAUDE_USAGE_LIMITS_REFRESH_INTERVAL", 300))


class ClaudeUsageApp(App):
    TITLE = "Claude Token Usage"
    CSS_PATH = "styles/app.tcss"
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
        self.set_interval(LIMITS_REFRESH_INTERVAL, self._auto_fetch_limits)
        cached = parser.load_rate_limits_cache()
        if cached:
            self.query_one(SummaryPanel).rate_limits = cached

    def _load_data(self) -> tuple[parser.Totals, parser.Totals]:
        records = parser.load_records()
        now = datetime.now(tz=timezone.utc)
        all_totals = parser.totals(records)
        daily = parser.by_day(records)
        weekly = parser.by_week(records)
        sessions = parser.by_session(records)
        last_seen = parser.session_last_seen(records)
        plan_config = parser.load_plan_config()
        rl = parser.load_rate_limits_cache()

        if rl:
            session_start = rl.session_reset_at - timedelta(hours=5)
            session_window = parser.window_totals(records, session_start, now)
            weekly_start = rl.weekly_reset_at - timedelta(days=7)
            weekly_window = parser.window_totals(records, weekly_start, now)

            if rl.session_utilization > 0:
                session_limit_cost = session_window.estimated_cost / rl.session_utilization
                daily_limit_cost = session_limit_cost * (24 / 5)
            else:
                daily_limit_cost = None

            if rl.weekly_utilization > 0:
                weekly_limit_cost = weekly_window.estimated_cost / rl.weekly_utilization
            else:
                weekly_limit_cost = None

            daily_total = parser.window_totals(records, now - timedelta(hours=24), now)
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
        if rl:
            panel.rate_limits = rl

        self.query_one(DailyChart).day_data = daily
        self.query_one(WeeklyChart).week_data = weekly
        self.query_one(SessionsTable).session_data = sorted_sessions

        return all_totals, daily_total

    def action_refresh(self) -> None:
        all_totals, daily_total = self._load_data()
        ts = datetime.now().strftime("%H:%M:%S")
        msg = (
            f"[bold]Refreshed[/bold]  [dim]{ts}[/dim]\n"
            f"[dim]Today  {_fmt(daily_total.total_tokens)} tokens · {_fmt_cost(daily_total.estimated_cost)}[/dim]\n"
            f"[dim]All time  {_fmt(all_totals.record_count)} requests · {_fmt_cost(all_totals.estimated_cost)}[/dim]"
        )
        self.push_screen(RefreshPopup(msg))

    def _auto_fetch_limits(self) -> None:
        self.run_worker(self._do_auto_fetch_limits, exclusive=True)

    def action_fetch_limits(self) -> None:
        self.query_one(SummaryPanel).fetching = True
        self.run_worker(self._do_fetch_limits, exclusive=True)

    async def _do_auto_fetch_limits(self) -> None:
        limits = await asyncio.get_event_loop().run_in_executor(None, parser.fetch_rate_limits)
        if limits:
            self.query_one(SummaryPanel).rate_limits = limits

    async def _do_fetch_limits(self) -> None:
        limits = await asyncio.get_event_loop().run_in_executor(None, parser.fetch_rate_limits)
        panel = self.query_one(SummaryPanel)
        panel.fetching = False
        if limits:
            panel.rate_limits = limits
            await self.push_screen(RefreshPopup("[bold][green]Rate limits updated[/green][/bold]"))
        else:
            await self.push_screen(RefreshPopup("[bold][red]Failed to fetch rate limits[/red][/bold]", timeout=3.0))

    def action_quit(self) -> None:
        self.exit()


def main() -> None:
    from claude_usage import __version__

    ap = argparse.ArgumentParser(prog="claude-usage", description="Terminal dashboard for Claude Code token usage")
    ap.add_argument("-V", "--version", action="version", version=f"claude-usage {__version__}")
    ap.parse_args()

    if shutil.which("claude") is None:
        print("Error: the `claude` CLI is not installed or not in PATH.")
        print("claude-usage requires Claude Code to be installed.")
        print("See https://claude.ai/code to get started.")
        sys.exit(1)

    ClaudeUsageApp().run()
