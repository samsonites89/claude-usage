# claude-usage — Codebase Guide

## What this is

`claude-usage` (TUI alias: `clawd`) is a terminal dashboard for visualizing Claude Code token usage and estimated costs. It reads Claude Code's local conversation logs, aggregates token data, and displays it in a rich TUI. It also fetches live API rate-limit utilization from Anthropic's API.

**Entry point**: `claude_usage/app.py:main`  
**CLI command**: `claude-usage`  
**Version**: 1.2.0 (in `pyproject.toml` and `claude_usage/__init__.py`)

---

## Project layout

```
claude_usage/
├── app.py               # Textual app, CLI arg parsing, layout composition
├── parser.py            # Data layer: JSONL parsing, rate-limit fetching, aggregation
├── utils.py             # Pure formatting helpers (_fmt, _fmt_cost, _bar, _bar_pct, _pct, _fmt_reset)
├── styles/app.tcss      # Textual CSS (layout, sizing, colours)
└── components/
    ├── summary_panel.py # Left column: session/week rate-limit bars + daily/weekly cost breakdown
    ├── daily_chart.py   # Bar chart — last 14 days of token usage
    ├── weekly_chart.py  # Bar chart — last 8 weeks of token usage
    ├── workspace_table.py # Table — per-workspace cost/token share
    ├── sessions_table.py  # Table — last 20 sessions sorted by recency
    └── refresh_popup.py   # Modal overlay shown after manual refresh (r key)
tests/
├── test_parser.py       # Unit tests for parser.py (data layer)
├── test_utils.py        # Unit tests for utils.py (formatting)
└── test_cli.py          # CLI arg parsing / integration tests
```

---

## TUI layout (TCSS-defined)

```
Screen (vertical)
├── Header                          (Textual built-in)
├── ClawdBanner                     (ASCII art, height=9)
├── #main  (horizontal, height=1fr)
│   ├── SummaryPanel                (width=38, fixed left column)
│   └── #right  (vertical, width=1fr)
│       ├── #charts  (horizontal, height=1fr)
│       │   ├── DailyChart
│       │   └── WeeklyChart
│       └── #bottom  (horizontal, height=1fr)
│           ├── WorkspaceTable
│           └── SessionsTable
├── FooterBar                       (github attribution, height=1)
└── Footer                          (Textual built-in — shows keybindings)
```

Keybindings: `r` → manual refresh (shows `RefreshPopup`), `q` → quit.

---

## Data flow

### 1. Reading usage records

`parser.load_records()` scans `~/.claude/projects/**/*.jsonl`. Claude Code writes one JSONL file per conversation session. Each line is a JSON event; only lines where `type == "assistant"` **and** the `message.usage` field is present are parsed into `UsageRecord` objects.

```
~/.claude/projects/<encoded-path>/<session-uuid>.jsonl
                   └─ folder name is the workspace path with every non-alnum char replaced by '-'
```

**Path decoding**: `_decode_workspace()` in `parser.py` reconstructs the original filesystem path from the encoded directory name by walking the real filesystem. Naive string replacement is used as a fallback.

### 2. Aggregation

All aggregation lives in `parser.py`. Functions return `Totals` dataclass instances (or dicts keyed by date/session):

| Function | Returns |
|---|---|
| `totals(records)` | All-time aggregate |
| `today_totals(records)` | Today (local date) |
| `week_totals(records)` | Current calendar week (Mon–Sun) |
| `window_totals(records, start, end)` | Arbitrary time window |
| `by_day(records)` | `dict[date, Totals]` |
| `by_week(records)` | `dict[date, Totals]` keyed by week's Monday |
| `by_session(records)` | `dict[str, Totals]` keyed by session UUID |
| `by_workspace(records)` | `dict[str, Totals]` sorted by cost desc |
| `session_last_seen(records)` | `dict[str, datetime]` latest timestamp per session |

### 3. Rate limits (live)

`fetch_rate_limits()` makes a minimal Haiku API call (1 output token) to extract rate-limit headers from the Anthropic API response:

- `anthropic-ratelimit-unified-5h-utilization` / `anthropic-ratelimit-unified-5h-reset`  
- `anthropic-ratelimit-unified-7d-utilization` / `anthropic-ratelimit-unified-7d-reset`

If the returned reset timestamp is already in the past, the code advances it by the window period (5 h or 7 d) and zeroes the utilization — this avoids showing stale "reset in the past" state.

Results are cached to `~/.claude_usage_limits_cache.json`. Stale cache (session_reset_at ≤ now) is discarded on load.

### 4. Authentication chain

`_get_auth_headers()` tries three sources in order:
1. `~/.claude/.credentials.json` — file-based OAuth token (Linux / older Claude Code)
2. macOS Keychain — `security find-generic-password -s "Claude Code-credentials"` (macOS desktop/CLI)
3. `ANTHROPIC_API_KEY` environment variable (loaded from `~/.claude_usage.env` via python-dotenv)

### 5. Refresh cycle

`ClaudeUsageApp.on_mount` sets a timer that calls `_refresh_all` every `CLAUDE_USAGE_REFRESH_INTERVAL` seconds (default: 60, overridable via env var). Rate-limit fetching runs in a Textual worker (`run_worker`) to avoid blocking the UI.

---

## Key data structures

```python
@dataclass
class UsageRecord:
    timestamp: datetime
    session_id: str
    workspace: str        # decoded human-readable path
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    # computed: total_tokens, estimated_cost

@dataclass
class Totals:
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    record_count: int
    # computed: total_tokens, estimated_cost
    def add(self, rec: UsageRecord) -> None: ...

@dataclass
class RateLimits:
    session_utilization: float   # 0.0–1.0
    session_reset_at: datetime
    weekly_utilization: float    # 0.0–1.0
    weekly_reset_at: datetime
    fetched_at: datetime
    # computed: session_pct, weekly_pct

@dataclass
class PlanConfig:
    plan_key: str            # "pro" | "max_5x" | "max_20x"
    label: str
    monthly_budget: float
    # computed: daily_budget, weekly_budget
```

---

## Pricing constants (parser.py)

Hardcoded as Sonnet 4.x rates (per million tokens):

| Token type | Price |
|---|---|
| Input | $3.00 |
| Output | $15.00 |
| Cache write | $3.75 |
| Cache read | $0.30 |

---

## Plan budgets (parser.py `PLANS` dict)

| Key | Label | Monthly budget |
|---|---|---|
| `pro` | Pro | $20 |
| `max_5x` | Max 5× | $100 |
| `max_20x` | Max 20× | $200 |

Plan can be overridden at startup via `--plan pro|max_5x|max_20x`. Config persisted to `~/.claude_usage_config.json`.

---

## CLI modes

| Flag | Behaviour |
|---|---|
| _(none)_ | Launch full TUI |
| `--summary` | Print plain-text summary and exit |
| `--json` | Print JSON and exit |
| `--plan <key>` | Override plan for budget bars |
| `-V` / `--version` | Print version and exit |

The `claude` binary must be in PATH; the app exits with a helpful message if not found.

---

## Component pattern

All components extend `textual.widgets.Static` and use Textual's `reactive` descriptors with `recompose=True` so the widget re-renders automatically when data changes. Data is pushed into components by `ClaudeUsageApp._load_data()` by directly setting the reactive attributes.

---

## Testing

```bash
python -m pytest          # run all tests
python -m pytest tests/test_parser.py  # parser unit tests only
```

Tests use `unittest.mock.patch` to mock `urllib.request.urlopen` and `_get_auth_headers`. No real API calls are made in the test suite.

---

## External files written by the app

| Path | Purpose |
|---|---|
| `~/.claude_usage_limits_cache.json` | Cached rate-limit response |
| `~/.claude_usage_config.json` | Saved plan selection |
| `~/.claude_usage.env` | User-level env vars (e.g. `ANTHROPIC_API_KEY`) |
