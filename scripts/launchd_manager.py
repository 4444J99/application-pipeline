#!/usr/bin/env python3
"""Manage launchd agents for pipeline automation on macOS.

Usage:
    python scripts/launchd_manager.py --status
    python scripts/launchd_manager.py --install --kickstart
    python scripts/launchd_manager.py --uninstall
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHD_DIR = REPO_ROOT / "launchd"
USER_LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LOG_DIR = Path.home() / "System" / "Logs"


def _ensure_macos() -> None:
    if platform.system() != "Darwin":
        print("launchd manager is macOS-only.", file=sys.stderr)
        sys.exit(1)


def _plist_paths() -> list[Path]:
    return sorted(LAUNCHD_DIR.glob("com.4jp.pipeline.*.plist"))


def _launchctl_target(label: str) -> str:
    return f"gui/{os.getuid()}/{label}"


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        details = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"{' '.join(cmd)} failed: {details}")
    return proc


def install_agents(kickstart: bool, dry_run: bool) -> None:
    """Copy, load, and optionally kickstart pipeline launch agents."""
    _ensure_macos()
    plists = _plist_paths()
    if not plists:
        print(f"No plist files found in {LAUNCHD_DIR}", file=sys.stderr)
        sys.exit(1)

    USER_LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    for source in plists:
        label = source.stem
        target = _launchctl_target(label)
        destination = USER_LAUNCH_AGENTS / source.name

        print(f"Installing {source.name}")
        if dry_run:
            print(f"  cp {source} {destination}")
            print(f"  launchctl bootout {target}  # ignore failure if not loaded")
            print(f"  launchctl bootstrap gui/{os.getuid()} {destination}")
            if kickstart:
                print(f"  launchctl kickstart -k {target}")
            continue

        shutil.copy2(source, destination)
        _run(["launchctl", "bootout", target], check=False)
        _run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(destination)])
        if kickstart:
            _run(["launchctl", "kickstart", "-k", target], check=False)

    print("Launchd install complete.")


def uninstall_agents(dry_run: bool) -> None:
    """Unload and remove installed pipeline launch agents."""
    _ensure_macos()
    plists = _plist_paths()
    if not plists:
        print(f"No plist files found in {LAUNCHD_DIR}", file=sys.stderr)
        sys.exit(1)

    for source in plists:
        label = source.stem
        target = _launchctl_target(label)
        destination = USER_LAUNCH_AGENTS / source.name

        print(f"Removing {source.name}")
        if dry_run:
            print(f"  launchctl bootout {target}")
            print(f"  rm -f {destination}")
            continue

        _run(["launchctl", "bootout", target], check=False)
        if destination.exists():
            destination.unlink()

    print("Launchd uninstall complete.")


def get_agent_status() -> dict:
    """Return structured scheduler status for programmatic use.

    Returns dict with keys:
        agents: list of {label, installed, loaded}
        installed_count, loaded_count, total
        healthy: True if all agents are installed and loaded
    """
    if platform.system() != "Darwin":
        return {"agents": [], "installed_count": 0, "loaded_count": 0, "total": 0, "healthy": False}

    plists = _plist_paths()
    if not plists:
        return {"agents": [], "installed_count": 0, "loaded_count": 0, "total": 0, "healthy": False}

    agents = []
    installed_count = 0
    loaded_count = 0
    for source in plists:
        label = source.stem
        destination = USER_LAUNCH_AGENTS / source.name
        installed = destination.exists()
        installed_count += int(installed)

        target = _launchctl_target(label)
        loaded = _run(["launchctl", "print", target], check=False).returncode == 0
        loaded_count += int(loaded)

        agents.append({"label": label, "installed": installed, "loaded": loaded})

    return {
        "agents": agents,
        "installed_count": installed_count,
        "loaded_count": loaded_count,
        "total": len(plists),
        "healthy": installed_count == len(plists) and loaded_count == len(plists),
    }


def show_status() -> None:
    """Report installed and loaded state for each pipeline launch agent."""
    _ensure_macos()
    plists = _plist_paths()
    if not plists:
        print(f"No plist files found in {LAUNCHD_DIR}", file=sys.stderr)
        sys.exit(1)

    print("PIPELINE LAUNCHD STATUS")
    print("=" * 70)
    print(f"{'Label':42s} {'Installed':10s} {'Loaded':8s}")
    print("-" * 70)

    installed_count = 0
    loaded_count = 0
    for source in plists:
        label = source.stem
        destination = USER_LAUNCH_AGENTS / source.name
        installed = destination.exists()
        installed_count += int(installed)

        target = _launchctl_target(label)
        loaded = _run(["launchctl", "print", target], check=False).returncode == 0
        loaded_count += int(loaded)

        print(
            f"{label:42s} "
            f"{'yes' if installed else 'no':10s} "
            f"{'yes' if loaded else 'no':8s}"
        )

    print("-" * 70)
    print(f"Installed: {installed_count}/{len(plists)} | Loaded: {loaded_count}/{len(plists)}")
    if loaded_count == 0:
        print("Action: run `python scripts/launchd_manager.py --install --kickstart`")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage pipeline launchd automation")
    parser.add_argument("--install", action="store_true", help="Install and load launchd agents")
    parser.add_argument("--uninstall", action="store_true", help="Unload and remove launchd agents")
    parser.add_argument("--status", action="store_true", help="Show installed/loaded status")
    parser.add_argument("--kickstart", action="store_true", help="Run agents immediately after install")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = parser.parse_args()

    # Default behavior: show status.
    if not (args.install or args.uninstall or args.status):
        args.status = True

    if args.install and args.uninstall:
        print("Choose one: --install or --uninstall", file=sys.stderr)
        sys.exit(1)

    if args.install:
        install_agents(kickstart=args.kickstart, dry_run=args.dry_run)
    elif args.uninstall:
        uninstall_agents(dry_run=args.dry_run)
    else:
        show_status()


if __name__ == "__main__":
    main()
