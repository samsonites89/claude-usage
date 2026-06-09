# Changelog

## [1.2.3] - 2026-06-10

### Chores
- Updated GitHub Actions to Node.js 24-compatible major versions: `actions/checkout` v4→v5, `actions/setup-python` v5→v6, `actions/upload-artifact` v4→v6, `actions/download-artifact` v4→v6

## [1.2.2] - 2026-06-10

### Fixes
- Merged tag creation and binary release into a single workflow to bypass `GITHUB_TOKEN` limitation (tags pushed by `GITHUB_TOKEN` cannot trigger other workflows)
- Fixed shell injection in annotated tag message by passing changelog content via env var and `git tag -F`
- Fixed missing git identity when creating annotated tags in CI

## [1.2.1] - 2026-06-10

### Chores
- Added `CLAUDE.md` codebase guide for onboarding Claude before implementation work
- Added GitHub Actions release workflow: builds standalone `clawd` binaries (linux-x86_64, macos-arm64, macos-x86_64) on `v*` tag push
- Added GitHub Actions tag workflow: auto-creates an annotated tag with the matching CHANGELOG entry on every push to `main`
- Added GitHub Actions changelog workflow: auto-prepends a CHANGELOG entry from `git log` when a version bump is pushed to `develop` without a matching entry

## [1.2.0] - 2026-06-10

### Features
- Per-workspace cost breakdown panel (WORKSPACES) showing estimated cost, total tokens, and a proportional cost bar for every project directory found in `~/.claude/projects/`, sorted by cost
- Workspace path decoding now walks the real filesystem to correctly distinguish hyphens from slashes and underscores (e.g. `claude-usage` is no longer misread as `claude/usage`)

### Docs
- README: added Dashboard components section describing each panel
- README: added Raw data sources section with a sample JSONL record, consumed fields table, and rate-limit response headers reference

## [1.1.0] - 2026-05-09

### Features
- Live rate limits (SESSION / WEEK) are now fetched automatically on every refresh cycle — no separate `L` key needed
- Default refresh interval changed from 30s to 60s

### Removed
- `L` keybinding for manual rate-limit fetch (now happens automatically with every refresh)
- `CLAUDE_USAGE_LIMITS_REFRESH_INTERVAL` env var (no longer needed)

## [1.0.5] - 2026-05-09

### Features
- `--plan {pro,max_5x,max_20x}`: override the plan for budget calculations without editing the config file; affects the dashboard bars, `--summary`, and `--json` output

## [1.0.4] - 2026-05-09

### Fixes
- Cost values now display with 2 decimal places instead of 4 (e.g. `~$1.23` not `~$1.2345`)

## [1.0.3] - 2026-05-09

### Features
- `--summary` flag: print a plain-text usage summary (all-time, today, this week, cache, rate limits) and exit — no TUI required
- `--json` flag: output the same data as machine-readable JSON and exit

## [1.0.2] - 2026-05-09

### Features
- Gate startup on `claude` CLI presence — exits with a clear error message if `claude` is not found in `PATH`

## [1.0.1] - 2026-05-09

### Chores
- `run.py` now routes through `main()` so `python3 run.py --version` / `-V` works correctly

## [1.0.0] - 2026-05-09

### Features
- `--version` / `-V` flag prints program name and exit — no TUI required
- Centered modal popup on `r` and `l` with auto-dismiss; shows timestamp, today's token count/cost, and all-time request count on refresh; shows success/error on rate-limit fetch
- Daily and weekly usage bar charts (last 14 days / last 8 weeks)
- Recent sessions table sorted by last activity (last 20)
- Lifetime token totals with estimated cost (input, output, cache write/read)
- Live rate-limit fetch via Anthropic API (`l`); session and weekly utilisation bars with reset countdown
- Auto-refresh every 30 s; manual refresh with `r`

### Chores
- Split `app.py` into `components/` (one file per widget), `utils.py`, and `styles/app.tcss`
- Added `.idea/` to `.gitignore`
- Packaged as installable CLI (`pipx install .` → `claude-usage`)
- `.env` / `~/.claude_usage.env` support for `ANTHROPIC_API_KEY` and `CLAUDE_USAGE_REFRESH_INTERVAL`
