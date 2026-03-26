Dear Coinbase Hiring Team,

The Data Platform team's mandate — centralize all internal and third-party data, make it easy for every team to access, process, and transform — is exactly the problem I've spent five years building against, at a different scale and for a different purpose.

The registry-v2.json file I maintain is a 2,240-line data catalog. It tracks 116 repositories across 8 GitHub organizations: implementation status, organ membership, dependency declarations, promotion state, and schema metadata. It has a JSON Schema contract validated in CI on every push. Python scripts enforce referential integrity and lineage on every commit. When any downstream consumer — a scoring engine, a campaign orchestrator, a funnel reporting tool — pulls from it, they get a clean, typed, validated view of the system's state. That is a data catalog. I built it as a single practitioner, but the architecture reflects the same discipline Coinbase's Data Platform team applies to its internal services at scale: a single authoritative source that downstream teams can trust without reading raw files.

Beyond the registry, I've built 30+ Python CLI scripts that form an analytics processing layer on top of that data store: TF-IDF text matching, multi-dimension scoring engines, conversion funnel analytics, velocity trend snapshots, external API ingestion from BLS OES, GitHub, and job board sources, and a multi-step campaign orchestrator that coordinates enrichment, validation, and submission in sequence. The pipeline has ~1,977 pytest tests, a shared common library with explicit schema contracts, and CI enforcement on every push. The design pattern is consistent with what Coinbase describes: frameworks and SDKs that transform raw data into reusable, scalable patterns for downstream consumers.

My Python backend skills are production-grade: type-annotated function signatures, explicit error handling with actionable messages, pathlib-first filesystem logic, and ruff-enforced style. I understand the scale-out, caching, key/value, and columnar design patterns the role specifies — these are architectural principles I've applied to a system spanning 82K files and 23,470 tests. Go is part of my 22-language repertoire, and I'm familiar with Airflow's orchestration model, Kafka's streaming patterns, and SQL as a first-class data transformation tool.

I'm based in New York City and open to the in-person offsites the role requires. My full work is public on GitHub at 4444j99, and a case study walkthrough is at my portfolio. I'd welcome the chance to talk through how this infrastructure translates directly to the problems your team is solving.

Sincerely,
Anthony James Padavano
