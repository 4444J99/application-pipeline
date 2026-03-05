#!/usr/bin/env python3
"""Composite daily pipeline health job.

Runs a full daily freshness loop:
1) fetch new ATS postings
2) auto-score and auto-qualify
3) auto-enrich entry materials/portal metadata
4) generate campaign + standup outputs
5) run hygiene checks
6) optionally email a daily report to stakeholders

Usage:
    python scripts/daily_pipeline_health.py                 # execute full daily job
    python scripts/daily_pipeline_health.py --dry-run       # preview mutating steps
    python scripts/daily_pipeline_health.py --email-to a@x.com,b@y.com
    python scripts/daily_pipeline_health.py --strict        # non-zero if a step fails
"""

from __future__ import annotations

import argparse
import os
import smtplib
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import REPO_ROOT, SIGNALS_DIR

SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
REPORT_DIR = SIGNALS_DIR / "daily-health"


@dataclass
class StepResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _run_step(name: str, command: list[str], capture: bool = True) -> StepResult:
    proc = subprocess.run(command, text=True, capture_output=capture)
    return StepResult(
        name=name,
        command=command,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def _email_report(report_text: str, recipients: list[str], subject: str) -> tuple[bool, str]:
    """Send report via SMTP using PIPELINE_SMTP_* environment variables."""
    if not recipients:
        return True, "no recipients configured"

    host = os.getenv("PIPELINE_SMTP_HOST", "").strip()
    port_raw = os.getenv("PIPELINE_SMTP_PORT", "587").strip()
    username = os.getenv("PIPELINE_SMTP_USER", "").strip()
    password = os.getenv("PIPELINE_SMTP_PASS", "").strip()  # allow-secret
    sender = os.getenv("PIPELINE_SMTP_FROM", username).strip()

    if not host:
        return False, "PIPELINE_SMTP_HOST is not set"
    if not sender:
        return False, "PIPELINE_SMTP_FROM or PIPELINE_SMTP_USER must be set"

    try:
        port = int(port_raw)
    except ValueError:
        return False, f"invalid PIPELINE_SMTP_PORT: {port_raw}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(report_text)

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            if os.getenv("PIPELINE_SMTP_STARTTLS", "1").strip() != "0":
                smtp.starttls()
                smtp.ehlo()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)
    except Exception as exc:  # pragma: no cover - network dependent
        return False, str(exc)

    return True, f"sent to {len(recipients)} recipient(s)"


def _format_report(results: list[StepResult], dry_run: bool, email_status: str) -> str:
    ts = datetime.now().isoformat(timespec="seconds")
    lines: list[str] = []
    lines.append(f"# Daily Pipeline Health — {ts}")
    lines.append("")
    lines.append(f"Mode: {'dry-run' if dry_run else 'execute'}")
    lines.append(f"Repo: {REPO_ROOT}")
    lines.append(f"Email: {email_status}")
    lines.append("")

    ok_count = sum(1 for r in results if r.ok)
    fail_count = len(results) - ok_count
    lines.append(f"Summary: {ok_count} ok | {fail_count} failed")
    lines.append("")

    for r in results:
        status = "OK" if r.ok else "FAIL"
        cmd = " ".join(r.command)
        lines.append(f"## {status} — {r.name}")
        lines.append(f"Command: `{cmd}`")
        if r.stdout.strip():
            lines.append("")
            lines.append("```text")
            lines.append(r.stdout.rstrip())
            lines.append("```")
        if r.stderr.strip():
            lines.append("")
            lines.append("```text")
            lines.append(r.stderr.rstrip())
            lines.append("```")
        lines.append("")

    return "\n".join(lines)


def run_daily_health(dry_run: bool, recipients: list[str], strict: bool) -> int:
    """Run the composite health workflow and return process exit code."""
    mutating_flag = "--dry-run" if dry_run else "--yes"

    steps: list[tuple[str, list[str]]] = [
        (
            "source-jobs",
            [PYTHON, str(SCRIPTS_DIR / "source_jobs.py"), "--fetch", mutating_flag],
        ),
        (
            "score-auto-qualify",
            [PYTHON, str(SCRIPTS_DIR / "score.py"), "--auto-qualify", mutating_flag],
        ),
        (
            "enrich-all",
            [PYTHON, str(SCRIPTS_DIR / "enrich.py"), "--all", mutating_flag],
        ),
        (
            "campaign-report",
            [PYTHON, str(SCRIPTS_DIR / "campaign.py")],
        ),
        (
            "standup-report",
            [PYTHON, str(SCRIPTS_DIR / "standup.py")],
        ),
        (
            "hygiene-check",
            [PYTHON, str(SCRIPTS_DIR / "hygiene.py")],
        ),
        (
            "scheduler-health",
            [PYTHON, str(SCRIPTS_DIR / "scheduler_health.py"), "--strict"],
        ),
    ]

    results: list[StepResult] = []
    for name, command in steps:
        result = _run_step(name, command, capture=True)
        results.append(result)

    email_status = "not requested"
    report_text = _format_report(results, dry_run=dry_run, email_status="pending")

    if recipients:
        ok, detail = _email_report(
            report_text,
            recipients,
            subject=f"Pipeline Daily Health — {datetime.now().date().isoformat()}",
        )
        email_status = f"ok ({detail})" if ok else f"failed ({detail})"
    else:
        email_status = "skipped (no recipients)"

    report_text = _format_report(results, dry_run=dry_run, email_status=email_status)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dated_path = REPORT_DIR / f"daily-health-{timestamp}.md"
    latest_path = REPORT_DIR / "latest.md"
    dated_path.write_text(report_text)
    latest_path.write_text(report_text)

    print(report_text)
    print()
    print(f"Saved report: {dated_path.relative_to(REPO_ROOT)}")

    failed = [r for r in results if not r.ok]
    if strict and failed:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run composite daily pipeline health workflow")
    parser.add_argument("--dry-run", action="store_true", help="Preview mutating steps without writing")
    parser.add_argument(
        "--email-to",
        default="",
        help="Comma-separated recipient emails for standup report",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any step fails")
    args = parser.parse_args()

    recipients = [e.strip() for e in args.email_to.split(",") if e.strip()]
    raise SystemExit(run_daily_health(dry_run=args.dry_run, recipients=recipients, strict=args.strict))


if __name__ == "__main__":
    main()
