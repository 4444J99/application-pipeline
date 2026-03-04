# PRELIMINARY PAGES

---

## TITLE PAGE

# PRECISION OVER VOLUME: A MULTI-CRITERIA DECISION ANALYSIS FRAMEWORK FOR OPTIMAL CAREER APPLICATION PIPELINE MANAGEMENT

### A Comparative Systems Analysis of Volume-Optimized versus Precision-Optimized Strategies with Mathematical Proofs of Algorithmic Superiority

---

A Doctoral Thesis

Submitted in Partial Fulfillment of the Requirements for the Degree of
**Doctor of Business Administration**

---

**Anthony James Padavano**

---

Humboldt International University
Miami, Florida

March 2026

---

## DISSERTATION COMMITTEE APPROVAL PAGE

This doctoral thesis, written by Anthony James Padavano under the direction of his Dissertation Committee and approved by all members, has been presented to and accepted by the Faculty of Humboldt International University in partial fulfillment of the requirements for the degree of Doctor of Business Administration.

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Committee Chair | _________________________ | _________________________ | ____________ |
| Committee Member | _________________________ | _________________________ | ____________ |
| Committee Member | _________________________ | _________________________ | ____________ |
| Dean, School of Business | _________________________ | _________________________ | ____________ |

---

## DECLARATION OF ORIGINAL WORK / COPYRIGHT PAGE

I hereby declare that the work contained in this thesis is my own original research. Where the work of others has been used, it has been properly cited and acknowledged in accordance with academic standards. No part of this thesis has been previously submitted for any other degree or qualification at Humboldt International University or any other institution.

The software system described and analyzed in this thesis was designed, developed, and deployed by the author as a personal career management tool. All pipeline data analyzed herein was generated through the author's own career activities. No third-party personal data was collected, stored, or analyzed in the course of this research.

The mathematical proofs presented in Chapters 3 and 4 are original syntheses applying established theorems from multi-criteria decision analysis, information theory, portfolio optimization, and Markov chain theory to the novel domain of career pipeline management. The theoretical framework integrating six research traditions (Chapter 2, Section 2.11) is, to the author's knowledge, the first such synthesis in the literature.

---

**Copyright 2026 Anthony James Padavano. All rights reserved.**

No part of this work may be reproduced, distributed, or transmitted in any form or by any means without the prior written permission of the author, except in the case of brief quotations embodied in critical reviews and certain other noncommercial uses permitted by copyright law.

---

## DEDICATION

To every applicant who has sent sixty applications into the void and received only silence in return --- this work proves there is a better way.

To the precarious workers, the career changers, the artists seeking institutional support, the engineers caught in layoff cycles --- may algorithmic precision replace the tyranny of volume.

To the researchers who built the theoretical foundations upon which this work stands: Mark Granovetter, whose insight that weak ties carry strong information changed how we understand social networks; Harry Markowitz, whose portfolio theory showed that diversification is not merely prudent but mathematically optimal; John Kelly, whose criterion proved that some bets should never be made; and Claude Shannon, whose information theory gave us the language to distinguish signal from noise.

And to the 51,330 technology workers displaced in the first quarter of 2026 alone --- may this work contribute, however modestly, to a more rational and humane approach to the search for meaningful employment.

---

## ACKNOWLEDGMENTS

The author wishes to acknowledge the convergence of necessity and engineering that produced this research. The pipeline system described herein was not built as an academic exercise; it was built because the alternative --- submitting sixty cold applications in four days and receiving zero interviews --- was untenable. That failure, documented in the system's own conversion logs, became the inciting event for what evolved into a formal research program.

Gratitude is owed to the open-source communities whose foundational work made this synthesis possible. The Python scientific computing ecosystem (NumPy, SciPy, and the broader PyData community), the PyYAML library that serves as the pipeline's data substrate, and the testing frameworks (pytest, ruff) that ensure the system's 1,554 automated tests continue to pass --- these are the invisible infrastructure upon which applied research depends.

The market intelligence that informs the pipeline's scoring engine draws on the public research of LinkedIn's Economic Graph team, the Bureau of Labor Statistics, the Indeed Hiring Lab, Greenhouse Software's annual hiring reports, and the annual reports of creative funding organizations including Creative Capital, the Guggenheim Foundation, and the Rauschenberg Foundation. Their commitment to data transparency makes evidence-based career strategy possible.

The theoretical foundations of this work span six decades of scholarship across decision science, social network theory, labor economics, information theory, portfolio optimization, and rhetorical theory. The author is particularly indebted to the intellectual lineage of Fishburn (1967), Saaty (1980), Granovetter (1973), McCall (1970), Markowitz (1952), Kelly (1956), Shannon (1948), and Dawes (1979), whose work --- often developed for entirely different purposes --- converges with remarkable precision on the problem of career pipeline optimization.

Finally, the author acknowledges the role of AI-assisted research in the preparation of this thesis. Large language models were used as research assistants for literature discovery, citation verification, and mathematical exposition. All substantive claims, proofs, and interpretations are the author's own. The pipeline system's codebase --- 30+ scripts, 15,000+ lines of Python, 1,554 automated tests --- was developed through human-AI collaboration in accordance with the "AI-conductor" methodology described in this thesis: human direction, AI-assisted generation, human review and editorial control.

---

## ABSTRACT

**Background.** The contemporary career application landscape is characterized by an unprecedented volume crisis: application volumes have doubled since 2022, the average engineering role receives 250+ applications, cold application-to-interview conversion rates have fallen below 2%, and the technology sector alone has shed 51,330 jobs year-to-date in 2026. Traditional "spray and pray" approaches --- submitting maximum applications with minimal tailoring --- produce diminishing returns as applicant tracking systems process 98% of Fortune 500 applications while human reviewers allocate 6--10 seconds per resume. Simultaneously, 62% of AI-generated generic application content is rejected outright, creating a dual crisis of volume saturation and authenticity erosion. This study addresses the fundamental question: does a precision-targeted, algorithmically-guided application strategy constitute a provably superior approach to career pipeline management compared to volume-based alternatives?

**Methods.** This research employs a mixed-methods design science approach (Hevner et al., 2004) combining three analytical methods: (1) formal mathematical analysis proving optimality properties using established theorems from multi-criteria decision analysis (Fishburn, 1967; Triantaphyllou, 2000), portfolio optimization (Markowitz, 1952; Kelly, 1956), optimal stopping theory (McCall, 1970), information theory (Shannon, 1948), and social network analysis (Granovetter, 1973; Burt, 1992); (2) systematic competitive evaluation of 60+ existing products, platforms, and academic prototypes across a 12-dimension capability taxonomy; and (3) empirical analysis of a production pipeline system containing 1,000+ entries across 9 application tracks (job, grant, residency, fellowship, writing, prize, consulting, program, emergency), processed through a 10-state finite state machine with era-separated cohort comparison. The system's core architecture --- a 9-dimension Weighted Sum Model scoring engine with dual weight vectors, 6-signal time-decayed network proximity scoring, Bayesian outcome-learning calibration, and absorbing Markov chain pipeline modeling --- is evaluated against theoretical optima from each framework.

**Results.** Mathematical analysis demonstrates that the v2 precision pipeline achieves provable optimality under five independent theoretical frameworks: (1) Weighted Sum Model boundedness with guaranteed [1.0, 10.0] composite range under normalized weights, proven optimal for fully compensable problems (Triantaphyllou & Mann, 1989); (2) Kelly criterion analysis showing negative expected value for cold applications (Kelly fraction f* = -0.164) versus positive expected value for network-cultivated applications (f* = +0.04); (3) Shannon entropy reduction through targeted signal concentration, producing 6x higher signal-to-noise ratio compared to generic applications; (4) Markowitz portfolio diversification across 9 weakly-correlated application tracks; and (5) McCall reservation wage optimality of the 9.0/10 qualification threshold calibrated to the 89th percentile of the feasible scoring range. Competitive analysis reveals that no existing commercial product, open-source system, or documented academic prototype achieves more than 3 out of 12 on the capability matrix, versus the precision pipeline's 12/12. Empirical analysis confirms that the weight structure makes it mathematically impossible for cold-network job-track entries to reach the qualification threshold, enforcing network cultivation as a structural prerequisite. The Aristotelian rhetorical framework (ethos, logos, pathos) is shown to be embedded at every level of the system's composition engine, from the Storefront/Cathedral content architecture to the identity position system to the block-based narrative assembly.

**Conclusions.** The v2 precision pipeline represents a paradigm shift from volume-optimized to precision-optimized career management. Its mathematical foundations are not merely adequate but provably optimal under well-established theoretical conditions validated across decades of operations research, labor economics, and decision science. The most practically significant finding is the Kelly criterion result: cold applications have mathematically negative expected value, meaning the optimal strategy is to not submit them at all --- a finding that challenges the prevailing "apply to everything" advice. The system constitutes the first documented implementation that unifies multi-criteria decision analysis, social network theory, portfolio optimization, optimal stopping theory, information theory, and Aristotelian rhetoric into a single operational career pipeline, closing four identified gaps in the existing literature.

*Keywords:* multi-criteria decision analysis, weighted sum model, career pipeline optimization, network proximity scoring, time decay, precision hiring, portfolio theory, Kelly criterion, optimal stopping, McCall reservation wage, Shannon entropy, Aristotelian rhetoric, application tracking systems, Markov chain, outcome learning, design science research

---

## TABLE OF CONTENTS

- **Preliminary Pages** ... i--xii
- **Chapter 1: Introduction** ... 1
  - 1.1 Background and Context ... 1
  - 1.2 The Volume Crisis: A Quantitative Portrait ... 5
  - 1.3 Statement of the Research Problem ... 9
  - 1.4 Purpose of the Study ... 12
  - 1.5 Research Questions and Hypotheses ... 14
  - 1.6 Scope and Limitations ... 16
  - 1.7 Significance and Potential Contribution ... 18
  - 1.8 Definition of Terms ... 20
  - 1.9 Organization of the Thesis ... 24
- **Chapter 2: Literature Review** ... 26
  - 2.1 Introduction ... 26
  - 2.2 Search Strategy ... 28
  - 2.3 The Application Volume Crisis ... 31
  - 2.4 Multi-Criteria Decision Analysis ... 42
  - 2.5 Social Network Theory and Hiring ... 56
  - 2.6 Optimal Stopping and Job Search Theory ... 68
  - 2.7 Portfolio Theory Applied to Career Decisions ... 76
  - 2.8 Information Theory and Signal-to-Noise Ratio ... 84
  - 2.9 Persuasion Science and Application Rhetoric ... 90
  - 2.10 Existing Systems and Competitive Landscape ... 98
  - 2.11 Identification of Gaps ... 108
  - 2.12 Theoretical Framework ... 112
  - 2.13 Conclusion ... 116
- **Chapter 3: Methodology** ... 118
  - 3.1 Research Design and Method ... 118
  - 3.2 Population and Sample ... 122
  - 3.3 System Architecture: v1 versus v2 ... 126
  - 3.4 The Weighted Sum Model Scoring Engine ... 132
  - 3.5 Network Proximity Scoring with Time Decay ... 142
  - 3.6 Pipeline State Machine as Absorbing Markov Chain ... 154
  - 3.7 Reachability Analysis as Sensitivity Analysis ... 162
  - 3.8 Bayesian Outcome Learning ... 168
  - 3.9 The Relationship Cultivation Subsystem ... 174
  - 3.10 Mode Switching and Adaptive Governance ... 178
  - 3.11 Data Collection Methods and Instruments ... 182
  - 3.12 Data Analysis Methods ... 186
  - 3.13 Validity and Reliability ... 190
  - 3.14 Ethical Considerations ... 194
  - 3.15 Limitations ... 196
- **Chapter 4: Results** ... 198
  - 4.1 Introduction ... 198
  - 4.2 Mathematical Proofs of Optimality ... 200
  - 4.3 Competitive Analysis Results ... 220
  - 4.4 Empirical Pipeline Analysis ... 230
  - 4.5 The Aristotelian Framework: Ethos, Logos, Pathos ... 240
  - 4.6 Limitations of Results ... 250
  - 4.7 Summary of Key Findings ... 252
- **Chapter 5: Discussion** ... 254
  - 5.1 Introduction ... 254
  - 5.2 Interpretation of Results ... 256
  - 5.3 Implications for Theory ... 268
  - 5.4 Implications for Practice ... 274
  - 5.5 Main Conclusions ... 280
  - 5.6 Recommendations for Future Research ... 284
  - 5.7 Contribution to the Field ... 290
  - 5.8 Reflection on the Research Process ... 294
- **References** ... 298
- **Appendix A: System Architecture Diagrams** ... 318
- **Appendix B: Complete Scoring Rubric Configuration** ... 322
- **Appendix C: Mathematical Notation Reference** ... 326
- **Appendix D: Codebase Function Index** ... 330
- **Appendix E: Pipeline Entry Schema** ... 336
- **Appendix F: Competitive Product Detailed Assessments** ... 340
- **Appendix G: Research Agent Methodology** ... 348

---

## LIST OF FIGURES

| Figure | Title |
|--------|-------|
| 1.1 | Application Volume Growth by Quarter, 2020--2026 |
| 1.2 | Cold versus Warm Application Conversion Funnel |
| 1.3 | Technology Sector Layoff Trajectory, 2023--2026 |
| 1.4 | The Attention Economy: Reviewer Time Allocation |
| 2.1 | Theoretical Framework Integration Map |
| 2.2 | MCDA Method Taxonomy and Selection Decision Tree |
| 2.3 | Granovetter's Weak Ties Bridge Mechanism |
| 2.4 | Burt's Structural Holes: Network Advantage |
| 2.5 | McCall's Reservation Wage Model |
| 2.6 | Markowitz Efficient Frontier Applied to Application Tracks |
| 2.7 | Shannon's Channel Capacity Applied to Reviewer Attention |
| 2.8 | Aristotelian Rhetorical Triad in Application Context |
| 3.1 | v1 versus v2 Architecture Comparison (Side-by-Side) |
| 3.2 | Nine-Dimension Scoring Radar Chart (Creative vs. Job Weights) |
| 3.3 | Network Proximity Signal Aggregation Flow |
| 3.4 | Step-Function Time Decay Model with Behavioral Thresholds |
| 3.5 | Pipeline State Machine (Absorbing Markov Chain Formulation) |
| 3.6 | Canonical Form of the Pipeline Transition Matrix |
| 3.7 | Reachability Analysis Decision Tree by Track |
| 3.8 | Bayesian Outcome Learning Feedback Loop |
| 3.9 | Cultivation Workflow Integration with Scoring Engine |
| 3.10 | Mode Switching: Precision / Volume / Hybrid Threshold Surfaces |
| 4.1 | Kelly Criterion Surface: Expected Value by Probability and Payoff |
| 4.2 | Kelly Fraction by Application Type (Cold through Internal) |
| 4.3 | Competitive Landscape Feature Matrix Heat Map |
| 4.4 | Pipeline Score Distribution: Volume Era versus Precision Era |
| 4.5 | Network Proximity Impact on Maximum Achievable Score |
| 4.6 | Storefront/Cathedral Information Density Gradient |
| 4.7 | ROC Curve: Pipeline Threshold as Signal Detection |
| 5.1 | Precision Pipeline Contribution Map to Six Theoretical Domains |
| 5.2 | Research Agenda: Short-Term, Medium-Term, Long-Term |

---

## LIST OF TABLES

| Table | Title |
|-------|-------|
| 1.1 | Key Labor Market Statistics, 2023--2026 |
| 1.2 | Application Conversion Rates by Channel and Method |
| 1.3 | Grant and Fellowship Acceptance Rates by Program |
| 2.1 | Literature Search Strategy: Databases, Terms, and Results |
| 2.2 | MCDA Methods Comparison: Assumptions, Strengths, Limitations |
| 2.3 | Social Network Theory: Key Concepts and Empirical Evidence |
| 2.4 | Competitive Product Feature Assessment (12 Dimensions) |
| 2.5 | Academic Decision Support Systems: Domain and Method |
| 3.1 | v1 versus v2 Feature Comparison (22 Dimensions) |
| 3.2 | Scoring Dimension Weights: Creative Track versus Job Track |
| 3.3 | Network Proximity Ordinal Scale with Empirical Multipliers |
| 3.4 | Six Network Proximity Signals: Sources and Score Ranges |
| 3.5 | Time Decay Tier Thresholds with Behavioral Rationale |
| 3.6 | Pipeline State Transition Matrix (Valid Transitions) |
| 3.7 | Reachability Scenarios: Network Level to Composite Score |
| 3.8 | Outcome Learning Parameters and Safeguards |
| 3.9 | Mode Thresholds: Precision, Volume, Hybrid |
| 4.1 | WSM Axiom Verification for Career Application Domain |
| 4.2 | Kelly Criterion Calculations by Application Type |
| 4.3 | Shannon Entropy: Generic versus Tailored Applications |
| 4.4 | Competitive System Feature Gap Analysis (60+ Products) |
| 4.5 | Pipeline Entry Score Distribution by Era |
| 4.6 | Maximum Achievable Score by Network Level and Track |
| 4.7 | Aristotelian Dimensions in System Architecture |
| 4.8 | Summary of Key Findings by Research Question |
| 5.1 | Implications for Practice: Stakeholder-Specific Recommendations |
| 5.2 | Future Research Agenda with Priority and Feasibility |
