#!/usr/bin/env python3
"""Inter-Rater Agreement (IRA) computation for diagnostic grade norming.

Computes ICC, Cohen's kappa, Fleiss kappa, and consensus scores from
multiple rater JSON files produced by diagnose.py --json.

Pure-stdlib implementation — no scipy or numpy dependency.

Usage:
    python scripts/diagnose_ira.py                # Auto-load ratings/*.json
    python scripts/diagnose_ira.py ratings/*.json
    python scripts/diagnose_ira.py ratings/*.json --consensus
    python scripts/diagnose_ira.py ratings/*.json --json
"""

import argparse
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Landis & Koch (1977) interpretation bands (default fallback)
DEFAULT_INTERPRETATION_BANDS = [
    (-1.0, 0.00, "poor"),
    (0.00, 0.20, "slight"),
    (0.20, 0.40, "fair"),
    (0.40, 0.60, "moderate"),
    (0.60, 0.80, "substantial"),
    (0.80, 1.01, "almost_perfect"),
]


def load_rubric_bands() -> list[tuple[float, float, str]]:
    """Load interpretation bands from the rubric YAML if available."""
    rubric_path = REPO_ROOT / "strategy" / "system-grading-rubric.yaml"
    if not rubric_path.is_file():
        return DEFAULT_INTERPRETATION_BANDS

    try:
        import yaml
        with open(rubric_path) as f:
            rubric = yaml.safe_load(f)
        bands_cfg = rubric.get("ira", {}).get("interpretation_bands", {})
        if not bands_cfg:
            return DEFAULT_INTERPRETATION_BANDS

        bands = []
        for label, range_list in bands_cfg.items():
            if isinstance(range_list, list) and len(range_list) == 2:
                bands.append((float(range_list[0]), float(range_list[1]), label))
        return sorted(bands, key=lambda x: x[0])
    except Exception:
        return DEFAULT_INTERPRETATION_BANDS


def interpret_agreement(value: float) -> str:
    """Map an agreement coefficient to interpretation band."""
    bands = load_rubric_bands()
    for low, high, label in bands:
        if low <= value <= high:
            return label
    if value >= 1.0:
        return bands[-1][2] if bands else "almost_perfect"
    return "poor"


# ---------------------------------------------------------------------------
# ICC(2,1) — Two-way random, absolute agreement
# ---------------------------------------------------------------------------

def compute_icc(ratings_matrix: list[list[float]]) -> float:
    """Compute ICC(2,1) — two-way random, single measures, absolute agreement.

    Args:
        ratings_matrix: n×k matrix where n=subjects (dimensions), k=raters.
            Each row is a dimension, each column is a rater's score.

    Returns:
        ICC value in [-1, 1]. Returns 0.0 for degenerate inputs.

    Uses two-way ANOVA decomposition:
        SSR = k × Σ(row_mean - grand_mean)²
        SSC = n × Σ(col_mean - grand_mean)²
        SSE = SST - SSR - SSC
        MSR = SSR / (n-1)
        MSC = SSC / (k-1)
        MSE = SSE / ((n-1)(k-1))
        ICC(2,1) = (MSR - MSE) / (MSR + (k-1)×MSE + k/n × (MSC - MSE))
    """
    n = len(ratings_matrix)
    if n < 2:
        return 0.0
    k = len(ratings_matrix[0])
    if k < 2:
        return 0.0

    # Validate all rows have same length
    for row in ratings_matrix:
        if len(row) != k:
            return 0.0

    # Grand mean
    all_values = [v for row in ratings_matrix for v in row]
    grand_mean = sum(all_values) / len(all_values)

    # Row means (per dimension)
    row_means = [sum(row) / k for row in ratings_matrix]

    # Column means (per rater)
    col_means = [sum(ratings_matrix[i][j] for i in range(n)) / n for j in range(k)]

    # Sum of squares
    ss_total = sum((v - grand_mean) ** 2 for v in all_values)
    ss_rows = k * sum((rm - grand_mean) ** 2 for rm in row_means)
    ss_cols = n * sum((cm - grand_mean) ** 2 for cm in col_means)
    ss_error = ss_total - ss_rows - ss_cols

    # Mean squares
    df_rows = n - 1
    df_cols = k - 1
    df_error = df_rows * df_cols

    if df_rows == 0 or df_cols == 0 or df_error == 0:
        return 0.0

    ms_rows = ss_rows / df_rows
    ms_cols = ss_cols / df_cols
    ms_error = ss_error / df_error

    # ICC(2,1) formula
    denominator = ms_rows + (k - 1) * ms_error + (k / n) * (ms_cols - ms_error)
    if abs(denominator) < 1e-10:
        return 0.0

    icc = (ms_rows - ms_error) / denominator
    return max(-1.0, min(1.0, icc))


# ---------------------------------------------------------------------------
# Cohen's kappa (pairwise, categorical)
# ---------------------------------------------------------------------------

def compute_cohens_kappa(rater1: list[str], rater2: list[str]) -> float:
    """Compute Cohen's kappa for two raters on categorical data.

    Args:
        rater1, rater2: Lists of category labels, same length.

    Returns:
        Kappa value. 1.0 = perfect agreement, 0.0 = chance agreement.
    """
    n = len(rater1)
    if n == 0 or len(rater2) != n:
        return 0.0

    # Observed agreement
    observed = sum(1 for a, b in zip(rater1, rater2) if a == b) / n

    # Expected agreement by chance
    categories = set(rater1) | set(rater2)
    expected = 0.0
    for cat in categories:
        p1 = sum(1 for x in rater1 if x == cat) / n
        p2 = sum(1 for x in rater2 if x == cat) / n
        expected += p1 * p2

    if abs(1.0 - expected) < 1e-10:
        return 1.0 if abs(observed - expected) < 1e-10 else 0.0

    return (observed - expected) / (1.0 - expected)


# ---------------------------------------------------------------------------
# Fleiss' kappa (3+ raters, categorical)
# ---------------------------------------------------------------------------

def compute_fleiss_kappa(ratings_matrix: list[list[str]]) -> float:
    """Compute Fleiss' kappa for 3+ raters on categorical data.

    Args:
        ratings_matrix: n×k matrix where n=subjects, k=raters.
            Each cell is a category label.

    Returns:
        Fleiss' kappa value.
    """
    n = len(ratings_matrix)
    if n == 0:
        return 0.0
    k = len(ratings_matrix[0])
    if k < 2:
        return 0.0

    # Collect all categories
    categories = sorted(set(c for row in ratings_matrix for c in row))
    num_cats = len(categories)
    if num_cats == 0:
        return 0.0
    cat_index = {c: i for i, c in enumerate(categories)}

    # Build count matrix: n_ij = number of raters who assigned subject i to category j
    count_matrix = []
    for row in ratings_matrix:
        counts = [0] * num_cats
        for val in row:
            counts[cat_index[val]] += 1
        count_matrix.append(counts)

    # P_i = proportion of agreeing pairs for subject i
    p_i_list = []
    for counts in count_matrix:
        sum_sq = sum(c * c for c in counts)
        p_i = (sum_sq - k) / (k * (k - 1)) if k > 1 else 0.0
        p_i_list.append(p_i)

    p_bar = sum(p_i_list) / n

    # p_j = proportion of all assignments to category j
    p_j_list = []
    total_assignments = n * k
    for j in range(num_cats):
        col_sum = sum(count_matrix[i][j] for i in range(n))
        p_j_list.append(col_sum / total_assignments)

    p_e = sum(pj * pj for pj in p_j_list)

    if abs(1.0 - p_e) < 1e-10:
        return 1.0 if abs(p_bar - p_e) < 1e-10 else 0.0

    return (p_bar - p_e) / (1.0 - p_e)


# ---------------------------------------------------------------------------
# Consensus and outlier detection
# ---------------------------------------------------------------------------

def compute_consensus(
    scores_per_dimension: dict[str, list[float]],
    iqr_factor: float = 1.5,
) -> dict[str, dict]:
    """Compute consensus values and flag outliers per dimension.

    Args:
        scores_per_dimension: {dimension_name: [score_per_rater]}
        iqr_factor: Multiplier for IQR-based outlier detection.

    Returns:
        {dimension: {consensus, median, q1, q3, iqr, outliers: [indices]}}
    """
    result = {}
    for dim, scores in scores_per_dimension.items():
        if not scores:
            result[dim] = {"consensus": None, "median": None, "outliers": []}
            continue

        sorted_s = sorted(scores)
        n = len(sorted_s)

        # Median
        if n % 2 == 1:
            median = sorted_s[n // 2]
        else:
            median = (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2

        # Quartiles (method of included median)
        lower = sorted_s[:n // 2]
        upper = sorted_s[(n + 1) // 2:]

        q1 = _median(lower) if lower else median
        q3 = _median(upper) if upper else median
        iqr = q3 - q1

        # Outlier detection
        low_bound = q1 - iqr_factor * iqr
        high_bound = q3 + iqr_factor * iqr
        outliers = [i for i, s in enumerate(scores) if s < low_bound or s > high_bound]

        result[dim] = {
            "consensus": round(median, 1),
            "median": round(median, 1),
            "q1": round(q1, 1),
            "q3": round(q3, 1),
            "iqr": round(iqr, 1),
            "outliers": outliers,
        }

    return result


def _median(values: list[float]) -> float:
    """Compute median of a sorted list."""
    n = len(values)
    if n == 0:
        return 0.0
    s = sorted(values)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


# ---------------------------------------------------------------------------
# Score binning (for kappa on continuous scores)
# ---------------------------------------------------------------------------

def bin_score(score: float) -> str:
    """Bin a continuous score into a categorical band based on rubric anchors.
    
    Anchors: 1 (critical), 3 (below_average), 5 (adequate), 7 (strong), 10 (exemplary)
    """
    if score < 2.0:
        return "critical"
    elif score < 4.0:
        return "below_average"
    elif score < 6.0:
        return "adequate"
    elif score < 8.5:
        return "strong"
    else:
        return "exemplary"


# ---------------------------------------------------------------------------
# Load rating files
# ---------------------------------------------------------------------------

def discover_rating_files(repo_root: Path = REPO_ROOT) -> list[str]:
    """Discover default rating JSON files from ratings/ directory."""
    ratings_dir = repo_root / "ratings"
    if not ratings_dir.is_dir():
        return []
    return [str(p) for p in sorted(ratings_dir.glob("*.json")) if p.is_file()]


def load_ratings(paths: list[str]) -> list[dict]:
    """Load rating JSON files."""
    ratings = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            print(f"Warning: {p} not found, skipping", file=sys.stderr)
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            if "dimensions" not in data:
                print(f"Warning: {p} missing 'dimensions', skipping", file=sys.stderr)
                continue
            ratings.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: {p} error: {e}", file=sys.stderr)
    return ratings


def extract_dimension_scores(ratings: list[dict]) -> tuple[list[str], dict[str, list[float]]]:
    """Extract per-dimension score lists and rater IDs from loaded ratings.

    Returns:
        (rater_ids, {dimension: [score_per_rater]})
    """
    rater_ids = [r.get("rater_id", f"rater-{i}") for i, r in enumerate(ratings)]

    # Collect all dimension keys
    all_dims = set()
    for r in ratings:
        all_dims.update(r["dimensions"].keys())

    scores_per_dim: dict[str, list[float]] = {}
    for dim in sorted(all_dims):
        scores = []
        for r in ratings:
            dim_data = r["dimensions"].get(dim, {})
            score = dim_data.get("score")
            if score is not None:
                scores.append(float(score))
        scores_per_dim[dim] = scores

    return rater_ids, scores_per_dim


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_ira_report(
    ratings: list[dict],
    show_consensus: bool = False,
) -> str:
    """Generate human-readable IRA report."""
    rater_ids, scores_per_dim = extract_dimension_scores(ratings)
    n_raters = len(ratings)

    lines = [
        "=" * 65,
        "  INTER-RATER AGREEMENT (IRA) REPORT",
        "=" * 65,
        "",
        f"  Raters ({n_raters}): {', '.join(rater_ids)}",
        "",
    ]

    # Build ratings matrix for overall ICC
    all_dims = sorted(scores_per_dim.keys())
    # Only include dimensions where all raters provided scores
    complete_dims = [d for d in all_dims if len(scores_per_dim[d]) == n_raters]

    if complete_dims and n_raters >= 2:
        # Per-dimension ICC using leave-one-out is not meaningful;
        # compute overall ICC across all dimensions
        matrix = [scores_per_dim[d] for d in complete_dims]
        overall_icc = compute_icc(matrix)
        band = interpret_agreement(overall_icc)

        lines.append(f"  Overall ICC(2,1): {overall_icc:.3f} ({band})")

        binned = [[bin_score(s) for s in scores_per_dim[d]] for d in complete_dims]
        if n_raters == 2:
            cohen = compute_cohens_kappa(
                [row[0] for row in binned],
                [row[1] for row in binned],
            )
            lines.append(f"  Cohen's kappa (binned): {cohen:.3f} ({interpret_agreement(cohen)})")
        elif n_raters >= 3:
            fleiss = compute_fleiss_kappa(binned)
            lines.append(f"  Fleiss' kappa (binned): {fleiss:.3f} ({interpret_agreement(fleiss)})")
        lines.append("")

    # Per-dimension table
    lines.append(f"  {'Dimension':<25s} {'Scores':>30s}  {'Range':>6s}  {'SD':>5s}")
    lines.append("  " + "-" * 70)

    divergent_dims = []
    for dim in all_dims:
        scores = scores_per_dim[dim]
        if not scores:
            continue
        score_str = ", ".join(f"{s:.1f}" for s in scores)
        rng = max(scores) - min(scores)
        mean = sum(scores) / len(scores)
        sd = math.sqrt(sum((s - mean) ** 2 for s in scores) / len(scores)) if len(scores) > 1 else 0.0

        lines.append(f"  {dim:<25s} {score_str:>30s}  {rng:>6.1f}  {sd:>5.2f}")

        if sd > 1.5:
            divergent_dims.append((dim, sd))

    lines.append("")

    # Outlier flags
    if divergent_dims:
        lines.append("  HIGH DIVERGENCE (SD > 1.5) — candidates for rubric refinement:")
        for dim, sd in sorted(divergent_dims, key=lambda x: -x[1]):
            # Find most divergent rater
            scores = scores_per_dim[dim]
            mean = sum(scores) / len(scores)
            max_dev_idx = max(range(len(scores)), key=lambda i: abs(scores[i] - mean))
            max_dev_rater = rater_ids[max_dev_idx] if max_dev_idx < len(rater_ids) else f"rater-{max_dev_idx}"
            lines.append(f"    {dim}: SD={sd:.2f}, most divergent: {max_dev_rater} ({scores[max_dev_idx]:.1f})")
        lines.append("")

    # Consensus
    if show_consensus:
        consensus = compute_consensus(scores_per_dim)
        lines.append("  CONSENSUS SCORES (median):")
        lines.append(f"  {'Dimension':<25s} {'Consensus':>10s}  {'IQR':>5s}  {'Outliers':>10s}")
        lines.append("  " + "-" * 55)
        for dim in all_dims:
            c = consensus.get(dim, {})
            con = c.get("consensus")
            iqr = c.get("iqr", 0)
            outlier_count = len(c.get("outliers", []))
            if con is not None:
                lines.append(f"  {dim:<25s} {con:>10.1f}  {iqr:>5.1f}  {outlier_count:>10d}")
        lines.append("")

    return "\n".join(lines)


def generate_json_report(ratings: list[dict], show_consensus: bool = False) -> dict:
    """Generate machine-readable IRA report."""
    rater_ids, scores_per_dim = extract_dimension_scores(ratings)
    n_raters = len(ratings)
    all_dims = sorted(scores_per_dim.keys())
    complete_dims = [d for d in all_dims if len(scores_per_dim[d]) == n_raters]

    overall_icc = 0.0
    categorical_agreement: dict | None = None
    if complete_dims and n_raters >= 2:
        matrix = [scores_per_dim[d] for d in complete_dims]
        overall_icc = compute_icc(matrix)
        binned = [[bin_score(s) for s in scores_per_dim[d]] for d in complete_dims]
        if n_raters == 2:
            value = compute_cohens_kappa(
                [row[0] for row in binned],
                [row[1] for row in binned],
            )
            categorical_agreement = {
                "method": "cohens_kappa",
                "value": round(value, 3),
                "interpretation": interpret_agreement(value),
            }
        elif n_raters >= 3:
            value = compute_fleiss_kappa(binned)
            categorical_agreement = {
                "method": "fleiss_kappa",
                "value": round(value, 3),
                "interpretation": interpret_agreement(value),
            }

    per_dim = {}
    for dim in all_dims:
        scores = scores_per_dim[dim]
        if not scores:
            continue
        mean = sum(scores) / len(scores)
        sd = math.sqrt(sum((s - mean) ** 2 for s in scores) / len(scores)) if len(scores) > 1 else 0.0
        per_dim[dim] = {
            "scores": scores,
            "mean": round(mean, 2),
            "sd": round(sd, 2),
            "range": round(max(scores) - min(scores), 1),
        }

    result = {
        "n_raters": n_raters,
        "rater_ids": rater_ids,
        "overall_icc": round(overall_icc, 3),
        "overall_interpretation": interpret_agreement(overall_icc),
        "dimensions": per_dim,
    }
    if categorical_agreement:
        result["categorical_agreement"] = categorical_agreement

    if show_consensus:
        result["consensus"] = compute_consensus(scores_per_dim)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Inter-Rater Agreement computation for diagnostic grade norming",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Rating JSON files from diagnose.py --json (defaults to ratings/*.json)",
    )
    parser.add_argument("--consensus", action="store_true", help="Include consensus scores")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    files = args.files or discover_rating_files()
    if not files:
        print("Error: provide at least 2 rating JSON files.", file=sys.stderr)
        print("Usage: python scripts/diagnose_ira.py ratings/*.json", file=sys.stderr)
        sys.exit(1)

    ratings = load_ratings(files)
    if len(ratings) < 2:
        print(f"Error: need ≥2 valid rating files, got {len(ratings)}.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        output = generate_json_report(ratings, show_consensus=args.consensus)
        print(json.dumps(output, indent=2))
    else:
        print(generate_ira_report(ratings, show_consensus=args.consensus))


if __name__ == "__main__":
    main()
