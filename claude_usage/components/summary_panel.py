from __future__ import annotations

from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static

from claude_usage import parser
from claude_usage.utils import _bar, _bar_pct, _fmt, _fmt_cost, _pct, _fmt_reset


class SummaryPanel(Static):
    totals: reactive[parser.Totals] = reactive(parser.Totals, recompose=True)
    daily: reactive[parser.Totals] = reactive(parser.Totals, recompose=True)
    weekly: reactive[parser.Totals] = reactive(parser.Totals, recompose=True)
    daily_limit: reactive[float | None] = reactive(None, recompose=True)
    weekly_limit: reactive[float | None] = reactive(None, recompose=True)
    plan_config: reactive[parser.PlanConfig | None] = reactive(None, recompose=True)
    rate_limits: reactive[parser.RateLimits | None] = reactive(None, recompose=True)

    def compose(self) -> ComposeResult:
        plan = self.plan_config
        rl = self.rate_limits

        plan_label = f"[dim]{plan.label}[/dim]" if plan else "[dim]Pro[/dim]"
        yield Static(f"[bold dark_orange]▶[/bold dark_orange] [bold]USAGE[/bold]  {plan_label}")
        yield Static("─" * 30)

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
        else:
            yield Static("[dim]Fetching live limits...[/dim]")

        yield Static("─" * 30)

        limit_source = "[dim]~24h est.[/dim]" if rl else "[dim]plan budget[/dim]"
        yield Static(f"[bold]Today[/bold]  {limit_source if self.daily_limit else ''}")
        if self.daily_limit:
            yield Static(f"  {_bar(self.daily.estimated_cost, self.daily_limit, width=20)} {_pct(self.daily.estimated_cost, self.daily_limit)}")
            yield Static(f"  {_fmt_cost(self.daily.estimated_cost)} / ${self.daily_limit:.2f}")
        else:
            yield Static(f"  {_fmt_cost(self.daily.estimated_cost)}")
        yield Static(f"  [dim]{_fmt(self.daily.total_tokens)} tokens ({_fmt(self.daily.record_count)} req)[/dim]")
        yield Static("")

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
