# Deployment Scripts

This directory contains deployment and management scripts for MVG Departures. All scripts work from any directory.

## Available Scripts

### `start.sh`

Start the MVG Departures application.

**Usage:**

```bash
# Development mode (runs in foreground)
./scripts/start.sh

# Service mode (requires root)
sudo ./scripts/start.sh
```

**Features:**

- Automatically detects if running in development or service mode
- Development mode: runs in foreground, easy to stop with Ctrl+C
- Service mode: runs as background daemon with logging

### `stop.sh`

Stop the MVG Departures application.

**Usage:**

```bash
# Development mode
./scripts/stop.sh

# Service mode (requires root)
sudo ./scripts/stop.sh
```

**Features:**

- Graceful shutdown (SIGTERM)
- Force kill if needed (SIGKILL after 10 seconds)
- Cleans up PID files

### `restart.sh`

Restart the MVG Departures application.

**Usage:**

```bash
./scripts/restart.sh
# or
sudo ./scripts/restart.sh
```

### `status.sh`

Check the status of the MVG Departures application.

**Usage:**

```bash
./scripts/status.sh
```

**Output includes:**

- Running status (RUNNING/STOPPED)
- Process ID (PID)
- Process information (CPU, memory, uptime)
- Recent log entries

### `install.sh`

Install MVG Departures as a system service.

**Usage:**

```bash
sudo ./scripts/install.sh
```

**What it does:**

1. Creates application directory at `/opt/mvg-departures`
2. Copies application files
3. Sets up virtual environment
4. Installs dependencies
5. Creates system user `mvg-departures`
6. Registers as systemd or init.d service
7. Sets up configuration files

**After installation:**

1. Edit `/opt/mvg-departures/.env` or `/opt/mvg-departures/config.toml`
2. Start the service: `sudo ./scripts/start.sh` or `sudo systemctl start mvg-departures`

### `mvg-departures.initd`

Init.d service script (used by install.sh).

### `find_station.py`

Helper script to find station IDs (see main README).

### `list_routes.sh`

List available routes and destinations for a station. Useful for configuring direction mappings.

**Usage:**

```bash
# Search by station name
./scripts/list_routes.sh "Giesing"

# By station ID
./scripts/list_routes.sh de:09162:100

# By specific stop point ID
./scripts/list_routes.sh de:09162:1108:4:4
```

**Output includes:**

- Available routes and their destinations
- Config patterns ready to copy into `direction_mappings`
- Stop point differentiation hints for physical stops

### `list_departures.sh`

Show live departures for a station. Useful for debugging when departures don't appear.

**Usage:**

```bash
# Search by station name
./scripts/list_departures.sh "Chiemgaustr"

# By station ID (shows all stop points)
./scripts/list_departures.sh de:09162:100

# By specific stop point (filter to one physical stop)
./scripts/list_departures.sh de:09162:1108:4:4

# Limit number of results
./scripts/list_departures.sh de:09162:100 --limit 50

# Output as JSON
./scripts/list_departures.sh de:09162:100 --json
```

**Output includes:**

- Live departure times with delays
- Transport type, line number, and destination
- Stop point IDs for each departure
- Platform information (when available)
- Cancelled departures marked

**Use cases:**

- Debug why a stop shows no departures
- Verify stop point IDs are correct
- Check departure frequency for specific stop points
- Compare departures across different physical stops

## How Scripts Work

All scripts use `deploy-common.sh` which provides:

- **Auto-detection**: Finds project root automatically
- **Mode detection**: Distinguishes between development and service modes
- **Path resolution**: Works from any directory
- **Common functions**: Shared functionality for all scripts

### Development Mode

- Runs from project directory
- Uses project's virtual environment (if exists) or system Python
- Runs in foreground (for easy debugging)
- No root privileges required

### Service Mode

- Runs from `/opt/mvg-departures`
- Uses installed virtual environment
- Runs as background daemon
- Requires root privileges
- Logs to `/var/log/mvg-departures.log`

## Examples

### Development Workflow

```bash
# Start in development mode
./scripts/start.sh

# In another terminal, check status
./scripts/status.sh

# Stop when done
./scripts/stop.sh
```

### Production Deployment

```bash
# Install as service
sudo ./scripts/install.sh

# Configure stops
sudo nano /opt/mvg-departures/.env

# Start service
sudo ./scripts/start.sh

# Check status
sudo ./scripts/status.sh

# View logs
sudo tail -f /var/log/mvg-departures.log
```

### Using System Service Commands

After installation, you can also use standard service commands:

```bash
# Systemd
sudo systemctl start mvg-departures
sudo systemctl stop mvg-departures
sudo systemctl status mvg-departures
sudo systemctl restart mvg-departures

# Init.d (if systemd not available)
sudo service mvg-departures start
sudo service mvg-departures stop
sudo service mvg-departures status
sudo service mvg-departures restart
```

## Troubleshooting

### Scripts not executable

```bash
chmod +x scripts/*.sh
```

### Permission denied

- Development mode: scripts should work without sudo
- Service mode: use `sudo` for start/stop/install

### Can't find project root

- Make sure you're running scripts from within the project or have the project in your path
- Scripts automatically detect project root based on script location

### Service not starting

- Check logs: `tail -f /var/log/mvg-departures.log`
- Check configuration: `/opt/mvg-departures/.env`
- Verify virtual environment: `/opt/mvg-departures/.venv/bin/python --version`
