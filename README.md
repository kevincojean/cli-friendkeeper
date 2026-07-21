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
friend list
friend due
friend touch alice
friend remove alice --force
```

## Subcommands

| Command | Description |
|---------|-------------|
| `add` | Add a new contact |
| `list` | List all contacts |
| `due` | Show contacts that are due for a message |
| `touch` | Mark a contact as recently contacted |
| `remove` | Remove a contact |
| `rebuild-state` | Rebuild state.jsonl from the audit log |
| `config-show` | Show current configuration |
| `config-set` | Set a configuration key |

## Data & Config

## Priorities

| Priority | Default Cadence | Description |
|----------|----------------|-------------|
| `deep` | 15 days | Close relationships — stay in regular contact |
| `casual` | 45 days | Friends you want to check in on periodically |
| `network` | 180 days | Professional network, infrequent check-ins |
| `acquaintance` | Never due | People you want to track but never get prompted about |

The default priority for new contacts is `casual`. Override it in config:
```
friend config-set default_priority acquaintance
```

## Data & Config

- **Data**: `~/.cache/com.kevincojean.cli-friendkeeper/` (or `$XDG_CACHE_HOME`)
- **Config**: `~/.config/com.kevincojean.cli-friendkeeper/config.json` (or `$XDG_CONFIG_HOME`)
- Config overrides default cadences: `friend config-set cadence.deep 7`

## Concurrency

All state mutations are serialized via POSIX file locks (`flock`). This prevents data corruption when running multiple `friend` instances concurrently.

## Credit
API inspired by https://github.com/justinabrahms/frm
