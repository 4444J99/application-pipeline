Dear Toast Hiring Team,

Restaurant technology is fundamentally a reliability problem. An order must arrive in the kitchen. A payment must process. A reservation must be honored. The failure modes are visible, immediate, and directly tied to someone's livelihood. That constraint shapes how you design backend systems — correctness over throughput, explicit error handling, and state machines that cannot be bypassed.

I'm a backend engineer based in New York City who builds exactly this kind of infrastructure. My primary body of work is a 113-repository system across 8 GitHub organizations: 23,470 tests, 104 CI/CD pipelines, 50 enforced dependency edges, and a Python YAML state machine I designed from scratch with 9 states, forward-only transitions, schema validation at every boundary, preflight gates before every write, and an audit trail that logs every state change. The pattern is identical to payment transaction lifecycle management — because the underlying engineering problem is the same: a state that must advance correctly or not at all.

The Python work is production-grade. I've built ATS API clients using stdlib urllib, a 14-script CLI suite with a shared library, and a test suite covering both live-data scenarios (validating against actual YAML files) and isolated unit tests using monkeypatch and tmp_path. Ruff runs in CI. Error handling is explicit throughout — invalid inputs fail fast with messages that tell the next engineer exactly what to fix. The test suite covers edge cases, failure modes, and schema changes specifically because those are the scenarios that surface in production at the worst time.

The CI/CD infrastructure reflects the same discipline: 104 pipelines, 128 GitHub Actions workflows (18 reusable templates), automated dependency validation. Nothing advances without passing the gates.

I hold a Meta Full-Stack Developer certification and have been teaching technical communication to 2,000+ students since 2015. The teaching background shapes how I document systems: for the engineer who wasn't in the room when it was built, not for the engineer who wrote it.

I'd welcome the opportunity to discuss how this background maps to Toast's backend engineering needs.

Anthony James Padavano
New York City

Sincerely,
Anthony James Padavano
