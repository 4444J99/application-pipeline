Dear Temporal Hiring Team,

I've been thinking carefully about Temporal's core value proposition — make application code durable, reliable, and resumable — because I spent five years building a system that solves the same class of problem without it. That experience is why I want to work on the real thing.

The ORGANVM promotion state machine governs 113 repositories through five states: LOCAL, CANDIDATE, PUBLIC_PROCESS, GRADUATED, ARCHIVED. Transitions are forward-only, validated by a Python CLI that enforces JSON Schema contracts before advancing any entry. Deferred entries can reactivate on conditions — a resume_date field, a signal from an external check. 55 dependency edges are validated weekly with automated integrity checks; zero back-edge violations since the system was designed. Registry-v2.json is the durable state store: a 2,240-line record of every entity's current state, lineage, and metadata. When I look at Temporal's architecture — workflow history as the source of truth, activities as retriable units, signals as external triggers — I see the same pattern I implemented by hand. I know the problem Temporal solves because I felt the absence of it while building mine.

The Application Pipeline is a second example: a durable multi-step orchestrator where each entry progresses through a validated DAG — research, qualified, drafting, staged, submitted, acknowledged, interview, outcome — with schema guards at every transition. Long-running sequences (enrich, score, advance, submit, record) chain as a pipeline with preflight validation before each step. Deferred entries wait on conditions and reactivate automatically. That is Temporal's workflow-activity model, implemented in ~1,977 pytest-tested Python scripts. I'm applying to work on the infrastructure that would have made it correct by design.

The open source commitment resonates. All 113 of my repositories are public on GitHub under 8 organizations. I've written 23,470 tests — 14.5K Python, 8.9K TypeScript — and shipped 104 CI/CD pipelines with lint, test, validate, and deploy gates on every active repository. The role specifies Go for concurrent distributed systems work; Go is part of my 22-language system and I'm ready to go deep. I have also connected with Mason Egger and Cecil Phillip on LinkedIn, whose developer advocacy and open source community work first brought Temporal onto my radar.

I'm based in New York City. My full system is publicly available at github.com/4444j99. I'd welcome the chance to discuss the promotion state machine design and where the seams are — the exact places where Temporal underneath would have made it correct instead of hand-verified.

Sincerely,
Anthony James Padavano
