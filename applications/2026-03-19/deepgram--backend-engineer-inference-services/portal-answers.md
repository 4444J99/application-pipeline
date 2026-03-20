# Deepgram — Backend Engineer, Inference Services — Portal Answers

## Are you located in the United States?

Yes

## Will you now or in the future require visa sponsorship (H1B, etc) for employment in the United States?

No

## What excites you about Deepgram?

Deepgram processes voice at a scale where backend engineering decisions have direct latency and cost impact on 200,000+ developers. The inference services problem — networking, speech processing, audio transcoding, scheduling across distributed compute — is a systems engineering challenge, not just an API wrapper. I build pipeline systems where processing stages must execute in strict order with validation at every boundary: 113 repositories, 104 CI/CD pipelines, 23,470 tests. That same pipeline discipline applies to inference service orchestration where a request must flow through transcoding → model inference → post-processing → response with hard latency constraints at each stage.

## Do you have hands-on experience in production-environment development with either Rust, C, or C++?

No

## What is the most impressive thing you've personally built or automated with AI?

A self-governing evaluative authority that uses 4 AI raters with distinct personas to assess system quality across 9 dimensions, computing inter-rater agreement (ICC, Cohen's kappa) to calibrate whether the AI evaluators agree with each other and with human judgment. The system implements Beer's Viable System Model System 3* — an independent audit function. Each rater gets a different persona prompt (architect-opus, pragmatist-sonnet, skeptic-haiku, generalist-gemini), rates the same 9 dimensions on a 1-10 scale, and the IRA analysis identifies which dimensions have consensus and which need human adjudication. Built with Anthropic and Google GenAI APIs, pytest-driven, and the ratings feed back into a quarterly recalibration system that adjusts scoring weights based on actual outcome data. The entire pipeline — from prompt generation to API calls to statistical analysis to weight adjustment — runs as a single command: `python scripts/run.py rateall`.

## LinkedIn

https://www.linkedin.com/in/anthonyjamespadavano

## Other

https://4444j99.github.io/portfolio/
