# LaunchAgent Configuration

macOS LaunchAgent plist files for pipeline automation.

## Install

```bash
# Install, load, and run immediately once
python scripts/launchd_manager.py --install --kickstart

# Verify status
python scripts/launchd_manager.py --status
```

## Schedule

| Agent | Schedule | What It Does |
|-------|----------|-------------|
| `daily-deferred` | Daily 6:00 AM | Check deferred entries for re-activation |
| `daily-monitor` | Daily 6:30 AM | Alert on stale backups and stale signal logs |
| `weekly-backup` | Sunday 2:00 AM | Create pipeline backup tar.gz |
| `agent-biweekly` | Mon/Thu 7:00 AM | Autonomous agent: score, advance, flag |

## Uninstall

```bash
python scripts/launchd_manager.py --uninstall
```

## Logs

All logs write to `~/System/Logs/pipeline-*.log`.

## Customization

Edit the plist files to change schedules. Key fields:
- `StartCalendarInterval`: When to run (Hour, Minute, Weekday)
- `ProgramArguments`: Python path and script arguments
- `RunAtLoad`: Set to `<true/>` to run immediately on load
