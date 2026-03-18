Dear Tailscale Hiring Team,

Tailscale's core proposition is that secure networking should disappear — it should work reliably, stay out of the way, and never require the user to think about it. Building software that achieves that quality takes a specific engineering discipline: correctness-first design, security hygiene as default practice, and CLI tooling that behaves predictably at the edge.

I'm a systems engineer and CLI infrastructure builder based in New York City. My primary body of work spans 22 languages including Go across 113 repositories: 82K files, 23,470 tests, 104 CI/CD pipelines, and 50 cross-org dependency edges enforced automatically. I've built CLI tooling suites in Python and TypeScript with shared libraries, explicit input validation, actionable error messages, and fail-fast design for bad inputs. The infrastructure patterns — explicit contracts, schema validation at every boundary, correctness over throughput — are directly applicable to client networking software where undefined behavior is a security surface.

Security hygiene is a default, not an add-on, in my engineering practice. I've never committed credentials to a codebase. Configuration files containing personal or sensitive data are explicitly excluded from version control and documented as such. Input validation is explicit and runs before any state change. Audit trails log every significant operation. These habits are baked into how I build systems, not retrofitted during code review.

The Go work is genuine. Go appears in my 22-language codebase alongside TypeScript and Python, and the mental model it enforces — explicit error handling, composition over inheritance, clear interface contracts — aligns with how I approach systems design regardless of language. The Tailscale codebase's emphasis on correctness, static analysis, and comprehensive testing matches my own engineering standards. I have 23,470 tests across my system because correctness guarantees require test coverage for the edge cases, not just the happy path.

I hold a Meta Full-Stack Developer certification and have been writing technical documentation for complex systems for 2,000+ students across 8 institutions since 2015. I'd welcome the opportunity to discuss how this background maps to Tailscale's Go core client engineering needs.

Anthony James Padavano
New York City

Sincerely,
Anthony James Padavano
