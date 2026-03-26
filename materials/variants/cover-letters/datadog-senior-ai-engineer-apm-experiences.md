Dear Datadog Hiring Team,

I have been running observability infrastructure for a production system for five years. It does not look like a SaaS product — it is a 113-repository, 8-organization software ecosystem I built and operate alone — but the discipline is identical: instrument, observe, alert, improve.

The system includes a pulse daemon that monitors health across all 8 GitHub organizations, system-snapshot.json capturing pipeline telemetry with 7d/30d/90d trend deltas and linear regression slopes, AMMOI (automated multi-model observability index) tracking quality signals over time, and staleness detection alerts for entries that have gone quiet. 104 CI/CD pipelines surface per-repo health on every merge. Inflection detection catches drift before it becomes regression. This is APM at the system level.

The AI layer of this work is where it connects most directly to the APM Experiences role. I built multi-agent systems using the Claude Agent SDK (agent--claude-smith: session persistence, self-correction, structured tool invocation) and TypeScript (agentic-titan: 1,095+ tests, 18 phases, parallel execution patterns). Adding AI to observability products is not just a feature addition — it changes how engineers interact with signal, and the interface design matters as much as the model. I have been thinking about that problem from both sides: as someone who builds AI systems and as someone who needs to trust observability data to make engineering decisions.

The 23,470 tests I maintain (14.5K Python, 8.9K TypeScript) represent a commitment to automated regression detection that I believe is the foundation of any reliable observability system. You cannot trust your alerts if you cannot trust your test suite.

I am based in New York City. I would be glad to discuss how my experience designing observability and AI systems at scale maps to the APM Experiences engineering challenges at Datadog.

Sincerely,
Anthony James Padavano
