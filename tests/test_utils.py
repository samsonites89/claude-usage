from __future__ import annotations

from claude_usage.utils import _bar, _bar_pct, _fmt, _fmt_cost, _pct


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
