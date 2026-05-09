# claude-usage

A terminal dashboard for visualizing your [Claude Code](https://claude.ai/code) CLI token usage.

Reads directly from `~/.claude/projects/` — no extra configuration needed.

![dashboard layout: summary panel on the left, daily bar chart and sessions table on the right]

## Features

- Lifetime token totals (input, output, cache write, cache read)
- Estimated cost based on Sonnet 4.x pricing
- Daily usage bar chart (last 14 days)
- Weekly usage bar chart (last 8 weeks)
- Recent sessions table sorted by last activity
- Live rate limit fetch via Anthropic API (press `L`)
- Auto-refreshes every 30 seconds; press `R` to refresh manually

---

## Requirements

- Python 3.10+
- [Claude Code](https://claude.ai/code) CLI installed and available in `PATH` (`claude` command must be found) — `claude-usage` will exit with an error if it is not present
- Claude Code used at least once so that usage data exists in `~/.claude/`

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
| `ANTHROPIC_API_KEY` | — | Anthropic API key for live rate-limit fetches. Not needed if you use Claude Code. |
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
│   │   └── refresh_popup.py
│   └── styles/
│       └── app.tcss       # all Textual CSS
├── run.py                 # legacy entry point (still works)
├── pyproject.toml         # package definition and claude-usage CLI entry point
├── requirements.txt
└── README.md
```
