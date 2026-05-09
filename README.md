# claude-usage

A terminal dashboard for visualizing your [Claude Code](https://claude.ai/code) CLI token usage.

Reads directly from `~/.claude/projects/` — no API key or configuration needed.

![dashboard layout: summary panel on the left, daily bar chart and sessions table on the right]

## Features

- Lifetime token totals (input, output, cache write, cache read)
- Estimated cost based on Sonnet 4.x pricing
- Daily usage bar chart (last 14 days)
- Recent sessions table sorted by last activity
- Auto-refreshes every 30 seconds; press `R` to refresh manually

---

## Requirements

- Python 3.10+
- Claude Code CLI installed and used at least once (data lives in `~/.claude/`)

---

## Installation

### macOS

1. **Check your Python version** (macOS ships Python 3.x; Homebrew is recommended for a clean install):
   ```bash
   python3 --version
   ```
   If you need Python: `brew install python`

2. **Clone the repo:**
   ```bash
   git clone https://github.com/samsonites89/claude-usage.git ~/claude-usage
   cd ~/claude-usage
   ```

3. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run:**
   ```bash
   python3 run.py
   ```

   To launch it from anywhere without activating the venv each time, add a shell alias:
   ```bash
   # Add to ~/.zshrc or ~/.bashrc
   alias claude-usage="source ~/claude-usage/.venv/bin/activate && python3 ~/claude-usage/run.py"
   ```

---

### Ubuntu / Debian

1. **Install Python and venv** (if not already present):
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-venv
   ```

2. **Clone the repo:**
   ```bash
   git clone https://github.com/samsonites89/claude-usage.git ~/claude-usage
   cd ~/claude-usage
   ```

3. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run:**
   ```bash
   python3 run.py
   ```

   Optional alias in `~/.bashrc`:
   ```bash
   alias claude-usage="source ~/claude-usage/.venv/bin/activate && python3 ~/claude-usage/run.py"
   ```

---

## Usage

| Key | Action |
|-----|--------|
| `R` | Refresh data immediately |
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
│   ├── parser.py   # reads and aggregates ~/.claude JSONL logs
│   └── app.py      # Textual TUI layout
├── run.py
├── requirements.txt
└── README.md
```
