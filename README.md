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
friend add "Alice Smith" --email alice@example.com --priority deep
friend add "Bob Jones" --email bob@example.com --priority casual
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

### Full default config

Dot separates the domain from the sub-key (e.g. `cadence.deep`). Keys without a dot are global settings. Old-style nested `{"cadence": {"deep": 15}}` is also accepted for backward compatibility, but saving always writes the flat format.

```json
{
  "cadence.deep": 15,
  "cadence.casual": 45,
  "cadence.network": 180,
  "cadence.acquaintance": 0,
  "snooze.deep": 7,
  "snooze.casual": 15,
  "snooze.network": 30,
  "snooze.acquaintance": 90,
  "default_priority": "casual",
  "default_subcommand": "due",
  "list.priority_order": ["acquaintance", "network", "casual", "deep"],
  "list.hide_acquaintances": true,
  "list.sort_priority": "asc",
  "list.sort_due_date": "desc",
  "list.columns": ["id", "name", "priority", "last_touched", "due_date"]
}
```

| Key | Domain | Default | Description |
|-----|--------|---------|-------------|
| `cadence.{priority}` | `cadence` | 15/45/180/0 | Per-priority cadence in days |
| `snooze.{priority}` | `snooze` | 7/15/30/90 | Per-priority snooze defaults (days) |
| `default_priority` | _(global)_ | `"casual"` | Priority used when `--priority` is omitted on `add` |
| `default_subcommand` | _(global)_ | `"due"` | Subcommand dispatched when no subcommand is given |
| `list.priority_order` | `list` | list above | Display order for priority groups in `list` |
| `list.hide_acquaintances` | `list` | `true` | Hide acquaintance-priority contacts from `list` by default |
| `list.sort_priority` | `list` | `"asc"` | Sort direction for priority groups (`"asc"` or `"desc"`) |
| `list.sort_due_date` | `list` | `"desc"` | Sort direction for due date within each group (`"asc"` or `"desc"`) |
| `list.columns` | `list` | list above | Columns shown in the `list` table (see below) |

Available columns for `list.columns`: `id`, `name`, `priority`, `last_touched`, `due_date`, `days_since`, `cadence`, `removed`, `notes`, `email`, `phone`.

At least one `cadence.*` key (or the old nested `cadence` object) is required. All other keys can be omitted — missing keys fall back to defaults.

Set values with `friend config-set`:

```
friend config-set cadence.deep 7
friend config-set list.columns id,name,due_date
friend config-set list.hide_acquaintances true
friend config-set list.priority_order deep,casual,network,acquaintance
```

## Concurrency

All state mutations are serialized via POSIX file locks (`flock`). This prevents data corruption when running multiple `friend` instances concurrently.

## Credit
API inspired by https://github.com/justinabrahms/frm
