# LaunchAgent Configuration

macOS LaunchAgent plist files for pipeline automation.

## Install

```bash
# Copy plists to LaunchAgents directory
cp launchd/com.4jp.pipeline.*.plist ~/Library/LaunchAgents/

# Ensure log directory exists
mkdir -p ~/System/Logs

# Load agents
launchctl load ~/Library/LaunchAgents/com.4jp.pipeline.daily-deferred.plist
launchctl load ~/Library/LaunchAgents/com.4jp.pipeline.weekly-backup.plist
launchctl load ~/Library/LaunchAgents/com.4jp.pipeline.agent-biweekly.plist
```

## Schedule

| Agent | Schedule | What It Does |
|-------|----------|-------------|
| `daily-deferred` | Daily 6:00 AM | Check deferred entries for re-activation |
| `weekly-backup` | Sunday 2:00 AM | Create pipeline backup tar.gz |
| `agent-biweekly` | Mon/Thu 7:00 AM | Autonomous agent: score, advance, flag |

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.4jp.pipeline.daily-deferred.plist
launchctl unload ~/Library/LaunchAgents/com.4jp.pipeline.weekly-backup.plist
launchctl unload ~/Library/LaunchAgents/com.4jp.pipeline.agent-biweekly.plist
rm ~/Library/LaunchAgents/com.4jp.pipeline.*.plist
```

## Logs

All logs write to `~/System/Logs/pipeline-*.log`.

## Customization

Edit the plist files to change schedules. Key fields:
- `StartCalendarInterval`: When to run (Hour, Minute, Weekday)
- `ProgramArguments`: Python path and script arguments
- `RunAtLoad`: Set to `<true/>` to run immediately on load
