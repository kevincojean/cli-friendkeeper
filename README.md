# friend — stay in touch with the people who matter

friend is a personal CLI tool that helps you maintain relationships by tracking who you want to stay in touch with, how often, and when you last reached out.

## Rationale
I want a simple CLI tool which tracks when I last talked to my friends which doesn't rely on hosting anything, or on an external protocol.

## Install

> This tool supports Linux only. macOS/BSD/Windows are unsupported.

```bash
git clone git@github.com:kevincojean/cli-friendkeeper.git
cd cli-friendkeeper
./install.sh
```

Optional: `BIN_NAME=my-friend ./install.sh` or `PREFIX=/usr/local ./install.sh`

## Quick Start

```bash
friend add --name "Alice Smith" --email alice@example.com --priority deep
friend add --name "Bob Jones" --email bob@example.com --priority casual
friend catch-up
```

## Subcommands

| Command | Description |
|---------|-------------|
| `add` | Add a new contact |
| `list` | List all contacts |
| `due` | Show contacts that are due for a message |
| `catch-up` | **Interactive session** — walk through due contacts one at a time |
| `touch` | Mark a contact as recently contacted |
| `remove` | Remove a contact |
| `rebuild-state` | Rebuild state.jsonl from the audit log |
| `config-show` | Show current configuration |
| `config-set` | Set a configuration key |

## `friend catch-up`

The killer feature. An interactive session that walks you through your due contacts one at a time.

```
$ friend catch-up

[1/3] Alice Smith          deep      18d
       Notes: working on new startup

  Have you caught up yet ?
  (y) Yes  (n) Nope  (s) Snooze  (q) Quit
> y
Note: Called to catch up, she's hiring
✓ Alice — touched

[2/3] Bob Jones            casual    50d
       Notes: —

  Have you caught up yet ?
  (y) Yes  (n) Nope  (s) Snooze  (q) Quit
> n
✓ Bob — noped

[3/3] Carol Lee            network   never

  Have you caught up yet ?
  (y) Yes  (n) Nope  (s) Snooze  (q) Quit
> s
Days [30]: 60
✓ Carol — snoozed 60d

─── Summary ───
Touched: 1  Snoozed: 2
```

| Key | Action | What happens |
|-----|--------|-------------|
| `y` | Yes | Logs a touch with optional note. Resets due timer. |
| `n` | Nope | Snoozes until tomorrow. Contact reappears based on normal cadence. |
| `s` | Snooze | Prompts for days (default per priority). Sets `last_touched` forward. |
| `q` | Quit | Stops the session. Unprocessed contacts remain due. |

Pass a number to limit the session: `friend catch-up 5` processes at most 5 contacts.

### Snooze Defaults (configurable)

| Priority | Default Snooze | Default Cadence |
|----------|---------------|-----------------|
| `deep` | 7 days | 15 days |
| `casual` | 15 days | 45 days |
| `network` | 30 days | 180 days |
| `acquaintance` | 90 days | Never due |

> Acquaintance priority has a cadence of 0 by default, so they never appear in `due` or `catch-up`. The 90-day snooze default only applies if you override cadence per-contact with `--cadence-days`.

Override snooze defaults via config:
```
friend config-set snooze.deep 14
friend config-set snooze.casual 30
```

### Interactive Selection (fzf)

If you prefer fuzzy-finding contacts over the interactive session, add this alias to your `~/.zshrc` / `~/.bashrc`:

```bash
friend-touch-fzf() {
  local selection
  selection=$(
    friend list --json \
      | jq -r '.[] | "\(.id)\t\(.name)  (\(.priority))"' \
      | fzf --with-nth=2.. --delimiter=$'\t'
  )
  [[ -z "$selection" ]] && return 1
  friend touch "$(cut -f1 <<<"$selection")" --note "$*"
}
```

## Data & Config

- **Data**: `~/.cache/com.kevincojean.cli-friendkeeper/` (or `$XDG_CACHE_HOME`)
- **Config**: `~/.config/com.kevincojean.cli-friendkeeper/config.json` (or `$XDG_CONFIG_HOME`)
- Config overrides default cadences: `friend config-set cadence.deep 7`
- Config overrides default snooze: `friend config-set snooze.deep 14`

## Concurrency

All state mutations are serialized via POSIX file locks (`flock`). This prevents data corruption when running multiple `friend` instances concurrently.

## Credit
API inspired by https://github.com/justinabrahms/frm
