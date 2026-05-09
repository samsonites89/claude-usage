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
from textual.widgets import Footer, Header, Static

from claude_usage import parser
from claude_usage.components import DailyChart, RefreshPopup, SessionsTable, SummaryPanel, WeeklyChart
from claude_usage.utils import _fmt, _fmt_cost


REFRESH_INTERVAL = int(os.environ.get("CLAUDE_USAGE_REFRESH_INTERVAL", 60))

_CLAWD_ART = (
    "[bold dark_orange] ▐▛███▜▌ [/bold dark_orange]\n"
    "[bold dark_orange]▝▜█████▛▘[/bold dark_orange]\n"
    "[dark_orange]  ▘▘ ▝▝  [/dark_orange]\n"
    "[bold dark_orange]  clawd  [/bold dark_orange]"
)


class ClawdBanner(Static):
    def render(self) -> str:
        return _CLAWD_ART


class ClaudeUsageApp(App):
    TITLE = "clawd"
    CSS_PATH = "styles/app.tcss"
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    plan_override: parser.PlanConfig | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield ClawdBanner()
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
        self._auto_fetch_limits()
        self.set_interval(REFRESH_INTERVAL, self._refresh_all)
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
        plan_config = self.plan_override or parser.load_plan_config()
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

    def _refresh_all(self) -> None:
        self._load_data()
        self._auto_fetch_limits()

    def action_refresh(self) -> None:
        all_totals, daily_total = self._load_data()
        self._auto_fetch_limits()
        ts = datetime.now().strftime("%H:%M:%S")
        msg = (
            f"[bold]Refreshed[/bold]  [dim]{ts}[/dim]\n"
            f"[dim]Today  {_fmt(daily_total.total_tokens)} tokens · {_fmt_cost(daily_total.estimated_cost)}[/dim]\n"
            f"[dim]All time  {_fmt(all_totals.record_count)} requests · {_fmt_cost(all_totals.estimated_cost)}[/dim]"
        )
        self.push_screen(RefreshPopup(msg))

    def _auto_fetch_limits(self) -> None:
        self.run_worker(self._do_auto_fetch_limits, exclusive=True)

    async def _do_auto_fetch_limits(self) -> None:
        limits = await asyncio.get_event_loop().run_in_executor(None, parser.fetch_rate_limits)
        if limits:
            self.query_one(SummaryPanel).rate_limits = limits

    def action_quit(self) -> None:
        self.exit()


def _print_summary(records: list[parser.UsageRecord]) -> None:
    from claude_usage.utils import _fmt, _fmt_cost

    all_t = parser.totals(records)
    today_t = parser.today_totals(records)
    week_t = parser.week_totals(records)

    rl = parser.load_rate_limits_cache()
    if rl:
        from datetime import timedelta
        now = datetime.now(tz=timezone.utc)
        session_t = parser.window_totals(records, rl.session_reset_at - timedelta(hours=5), now)
        week_window_t = parser.window_totals(records, rl.weekly_reset_at - timedelta(days=7), now)
    else:
        session_t = week_window_t = None

    print("Claude Code Usage Summary")
    print("=" * 40)
    print(f"All time   {_fmt_cost(all_t.estimated_cost):>10}  {_fmt(all_t.record_count)} req  "
          f"{_fmt(all_t.input_tokens)} in / {_fmt(all_t.output_tokens)} out tokens")
    print(f"Today      {_fmt_cost(today_t.estimated_cost):>10}  {_fmt(today_t.record_count)} req  "
          f"{_fmt(today_t.total_tokens)} tokens")
    print(f"This week  {_fmt_cost(week_t.estimated_cost):>10}  {_fmt(week_t.record_count)} req  "
          f"{_fmt(week_t.total_tokens)} tokens")
    print(f"Cache      write {_fmt(all_t.cache_creation_tokens)} / read {_fmt(all_t.cache_read_tokens)} tokens")
    if rl and session_t and week_window_t:
        print(f"Session    {rl.session_pct:.1f}% of 5-hour window used  "
              f"({_fmt_cost(session_t.estimated_cost)})")
        print(f"Week       {rl.weekly_pct:.1f}% of 7-day window used  "
              f"({_fmt_cost(week_window_t.estimated_cost)})")


def _print_json(records: list[parser.UsageRecord]) -> None:
    import json as _json

    all_t = parser.totals(records)
    today_t = parser.today_totals(records)
    week_t = parser.week_totals(records)
    sessions = parser.by_session(records)
    last_seen = parser.session_last_seen(records)

    rl = parser.load_rate_limits_cache()
    if rl:
        from datetime import timedelta
        now = datetime.now(tz=timezone.utc)
        session_t = parser.window_totals(records, rl.session_reset_at - timedelta(hours=5), now)
        week_window_t = parser.window_totals(records, rl.weekly_reset_at - timedelta(days=7), now)
    else:
        session_t = week_window_t = None

    def totals_dict(t: parser.Totals) -> dict:
        return {
            "estimated_cost": round(t.estimated_cost, 6),
            "input_tokens": t.input_tokens,
            "output_tokens": t.output_tokens,
            "cache_creation_tokens": t.cache_creation_tokens,
            "cache_read_tokens": t.cache_read_tokens,
            "record_count": t.record_count,
        }

    sorted_sessions = sorted(
        [(sid, t, last_seen[sid]) for sid, t in sessions.items()],
        key=lambda x: x[2],
        reverse=True,
    )[:20]

    out: dict = {
        "all_time": totals_dict(all_t),
        "today": totals_dict(today_t),
        "this_week": totals_dict(week_t),
        "sessions": [
            {**totals_dict(t), "session_id": sid, "last_seen": ls.isoformat()}
            for sid, t, ls in sorted_sessions
        ],
    }

    if rl and session_t and week_window_t:
        out["rate_limits"] = {
            "session_pct": round(rl.session_pct, 2),
            "session_cost": round(session_t.estimated_cost, 6),
            "session_reset_at": rl.session_reset_at.isoformat(),
            "weekly_pct": round(rl.weekly_pct, 2),
            "weekly_cost": round(week_window_t.estimated_cost, 6),
            "weekly_reset_at": rl.weekly_reset_at.isoformat(),
            "fetched_at": rl.fetched_at.isoformat(),
        }

    print(_json.dumps(out, indent=2))


def main() -> None:
    from claude_usage import __version__

    ap = argparse.ArgumentParser(prog="claude-usage", description="Terminal dashboard for Claude Code token usage")
    ap.add_argument("-V", "--version", action="version", version=f"claude-usage {__version__}")
    ap.add_argument("--summary", action="store_true", help="Print a plain-text usage summary and exit")
    ap.add_argument("--json", action="store_true", help="Print usage data as JSON and exit")
    ap.add_argument(
        "--plan",
        choices=["pro", "max_5x", "max_20x"],
        metavar="PLAN",
        help="Override plan for budget calculations: pro, max_5x, max_20x",
    )
    args = ap.parse_args()

    if shutil.which("claude") is None:
        print("Error: the `claude` CLI is not installed or not in PATH.")
        print("claude-usage requires Claude Code to be installed.")
        print("See https://claude.ai/code to get started.")
        sys.exit(1)

    if args.summary:
        _print_summary(parser.load_records())
        return

    if args.json:
        _print_json(parser.load_records())
        return

    plan_override: parser.PlanConfig | None = None
    if args.plan:
        p = parser.PLANS[args.plan]
        plan_override = parser.PlanConfig(plan_key=args.plan, label=p["label"], monthly_budget=p["monthly_budget"])

    app = ClaudeUsageApp()
    app.plan_override = plan_override
    app.run()
