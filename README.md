# uptime-kuma-cli

A command-line tool for managing [Uptime Kuma](https://github.com/louislam/uptime-kuma) monitors.

## Installation

Requires Python >= 3.13.

```bash
# Using uv
uv tool install .

# Or using pip
pip install .
```

## Configuration

Provide connection info via environment variables or CLI options:

```bash
# Environment variables (recommended)
export KUMA_URL=http://localhost:3001
export KUMA_USERNAME=admin
export KUMA_PASSWORD=yourpassword

# Or CLI options
kuma --url http://localhost:3001 -u admin -p yourpassword <command>
```

## Commands

### Server info

```bash
kuma info
```

### List monitors

```bash
kuma list
```

Output example:

```
 ID  Name           Type  Target                 Status  Interval
  1  Google         http  https://google.com     UP           60s
  2  Database       port  db.example.com:5432    DOWN         30s
  3  DNS Check      dns   example.com:53         PAUSED       60s
```

### Get monitor details

```bash
kuma get 1
```

### Add a monitor

```bash
# HTTP monitor
kuma add http "Google" "https://google.com"

# HTTP with custom interval (30s)
kuma add http "GitHub" "https://github.com" -i 30

# Ping monitor
kuma add ping "Server" "8.8.8.8"

# TCP port monitor
kuma add port "Database" "db.example.com" --port 5432

# DNS monitor
kuma add dns "DNS Check" "example.com" --dns-type A

# Keyword monitor (check if response contains a keyword)
kuma add keyword "Status Page" "https://example.com/health" -k "ok"
```

Supported monitor types: `http`, `ping`, `port`, `dns`, `keyword`, `push`, `docker`, `mqtt`, `postgres`, `mysql`, `mongodb`, `redis`.

### Edit a monitor

```bash
kuma edit 1 --name "New Name"
kuma edit 1 --interval 30
kuma edit 1 --target "https://new-url.com"
```

### Pause / Resume

```bash
kuma pause 1
kuma resume 1
```

### Delete a monitor

```bash
kuma delete 1        # with confirmation prompt
kuma delete 1 -y     # skip confirmation
```

## License

MIT
