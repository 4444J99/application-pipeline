"""Configuration constants extracted from standup.py."""


OUTREACH_BY_STATUS = {
    "research": [
        "Search for past grantees/winners — calibrate your framing",
        "Check for upcoming info sessions or webinars",
        "Search LinkedIn for warm contacts at the org",
    ],
    "qualified": [
        "Visit the actual portal — note field names and character limits",
        "Read 2-3 past winners' statements for tone/length calibration",
        "Check if you know anyone connected to this org",
    ],
    "drafting": [
        "Request references/recommendations (2+ weeks before deadline)",
        "Verify portfolio URL and work samples are live and current",
        "Prepare a brief for any recommenders (opportunity + your angle)",
    ],
    "staged": [
        "Submit 24-48 hours before deadline (portals crash at deadlines)",
        "Do a final check of all links in your materials",
        "Prepare a thank-you draft for anyone who helped",
    ],
    "submitted": [
        "Send thank-you emails within 48 hours to anyone who helped",
        "Verify you received a confirmation email from the portal",
        "Note expected response timeline from the org's website/materials",
    ],
}


PRACTICES_BY_CONTEXT = {
    "pre_deadline_week": [
        "Submit 24-48 hours before the deadline — portals crash at the wire",
        "Check that all linked work samples/portfolio URLs are live",
        "Do a final proofread pass on all materials",
    ],
    "no_submissions_ever": [
        "Have you identified your top 3 perfect-fit roles?",
        "Invest time in relationship building before submitting cold",
        "One deeply researched application beats ten generic ones",
    ],
    "high_stagnation": [
        "Review your top entries — is each still a genuine perfect fit?",
        "If an entry has been stagnant >30 days, decide: invest deeper or withdraw",
    ],
    "networking_cadence": [
        "Target 2-3 outreach messages per week (quality over quantity)",
        "Warm introductions convert 5-10x better than cold emails",
    ],
    "reference_requests": [
        "Ask recommenders 2+ weeks before deadline",
        "Provide them a brief: what the opportunity is + your angle + deadline",
    ],
}


SECTIONS = {
    "health": "Pipeline health counts and velocity",
    "wins": "Recent milestones and achievements",
    "stale": "Staleness alerts (expired, at-risk, stagnant)",
    "execution": "Execution bottlenecks (stale staged, portal wiring, conversion)",
    "plan": "Today's work plan",
    "outreach": "Outreach suggestions per target",
    "practices": "Context-sensitive best practice reminders",
    "replenish": "Pipeline replenishment alerts",
    "deferred": "Deferred entries awaiting external unblock",
    "followup": "Follow-up dashboard for submitted entries",
    "readiness": "Staged entry readiness scores and blockers",
    "log": "Append session record to standup-log.yaml",
    "jobs": "Job pipeline status",
    "jobfreshness": "Job posting freshness tiers (hot/warm/cooling/stale)",
    "opportunities": "Opportunity pipeline (grants/residencies/prizes/writing)",
    "market": "Market conditions, hot skills, and upcoming grant deadlines",
    "funding": "Funding pulse: viability score, top pathways, urgent blind spots",
    "relationships": "Relationship cultivation: top targets, today's actions, dense orgs",
}


def build_next_status(valid_transitions: dict[str, set[str]]) -> dict[str, str]:
    """Build a forward-only next-status map from canonical transitions."""
    forward_path = ["research", "qualified", "drafting", "staged", "submitted"]
    next_status: dict[str, str] = {}
    for idx, status in enumerate(forward_path[:-1]):
        nxt = forward_path[idx + 1]
        if nxt in valid_transitions.get(status, set()):
            next_status[status] = nxt
    return next_status
