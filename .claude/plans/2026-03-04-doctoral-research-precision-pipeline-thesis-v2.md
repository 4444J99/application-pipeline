# Doctoral Research Notes v2: Mathematical & Algorithmic Foundations for Multi-Criteria Application Scoring

**Date:** 2026-03-04
**Supersedes:** `2026-03-04-doctoral-research-precision-pipeline-thesis.md` (behavioral/empirical focus)
**Purpose:** Deep mathematical and algorithmic treatment of the theoretical foundations underpinning a multi-criteria job/grant application scoring system. Formulas in LaTeX notation. Full academic citations.

---

## 1. MULTI-CRITERIA DECISION ANALYSIS (MCDA)

### 1.1 Weighted Sum Model (WSM)

The Weighted Sum Model is the simplest and most widely used MCDA method. For $m$ alternatives and $n$ criteria:

$$A_{WSM}^* = \max_i \sum_{j=1}^{n} w_j \cdot a_{ij}$$

where $w_j$ is the weight of criterion $j$ (with $\sum_{j=1}^{n} w_j = 1$), and $a_{ij}$ is the performance value of alternative $i$ on criterion $j$.

**When WSM is provably optimal:**

**Theorem (Keeney & Raiffa, 1976).** An additive value function $V(x) = \sum_{j=1}^{n} w_j v_j(x_j)$ is a valid representation of preferences if and only if the criteria satisfy **mutual preferential independence** (MPI). That is, the preference ordering over any subset of criteria is independent of the levels of the remaining criteria.

Formally, criteria $\{1, \ldots, n\}$ are mutually preferentially independent if for every subset $S \subseteq \{1, \ldots, n\}$, the conditional preference order $\succeq_S$ over outcomes varying only on $S$ does not depend on the fixed levels of criteria in $\{1, \ldots, n\} \setminus S$.

**Conditions under which WSM is appropriate:**
1. All criteria are measured on a common scale (or properly normalized)
2. Criteria are mutually preferentially independent (no synergies/conflicts between dimensions)
3. The value function is additive (no interaction effects)
4. Preference is monotonic in each criterion

**Reference:** Keeney, R. L., & Raiffa, H. (1976). *Decisions with Multiple Objectives: Preferences and Value Tradeoffs*. Wiley. Reprinted by Cambridge University Press, 1993.

### 1.2 The Robust Beauty of Improper Linear Models (Dawes, 1979)

**Key Theorem (Informal).** Unit-weighted linear composites (where all $w_j = 1/n$) perform comparably to optimally-weighted regression models in out-of-sample prediction, and consistently outperform clinical (human expert) judgment.

Dawes distinguishes:
- **Proper linear models**: weights $w_j$ derived by optimization (regression, discriminant analysis, ridge regression)
- **Improper linear models**: weights derived by non-optimal methods (intuition, equal weighting, random positive weights)

**Core finding:** For predicting a numerical criterion from numerical predictors, even improper linear models (including unit weights) are superior to clinical intuition. This is because:
1. Linear models are **perfectly consistent** (same inputs always yield same output)
2. Human judges suffer from **configural weighting errors** and **inconsistency noise**
3. The advantage of optimal weights over unit weights is small relative to the advantage of any linear model over holistic judgment

**Implication for scoring systems:** A 9-dimension weighted scoring rubric with reasonable weights will outperform unstructured human evaluation even if the weights are not precisely calibrated. The critical property is *consistency*, not *optimality* of weights.

**Reference:** Dawes, R. M. (1979). The robust beauty of improper linear models in decision making. *American Psychologist*, 34(7), 571-582.

### 1.3 Analytic Hierarchy Process (AHP) — Saaty, 1980

AHP structures decisions as a hierarchy and derives weights from pairwise comparison matrices.

**Pairwise comparison matrix:** For $n$ criteria, construct an $n \times n$ positive reciprocal matrix $A$ where $a_{ij}$ represents the relative importance of criterion $i$ over criterion $j$ on Saaty's 1-9 scale:

$$A = \begin{pmatrix} 1 & a_{12} & \cdots & a_{1n} \\ 1/a_{12} & 1 & \cdots & a_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ 1/a_{1n} & 1/a_{2n} & \cdots & 1 \end{pmatrix}$$

**Reciprocal axiom:** $a_{ji} = 1/a_{ij}$ for all $i, j$.

**Eigenvalue method:** The weight vector $w$ is the principal eigenvector of $A$:

$$A w = \lambda_{\max} w$$

**Theorem (Saaty, 1980).** For a perfectly consistent matrix (where $a_{ij} = w_i / w_j$ for all $i,j$), the principal eigenvalue $\lambda_{\max} = n$ (the order of the matrix). Any deviation $\lambda_{\max} > n$ indicates inconsistency.

**Consistency Index:**

$$CI = \frac{\lambda_{\max} - n}{n - 1}$$

**Consistency Ratio:**

$$CR = \frac{CI}{RI}$$

where $RI$ is the Random Index (average CI for random reciprocal matrices of the same order). Saaty's rule: $CR \leq 0.10$ is acceptable.

| n | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| RI | 0 | 0.58 | 0.90 | 1.12 | 1.24 | 1.32 | 1.41 | 1.45 |

**Reference:** Saaty, T. L. (1980). *The Analytic Hierarchy Process*. McGraw-Hill.

### 1.4 TOPSIS — Hwang & Yoon, 1981

**Technique for Order Preference by Similarity to Ideal Solution.** Based on the principle that the best alternative has the shortest Euclidean distance from the Positive Ideal Solution (PIS) and the longest from the Negative Ideal Solution (NIS).

**Step 1: Normalize** the decision matrix:

$$r_{ij} = \frac{x_{ij}}{\sqrt{\sum_{k=1}^{m} x_{kj}^2}}$$

**Step 2: Weighted normalized matrix:**

$$v_{ij} = w_j \cdot r_{ij}$$

**Step 3: Determine ideal solutions:**

$$A^+ = \{v_1^+, v_2^+, \ldots, v_n^+\} \quad \text{where } v_j^+ = \max_i v_{ij} \text{ (benefit criteria)}$$

$$A^- = \{v_1^-, v_2^-, \ldots, v_n^-\} \quad \text{where } v_j^- = \min_i v_{ij} \text{ (benefit criteria)}$$

**Step 4: Euclidean distances:**

$$D_i^+ = \sqrt{\sum_{j=1}^{n} (v_{ij} - v_j^+)^2} \qquad D_i^- = \sqrt{\sum_{j=1}^{n} (v_{ij} - v_j^-)^2}$$

**Step 5: Relative closeness coefficient:**

$$C_i^* = \frac{D_i^-}{D_i^+ + D_i^-}, \quad 0 \leq C_i^* \leq 1$$

The alternative with $C_i^*$ closest to 1 is preferred.

**Reference:** Hwang, C. L., & Yoon, K. (1981). *Multiple Attribute Decision Making: Methods and Applications*. Springer-Verlag.

### 1.5 ELECTRE — Roy, 1968

**ELimination Et Choix Traduisant la REalite** (Elimination and Choice Expressing Reality). An outranking method.

For alternatives $a$ and $b$:

**Concordance index** (degree to which $a$ outranks $b$):

$$C(a, b) = \frac{1}{W} \sum_{j: g_j(a) \geq g_j(b)} w_j, \quad W = \sum_{j=1}^{n} w_j$$

**Discordance index** (degree to which $b$ is strongly preferred to $a$ on some criterion):

$$D(a, b) = \max_j \frac{g_j(b) - g_j(a)}{\Delta_j^{\max}}$$

where $\Delta_j^{\max} = \max_{k,l} |g_j(a_k) - g_j(a_l)|$.

**Outranking:** $a$ outranks $b$ (written $a \mathrel{S} b$) if $C(a,b) \geq c^*$ (concordance threshold) AND $D(a,b) \leq d^*$ (discordance threshold).

The discordance veto is the critical innovation: even if an alternative is superior on most criteria, a sufficiently poor score on any single criterion can block the outranking relation entirely.

**Reference:** Roy, B. (1968). Classement et choix en presence de points de vue multiples (la methode ELECTRE). *RIRO*, 2(8), 57-75.

### 1.6 PROMETHEE — Brans, 1982

**Preference Ranking Organization METHod for Enrichment Evaluations.**

For each criterion $j$, define a preference function $P_j(a, b) = F_j[d_j(a, b)]$ where $d_j(a, b) = g_j(a) - g_j(b)$.

Common preference functions include:
- **Usual:** $P = 0$ if $d \leq 0$; $P = 1$ if $d > 0$
- **Linear:** $P = d/p$ if $0 < d \leq p$; $P = 1$ if $d > p$
- **Gaussian:** $P = 1 - e^{-d^2 / (2\sigma^2)}$

**Aggregate preference index:**

$$\pi(a, b) = \sum_{j=1}^{n} w_j P_j(a, b)$$

**Positive flow** (how much $a$ outranks all others):

$$\phi^+(a) = \frac{1}{m-1} \sum_{b \neq a} \pi(a, b)$$

**Negative flow** (how much $a$ is outranked):

$$\phi^-(a) = \frac{1}{m-1} \sum_{b \neq a} \pi(b, a)$$

**Net flow:**

$$\phi(a) = \phi^+(a) - \phi^-(a)$$

**Reference:** Brans, J. P. (1982). L'ingenierie de la decision: elaboration d'instruments d'aide a la decision. *Universite Laval, Quebec*.

---

## 2. SCORING THEORY AND PSYCHOMETRICS

### 2.1 Classical Test Theory (CTT)

**Fundamental equation:**

$$X = T + E$$

where $X$ is the observed score, $T$ is the true score, and $E$ is measurement error. Key assumptions: $E[E] = 0$, $\text{Cov}(T, E) = 0$, errors across items are uncorrelated.

**Reliability** is the ratio of true score variance to observed score variance:

$$\rho_{XX'} = \frac{\sigma_T^2}{\sigma_X^2} = 1 - \frac{\sigma_E^2}{\sigma_X^2}$$

**Cronbach's alpha** (Cronbach, 1951) — the most widely used reliability estimate:

$$\alpha = \frac{k}{k-1}\left(1 - \frac{\sum_{j=1}^{k} \sigma_{Y_j}^2}{\sigma_X^2}\right)$$

where $k$ is the number of items, $\sigma_{Y_j}^2$ is the variance of item $j$, and $\sigma_X^2$ is the variance of the total score.

**Interpretation:** $\alpha$ estimates the proportion of total variance attributable to the common factor. Conventional thresholds: $\alpha \geq 0.70$ acceptable, $\geq 0.80$ good, $\geq 0.90$ excellent.

**Important caveat:** Alpha increases mechanically with the number of items (Spearman-Brown effect) and assumes essential tau-equivalence (all items measure the same construct with equal true-score variance). Multidimensional constructs violate this assumption, leading to underestimation of reliability.

**Spearman-Brown Prophecy Formula:**

$$\rho_{k} = \frac{k \cdot \rho_1}{1 + (k-1) \cdot \rho_1}$$

where $\rho_1$ is the reliability of a single item and $\rho_k$ is the predicted reliability after increasing the test length by factor $k$.

**References:**
- Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests. *Psychometrika*, 16(3), 297-334.
- Spearman, C. (1910). Correlation calculated from faulty data. *British Journal of Psychology*, 3(3), 271-295.

### 2.2 Item Response Theory (IRT)

**Two-Parameter Logistic Model (2PL):**

$$P(X_i = 1 \mid \theta) = \frac{e^{a_i(\theta - b_i)}}{1 + e^{a_i(\theta - b_i)}}$$

where:
- $\theta$ = latent trait level (person ability/quality)
- $a_i$ = discrimination parameter (slope at inflection point; higher = more discriminating)
- $b_i$ = difficulty parameter (value of $\theta$ where $P = 0.50$)

**Three-Parameter Logistic Model (3PL)** adds a guessing parameter $c_i$:

$$P(X_i = 1 \mid \theta) = c_i + (1 - c_i) \frac{e^{a_i(\theta - b_i)}}{1 + e^{a_i(\theta - b_i)}}$$

**Information Function** (the IRT analog of reliability):

$$I_i(\theta) = a_i^2 P_i(\theta) Q_i(\theta), \quad Q_i(\theta) = 1 - P_i(\theta)$$

**Test Information Function** (sum of item information):

$$I(\theta) = \sum_{i=1}^{k} I_i(\theta)$$

**Standard Error of Measurement:**

$$SE(\theta) = \frac{1}{\sqrt{I(\theta)}}$$

**Key advantage over CTT:** IRT provides precision estimates at *every level* of the latent trait, not just overall. This means different applicant profiles can have different measurement precision.

**Graded Response Model (GRM)** — for polytomous scoring (Samejima, 1969):

$$P^*(X_i \geq k \mid \theta) = \frac{e^{a_i(\theta - b_{ik})}}{1 + e^{a_i(\theta - b_{ik})}}$$

$$P(X_i = k \mid \theta) = P^*(X_i \geq k \mid \theta) - P^*(X_i \geq k+1 \mid \theta)$$

**References:**
- Lord, F. M. (1980). *Applications of Item Response Theory to Practical Testing Problems*. Erlbaum.
- Samejima, F. (1969). Estimation of latent ability using a response pattern of graded scores. *Psychometrika Monograph*, 17.

### 2.3 Validity Framework

A scoring rubric must demonstrate three types of validity:

**Content Validity:** The degree to which the scoring dimensions adequately sample the domain of interest. Established through expert review, not statistics. For the 9-dimension rubric, content validity requires demonstrating that {mission_alignment, evidence_match, track_record_fit, network_proximity, strategic_value, financial_alignment, effort_to_value, deadline_feasibility, portal_friction} collectively cover all factors relevant to application success.

**Construct Validity:** The degree to which the rubric measures the theoretical construct it claims to measure. Assessed via:
- **Convergent validity**: High correlations with other measures of the same construct (e.g., scores correlate with eventual interview rates)
- **Discriminant validity**: Low correlations with measures of unrelated constructs (e.g., scores do not merely reflect name recognition or prestige)
- **Factor structure**: Factor analysis should reveal dimensions consistent with the theoretical model

**Criterion Validity:** The degree to which scores predict external outcomes.
- **Predictive validity**: Do higher-scored applications yield higher acceptance rates?
- **Concurrent validity**: Do scores correlate with expert assessments made at the same time?

**Reference:** Messick, S. (1989). Validity. In R. L. Linn (Ed.), *Educational Measurement* (3rd ed., pp. 13-103). Macmillan.

---

## 3. PORTFOLIO OPTIMIZATION THEORY

### 3.1 Markowitz Mean-Variance Optimization

**The Problem:** Given $n$ assets (application tracks/types) with expected returns $\mu = (\mu_1, \ldots, \mu_n)^T$ and covariance matrix $\Sigma$, find portfolio weights $w = (w_1, \ldots, w_n)^T$ that minimize variance for a given expected return:

$$\min_w \quad w^T \Sigma w$$
$$\text{s.t.} \quad w^T \mu = \mu_p, \quad w^T \mathbf{1} = 1$$

**Lagrangian solution:**

$$\mathcal{L}(w, \lambda_1, \lambda_2) = w^T \Sigma w + \lambda_1(\mu_p - w^T \mu) + \lambda_2(1 - w^T \mathbf{1})$$

**First-order conditions:** $2\Sigma w = \lambda_1 \mu + \lambda_2 \mathbf{1}$, yielding:

$$w^* = \frac{1}{2}\Sigma^{-1}(\lambda_1 \mu + \lambda_2 \mathbf{1})$$

**The efficient frontier** is the set of all portfolios that are Pareto-optimal in $(\sigma_p, \mu_p)$ space — no portfolio achieves higher return at the same risk level. It traces the upper boundary of the "Markowitz bullet" (a hyperbola in $\sigma_p$-$\mu_p$ space).

**Application to non-financial decisions:** Replacing "return" with "expected acceptance probability" and "risk" with "variance of outcomes across application types," the framework justifies diversifying across tracks (grants, jobs, residencies, fellowships) to reduce total portfolio risk.

**Diversification benefit** (for $n$ equally-weighted uncorrelated applications):

$$\sigma_p^2 = \frac{1}{n}\bar{\sigma}^2 + \frac{n-1}{n}\bar{\sigma}_{ij}$$

As $n \to \infty$, idiosyncratic risk vanishes and only systematic risk (correlated market conditions) remains.

**Reference:** Markowitz, H. (1952). Portfolio Selection. *The Journal of Finance*, 7(1), 77-91.

### 3.2 Kelly Criterion — Optimal Bet Sizing

**The Kelly Criterion** (Kelly, 1956) maximizes the expected logarithm of wealth, equivalent to maximizing the long-run geometric growth rate.

**Binary case:** For a bet with win probability $p$ and loss probability $q = 1 - p$, with odds $b$ (win $b$ dollars for each dollar bet):

$$f^* = \frac{bp - q}{b} = \frac{p(b + 1) - 1}{b}$$

where $f^*$ is the optimal fraction of capital to wager.

**Derivation:** Starting with wealth $W$, after betting fraction $f$:
- Win: $W(1 + bf)$ with probability $p$
- Lose: $W(1 - f)$ with probability $q$

Expected log wealth:

$$E[\ln W'] = p \ln(1 + bf) + q \ln(1 - f)$$

Setting $\frac{d}{df}E[\ln W'] = 0$:

$$\frac{pb}{1 + bf^*} - \frac{q}{1 - f^*} = 0 \implies f^* = \frac{bp - q}{b}$$

**Multi-asset generalization (continuous case):**

$$f^* = \Sigma^{-1}(\mu - r\mathbf{1})$$

where $\mu$ is the vector of expected returns, $r$ is the risk-free rate, and $\Sigma$ is the covariance matrix. This is proportional to the Markowitz tangency portfolio but determines the *leverage* (total allocation) rather than just relative weights.

**Theorem (Kelly, 1956).** The Kelly strategy maximizes the expected growth rate $G = E[\ln(W_{t+1}/W_t)]$, and the maximum growth rate equals the information-theoretic mutual information (channel capacity) between the signal and the outcome.

**Application to application limiting (max 10 active):** Each active application is an "investment" of time/effort. The Kelly framework suggests that over-diversifying (too many applications) reduces the effective "bet size" per application below the threshold needed for quality. The optimal number balances between:
- Too few: high idiosyncratic risk (one rejection is catastrophic)
- Too many: each application gets insufficient effort, reducing its "edge" $p$ toward base rate

**References:**
- Kelly, J. L. (1956). A New Interpretation of Information Rate. *Bell System Technical Journal*, 35(4), 917-926.
- Thorp, E. O. (2006). The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market. In *Handbook of Asset and Liability Management*.

---

## 4. OPTIMAL STOPPING THEORY

### 4.1 The Secretary Problem / Best Choice Problem

**Setup:** $n$ candidates arrive in random order. After each interview, irrevocably accept or reject. Goal: maximize probability of selecting the absolute best.

**Optimal strategy:** Reject the first $r^* - 1$ candidates (observation phase), then accept the first subsequent candidate who is better than all previously seen.

**Theorem (Lindley, 1961; Dynkin, 1963).** The probability of selecting the best candidate under the optimal rule with cutoff $r$ is:

$$P_n(r) = \frac{r-1}{n} \sum_{j=r}^{n} \frac{1}{j-1}$$

**Asymptotic result.** Let $x = r/n$ (fraction of candidates to reject). As $n \to \infty$:

$$P_n(r) \to -x \ln x$$

Maximizing $-x \ln x$: setting $\frac{d}{dx}(-x \ln x) = -\ln x - 1 = 0$ yields $x^* = 1/e$.

**Theorem.** The optimal cutoff is $r^* = \lfloor n/e \rfloor$ and the maximum success probability approaches $1/e \approx 0.3679$.

**Reference:** Ferguson, T. S. (1989). Who Solved the Secretary Problem? *Statistical Science*, 4(3), 282-296.

### 4.2 McCall's Job Search Model (1970)

**Setup:** An unemployed worker receives i.i.d. wage offers $w$ drawn from known distribution $F(w)$ each period. Discount factor $\beta \in (0, 1)$. Unemployment compensation $c$ per period.

**Bellman equation:**

$$V(w) = \max\left\{\frac{w}{1 - \beta}, \; c + \beta \sum_{w'} V(w') q(w')\right\}$$

where the first term is the lifetime value of accepting wage $w$ forever, and the second is the continuation value of rejecting and searching further.

**Reservation wage:** Define $\bar{w}$ as the wage at which the worker is indifferent between accepting and rejecting:

$$\frac{\bar{w}}{1 - \beta} = c + \beta \sum_{w'} V(w') q(w')$$

This yields the **reservation wage equation:**

$$\bar{w} = (1 - \beta)\left[c + \frac{\beta}{1 - \beta} \sum_{w' > \bar{w}} (w' - \bar{w}) q(w')\right]$$

Or equivalently in continuous form:

$$\bar{w} - c = \frac{\beta}{1 - \beta} \int_{\bar{w}}^{\infty} (w' - \bar{w}) \, dF(w')$$

**Interpretation:** The LHS is the cost of rejecting one more offer (foregoing $\bar{w}$ and receiving only $c$). The RHS is the expected discounted benefit of continued search (the "option value" of seeing better offers).

**Theorem (McCall, 1970).** The optimal policy is a *threshold strategy*: accept any offer $w \geq \bar{w}$, reject any offer $w < \bar{w}$. This follows from the contraction mapping theorem applied to the Bellman operator $T$:

$$(Tv)(w) = \max\left\{\frac{w}{1 - \beta}, \; c + \beta \sum_{w'} v(w') q(w')\right\}$$

$T$ is a contraction on the space of bounded functions, so it has a unique fixed point $V^* = TV^*$, and the associated policy is optimal.

**Comparative statics:**
- $\uparrow c$ (higher unemployment compensation) $\implies$ $\uparrow \bar{w}$ (more selective)
- $\uparrow \beta$ (more patient) $\implies$ $\uparrow \bar{w}$ (willing to wait longer)
- Mean-preserving spread of $F$ $\implies$ $\uparrow \bar{w}$ (more volatility increases option value)

**Direct mapping to application pipeline:** The minimum score threshold of 9.0/10 functions exactly as a reservation wage. The worker rejects all opportunities below this threshold, accepting only those above it. The comparative statics predict:
- Higher savings/runway $\implies$ higher threshold (can afford to be more selective)
- Greater patience (longer time horizon) $\implies$ higher threshold
- Greater variance in opportunity quality $\implies$ higher threshold (more upside from waiting)

**References:**
- McCall, J. J. (1970). Economics of Information and Job Search. *Quarterly Journal of Economics*, 84(1), 113-126.
- Mortensen, D. T. (1986). Job Search and Labor Market Analysis. In O. Ashenfelter & R. Layard (Eds.), *Handbook of Labor Economics*, Vol. 2, Ch. 15.

---

## 5. NETWORK EFFECTS AND GRAPH THEORY

### 5.1 Network Centrality Measures

Let $G = (V, E)$ be a graph with $|V| = n$ nodes.

**Degree Centrality (Freeman, 1979):**

$$C_D(v) = \frac{\deg(v)}{n - 1}$$

Simply the fraction of other nodes to which $v$ is connected.

**Closeness Centrality (Freeman, 1979):**

$$C_C(v) = \frac{n - 1}{\sum_{u \neq v} d(v, u)}$$

where $d(v, u)$ is the shortest-path distance between $v$ and $u$. Higher values indicate a node that can reach all others quickly.

**Betweenness Centrality (Freeman, 1979):**

$$C_B(v) = \sum_{s \neq v \neq t} \frac{\sigma_{st}(v)}{\sigma_{st}}$$

where $\sigma_{st}$ is the total number of shortest paths from $s$ to $t$, and $\sigma_{st}(v)$ is the number of those paths passing through $v$.

**Normalized betweenness:**

$$C_B'(v) = \frac{2 C_B(v)}{(n-1)(n-2)}$$

**Eigenvector Centrality (Bonacich, 1972):**

$$x_v = \frac{1}{\lambda} \sum_{u \in N(v)} x_u$$

In matrix form: $Ax = \lambda x$, where $A$ is the adjacency matrix and $x$ is the principal eigenvector corresponding to the largest eigenvalue $\lambda_1$.

**Interpretation:** A node is central if it is connected to other central nodes (recursive definition). Google's PageRank is a variant with damping factor.

**References:**
- Freeman, L. C. (1979). Centrality in social networks: Conceptual clarification. *Social Networks*, 1(3), 215-239.
- Bonacich, P. (1972). Factoring and weighting approaches to status scores and clique identification. *Journal of Mathematical Sociology*, 2(1), 113-120.

### 5.2 Weak Ties and Structural Holes

**Granovetter's Strength of Weak Ties (1973):**

The tie strength between persons A and B is a function of: (1) time invested, (2) emotional intensity, (3) intimacy, and (4) reciprocal services.

**The Forbidden Triad:** If A-B is a strong tie and A-C is a strong tie, then B-C must have at least a weak tie (the triad cannot be open). This follows from the overlap hypothesis: the stronger the tie between A and B, the larger the proportion of individuals to whom they are both tied.

**Bridge definition:** An edge $e = (u, v)$ is a *bridge* if its removal disconnects the graph. Weak ties are more likely to be bridges because strong ties embed in dense clusters.

**Job market implication:** In Granovetter's survey (1973) of 282 men who found jobs through contacts, 83.4% described the contact as an acquaintance (weak tie) rather than a close friend. A 2022 LinkedIn experiment (Rajkumar et al., *Science*, 2022) causally confirmed this: moderately weak ties were the most effective for job mobility, with the probability of getting a new job increasing by 2-3x through weak ties vs. strong ties.

**Burt's Structural Holes (1992):**

An actor benefits not from strong ties per se, but from *non-redundant* ties that bridge structural holes (gaps between clusters). The **constraint measure** quantifies how much of an actor's network is invested in redundant contacts:

$$c_{ij} = \left(p_{ij} + \sum_{q \neq i, j} p_{iq} p_{qj}\right)^2$$

$$C_i = \sum_j c_{ij}$$

where $p_{ij}$ is the proportion of $i$'s network time invested in $j$. Lower constraint = more structural holes = more novel information access.

**Application to `network_proximity` scoring:** The dimension should capture not just whether a referral exists (binary), but the *bridging quality* of the connection — whether the contact spans a structural hole between the applicant's current network and the target organization.

**References:**
- Granovetter, M. S. (1973). The Strength of Weak Ties. *American Journal of Sociology*, 78(6), 1360-1380.
- Burt, R. S. (1992). *Structural Holes: The Social Structure of Competition*. Harvard University Press.
- Rajkumar, K., et al. (2022). A causal test of the strength of weak ties. *Science*, 377(6612), 1304-1310.

### 5.3 Decay Functions for Relationship Freshness

The value of a network connection decays over time since last interaction. Three canonical models:

**Exponential decay:**

$$f(t) = f_0 \cdot e^{-\lambda t}$$

**Half-life:** $t_{1/2} = \ln 2 / \lambda$. If a relationship's "value" halves every 90 days, then $\lambda = \ln 2 / 90 \approx 0.0077$ per day.

**Advantages:** Memoryless property ($P(T > t + s \mid T > s) = P(T > t)$); analytically tractable; well-established in physics, pharmacology, and information theory.

**Step function (threshold decay):**

$$f(t) = \begin{cases} f_0 & \text{if } t \leq \tau \\ 0 & \text{if } t > \tau \end{cases}$$

Simple but discontinuous. Used in the pipeline's current stale thresholds (14 days, 30 days).

**Logarithmic decay:**

$$f(t) = f_0 - k \ln(1 + t)$$

Slow initial decay, accelerating over time. Matches the **Ebbinghaus forgetting curve** (1885):

$$R(t) = e^{-t/S}$$

where $R$ is retention, $t$ is time, and $S$ is the stability of the memory. Each review resets $S$ to a higher value (spaced repetition effect).

**Theoretical backing:** Exponential decay has the strongest theoretical justification because it naturally arises from any process where the instantaneous rate of decay is proportional to the current value ($dN/dt = -\lambda N$). For relationship scoring, the recommendation is a **hybrid model**: exponential decay as the base, with step-function cutoffs for actionability thresholds.

**Reference:** Ebbinghaus, H. (1885). *Uber das Gedachtnis: Untersuchungen zur experimentellen Psychologie* [Memory: A Contribution to Experimental Psychology]. Duncker & Humblot.

---

## 6. SIGNAL DETECTION THEORY (SDT)

### 6.1 Core Framework

SDT models the discrimination between two states (signal present vs. absent) under uncertainty, producing four outcomes:

|  | Signal Present | Signal Absent |
|--|---------------|---------------|
| **Respond "Yes"** | Hit (TP) | False Alarm (FP) |
| **Respond "No"** | Miss (FN) | Correct Rejection (TN) |

**Sensitivity (d-prime):**

$$d' = z(H) - z(F)$$

where $H$ = hit rate, $F$ = false alarm rate, and $z(\cdot)$ is the inverse normal CDF ($\Phi^{-1}$).

**Alternative formulation (Gaussian equal-variance model):**

$$d' = \frac{\mu_S - \mu_N}{\sigma}$$

where $\mu_S$ and $\mu_N$ are the means of the signal and noise distributions.

**Decision criterion (c):**

$$c = -\frac{1}{2}[z(H) + z(F)]$$

$c > 0$: conservative (biased toward "no"); $c < 0$: liberal (biased toward "yes").

**Likelihood ratio criterion ($\beta$):**

$$\beta = \frac{f_S(\text{criterion})}{f_N(\text{criterion})} = e^{d' \cdot c}$$

Unbiased observer: $\beta = 1$.

### 6.2 ROC Curves

The Receiver Operating Characteristic curve plots $H$ (true positive rate) vs. $F$ (false positive rate) as the criterion varies.

**Area Under the Curve (AUC):**

$$AUC = \Phi\left(\frac{d'}{\sqrt{2}}\right)$$

for the equal-variance Gaussian model. $AUC = 0.5$ is chance; $AUC = 1.0$ is perfect discrimination.

### 6.3 Application to Job Search Decisions

Map the framework:
- **Signal:** "This opportunity is a genuine good fit" ($\text{score} \geq 9.0$)
- **Noise:** "This opportunity appears good but is not" ($\text{score} < 9.0$ despite surface appeal)
- **Hit:** Correctly applying to a good-fit opportunity
- **Miss:** Failing to apply to a genuinely good opportunity (Type II error)
- **False Alarm:** Applying to a poor-fit opportunity (Type I error — wasted effort)
- **Correct Rejection:** Correctly passing on a poor fit

**Precision-over-volume as criterion shift:** The pipeline's 9.0 threshold represents a *conservative* criterion ($c > 0$), which:
- Reduces false alarms (wasted applications) at the cost of increased misses
- Is optimal when the *cost of a false alarm* (time/effort on doomed application) exceeds the *cost of a miss* (potential opportunity forgone)
- In the current market (51,330 layoffs YTD, cold app viability LOW), a conservative criterion is justified because the base rate of genuine good-fit opportunities is low

**Precision and Recall (Information Retrieval analogy):**

$$\text{Precision} = \frac{TP}{TP + FP} = PPV$$

$$\text{Recall} = \frac{TP}{TP + FN} = TPR$$

$$F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

The pipeline optimizes for **high precision** (every application sent is a genuine fit) over high recall (catching every possible opportunity), which is the correct optimization target when application cost is high and reviewer attention is scarce.

**References:**
- Green, D. M., & Swets, J. A. (1966). *Signal Detection Theory and Psychophysics*. Wiley.
- Macmillan, N. A., & Creelman, C. D. (2005). *Detection Theory: A User's Guide* (2nd ed.). Erlbaum.

---

## 7. TIME DECAY FUNCTIONS

### 7.1 Formal Comparison

| Property | Exponential | Step Function | Logarithmic | Power Law |
|----------|-------------|---------------|-------------|-----------|
| Formula | $f_0 e^{-\lambda t}$ | $f_0 \cdot \mathbb{1}_{t \leq \tau}$ | $f_0 - k\ln(1+t)$ | $f_0 (1+t)^{-\alpha}$ |
| Memoryless | Yes | No | No | No |
| Continuous | Yes | No | Yes | Yes |
| Derivative | $-\lambda f$ | Undefined at $\tau$ | $-k/(1+t)$ | $-\alpha f_0 (1+t)^{-\alpha-1}$ |
| Half-life | $\ln 2 / \lambda$ | $\tau$ | Not constant | $(2^{1/\alpha}-1)$ |
| Domain | Physics, radioactivity | Pipeline thresholds | Memory, learning | Complex systems |

### 7.2 Jost's Law and Memory Decay

**Jost's Law (1897):** Of two memory traces of equal strength, the older one will decay more slowly. This implies a **power-law** or **sum-of-exponentials** model rather than a simple exponential:

$$R(t) = a \cdot t^{-b}$$

or:

$$R(t) = \alpha_1 e^{-\lambda_1 t} + \alpha_2 e^{-\lambda_2 t}$$

where $\lambda_1 > \lambda_2$ (fast initial decay + slow long-term decay).

**Implication:** For relationship freshness, a two-exponential model is more realistic: recent interactions decay fast but established relationships retain a "floor" value.

### 7.3 Recommended Model for Network Proximity Decay

$$\text{freshness}(t) = w_{\text{fast}} e^{-\lambda_1 t} + w_{\text{slow}} e^{-\lambda_2 t}$$

with suggested parameters for professional relationships:
- $\lambda_1 \approx 0.023$ (30-day half-life for recent interaction value)
- $\lambda_2 \approx 0.0019$ (1-year half-life for established relationship value)
- $w_{\text{fast}} = 0.6$, $w_{\text{slow}} = 0.4$

**Reference:** Wixted, J. T. (2004). On common ground: Jost's (1897) law of forgetting and Ribot's (1881) law of retrograde amnesia. *Psychological Review*, 111(4), 864-879.

---

## 8. ALGORITHMIC FAIRNESS AND BIAS

### 8.1 Fairness Definitions

**Statistical (Demographic) Parity:**

$$P(\hat{Y} = 1 \mid A = 0) = P(\hat{Y} = 1 \mid A = 1)$$

The selection rate must be equal across protected groups $A$.

**Equalized Odds (Hardt, Price, & Srebro, 2016):**

$$P(\hat{Y} = 1 \mid Y = y, A = 0) = P(\hat{Y} = 1 \mid Y = y, A = 1) \quad \forall y \in \{0, 1\}$$

Both FPR and TPR must be equal across groups.

**Calibration (within groups):**

$$P(Y = 1 \mid \hat{Y} = s, A = a) = s \quad \forall s \in [0,1], \; \forall a$$

A predicted probability $s$ should mean the same thing regardless of group membership.

**Predictive Parity:**

$$PPV_0 = PPV_1 \quad \iff \quad P(Y = 1 \mid \hat{Y} = 1, A = 0) = P(Y = 1 \mid \hat{Y} = 1, A = 1)$$

### 8.2 Impossibility Theorems

**Theorem (Chouldechova, 2017).** If the base rates differ across groups ($P(Y=1 \mid A=0) \neq P(Y=1 \mid A=1)$), then no classifier can simultaneously achieve:
1. Predictive parity: $PPV_0 = PPV_1$
2. Equal FPR: $FPR_0 = FPR_1$
3. Equal FNR: $FNR_0 = FNR_1$

**Proof sketch.** From the definitions:

$$\frac{PPV}{1 - PPV} = \frac{p}{1 - p} \cdot \frac{1 - FNR}{FPR}$$

where $p$ is the base rate. If $p_0 \neq p_1$ and $PPV_0 = PPV_1$, then $(1 - FNR_0)/FPR_0 \neq (1 - FNR_1)/FPR_1$, so error rates cannot be equalized.

**Theorem (Kleinberg, Mullainathan, & Raghavan, 2016).** Except in degenerate cases (perfect prediction or equal base rates), no risk score can simultaneously satisfy:
1. Calibration within groups
2. Balance for the positive class: $E[S \mid Y=1, A=0] = E[S \mid Y=1, A=1]$
3. Balance for the negative class: $E[S \mid Y=0, A=0] = E[S \mid Y=0, A=1]$

### 8.3 Implications for the Scoring System

The scoring system is used for **self-selection** (deciding which opportunities to pursue), not for evaluating other people. This substantially changes the fairness calculus:

1. **No disparate impact concern** in the traditional sense — the system scores opportunities, not people
2. However, **structural bias can enter** through dimensions like `network_proximity` (which reflects existing social capital inequality) and `portal_friction` (which may correlate with employer accessibility practices)
3. **Mitigation:** Transparency in weight assignment, explicit tracking of outcomes by dimension, periodic weight recalibration based on observed prediction accuracy

**Reference:**
- Chouldechova, A. (2017). Fair prediction with disparate impact: A study of bias in recidivism prediction instruments. *Big Data*, 5(2), 153-163.
- Kleinberg, J., Mullainathan, S., & Raghavan, M. (2016). Inherent Trade-Offs in the Fair Determination of Risk Scores. *arXiv preprint* arXiv:1609.05807.
- Hardt, M., Price, E., & Srebro, N. (2016). Equality of opportunity in supervised learning. *Advances in Neural Information Processing Systems*, 29.

---

## 9. SYNTHESIS: MAPPING THEORY TO THE PIPELINE

### 9.1 The Scoring System as a WSM

The current 9-dimension weighted rubric is a Weighted Sum Model:

$$S_i = \sum_{j=1}^{9} w_j \cdot s_{ij}$$

where $w_j$ are from `scoring-rubric.yaml` (summing to 1.0) and $s_{ij} \in [1, 10]$.

**Theoretical justification:** By Dawes (1979), this linear composite will outperform unstructured judgment even with imperfect weights. By Keeney & Raiffa (1976), the additive form is valid if the 9 dimensions are mutually preferentially independent — a reasonable assumption since, e.g., `mission_alignment` can be assessed without knowing `portal_friction`.

### 9.2 The Threshold as a Reservation Wage

The 9.0 minimum threshold maps directly to McCall's reservation wage $\bar{w}$. The comparative statics predict that:
- With limited savings/runway: lower the threshold (more urgent)
- With generous runway: raise the threshold (more selective)
- In a volatile market with high variance: raise the threshold (option value increases)

### 9.3 The Application Cap as Portfolio Constraint

The max-10-active constraint functions as a portfolio diversification constraint. Markowitz theory suggests:
- Too concentrated (1-2 applications): idiosyncratic risk dominates
- Over-diversified (50+ applications): each gets insufficient effort, reducing edge
- The optimal number balances quality-per-application against total portfolio variance

The Kelly criterion further justifies concentration: if the "edge" (excess probability of acceptance over base rate) is proportional to effort invested, then allocating effort across too many applications dilutes each below the Kelly optimal fraction.

### 9.4 Network Proximity as Centrality Score

The `network_proximity` dimension can be formalized as:

$$NP_i = \begin{cases}
10 & \text{if direct referral from hiring manager} \\
8 & \text{if referral from current employee} \\
6 & \text{if 2nd-degree connection with introduction} \\
4 & \text{if shared community/event} \\
2 & \text{if cold application with alumni overlap} \\
1 & \text{if purely cold application}
\end{cases}$$

Weighted by freshness decay: $NP_i^{\text{adj}} = NP_i \cdot \text{freshness}(t_{\text{last\_contact}})$

### 9.5 The Precision-Over-Volume Decision as Signal Detection

The scoring system sets a high criterion $c > 0$ (conservative), optimizing for precision over recall. This is justified when:
- Base rate of good-fit opportunities is low (sparse signal environment)
- Cost of false alarm (wasted application effort) is high
- Cost of miss (foregone opportunity) is low relative to false alarm cost

The system's operating point on the ROC curve is in the high-specificity region, trading recall for precision.

---

## COMPLETE REFERENCE LIST

1. Bonacich, P. (1972). Factoring and weighting approaches to status scores and clique identification. *Journal of Mathematical Sociology*, 2(1), 113-120.
2. Brans, J. P. (1982). L'ingenierie de la decision. *Universite Laval, Quebec*.
3. Burt, R. S. (1992). *Structural Holes: The Social Structure of Competition*. Harvard University Press.
4. Chouldechova, A. (2017). Fair prediction with disparate impact. *Big Data*, 5(2), 153-163.
5. Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests. *Psychometrika*, 16(3), 297-334.
6. Dawes, R. M. (1979). The robust beauty of improper linear models in decision making. *American Psychologist*, 34(7), 571-582.
7. Ebbinghaus, H. (1885). *Uber das Gedachtnis*. Duncker & Humblot.
8. Ferguson, T. S. (1989). Who Solved the Secretary Problem? *Statistical Science*, 4(3), 282-296.
9. Freeman, L. C. (1979). Centrality in social networks: Conceptual clarification. *Social Networks*, 1(3), 215-239.
10. Granovetter, M. S. (1973). The Strength of Weak Ties. *American Journal of Sociology*, 78(6), 1360-1380.
11. Green, D. M., & Swets, J. A. (1966). *Signal Detection Theory and Psychophysics*. Wiley.
12. Hardt, M., Price, E., & Srebro, N. (2016). Equality of opportunity in supervised learning. *NeurIPS*, 29.
13. Hwang, C. L., & Yoon, K. (1981). *Multiple Attribute Decision Making*. Springer-Verlag.
14. Keeney, R. L., & Raiffa, H. (1976). *Decisions with Multiple Objectives*. Wiley/Cambridge UP.
15. Kelly, J. L. (1956). A New Interpretation of Information Rate. *Bell System Technical Journal*, 35(4), 917-926.
16. Kleinberg, J., Mullainathan, S., & Raghavan, M. (2016). Inherent Trade-Offs in the Fair Determination of Risk Scores. *arXiv:1609.05807*.
17. Lord, F. M. (1980). *Applications of Item Response Theory*. Erlbaum.
18. Macmillan, N. A., & Creelman, C. D. (2005). *Detection Theory: A User's Guide* (2nd ed.). Erlbaum.
19. Markowitz, H. (1952). Portfolio Selection. *The Journal of Finance*, 7(1), 77-91.
20. McCall, J. J. (1970). Economics of Information and Job Search. *Quarterly Journal of Economics*, 84(1), 113-126.
21. Messick, S. (1989). Validity. In R. L. Linn (Ed.), *Educational Measurement* (3rd ed.). Macmillan.
22. Mortensen, D. T. (1986). Job Search and Labor Market Analysis. *Handbook of Labor Economics*, Vol. 2.
23. Rajkumar, K., et al. (2022). A causal test of the strength of weak ties. *Science*, 377(6612), 1304-1310.
24. Roy, B. (1968). Classement et choix en presence de points de vue multiples. *RIRO*, 2(8), 57-75.
25. Saaty, T. L. (1980). *The Analytic Hierarchy Process*. McGraw-Hill.
26. Samejima, F. (1969). Estimation of latent ability using graded scores. *Psychometrika Monograph*, 17.
27. Thorp, E. O. (2006). The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market. *Handbook of Asset and Liability Management*.
28. Wixted, J. T. (2004). On common ground: Jost's (1897) law of forgetting. *Psychological Review*, 111(4), 864-879.
