# claude-usage

A terminal dashboard for visualizing your [Claude Code](https://claude.ai/code) CLI token usage.

Reads directly from `~/.claude/projects/`. Live rate-limit data is fetched automatically using your Claude Code session — no extra configuration needed on macOS.

![dashboard layout: summary panel on the left, daily bar chart and sessions table on the right]

## Features

- Lifetime token totals (input, output, cache write, cache read)
- Estimated cost based on Sonnet 4.x pricing
- Daily usage bar chart (last 14 days)
- Weekly usage bar chart (last 8 weeks)
- Per-workspace cost breakdown with proportional bars
- Recent sessions table sorted by last activity
- Live rate-limit utilisation (5-hour session window + 7-day weekly window)
- Auto-refreshes every 60 seconds; press `R` to refresh manually

---

## Requirements

- Python 3.10+
- [Claude Code](https://claude.ai/code) CLI installed and available in `PATH` (`claude` command must be found) — `claude-usage` will exit with an error if it is not present
- Claude Code used at least once so that usage data exists in `~/.claude/`

### Live rate-limit data (SESSION / WEEK bars)

The USAGE panel shows live 5-hour and 7-day rate-limit utilisation. This requires credentials to make an Anthropic API call. The app resolves credentials automatically in this order:

| Source | Platform | Notes |
|--------|----------|-------|
| `~/.claude/.credentials.json` | Linux / older Claude Code | Written by Claude Code at sign-in |
| macOS Keychain (`Claude Code-credentials`) | macOS | Used by Claude Code desktop/CLI on Mac |
| `ANTHROPIC_API_KEY` env var | All | Set in `~/.claude_usage.env` as fallback |

If no credentials are found, the USAGE panel shows a prompt to run `claude` (which signs in and stores credentials) or set `ANTHROPIC_API_KEY`.

---

## Installation

The recommended way is **pipx**, which installs the tool into its own isolated environment and adds a `claude-usage` command to your PATH.

### macOS

```bash
# 1. Install pipx (if not already installed)
brew install pipx
pipx ensurepath

# 2. Clone and install
git clone https://github.com/samsonites89/claude-usage.git
cd claude-usage
pipx install .

# 3. Run from anywhere
claude-usage

# To upgrade an existing installation after pulling updates:
# git pull && pipx install --force .
```

### Ubuntu / Debian

```bash
# 1. Install pipx
sudo apt-get update && sudo apt-get install -y pipx

# 2. Add pipx's bin directory to your PATH
pipx ensurepath

# 3. Reload your shell so the PATH change takes effect
source ~/.bashrc
```

> **Important:** steps 2 and 3 are required. If you skip `source ~/.bashrc` (or opening a new terminal), the `claude-usage` command will not be found even after a successful install.

```bash
# 4. Clone and install
git clone https://github.com/samsonites89/claude-usage.git
cd claude-usage
pipx install .

# 5. Run from anywhere
claude-usage

# To upgrade an existing installation after pulling updates:
# git pull && pipx install --force .
```

---

### Alternative: virtual environment (no pipx)

```bash
git clone https://github.com/samsonites89/claude-usage.git
cd claude-usage
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

---

## Configuration (optional)

Settings are read from `~/.claude_usage.env`. Copy the example file to get started:

```bash
cp .env.example ~/.claude_usage.env
```

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Fallback API key for live rate-limit fetches. Not needed on macOS (Keychain is used automatically). |
| `CLAUDE_USAGE_REFRESH_INTERVAL` | `60` | Dashboard auto-refresh interval in seconds. Live rate limits are fetched on every refresh. |

**Example `~/.claude_usage.env`:**
```env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_USAGE_REFRESH_INTERVAL=60
```

---

## Usage

```bash
claude-usage            # launch the interactive dashboard
claude-usage --summary  # print a plain-text summary and exit
claude-usage --json     # output usage data as JSON and exit
```

### Interactive dashboard keys

| Key | Action |
|-----|--------|
| `R` | Refresh data and fetch live rate limits immediately |
| `Q` | Quit |

The dashboard auto-refreshes every 60 seconds while open. Live rate limits (SESSION / WEEK) are fetched automatically on every refresh cycle.

### Non-interactive modes

`--summary` and `--json` print to stdout and exit immediately — no TUI is launched. Both include all-time totals, today, this week, cache token counts, and live rate-limit data (SESSION / WEEK) if a cached fetch is available.

```bash
# pipe JSON into jq
claude-usage --json | jq '.all_time.estimated_cost'
```

### CLI flags

| Flag | Description |
|------|-------------|
| `--summary` | Print plain-text usage summary and exit |
| `--json` | Output usage data as JSON and exit |
| `--plan PLAN` | Override plan for budget calculations (`pro`, `max_5x`, `max_20x`) |

The `--plan` flag overrides the plan set in `~/.claude_usage_config.json` for a single run.


---

## Cost estimates

Pricing is approximate and based on Sonnet 4.x rates:

| Token type | Price per 1M tokens |
|------------|-------------------|
| Input | $3.00 |
| Output | $15.00 |
| Cache write | $3.75 |
| Cache read | $0.30 |

Costs are displayed as `~$X.XXXX (est.)` since different Claude models have different rates.

---

## Dashboard components

The interactive TUI is composed of the following panels:

### USAGE — `summary_panel.py`
The left sidebar. Shows:
- **SESSION** — live 5-hour rate-limit utilisation bar + time until window reset
- **WEEK** — live 7-day rate-limit utilisation bar + time until weekly reset
- **Today** — cost and token count for the current day, with an optional progress bar against the plan daily budget
- **This week** — cost and token count for the current calendar week
- **All time** — lifetime totals (input / output / cache write / cache read tokens and request count)

When no credentials are available the panel shows an inline prompt to sign in or set `ANTHROPIC_API_KEY`.

### DAILY USAGE — `daily_chart.py`
Horizontal bar chart for the last 14 days. Each bar is scaled relative to the highest-token day in the visible window.

### WEEKLY USAGE — `weekly_chart.py`
Horizontal bar chart for the last 8 calendar weeks (Monday-anchored). Bars are scaled relative to the busiest week in the window.

### WORKSPACES — `workspace_table.py`
Table of every project directory found in `~/.claude/projects/`, sorted by estimated cost (highest first). Columns: workspace path, estimated cost, total tokens, proportional cost bar.

Directory names are decoded from Claude's encoding scheme (which replaces `/`, `-`, and `_` with `-`) by walking the real filesystem — so `my-project` and `my/project` are correctly distinguished.

### RECENT SESSIONS — `sessions_table.py`
The 20 most-recently-active sessions sorted by last activity. Columns: session ID (truncated), total tokens, estimated cost, last-active timestamp.

### Refresh popup — `refresh_popup.py`
A transient overlay shown when you press `R`. Displays the current timestamp, today's token count, and all-time request count.

---

## Raw data sources

### JSONL usage logs — `~/.claude/projects/<workspace>/<session>.jsonl`

Claude Code appends one JSON object per line for every message exchange. `claude-usage` reads only `"type": "assistant"` entries that contain a `usage` block.

**Example record (fields irrelevant to `claude-usage` omitted):**

```json
{
  "type": "assistant",
  "timestamp": "2026-05-09T10:19:42.488Z",
  "sessionId": "9460d6e1-5566-49eb-a54c-5d80a5a9eded",
  "message": {
    "model": "claude-sonnet-4-6",
    "usage": {
      "input_tokens": 3,
      "cache_creation_input_tokens": 5258,
      "cache_read_input_tokens": 12800,
      "output_tokens": 145
    }
  },
  "cwd": "/home/user/workspace/my-project"
}
```

Fields consumed:

| Field | Used for |
|-------|----------|
| `timestamp` | All time-window aggregations (today, weekly, session window) |
| `sessionId` | Grouping records into sessions |
| `message.model` | Stored on each record (future per-model breakdown) |
| `message.usage.input_tokens` | Cost and token totals |
| `message.usage.output_tokens` | Cost and token totals |
| `message.usage.cache_creation_input_tokens` | Cache write cost |
| `message.usage.cache_read_input_tokens` | Cache read cost |

The workspace name is derived from the encoded directory name (e.g. `-home-user-workspace-my-project`) via filesystem-walk decoding.

---

### Live rate-limit API — `POST https://api.anthropic.com/v1/messages`

To get real-time rate-limit utilisation, `claude-usage` makes a minimal API call (Haiku, 1 token) and reads the response **headers**. The body is discarded.

**Relevant response headers:**

| Header | Example value | Meaning |
|--------|---------------|---------|
| `anthropic-ratelimit-unified-5h-utilization` | `0.12` | Fraction of the 5-hour session window used (0.0 – 1.0) |
| `anthropic-ratelimit-unified-5h-reset` | `1749487800` | Unix timestamp when the 5-hour window resets |
| `anthropic-ratelimit-unified-7d-utilization` | `0.02` | Fraction of the 7-day weekly window used (0.0 – 1.0) |
| `anthropic-ratelimit-unified-7d-reset` | `1750042800` | Unix timestamp when the 7-day window resets |

The parsed values are cached at `~/.claude_usage_limits_cache.json` and reused until the session window expires:

```json
{
  "session_utilization": 0.12,
  "session_reset_at": "2026-06-09T16:50:00+00:00",
  "weekly_utilization": 0.02,
  "weekly_reset_at": "2026-06-16T03:00:00+00:00",
  "fetched_at": "2026-06-09T16:08:23.196527+00:00"
}
```

Credentials are resolved in priority order: `~/.claude/.credentials.json` → macOS Keychain (`Claude Code-credentials`) → `ANTHROPIC_API_KEY` env var.

---

## Project structure

```
claude-usage/
├── claude_usage/
│   ├── __init__.py
│   ├── parser.py          # reads and aggregates ~/.claude JSONL logs
│   ├── utils.py           # shared formatting helpers (_fmt, _bar, etc.)
│   ├── app.py             # ClaudeUsageApp entry point and data loading
│   ├── components/        # Textual widgets, one file each
│   │   ├── __init__.py
│   │   ├── summary_panel.py
│   │   ├── daily_chart.py
│   │   ├── weekly_chart.py
│   │   ├── sessions_table.py
│   │   ├── workspace_table.py
│   │   └── refresh_popup.py
│   └── styles/
│       └── app.tcss       # all Textual CSS
├── run.py                 # legacy entry point (still works)
├── pyproject.toml         # package definition and claude-usage CLI entry point
├── requirements.txt
└── README.md
```
