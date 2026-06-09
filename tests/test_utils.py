from __future__ import annotations

from datetime import datetime, timedelta, timezone

from claude_usage.utils import _bar, _bar_pct, _fmt, _fmt_cost, _fmt_reset, _pct


class TestFmt:
    def test_zero(self):
        assert _fmt(0) == "0"

    def test_thousands(self):
        assert _fmt(1234) == "1,234"

    def test_millions(self):
        assert _fmt(1234567) == "1,234,567"


class TestFmtCost:
    def test_zero(self):
        assert _fmt_cost(0.0) == "~$0.00"

    def test_rounds_to_two_decimals(self):
        assert _fmt_cost(1.2345) == "~$1.23"

    def test_whole_dollar(self):
        assert _fmt_cost(5.0) == "~$5.00"

    def test_sub_cent(self):
        assert _fmt_cost(0.001) == "~$0.00"


class TestPct:
    def test_zero_limit_returns_empty(self):
        assert _pct(1.0, 0.0) == ""

    def test_quarter(self):
        assert _pct(1.0, 4.0) == "25.0%"

    def test_full(self):
        assert _pct(1.0, 1.0) == "100.0%"

    def test_zero_value(self):
        assert _pct(0.0, 10.0) == "0.0%"


class TestBar:
    def test_empty(self):
        bar = _bar(0, 100, width=10)
        assert "░" * 10 in bar
        assert "█" not in bar

    def test_half(self):
        bar = _bar(50, 100, width=10)
        assert "█" * 5 in bar
        assert "░" * 5 in bar

    def test_full_is_red(self):
        bar = _bar(100, 100, width=10)
        assert "[red]" in bar
        assert "░" not in bar

    def test_zero_max_returns_empty_bar(self):
        bar = _bar(0, 0, width=10)
        assert "░" * 10 in bar

    def test_near_full_is_yellow(self):
        bar = _bar(85, 100, width=10)
        assert "[yellow]" in bar

    def test_below_threshold_is_cyan(self):
        bar = _bar(50, 100, width=10)
        assert "[cyan]" in bar


class TestFmtReset:
    def _future(self, **kwargs) -> datetime:
        return datetime.now(tz=timezone.utc) + timedelta(**kwargs)

    def _past(self, **kwargs) -> datetime:
        return datetime.now(tz=timezone.utc) - timedelta(**kwargs)

    def test_past_returns_window_available(self):
        assert _fmt_reset(self._past(hours=1)) == "window available"

    def test_past_many_hours_returns_window_available(self):
        assert _fmt_reset(self._past(hours=16)) == "window available"

    def test_under_one_hour_shows_minutes(self):
        result = _fmt_reset(self._future(minutes=45))
        # Allow ±1m for time elapsed between construction and assertion
        assert result in ("resets in 44m", "resets in 45m")

    def test_over_one_hour_shows_hours_and_minutes(self):
        result = _fmt_reset(self._future(hours=2, minutes=30))
        assert result in ("resets in 2h 29m", "resets in 2h 30m")

    def test_exactly_one_hour(self):
        # Just over 1h lands in the hours branch; just under falls into minutes
        result = _fmt_reset(self._future(hours=1, seconds=2))
        assert result == "resets in 1h 0m"

    def test_over_24_hours_shows_date(self):
        dt = self._future(hours=25)
        result = _fmt_reset(dt)
        assert result.startswith("resets ")
        assert ":" in result

    def test_zero_minutes_remaining(self):
        result = _fmt_reset(self._future(seconds=30))
        assert result == "resets in 0m"


class TestBarPct:
    def test_zero_is_empty(self):
        bar = _bar_pct(0, width=10)
        assert "░" * 10 in bar
        assert "█" not in bar

    def test_half_is_cyan(self):
        bar = _bar_pct(50, width=10)
        assert "[green]" in bar or "[cyan]" in bar

    def test_high_is_yellow(self):
        bar = _bar_pct(80, width=10)
        assert "[yellow]" in bar

    def test_critical_is_red(self):
        bar = _bar_pct(95, width=10)
        assert "[red]" in bar

    def test_full_clamps_to_width(self):
        bar = _bar_pct(100, width=10)
        assert "░" not in bar
