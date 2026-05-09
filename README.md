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
- Claude Code CLI installed and used at least once (data lives in `~/.claude/`)

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
| `ANTHROPIC_API_KEY` | — | Anthropic API key for the live rate-limit fetch (press `L`). Not needed if you use Claude Code. |
| `CLAUDE_USAGE_REFRESH_INTERVAL` | `30` | Dashboard auto-refresh interval in seconds. |
| `CLAUDE_USAGE_LIMITS_REFRESH_INTERVAL` | `300` | How often (seconds) to silently re-fetch live SESSION/WEEK rate limits in the background. |

**Example `~/.claude_usage.env`:**
```env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_USAGE_REFRESH_INTERVAL=20
CLAUDE_USAGE_LIMITS_REFRESH_INTERVAL=120
```

---

## Usage

| Key | Action |
|-----|--------|
| `R` | Refresh data immediately |
| `L` | Fetch live rate limits from Anthropic API |
| `Q` | Quit |

The dashboard auto-refreshes every 30 seconds while open.

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
