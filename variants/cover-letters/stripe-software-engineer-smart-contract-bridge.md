# Cover Letter — Stripe Software Engineer, Smart Contract Bridge (SF or NYC)

---

The hardest engineering problem I've solved wasn't building a feature — it was building a system that couldn't be left in an invalid state. 113 repositories, 8 GitHub organizations, a promotion state machine with four named states (LOCAL → CANDIDATE → PUBLIC → GRADUATED), forward-only transitions, and governance-rules.json enforced by CI on every push. No state skipping. No silent failures. Every transition validated before it executes.

That's the same guarantee a payment state machine requires. When I read the Smart Contract Bridge role description, the core engineering challenge — correctness guarantees across distributed state transitions — is identical in structure to what I've already built, just applied to a financial primitive instead of a repository lifecycle.

My technical stack is Python and TypeScript, which maps directly to what Stripe ships. I've built YAML schema validation pipelines, typed contract enforcement with Zod, 23,470 tests across the system with two testing strategies (live-data validation against contracts, isolated unit tests with monkeypatching). I run a 94-CI/CD-pipeline infrastructure where a failure at any gate blocks the transition. That's the culture Stripe describes: correctness first, velocity second.

The blockchain-specific layer is the gap I'm being transparent about. I understand contract execution semantics, finality, and the architectural constraints of immutable state — but I haven't shipped a production smart contract. I'd bring that up in an interview directly. What I'd offer in exchange: production-grade validation discipline, state machine architecture, and a track record of building systems where getting the invariants wrong has real consequences.

I'm available for SF or NYC. Happy to walk through the promotion state machine architecture in depth.

Anthony James Padavano
