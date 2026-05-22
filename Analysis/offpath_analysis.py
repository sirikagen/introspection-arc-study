#!/usr/bin/env python3
"""
Analysis: Are off-path clicks meaningful or random?

For participants with complete=True solved attempts, this script tests whether
off-path steps reflect structured, purposeful behaviour or random noise using
three complementary lenses:

  1. Mistake type   – what proportion of errors are wrong-color (right cell,
                      wrong paint) vs wrong-coordinate (cell outside the
                      required-change set)?
  2. Color relevance – are the colors painted in off-path steps drawn from the
                      task's required solution palette, or are they arbitrary?
                      Compared against a per-task random baseline.
  3. Spatial proximity – are off-path clicks spatially close to required-change
                      cells, or scattered uniformly across the grid?
                      Compared against a per-task random baseline.
  4. Cross-puzzle consistency – does a participant's off-path rate stay stable
                      across puzzles (trait-like) or vary randomly (noise)?
                      Quantified via intraclass correlation (ICC).

Statistical tests: Wilcoxon signed-rank (paired observed vs. baseline),
Mann-Whitney U (high vs. low off-path groups), and ICC decomposition.

Outputs (written to Analysis/results/):
  offpath_step_metrics.csv           – per off-path step
  offpath_participant_task_metrics.csv  – per participant × task
  offpath_participant_summary.csv    – per participant aggregated
  offpath_analysis_report.md         – full narrative report
  offpath_analysis_plots.png         – four-panel figure
"""

from __future__ import annotations

import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from scipy import stats

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
SOLUTION_PATHS_JSON = ROOT / "high_click_viewer" / "data" / "solution_paths.json"
OUT_DIR = Path(__file__).resolve().parent / "results"
OUT_DIR.mkdir(exist_ok=True)


# ── Helpers ────────────────────────────────────────────────────────────────
def parse_int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        try:
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return -1


def manhattan(r1: int, c1: int, r2: int, c2: int) -> int:
    return abs(r1 - r2) + abs(c1 - c2)


def nearest_target_dist(row: int, col: int, target_cells: list[tuple[int, int]]) -> float:
    if not target_cells:
        return float("nan")
    return float(min(manhattan(row, col, tr, tc) for tr, tc in target_cells))


def random_baseline_dist(target_cells: list, grid_rows: int, grid_cols: int,
                          n_samples: int = 2000, seed: int = 42) -> float:
    """Mean distance to nearest target from a uniformly random cell in the grid."""
    if not target_cells or not grid_rows or not grid_cols:
        return float("nan")
    rng = random.Random(seed)
    return statistics.mean(
        nearest_target_dist(rng.randint(0, grid_rows - 1), rng.randint(0, grid_cols - 1), target_cells)
        for _ in range(n_samples)
    )


def extract_targets(changes_only: list) -> tuple[list[tuple[int, int]], set[int]]:
    """Return (list of (row, col) that need changing, set of required output colors)."""
    cells, colors = [], set()
    for r, row in enumerate(changes_only):
        for c, val in enumerate(row):
            if val is not None:
                cells.append((r, c))
                colors.add(int(val))
    return cells, colors


def reason_category(reason: str) -> str:
    r = reason.lower()
    if "wrong color" in r:
        return "wrong_color"
    if "wrong coordinate" in r:
        return "wrong_coordinate"
    if "missing" in r:
        return "missing_coord"
    return "other"


def icc_one_way(df: pd.DataFrame, group_col: str, value_col: str) -> float:
    """
    One-way random-effects ICC(1,1) — proportion of total variance
    attributable to between-group (between-participant) differences.
    ICC close to 1 → behaviour is consistent across tasks within a person.
    """
    groups = [grp[value_col].dropna().values for _, grp in df.groupby(group_col)
              if grp[value_col].dropna().shape[0] > 0]
    if len(groups) < 2:
        return float("nan")
    grand_mean = np.concatenate(groups).mean()
    k = np.mean([len(g) for g in groups])
    n = len(groups)
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    ss_within = sum(((g - g.mean()) ** 2).sum() for g in groups)
    total_obs = sum(len(g) for g in groups)
    ms_between = ss_between / (n - 1) if n > 1 else float("nan")
    ms_within = ss_within / (total_obs - n) if total_obs > n else float("nan")
    if math.isnan(ms_between) or math.isnan(ms_within) or ms_within == 0:
        return float("nan")
    icc = (ms_between - ms_within) / (ms_between + (k - 1) * ms_within)
    return float(icc)


# ── Load data ──────────────────────────────────────────────────────────────
print("Loading solution_paths.json …")
with SOLUTION_PATHS_JSON.open() as f:
    summary = json.load(f)

# ── Step-level and participant×task-level analysis ─────────────────────────
step_records: list[dict] = []
pt_records: list[dict] = []

for task in summary.get("tasks", []):
    task_type = task["task_type"]
    task_name = task["task_name"]

    for path in task.get("solution_paths", []):
        if not path.get("complete"):
            continue

        pid = path["participant_id"]
        off_path_steps = path.get("off_path_steps", [])
        n_off = len(off_path_steps)

        # Pull target info from the embedded changes_only of the first available step
        target_cells, required_colors, grid_rows, grid_cols = [], set(), 0, 0
        for step in off_path_steps:
            co = step.get("changes_only")
            if co:
                target_cells, required_colors = extract_targets(co)
                grid_rows = len(co)
                grid_cols = len(co[0]) if co else 0
                break

        rand_dist = random_baseline_dist(target_cells, grid_rows, grid_cols)
        rand_color = len(required_colors) / 9.0  # 9 non-zero colors (0 = background, rarely a target)

        edit_steps = [s for s in off_path_steps
                      if s.get("action") in ("edit", "floodfill")]
        n_edit = len(edit_steps)

        reason_counts: dict[str, int] = defaultdict(int)
        dist_vals: list[float] = []
        color_flags: list[int] = []

        for step in edit_steps:
            row = parse_int(step.get("action_x", -1))
            col = parse_int(step.get("action_y", -1))
            color = parse_int(step.get("selected_symbol", -1))
            rcat = reason_category(step.get("reason", ""))
            reason_counts[rcat] += 1

            dist = (nearest_target_dist(row, col, target_cells)
                    if row >= 0 and col >= 0 and target_cells else float("nan"))
            c_rel = (1 if color in required_colors else 0) if color >= 0 else float("nan")

            if not math.isnan(dist):
                dist_vals.append(dist)
            if not math.isnan(float(c_rel)) if not isinstance(c_rel, float) else not math.isnan(c_rel):
                color_flags.append(c_rel)

            step_records.append({
                "participant_id": pid,
                "task_name": task_name,
                "task_type": task_type,
                "action": step.get("action"),
                "row": row,
                "col": col,
                "color": color,
                "reason": step.get("reason", ""),
                "reason_cat": rcat,
                "dist_to_target": dist,
                "color_relevant": c_rel,
                "rand_baseline_dist": rand_dist,
                "rand_baseline_color": rand_color,
                "n_target_cells": len(target_cells),
                "grid_rows": grid_rows,
                "grid_cols": grid_cols,
            })

        mean_dist = statistics.mean(dist_vals) if dist_vals else float("nan")
        mean_color = statistics.mean(color_flags) if color_flags else float("nan")
        frac_wc = reason_counts["wrong_color"] / n_edit if n_edit else float("nan")
        frac_wco = reason_counts["wrong_coordinate"] / n_edit if n_edit else float("nan")

        pt_records.append({
            "participant_id": pid,
            "task_name": task_name,
            "task_type": task_type,
            "n_off_path": n_off,
            "n_edit_steps": n_edit,
            "n_target_cells": len(target_cells),
            "frac_wrong_color": frac_wc,
            "frac_wrong_coord": frac_wco,
            "mean_dist_to_target": mean_dist,
            "rand_baseline_dist": rand_dist,
            "dist_delta": (rand_dist - mean_dist
                           if not math.isnan(mean_dist) and not math.isnan(rand_dist)
                           else float("nan")),
            "color_relevance": mean_color,
            "rand_baseline_color": rand_color,
            "color_delta": (mean_color - rand_color
                            if not math.isnan(mean_color)
                            else float("nan")),
        })

step_df = pd.DataFrame(step_records)
pt_df = pd.DataFrame(pt_records)

# ── Participant-level aggregation ──────────────────────────────────────────
part_rows = []
for pid, grp in pt_df.groupby("participant_id"):
    total_off = grp["n_off_path"].sum()
    n_tasks = len(grp)
    eg = grp[grp["n_edit_steps"] > 0]
    part_rows.append({
        "participant_id": pid,
        "total_off_path_steps": int(total_off),
        "n_tasks_solved": int(n_tasks),
        "avg_off_path_per_task": total_off / n_tasks,
        "mean_dist_to_target": eg["mean_dist_to_target"].mean(),
        "mean_rand_baseline_dist": eg["rand_baseline_dist"].mean(),
        "mean_dist_delta": eg["dist_delta"].mean(),
        "mean_color_relevance": eg["color_relevance"].mean(),
        "mean_rand_baseline_color": eg["rand_baseline_color"].mean(),
        "mean_color_delta": eg["color_delta"].mean(),
        "mean_frac_wrong_color": eg["frac_wrong_color"].mean(),
        "mean_frac_wrong_coord": eg["frac_wrong_coord"].mean(),
    })

part_df = pd.DataFrame(part_rows).sort_values("total_off_path_steps", ascending=False).reset_index(drop=True)

# ── Statistical tests ──────────────────────────────────────────────────────
edit_df = step_df[step_df["action"].isin(["edit", "floodfill"])]

# 1. Color relevance vs. random baseline
color_deltas = part_df["mean_color_delta"].dropna().values
if len(color_deltas) >= 5:
    color_w, color_p = stats.wilcoxon(color_deltas)
else:
    color_w, color_p = float("nan"), float("nan")

# 2. Spatial proximity vs. random baseline
dist_deltas = part_df["mean_dist_delta"].dropna().values
if len(dist_deltas) >= 5:
    dist_w, dist_p = stats.wilcoxon(dist_deltas)
else:
    dist_w, dist_p = float("nan"), float("nan")

# 3. High vs. low off-path participants
median_off = part_df["total_off_path_steps"].median()
hi = part_df[part_df["total_off_path_steps"] > median_off]
lo = part_df[part_df["total_off_path_steps"] <= median_off]

def mw(col: str):
    a, b = hi[col].dropna().values, lo[col].dropna().values
    if len(a) < 3 or len(b) < 3:
        return float("nan"), float("nan")
    return stats.mannwhitneyu(a, b, alternative="two-sided")

mw_color_u, mw_color_p = mw("mean_color_delta")
mw_dist_u, mw_dist_p = mw("mean_dist_delta")
mw_fwc_u, mw_fwc_p = mw("mean_frac_wrong_color")

# 4. ICC — cross-puzzle consistency of off-path rate
# Normalise by number of target cells to make tasks comparable
pt_df["off_path_rate"] = pt_df["n_off_path"] / pt_df["n_target_cells"].replace(0, float("nan"))
icc_val = icc_one_way(pt_df.dropna(subset=["off_path_rate"]), "participant_id", "off_path_rate")

# ── Shared plot colours / formatting helpers ───────────────────────────────
ACCENT = "#d3542a"
GRAY   = "#aaaaaa"

def fmt_p(p):
    if isinstance(p, float) and math.isnan(p):
        return "n/a"
    if p < 0.001:
        return "< 0.001"
    return f"{p:.4f}"

# ── Task-type breakdown (training vs. evaluation) ─────────────────────────
def compute_type_stats(sub_pt, sub_step):
    sub_edit = sub_step[sub_step["action"].isin(["edit", "floodfill"])]
    pid_cd, pid_dd = [], []
    for pid, grp in sub_pt.groupby("participant_id"):
        eg = grp[grp["n_edit_steps"] > 0]
        if len(eg):
            v_c = eg["color_delta"].mean()
            v_d = eg["dist_delta"].mean()
            if not math.isnan(v_c): pid_cd.append(v_c)
            if not math.isnan(v_d): pid_dd.append(v_d)
    w_c, p_c = stats.wilcoxon(pid_cd) if len(pid_cd) >= 5 else (np.nan, np.nan)
    w_d, p_d = stats.wilcoxon(pid_dd) if len(pid_dd) >= 5 else (np.nan, np.nan)
    rc = sub_edit["reason_cat"].value_counts()
    rc_pct = (rc / rc.sum() * 100).round(1) if len(rc) > 0 else pd.Series(dtype=float)
    sub_pt2 = sub_pt.copy()
    sub_pt2["off_path_rate"] = sub_pt2["n_off_path"] / sub_pt2["n_target_cells"].replace(0, np.nan)
    icc = icc_one_way(sub_pt2.dropna(subset=["off_path_rate"]), "participant_id", "off_path_rate")
    return {
        "n_participants": sub_pt["participant_id"].nunique(),
        "n_edit_steps": len(sub_edit),
        "total_off_path": int(sub_pt["n_off_path"].sum()),
        "obs_color": float(sub_edit["color_relevant"].dropna().mean()) if len(sub_edit) else np.nan,
        "base_color": float(sub_edit["rand_baseline_color"].dropna().mean()) if len(sub_edit) else np.nan,
        "mean_color_delta": float(np.mean(pid_cd)) if pid_cd else np.nan,
        "color_p": float(p_c),
        "mean_dist_delta": float(np.mean(pid_dd)) if pid_dd else np.nan,
        "dist_p": float(p_d),
        "pct_wrong_color": float(rc_pct.get("wrong_color", 0.0)),
        "pct_wrong_coord": float(rc_pct.get("wrong_coordinate", 0.0)),
        "icc": float(icc) if not math.isnan(icc) else np.nan,
    }

tt_stats = {}
for tt in ["training", "evaluation"]:
    tt_stats[tt] = compute_type_stats(pt_df[pt_df["task_type"] == tt],
                                       step_df[step_df["task_type"] == tt])
    s = tt_stats[tt]
    print(f"\n[{tt}] n_steps={s['n_edit_steps']}  "
          f"color_Δ={s['mean_color_delta']:.3f} (p={fmt_p(s['color_p'])})  "
          f"dist_Δ={s['mean_dist_delta']:.3f} (p={fmt_p(s['dist_p'])})  "
          f"ICC={s['icc']:.3f}  wrong_color={s['pct_wrong_color']:.1f}%")

# Comparison figure
fig2, axes2 = plt.subplots(1, 4, figsize=(18, 5))
fig2.patch.set_facecolor("#f5efe6")
labels = ["Training", "Evaluation"]
colors_tt = ["#0a84ff", "#d3542a"]
for ax in axes2:
    ax.set_facecolor("#f5efe6")
    for sp in ax.spines.values():
        sp.set_visible(False)

# Panel 1: colour delta
vals_c = [tt_stats[tt]["mean_color_delta"] for tt in ["training", "evaluation"]]
bars = axes2[0].bar(labels, vals_c, color=colors_tt, width=0.5, edgecolor="white")
axes2[0].axhline(0, color="black", linewidth=0.8, linestyle="--")
axes2[0].set_ylabel("Mean colour Δ (observed − baseline)")
axes2[0].set_title("A  Colour relevance above chance", fontweight="bold", loc="left")
for bar, p_val in zip(bars, [tt_stats[tt]["color_p"] for tt in ["training", "evaluation"]]):
    sig = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else ("*" if p_val < 0.05 else "ns"))
    axes2[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005, sig,
                  ha="center", va="bottom", fontsize=11, fontweight="bold")

# Panel 2: distance delta
vals_d = [tt_stats[tt]["mean_dist_delta"] for tt in ["training", "evaluation"]]
bars2 = axes2[1].bar(labels, vals_d, color=colors_tt, width=0.5, edgecolor="white")
axes2[1].axhline(0, color="black", linewidth=0.8, linestyle="--")
axes2[1].set_ylabel("Mean distance Δ (baseline − observed, cells)")
axes2[1].set_title("B  Spatial proximity above chance", fontweight="bold", loc="left")
for bar, p_val in zip(bars2, [tt_stats[tt]["dist_p"] for tt in ["training", "evaluation"]]):
    sig = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else ("*" if p_val < 0.05 else "ns"))
    axes2[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, sig,
                  ha="center", va="bottom", fontsize=11, fontweight="bold")

# Panel 3: mistake type breakdown
x3 = np.arange(2)
wc_vals = [tt_stats[tt]["pct_wrong_color"] for tt in ["training", "evaluation"]]
wco_vals = [tt_stats[tt]["pct_wrong_coord"] for tt in ["training", "evaluation"]]
axes2[2].bar(labels, wc_vals, color=ACCENT, label="Wrong color", width=0.5)
axes2[2].bar(labels, wco_vals, bottom=wc_vals, color="#7fdbff", label="Wrong coord", width=0.5)
axes2[2].set_ylabel("% of off-path edit steps")
axes2[2].set_ylim(0, 105)
axes2[2].set_title("C  Mistake type distribution", fontweight="bold", loc="left")
axes2[2].legend(fontsize=9)

# Panel 4: ICC
icc_vals = [tt_stats[tt]["icc"] for tt in ["training", "evaluation"]]
axes2[3].bar(labels, icc_vals, color=colors_tt, width=0.5, edgecolor="white")
axes2[3].axhline(0, color="black", linewidth=0.8, linestyle="--")
axes2[3].set_ylabel("ICC(1,1) — cross-puzzle consistency")
axes2[3].set_title("D  Cross-puzzle consistency (ICC)", fontweight="bold", loc="left")

fig2.suptitle("Off-path analysis: training vs. evaluation tasks",
              fontsize=13, fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(OUT_DIR / "offpath_tasktype_comparison.png", dpi=150, bbox_inches="tight",
            facecolor=fig2.get_facecolor())
plt.close()
print("  → offpath_tasktype_comparison.png written")

# ── Save CSVs ──────────────────────────────────────────────────────────────
step_df.to_csv(OUT_DIR / "offpath_step_metrics.csv", index=False)
pt_df.to_csv(OUT_DIR / "offpath_participant_task_metrics.csv", index=False)
part_df.to_csv(OUT_DIR / "offpath_participant_summary.csv", index=False)
print("CSVs saved.")

# ── Plots ──────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 12))
fig.patch.set_facecolor("#f5efe6")
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

# Panel A: distribution of off-path steps per participant
ax_a = fig.add_subplot(gs[0, 0])
ax_a.set_facecolor("#f5efe6")
vals = part_df["total_off_path_steps"].values
ax_a.hist(vals, bins=30, color=ACCENT, edgecolor="white", linewidth=0.5)
ax_a.axvline(np.median(vals), color="black", linestyle="--", linewidth=1.2,
             label=f"Median = {np.median(vals):.0f}")
ax_a.set_xlabel("Total off-path steps")
ax_a.set_ylabel("Number of participants")
ax_a.set_title("A  Distribution of off-path steps", fontweight="bold", loc="left")
ax_a.legend(fontsize=9)
for spine in ax_a.spines.values():
    spine.set_visible(False)

# Panel B: reason distribution (stacked bar for top-20 participants by off-path count)
ax_b = fig.add_subplot(gs[0, 1])
ax_b.set_facecolor("#f5efe6")
top20 = part_df.head(20)
x = np.arange(len(top20))
wc = top20["mean_frac_wrong_color"].fillna(0).values
wco = top20["mean_frac_wrong_coord"].fillna(0).values
other = np.clip(1.0 - wc - wco, 0, 1)
ax_b.bar(x, wc, color=ACCENT, label="Wrong color (right cell)")
ax_b.bar(x, wco, bottom=wc, color="#7fdbff", label="Wrong coordinate")
ax_b.bar(x, other, bottom=wc + wco, color=GRAY, alpha=0.6, label="Other")
ax_b.set_xticks(x)
ax_b.set_xticklabels([f"#{i+1}" for i in range(len(top20))], fontsize=7, rotation=45)
ax_b.set_ylabel("Fraction of off-path edit steps")
ax_b.set_title("B  Mistake types — top 20 off-path participants", fontweight="bold", loc="left")
ax_b.legend(fontsize=8, loc="upper right")
for spine in ax_b.spines.values():
    spine.set_visible(False)

# Panel C: color_delta by participant (observed – baseline color relevance)
ax_c = fig.add_subplot(gs[1, 0])
ax_c.set_facecolor("#f5efe6")
cd = part_df["mean_color_delta"].dropna().values
ax_c.hist(cd, bins=25, color=ACCENT, edgecolor="white", linewidth=0.5)
ax_c.axvline(0, color="black", linestyle="--", linewidth=1.2, label="Random baseline (0)")
ax_c.axvline(cd.mean(), color="#2ecc40", linestyle="-", linewidth=1.5,
             label=f"Mean Δ = {cd.mean():+.3f}")
pstr = f"p = {color_p:.4f}" if not math.isnan(color_p) else "p = n/a"
ax_c.set_xlabel("Color relevance (observed − baseline)")
ax_c.set_ylabel("Number of participants")
ax_c.set_title(f"C  Color relevance above chance  [{pstr}]", fontweight="bold", loc="left")
ax_c.legend(fontsize=9)
for spine in ax_c.spines.values():
    spine.set_visible(False)

# Panel D: dist_delta (random baseline – observed distance)
ax_d = fig.add_subplot(gs[1, 1])
ax_d.set_facecolor("#f5efe6")
dd = part_df["mean_dist_delta"].dropna().values
ax_d.hist(dd, bins=25, color=ACCENT, edgecolor="white", linewidth=0.5)
ax_d.axvline(0, color="black", linestyle="--", linewidth=1.2, label="No spatial bias (0)")
ax_d.axvline(dd.mean(), color="#2ecc40", linestyle="-", linewidth=1.5,
             label=f"Mean Δ = {dd.mean():+.2f}")
pstr_d = f"p = {dist_p:.4f}" if not math.isnan(dist_p) else "p = n/a"
ax_d.set_xlabel("Distance delta (baseline − observed)")
ax_d.set_ylabel("Number of participants")
ax_d.set_title(f"D  Spatial proximity above chance  [{pstr_d}]", fontweight="bold", loc="left")
ax_d.legend(fontsize=9)
for spine in ax_d.spines.values():
    spine.set_visible(False)

fig.suptitle("Off-path click analysis: meaningful vs. random behaviour",
             fontsize=14, fontweight="bold", y=0.98)

plt.savefig(OUT_DIR / "offpath_analysis_plots.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
plt.close()
print("Plots saved.")

# ── Write report ────────────────────────────────────────────────────────────
def fmt(v, dec=3):
    return f"{v:.{dec}f}" if not (isinstance(v, float) and math.isnan(v)) else "n/a"

n_participants = len(part_df)
n_with_offpath = (part_df["total_off_path_steps"] > 0).sum()
total_steps = len(step_df)
total_edit = len(edit_df)

rc = step_df["reason_cat"].value_counts()
rc_pct = (rc / rc.sum() * 100).round(1)

obs_color = edit_df["color_relevant"].dropna().mean()
base_color = edit_df["rand_baseline_color"].dropna().mean()

valid_dist = part_df.dropna(subset=["mean_dist_to_target", "mean_rand_baseline_dist"])
obs_dist_mean = valid_dist["mean_dist_to_target"].mean()
base_dist_mean = valid_dist["mean_rand_baseline_dist"].mean()

lines = [
    "# Off-path click analysis: meaningful vs. random behaviour",
    "",
    "## 1. Overview",
    "",
    f"| | |",
    f"|---|---|",
    f"| Participants (complete = true) | {n_participants} |",
    f"| Participants with ≥ 1 off-path step | {n_with_offpath} |",
    f"| Total off-path steps | {total_steps} |",
    f"| Edit / floodfill steps (position + color analysable) | {total_edit} |",
    f"| Median off-path steps per participant | {fmt(float(np.median(part_df['total_off_path_steps'])), 0)} |",
    f"| Max off-path steps (single participant) | {int(part_df['total_off_path_steps'].max())} |",
    "",
    "---",
    "",
    "## 2. Mistake type distribution",
    "",
    "Off-path steps fall into two main categories:",
    "",
    "- **Wrong color** — the participant clicked on a cell that *does* need to change, "
    "but applied the wrong colour. This indicates spatial awareness (they found the right cell) "
    "but an incorrect colour hypothesis.",
    "- **Wrong coordinate** — the participant painted a cell that is *not* in the required-change "
    "set. This could reflect exploratory behaviour, misidentifying the pattern, or fidgeting.",
    "",
    "| Reason category | Count | % of edit steps |",
    "|-----------------|-------|-----------------|",
]
for cat in ["wrong_color", "wrong_coordinate", "missing_coord", "other"]:
    cnt = rc.get(cat, 0)
    pct = rc_pct.get(cat, 0.0)
    lines.append(f"| {cat} | {cnt} | {pct}% |")

dominant = rc_pct.idxmax() if len(rc_pct) > 0 else "unknown"
lines += [
    "",
    f"The dominant error type is **{dominant}** ({rc_pct.get(dominant, 0):.1f}% of edit steps).",
    "",
    "---",
    "",
    "## 3. Color relevance — are participants using solution colours?",
    "",
    "For each off-path edit step, we test whether the colour painted is one of the "
    "colours required in the task's solved output (i.e., a colour that *should* appear "
    "somewhere in the grid). We compare this against a per-task random baseline "
    "(expected fraction if the participant sampled uniformly from the 9 non-background colours).",
    "",
    f"| Metric | Value |",
    f"|--------|-------|",
    f"| Mean observed colour relevance | {fmt(obs_color)} |",
    f"| Mean random baseline | {fmt(base_color)} |",
    f"| Mean delta (observed − baseline) | {fmt(obs_color - base_color):} |",
    f"| Wilcoxon W (per-participant deltas vs. 0) | {fmt(color_w, 1)} |",
    f"| p-value | {fmt_p(color_p)} |",
    "",
]

if not math.isnan(color_p):
    if color_p < 0.05 and obs_color > base_color:
        lines.append(
            "**Interpretation:** Off-path steps use solution-relevant colours significantly "
            "more than chance would predict. Even when making a mistake, participants are "
            "drawing from the correct colour palette — a hallmark of purposeful, informed behaviour."
        )
    elif color_p < 0.05 and obs_color < base_color:
        lines.append(
            "**Interpretation:** Off-path steps use solution-relevant colours significantly "
            "*less* than chance. Participants are frequently applying colours that have no role "
            "in the solution, suggesting exploratory or random colour selection."
        )
    else:
        lines.append(
            "**Interpretation:** Colour choice in off-path steps does not differ significantly "
            "from random selection. Participants are not systematically drawing on solution-relevant colours."
        )

lines += [
    "",
    "---",
    "",
    "## 4. Spatial proximity — are off-path clicks near required-change cells?",
    "",
    "For each off-path edit step, we compute the Manhattan distance from the clicked cell "
    "to the nearest required-change cell. A per-task random baseline is estimated by "
    "sampling 2,000 uniformly random cells from the same grid and averaging their distances "
    "to the nearest target cell. **A positive delta means off-path clicks are closer to "
    "target cells than random placement.**",
    "",
    f"| Metric | Value |",
    f"|--------|-------|",
    f"| Mean observed distance to nearest target cell | {fmt(obs_dist_mean, 2)} grid cells |",
    f"| Mean random baseline distance | {fmt(base_dist_mean, 2)} grid cells |",
    f"| Mean delta (baseline − observed) | {fmt(base_dist_mean - obs_dist_mean, 2)} |",
    f"| Wilcoxon W (per-participant deltas vs. 0) | {fmt(dist_w, 1)} |",
    f"| p-value | {fmt_p(dist_p)} |",
    "",
]

if not math.isnan(dist_p):
    delta_d = base_dist_mean - obs_dist_mean
    if dist_p < 0.05 and delta_d > 0:
        lines.append(
            "**Interpretation:** Off-path clicks are significantly closer to required-change "
            "cells than a uniformly random placement would predict. Participants are working "
            "in the right spatial neighbourhood — their mistakes are not scattered randomly "
            "across the grid."
        )
    elif dist_p < 0.05 and delta_d < 0:
        lines.append(
            "**Interpretation:** Off-path clicks are significantly *farther* from required-change "
            "cells than random — participants appear to be clicking away from the target region."
        )
    else:
        lines.append(
            "**Interpretation:** Spatial proximity of off-path clicks does not differ "
            "significantly from random placement."
        )

lines += [
    "",
    "---",
    "",
    "## 5. High vs. low off-path participants",
    "",
    f"Participants split at median total off-path steps ({median_off:.0f}):",
    f"- **High off-path group**: {len(hi)} participants",
    f"- **Low off-path group**: {len(lo)} participants",
    "",
    "| Metric | High off-path | Low off-path | Mann-Whitney U | p |",
    "|--------|--------------|-------------|----------------|---|",
]

for label, col, u_val, p_val in [
    ("Mean colour Δ", "mean_color_delta", mw_color_u, mw_color_p),
    ("Mean distance Δ", "mean_dist_delta", mw_dist_u, mw_dist_p),
    ("Frac wrong-color", "mean_frac_wrong_color", mw_fwc_u, mw_fwc_p),
]:
    h_m = fmt(hi[col].dropna().mean())
    l_m = fmt(lo[col].dropna().mean())
    lines.append(f"| {label} | {h_m} | {l_m} | {fmt(u_val, 1)} | {fmt_p(p_val)} |")

lines += [
    "",
    "**Interpretation:** If high off-path participants show higher colour deltas and "
    "distance deltas than low off-path participants, their extra clicks reflect the same "
    "purposeful (if imprecise) strategy — they are not simply adding random noise.",
    "",
    "---",
    "",
    "## 6. Cross-puzzle consistency (ICC)",
    "",
    "The intraclass correlation coefficient (one-way random effects, ICC(1,1)) partitions "
    "variance in off-path rate (off-path steps / required-change cells) into between-participant "
    "and within-participant components.",
    "",
    f"| Metric | Value |",
    f"|--------|-------|",
    f"| ICC(1,1) | {fmt(icc_val)} |",
    "",
]

if not math.isnan(icc_val):
    if icc_val > 0.5:
        lines.append(
            f"**Interpretation:** ICC = {icc_val:.3f} indicates **strong** between-participant "
            "consistency. Off-path rate is a stable individual trait — participants who deviate "
            "frequently on one puzzle tend to deviate frequently on others. This is inconsistent "
            "with pure task-by-task random noise."
        )
    elif icc_val > 0.2:
        lines.append(
            f"**Interpretation:** ICC = {icc_val:.3f} indicates **moderate** between-participant "
            "consistency. There is a detectable individual-differences component to off-path behaviour, "
            "though a sizeable proportion of variance is task-specific."
        )
    else:
        lines.append(
            f"**Interpretation:** ICC = {icc_val:.3f} indicates **low** between-participant "
            "consistency. Off-path behaviour varies considerably across puzzles within participants, "
            "suggesting task difficulty or puzzle-specific features drive deviations more than "
            "individual style."
        )

lines += [
    "",
    "---",
    "",
    "## 7. Top participants by total off-path steps",
    "",
    "| Rank | Participant ID | Total off-path | Tasks | Avg/task | "
    "Colour Δ | Dist Δ | % wrong-color | % wrong-coord |",
    "|------|---------------|----------------|-------|----------|"
    "---------|--------|--------------|--------------|",
]

for i, row in part_df.head(20).iterrows():
    pid_short = str(row["participant_id"])[:16] + "…"
    lines.append(
        f"| {i+1} | `{pid_short}` | {int(row['total_off_path_steps'])} | "
        f"{int(row['n_tasks_solved'])} | {row['avg_off_path_per_task']:.1f} | "
        f"{fmt(row['mean_color_delta'])} | {fmt(row['mean_dist_delta'], 2)} | "
        f"{row['mean_frac_wrong_color']*100:.0f}% | {row['mean_frac_wrong_coord']*100:.0f}% |"
    )

lines += [
    "",
    "---",
    "",
    "## 8. Summary",
    "",
]

summary_points = []
if not math.isnan(color_p):
    direction = "above" if obs_color > base_color else "below"
    sig = "significantly" if color_p < 0.05 else "not significantly"
    summary_points.append(
        f"**Colour relevance** is {sig} {direction} the random baseline "
        f"(Δ = {obs_color - base_color:+.3f}, p = {fmt_p(color_p)})."
    )
if not math.isnan(dist_p):
    direction = "closer to" if base_dist_mean > obs_dist_mean else "farther from"
    sig = "significantly" if dist_p < 0.05 else "not significantly"
    summary_points.append(
        f"**Spatial proximity**: off-path clicks are {sig} {direction} target cells "
        f"than random (Δ = {base_dist_mean - obs_dist_mean:+.2f} cells, p = {fmt_p(dist_p)})."
    )
if not math.isnan(icc_val):
    consistency = "strong" if icc_val > 0.5 else ("moderate" if icc_val > 0.2 else "low")
    summary_points.append(
        f"**Cross-puzzle consistency** is {consistency} (ICC = {icc_val:.3f}), "
        + ("suggesting off-path behaviour is a stable individual trait."
           if icc_val > 0.2
           else "suggesting off-path behaviour varies primarily by task.")
    )

dominant_pct = rc_pct.get(dominant, 0)
summary_points.append(
    f"The dominant error type is **{dominant}** ({dominant_pct:.1f}% of edit steps), "
    + ("indicating participants generally identify the correct cells but struggle with "
       "colour selection." if dominant == "wrong_color"
       else "indicating participants frequently paint cells outside the required-change set.")
)

for pt in summary_points:
    lines.append(f"- {pt}")

lines += [
    "",
    "---",
    "",
    "## 9. Training vs. evaluation task breakdown",
    "",
    "All key metrics were re-computed separately for training and evaluation task types.",
    "",
    "| Metric | Training | Evaluation |",
    "|--------|----------|------------|",
    f"| Participants with off-path steps | {tt_stats['training']['n_participants']} | {tt_stats['evaluation']['n_participants']} |",
    f"| Total off-path edit steps | {tt_stats['training']['n_edit_steps']} | {tt_stats['evaluation']['n_edit_steps']} |",
    f"| Mean colour relevance (observed) | {fmt(tt_stats['training']['obs_color'])} | {fmt(tt_stats['evaluation']['obs_color'])} |",
    f"| Mean colour Δ (observed − baseline) | {fmt(tt_stats['training']['mean_color_delta'])} | {fmt(tt_stats['evaluation']['mean_color_delta'])} |",
    f"| Colour relevance Wilcoxon p | {fmt_p(tt_stats['training']['color_p'])} | {fmt_p(tt_stats['evaluation']['color_p'])} |",
    f"| Mean distance to nearest target (cells) | see dist_delta | see dist_delta |",
    f"| Mean spatial proximity Δ | {fmt(tt_stats['training']['mean_dist_delta'], 2)} | {fmt(tt_stats['evaluation']['mean_dist_delta'], 2)} |",
    f"| Spatial proximity Wilcoxon p | {fmt_p(tt_stats['training']['dist_p'])} | {fmt_p(tt_stats['evaluation']['dist_p'])} |",
    f"| % wrong-color errors | {tt_stats['training']['pct_wrong_color']:.1f}% | {tt_stats['evaluation']['pct_wrong_color']:.1f}% |",
    f"| % wrong-coordinate errors | {tt_stats['training']['pct_wrong_coord']:.1f}% | {tt_stats['evaluation']['pct_wrong_coord']:.1f}% |",
    f"| ICC(1,1) cross-puzzle consistency | {fmt(tt_stats['training']['icc'])} | {fmt(tt_stats['evaluation']['icc'])} |",
    "",
    "Comparison figure saved to `offpath_tasktype_comparison.png`.",
]

report_text = "\n".join(lines)
(OUT_DIR / "offpath_analysis_report.md").write_text(report_text, encoding="utf-8")
print("\n" + report_text)
print(f"\nAll outputs written to {OUT_DIR}")
