Dear Coinbase Hiring Team,

Financial transactions are state machines. Every payment, every transfer, every risk decision is a transition that must be correct, auditable, and forward-only. I've spent the last five years building exactly this kind of infrastructure — not for fintech, but in the domain of software systems governance — and the underlying engineering is identical.

I'm a backend engineer based in New York City. My primary body of work is a 113-repository system across 8 GitHub organizations: 82K files, 23,470 tests, 104 CI/CD pipelines, and 50 cross-org dependency edges enforced automatically. At the center of this system is a YAML state machine I designed from scratch — 9 states, forward-only transitions, deferred states for externally blocked entries, explicit schema contracts at every transition boundary, and a signal-action audit trail that logs every state change with full context. The schema validator runs before any write. Invalid input fails fast with an actionable message, not a silent corruption.

This is the pattern Coinbase's money movement and risk infrastructure needs at scale: correctness guarantees over throughput, audit trails that survive incident review, and validation gates that prevent bad data from advancing through the pipeline. I designed my state machine so that the underlying logic could be audited by someone who was not present when it was written — which is exactly the property financial transaction systems require.

The Python work is production-grade. I've built ATS API clients using stdlib urllib, a 14-script CLI suite with a shared library, schema-enforced data contracts, and a test suite with two styles: live-data tests that validate against actual files, and isolated tests using monkeypatch and tmp_path for pure unit coverage. Ruff runs in CI. Edge cases and failure modes are explicit throughout.

I hold a Meta Full-Stack Developer certification and have been teaching technical systems across 8 institutions to 2,000+ students since 2015. The teaching background matters here: it means I document systems for people who weren't in the room, write error messages that explain what to do rather than just what broke, and build infrastructure that the next engineer can own.

Correctness, auditability, and explicit error handling are not constraints I work around — they are the methodology I bring to every system I build. I'd welcome the opportunity to discuss how this translates to Coinbase's money movement infrastructure.

Anthony James Padavano
New York City

Sincerely,
Anthony James Padavano
