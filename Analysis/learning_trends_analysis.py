#!/usr/bin/env python3
"""
Three-part analysis:

  Part 1 – 95th-percentile high-click participants
            (summary_data.csv, solved=True & complete=True)

  Part 2 – Learning-curve trends across attempts
            (summary_data.csv for counts, data.csv for action types)
            Examines both within-task (attempt 1→2→…) and
            across-task (task 1→2→…) trajectories.

  Part 3 – Materials & Methods narrative (written to a .md file)

Outputs (Analysis/results/):
  p95_high_clickers.csv / .md       – ranked 95th-pct participants
  learning_trends_report.md         – full trend analysis narrative
  learning_trends_plots.png         – figure panels
  materials_and_methods.md          – full M&M section
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats
from scipy.stats import spearmanr, mannwhitneyu

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
SUMMARY_CSV  = ROOT / "Data files" / "summary_data.csv"
DATA_CSV     = ROOT / "Data files" / "data.csv"
OUT_DIR      = Path(__file__).resolve().parent / "results"
OUT_DIR.mkdir(exist_ok=True)

ACCENT  = "#d3542a"
BLUE    = "#0a84ff"
GREEN   = "#2ecc40"
GRAY    = "#aaaaaa"
BG      = "#f5efe6"

# ══════════════════════════════════════════════════════════════════════════
# PART 1 — 95th-percentile high-click participants
# ══════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("PART 1 — 95th-percentile high-click participants")
print("=" * 60)

summary = pd.read_csv(SUMMARY_CSV)
# Normalise boolean columns that may be string "true"/"false"
for col in ("solved", "complete"):
    if summary[col].dtype == object:
        summary[col] = summary[col].str.lower() == "true"

filtered = summary[summary["solved"] & summary["complete"]].copy()
print(f"Rows after filtering (solved=True, complete=True): {len(filtered):,}")

# Participant-level aggregate: mean num_actions across their qualifying attempts
part_stats = (
    filtered.groupby("hashed_id")
    .agg(
        mean_num_actions   = ("num_actions", "mean"),
        total_num_actions  = ("num_actions", "sum"),
        n_attempts         = ("num_actions", "count"),
        n_tasks            = ("task_name",   "nunique"),
    )
    .reset_index()
)

p90_threshold = np.percentile(part_stats["mean_num_actions"], 95)
print(f"95th-percentile threshold (mean_num_actions): {p90_threshold:.1f}")

p90_df = (
    part_stats[
        (part_stats["mean_num_actions"] >= p90_threshold) &
        (part_stats["n_tasks"] >= 4)
    ]
    .sort_values("mean_num_actions", ascending=False)
    .reset_index(drop=True)
)
p90_df.index += 1  # 1-based rank
p90_df.index.name = "rank"

print(f"Participants at or above 95th percentile (≥4 tasks): {len(p90_df)}")

p90_df.to_csv(OUT_DIR / "p95_high_clickers.csv")

# Markdown document
p90_lines = [
    "# 95th-Percentile High-Click Participants",
    "",
    f"Filter: `solved = true` AND `complete = true`  ",
    f"Metric: mean `num_actions` across qualifying attempts  ",
    f"95th-percentile threshold: **{p90_threshold:.1f} actions**  ",
    f"Participants listed: **{len(p90_df)}**",
    "",
    "| Rank | Participant ID | Mean actions | Total actions | Qualifying attempts | Tasks |",
    "|------|---------------|-------------|--------------|--------------------|----|",
]
for rank, row in p90_df.iterrows():
    p90_lines.append(
        f"| {rank} | `{row['hashed_id']}` | {row['mean_num_actions']:.1f} | "
        f"{int(row['total_num_actions'])} | {int(row['n_attempts'])} | {int(row['n_tasks'])} |"
    )

(OUT_DIR / "p95_high_clickers.md").write_text("\n".join(p90_lines), encoding="utf-8")
print("  → p95_high_clickers.csv / .md written")

# ══════════════════════════════════════════════════════════════════════════
# PART 2 — Learning-curve trend analysis
# ══════════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("PART 2 — Learning-curve trend analysis")
print("=" * 60)

# ── 2a. Within-task trends (attempt_number) from summary_data ─────────────
# Use all complete rows (not just solved) so we see the full attempt arc.
within = summary[summary["complete"]].copy()

# Keep participants who have ≥ 2 attempts on at least one task
multi_attempt = (
    within.groupby(["hashed_id", "task_name"])
    .filter(lambda g: len(g) >= 2)
)
print(f"\nWithin-task analysis: {len(multi_attempt):,} rows "
      f"({multi_attempt['hashed_id'].nunique()} participants, "
      f"{multi_attempt.groupby(['hashed_id','task_name']).ngroups} participant-task pairs with ≥2 attempts)")

# Mean num_actions by attempt_number (across all participants & tasks)
within_mean = (
    multi_attempt.groupby("attempt_number")["num_actions"]
    .agg(["mean", "median", "sem", "count"])
    .reset_index()
    .rename(columns={"mean": "mean_actions", "median": "median_actions",
                     "sem": "sem_actions", "count": "n"})
)
# Restrict to attempt numbers with enough data
within_mean = within_mean[within_mean["n"] >= 20]
print("\nMean num_actions by attempt_number:")
print(within_mean[["attempt_number", "mean_actions", "median_actions", "n"]].to_string(index=False))

# Solve rate by attempt_number
solve_rate = (
    multi_attempt.groupby("attempt_number")["solved"]
    .mean()
    .reset_index()
    .rename(columns={"solved": "solve_rate"})
)
solve_rate = solve_rate[solve_rate["attempt_number"].isin(within_mean["attempt_number"])]

# Spearman correlation: attempt_number vs mean_actions
rho_within, p_within = spearmanr(within_mean["attempt_number"], within_mean["mean_actions"])

# Linear regression on participant-task level deltas
# For each participant-task, compute slope of num_actions over attempt_number
slopes_within = []
for (pid, task), grp in multi_attempt.groupby(["hashed_id", "task_name"]):
    grp_s = grp.sort_values("attempt_number")
    if len(grp_s) >= 2:
        slope, *_ = np.polyfit(grp_s["attempt_number"], grp_s["num_actions"], 1)
        slopes_within.append(slope)

slopes_within = np.array(slopes_within)
mean_slope_within = slopes_within.mean()
w_stat, p_slope_within = stats.wilcoxon(slopes_within) if len(slopes_within) >= 10 else (np.nan, np.nan)
pct_negative = (slopes_within < 0).mean() * 100

print(f"\nWithin-task slope (num_actions per attempt):")
print(f"  Mean slope : {mean_slope_within:+.2f} actions/attempt")
print(f"  % negative : {pct_negative:.1f}%  (negative = fewer actions over attempts)")
print(f"  Wilcoxon   : W={w_stat:.1f}, p={p_slope_within:.4f}")
print(f"  Spearman ρ (attempt# vs mean_actions): ρ={rho_within:.3f}, p={p_within:.4f}")

# Solve-rate trend
rho_solve, p_solve = spearmanr(solve_rate["attempt_number"], solve_rate["solve_rate"])
print(f"\nSolve-rate Spearman ρ (attempt# vs solve_rate): ρ={rho_solve:.3f}, p={p_solve:.4f}")
print("  Solve rates by attempt:")
print(solve_rate.to_string(index=False))

# ── 2b. Across-task trends (task_number) from summary_data ────────────────
# Only first attempts to avoid within-task confound
first_attempts = summary[(summary["complete"]) & (summary["attempt_number"] == 1)].copy()

# Participants with ≥ 3 tasks
multi_task = first_attempts.groupby("hashed_id").filter(lambda g: len(g) >= 3)
print(f"\nAcross-task analysis (first attempts, ≥3 tasks): "
      f"{len(multi_task):,} rows, {multi_task['hashed_id'].nunique()} participants")

task_mean = (
    multi_task.groupby("task_number")["num_actions"]
    .agg(["mean", "median", "sem", "count"])
    .reset_index()
    .rename(columns={"mean": "mean_actions", "median": "median_actions",
                     "sem": "sem_actions", "count": "n"})
)
task_mean = task_mean[task_mean["n"] >= 10]

task_solve = (
    multi_task.groupby("task_number")["solved"]
    .mean()
    .reset_index()
    .rename(columns={"solved": "solve_rate"})
)
task_solve = task_solve[task_solve["task_number"].isin(task_mean["task_number"])]

rho_across, p_across = spearmanr(task_mean["task_number"], task_mean["mean_actions"])
rho_task_solve, p_task_solve = spearmanr(task_solve["task_number"], task_solve["solve_rate"])

# Per-participant across-task slope
slopes_across = []
for pid, grp in multi_task.groupby("hashed_id"):
    grp_s = grp.sort_values("task_number")
    if len(grp_s) >= 3:
        slope, *_ = np.polyfit(grp_s["task_number"], grp_s["num_actions"], 1)
        slopes_across.append(slope)

slopes_across = np.array(slopes_across)
mean_slope_across = slopes_across.mean()
w_stat_across, p_slope_across = stats.wilcoxon(slopes_across) if len(slopes_across) >= 10 else (np.nan, np.nan)
pct_neg_across = (slopes_across < 0).mean() * 100

print(f"\nAcross-task slope (num_actions per task):")
print(f"  Mean slope : {mean_slope_across:+.2f} actions/task")
print(f"  % negative : {pct_neg_across:.1f}%")
print(f"  Wilcoxon   : W={w_stat_across:.1f}, p={p_slope_across:.4f}")
print(f"  Spearman ρ (task# vs mean_actions): ρ={rho_across:.3f}, p={p_across:.4f}")
print(f"  Spearman ρ (task# vs solve_rate):   ρ={rho_task_solve:.3f}, p={p_task_solve:.4f}")

# ── 2c. Action-type composition from data.csv ─────────────────────────────
print("\nLoading data.csv for action-type analysis (selecting columns) …")
usecols = ["hashed_id", "task_name", "task_number", "attempt_number",
           "action", "solved", "complete", "time", "task_type"]
raw = pd.read_csv(DATA_CSV, usecols=usecols, low_memory=False)
raw_complete = raw[raw["complete"].astype(str).str.lower() == "true"].copy()

# Map action types to broad categories
ACTION_MAP = {
    "edit":              "edit",
    "floodfill":         "edit",
    "copy_from_input":   "copy_from_input",
    "reset_grid":        "reset",
    "change_width":      "resize",
    "change_height":     "resize",
    "change_color":      "tool_change",
    "submit":            "submit",
    "write_first_description": "description",
    "no_last_description":     "description",
    "write_last_description":  "description",
}
raw_complete["action_cat"] = raw_complete["action"].map(ACTION_MAP).fillna("other")

# Per attempt: action category counts and fractions
agg = (
    raw_complete.groupby(["hashed_id", "task_name", "task_number", "attempt_number",
                           "task_type", "action_cat"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)
cats = [c for c in ["edit", "copy_from_input", "reset", "resize", "tool_change", "submit", "description", "other"]
        if c in agg.columns]
agg["total"] = agg[cats].sum(axis=1)
for cat in cats:
    agg[f"frac_{cat}"] = agg[cat] / agg["total"].replace(0, np.nan)

# Restrict to first attempts, ≥3 tasks, for across-task composition
first_comp = agg[(agg["attempt_number"] == 1)].copy()
multi_comp = first_comp.groupby("hashed_id").filter(lambda g: len(g) >= 3)

# Mean composition by task_number
comp_by_task = (
    multi_comp.groupby("task_number")[[f"frac_{c}" for c in cats]]
    .mean()
    .reset_index()
)
comp_by_task = comp_by_task[comp_by_task["task_number"].isin(task_mean["task_number"])]

print("\nAction-type composition trends (Spearman ρ vs task_number):")
comp_trends = {}
for cat in cats:
    col = f"frac_{cat}"
    if col in comp_by_task.columns:
        rho, p = spearmanr(comp_by_task["task_number"], comp_by_task[col])
        comp_trends[cat] = (rho, p)
        sig = "**" if p < 0.05 else "  "
        print(f"  {sig} {cat:<18} ρ={rho:+.3f}  p={p:.4f}")

# Within-task: action composition by attempt_number
multi_comp_within = agg.copy()
multi_comp_within_filt = (
    multi_comp_within.groupby(["hashed_id", "task_name"])
    .filter(lambda g: len(g) >= 2)
)
comp_by_attempt = (
    multi_comp_within_filt.groupby("attempt_number")[[f"frac_{c}" for c in cats]]
    .mean()
    .reset_index()
)
comp_by_attempt = comp_by_attempt[comp_by_attempt["attempt_number"].isin(within_mean["attempt_number"])]

print("\nAction-type composition trends (Spearman ρ vs attempt_number, within-task):")
comp_within_trends = {}
for cat in cats:
    col = f"frac_{cat}"
    if col in comp_by_attempt.columns:
        rho, p = spearmanr(comp_by_attempt["attempt_number"], comp_by_attempt[col])
        comp_within_trends[cat] = (rho, p)
        sig = "**" if p < 0.05 else "  "
        print(f"  {sig} {cat:<18} ρ={rho:+.3f}  p={p:.4f}")

# ── 2d. Session duration trend ─────────────────────────────────────────────
print("\nComputing session duration per attempt …")
raw_complete["time_parsed"] = pd.to_datetime(raw_complete["time"], errors="coerce")
durations = (
    raw_complete.groupby(["hashed_id", "task_name", "attempt_number"])["time_parsed"]
    .agg(lambda x: (x.max() - x.min()).total_seconds() / 60.0)
    .reset_index()
    .rename(columns={"time_parsed": "duration_min"})
)
durations = durations[durations["duration_min"] >= 0]
dur_merged = durations.merge(
    summary[["hashed_id", "task_name", "attempt_number", "task_number", "complete", "task_type"]],
    on=["hashed_id", "task_name", "attempt_number"], how="left"
)
dur_merged = dur_merged[dur_merged["complete"].astype(str).str.lower() == "true"]

dur_by_attempt = (
    dur_merged.groupby("attempt_number")["duration_min"]
    .agg(["mean", "median", "count"])
    .reset_index()
)
dur_by_attempt = dur_by_attempt[dur_by_attempt["count"] >= 20]
rho_dur, p_dur = spearmanr(dur_by_attempt["attempt_number"], dur_by_attempt["mean"])
print(f"  Duration Spearman ρ (attempt# vs mean_duration): ρ={rho_dur:.3f}, p={p_dur:.4f}")

dur_by_task = (
    dur_merged[dur_merged["attempt_number"] == 1]
    .groupby("task_number")["duration_min"]
    .agg(["mean", "median", "count"])
    .reset_index()
)
dur_by_task = dur_by_task[dur_by_task["count"] >= 10]
dur_by_task = dur_by_task[dur_by_task["task_number"].isin(task_mean["task_number"])]
rho_dur_task, p_dur_task = spearmanr(dur_by_task["task_number"], dur_by_task["mean"])
print(f"  Duration Spearman ρ (task#   vs mean_duration): ρ={rho_dur_task:.3f}, p={p_dur_task:.4f}")

# ── 2e. Plots ──────────────────────────────────────────────────────────────
print("\nGenerating plots …")
fig = plt.figure(figsize=(18, 14))
fig.patch.set_facecolor(BG)
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.5, wspace=0.38)

def style_ax(ax):
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(labelsize=9)

# A — Within-task: mean actions by attempt
ax_a = fig.add_subplot(gs[0, 0])
style_ax(ax_a)
x = within_mean["attempt_number"]
y = within_mean["mean_actions"]
e = within_mean["sem_actions"]
ax_a.errorbar(x, y, yerr=e, color=ACCENT, marker="o", linewidth=1.8, capsize=3)
ax_a.set_xlabel("Attempt number")
ax_a.set_ylabel("Mean actions")
ax_a.set_title(f"A  Within-task: actions per attempt\n(ρ={rho_within:.2f}, p={p_within:.3f})", fontweight="bold", loc="left", fontsize=9)

# B — Within-task: solve rate by attempt
ax_b = fig.add_subplot(gs[0, 1])
style_ax(ax_b)
ax_b.plot(solve_rate["attempt_number"], solve_rate["solve_rate"] * 100, color=GREEN, marker="o", linewidth=1.8)
ax_b.set_xlabel("Attempt number")
ax_b.set_ylabel("Solve rate (%)")
ax_b.set_title(f"B  Within-task: solve rate per attempt\n(ρ={rho_solve:.2f}, p={p_solve:.3f})", fontweight="bold", loc="left", fontsize=9)

# C — Within-task: slope distribution
ax_c = fig.add_subplot(gs[0, 2])
style_ax(ax_c)
ax_c.hist(slopes_within, bins=30, color=ACCENT, edgecolor="white", linewidth=0.5)
ax_c.axvline(0, color="black", linestyle="--", linewidth=1)
ax_c.axvline(mean_slope_within, color=GREEN, linewidth=1.5, label=f"Mean={mean_slope_within:+.1f}")
ax_c.set_xlabel("Slope (actions/attempt)")
ax_c.set_ylabel("Participant-task pairs")
ax_c.set_title(f"C  Within-task slope distribution\n({pct_negative:.0f}% negative, p={p_slope_within:.4f})", fontweight="bold", loc="left", fontsize=9)
ax_c.legend(fontsize=8)

# D — Across-task: mean actions by task number
ax_d = fig.add_subplot(gs[1, 0])
style_ax(ax_d)
x2 = task_mean["task_number"]
y2 = task_mean["mean_actions"]
e2 = task_mean["sem_actions"]
ax_d.errorbar(x2, y2, yerr=e2, color=BLUE, marker="o", linewidth=1.8, capsize=3, markersize=4)
ax_d.set_xlabel("Task number (sequence position)")
ax_d.set_ylabel("Mean actions (first attempt)")
ax_d.set_title(f"D  Across-task: actions vs task position\n(ρ={rho_across:.2f}, p={p_across:.3f})", fontweight="bold", loc="left", fontsize=9)

# E — Across-task: solve rate by task number
ax_e = fig.add_subplot(gs[1, 1])
style_ax(ax_e)
ax_e.plot(task_solve["task_number"], task_solve["solve_rate"] * 100, color=GREEN, marker="o", linewidth=1.8, markersize=4)
ax_e.set_xlabel("Task number (sequence position)")
ax_e.set_ylabel("Solve rate (%) — first attempt")
ax_e.set_title(f"E  Across-task: solve rate vs task position\n(ρ={rho_task_solve:.2f}, p={p_task_solve:.3f})", fontweight="bold", loc="left", fontsize=9)

# F — Across-task: slope distribution
ax_f = fig.add_subplot(gs[1, 2])
style_ax(ax_f)
ax_f.hist(slopes_across, bins=30, color=BLUE, edgecolor="white", linewidth=0.5)
ax_f.axvline(0, color="black", linestyle="--", linewidth=1)
ax_f.axvline(mean_slope_across, color=GREEN, linewidth=1.5, label=f"Mean={mean_slope_across:+.1f}")
ax_f.set_xlabel("Slope (actions/task)")
ax_f.set_ylabel("Participants")
ax_f.set_title(f"F  Across-task slope distribution\n({pct_neg_across:.0f}% negative, p={p_slope_across:.4f})", fontweight="bold", loc="left", fontsize=9)
ax_f.legend(fontsize=8)

# G — Action-type composition across tasks (stacked area, normalised)
ax_g = fig.add_subplot(gs[2, :2])
style_ax(ax_g)
cat_colors = {"edit": ACCENT, "copy_from_input": BLUE, "reset": "#ff4136",
              "tool_change": "#ffdc00", "resize": "#7fdbff", "other": GRAY}
bottom = np.zeros(len(comp_by_task))
for cat in cats:
    col = f"frac_{cat}"
    if col in comp_by_task.columns:
        vals = comp_by_task[col].fillna(0).values
        ax_g.bar(comp_by_task["task_number"], vals, bottom=bottom,
                 color=cat_colors.get(cat, GRAY), label=cat, alpha=0.85, width=0.8)
        bottom += vals
ax_g.set_xlabel("Task number (sequence position)")
ax_g.set_ylabel("Fraction of actions")
ax_g.set_title("G  Action-type composition across tasks (first attempts)", fontweight="bold", loc="left", fontsize=9)
ax_g.legend(fontsize=8, loc="upper right", ncol=3)

# H — Duration trend
ax_h = fig.add_subplot(gs[2, 2])
style_ax(ax_h)
ax_h.plot(dur_by_task["task_number"], dur_by_task["mean"], color=ACCENT, marker="o",
          linewidth=1.8, markersize=4, label="Across task")
ax_h.set_xlabel("Task number")
ax_h.set_ylabel("Mean duration (min)")
ax_h.set_title(f"H  Session duration vs task position\n(ρ={rho_dur_task:.2f}, p={p_dur_task:.3f})", fontweight="bold", loc="left", fontsize=9)

fig.suptitle("Learning-curve and action-pattern trends across ARC-AGI solving attempts",
             fontsize=13, fontweight="bold", y=0.99)
plt.savefig(OUT_DIR / "learning_trends_plots.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
plt.close()
print("  → learning_trends_plots.png written")

# ── 2f. Trend report ──────────────────────────────────────────────────────
def fmt_p(p):
    if p is None or (isinstance(p, float) and math.isnan(p)): return "n/a"
    return "< 0.001" if p < 0.001 else f"{p:.4f}"

def sig(p):
    if p is None or (isinstance(p, float) and math.isnan(p)): return ""
    return " ✓" if p < 0.05 else ""

trend_lines = [
    "# Learning-curve and action-pattern trend analysis",
    "",
    "## Data",
    f"- `summary_data.csv`: {len(summary):,} rows total; "
    f"{len(summary[summary['complete']]):,} complete rows used for within/across-task analyses.",
    f"- `data.csv`: {len(raw):,} action rows; "
    f"{len(raw_complete):,} from complete participants used for action-type analysis.",
    "",
    "---",
    "",
    "## 1. Within-task learning (attempt 1 → 2 → …)",
    "",
    "### Action count",
    f"Participant-task pairs with ≥ 2 attempts: **{len(slopes_within):,}**  ",
    f"Mean slope across pairs: **{mean_slope_within:+.2f} actions/attempt**  ",
    f"Proportion with negative slope (improving): **{pct_negative:.1f}%**  ",
    f"Wilcoxon signed-rank (slopes vs 0): W = {w_stat:.1f}, p = {fmt_p(p_slope_within)}{sig(p_slope_within)}  ",
    f"Spearman ρ (attempt# vs mean_actions): ρ = {rho_within:.3f}, p = {fmt_p(p_within)}{sig(p_within)}",
    "",
]

if p_slope_within < 0.05 and mean_slope_within < 0:
    trend_lines.append(
        "**Finding:** Participants use significantly **fewer actions** on later attempts of the same puzzle. "
        "This is consistent with a within-task learning effect — repeated exposure reduces "
        "the amount of exploration needed."
    )
elif p_slope_within < 0.05 and mean_slope_within > 0:
    trend_lines.append(
        "**Finding:** Participants use significantly **more actions** on later attempts of the same puzzle, "
        "suggesting that initial failures lead to more elaborate exploration strategies."
    )
else:
    trend_lines.append(
        "**Finding:** No significant linear trend in action count across within-task attempts."
    )

trend_lines += [
    "",
    "### Solve rate",
    f"Spearman ρ (attempt# vs solve rate): ρ = {rho_solve:.3f}, p = {fmt_p(p_solve)}{sig(p_solve)}",
    "",
    "Solve rates by attempt number:",
    "",
    "| Attempt | Solve rate |",
    "|---------|-----------|",
]
for _, row in solve_rate.iterrows():
    trend_lines.append(f"| {int(row['attempt_number'])} | {row['solve_rate']*100:.1f}% |")

if p_solve < 0.05 and rho_solve > 0:
    trend_lines.append("\n**Finding:** Solve rate increases significantly with attempt number — "
                       "repeated attempts on the same puzzle improve the probability of success.")
elif p_solve < 0.05 and rho_solve < 0:
    trend_lines.append("\n**Finding:** Solve rate decreases with attempt number — "
                       "participants who make multiple attempts may be facing harder puzzles.")
else:
    trend_lines.append("\n**Finding:** No significant trend in solve rate across within-task attempts.")

trend_lines += [
    "",
    "### Action-type composition (within-task)",
    "",
    "Spearman ρ between attempt_number and mean fraction of each action category:",
    "",
    "| Action type | ρ | p | Significant? |",
    "|-------------|---|---|-------------|",
]
for cat, (rho, p) in comp_within_trends.items():
    trend_lines.append(f"| {cat} | {rho:+.3f} | {fmt_p(p)} | {'Yes' if p < 0.05 else 'No'} |")

trend_lines += [
    "",
    "---",
    "",
    "## 2. Across-task learning (task 1 → 2 → …, first attempts only)",
    "",
    f"Participants with ≥ 3 solved tasks: **{multi_task['hashed_id'].nunique():,}**  ",
    f"Mean slope across participants: **{mean_slope_across:+.2f} actions/task**  ",
    f"Proportion with negative slope: **{pct_neg_across:.1f}%**  ",
    f"Wilcoxon signed-rank: W = {w_stat_across:.1f}, p = {fmt_p(p_slope_across)}{sig(p_slope_across)}  ",
    f"Spearman ρ (task# vs mean_actions): ρ = {rho_across:.3f}, p = {fmt_p(p_across)}{sig(p_across)}  ",
    f"Spearman ρ (task# vs solve_rate):   ρ = {rho_task_solve:.3f}, p = {fmt_p(p_task_solve)}{sig(p_task_solve)}",
    "",
]

if p_slope_across < 0.05 and mean_slope_across < 0:
    trend_lines.append(
        "**Finding:** Across-task learning is evident: as participants progress through more puzzles, "
        "they use significantly fewer actions per task on their first attempt."
    )
elif p_slope_across < 0.05 and mean_slope_across > 0:
    trend_lines.append(
        "**Finding:** Action count increases with task position, suggesting later tasks "
        "are harder or that participants adopt more thorough strategies over time."
    )
else:
    trend_lines.append(
        "**Finding:** No significant linear change in action count across task positions."
    )

trend_lines += [
    "",
    "### Action-type composition (across-task)",
    "",
    "| Action type | ρ | p | Significant? | Interpretation |",
    "|-------------|---|---|-------------|----------------|",
]
interpretations_comp = {
    "edit":           "Core solving actions",
    "copy_from_input": "Template strategy (copies input as starting point)",
    "reset":          "Undo/restart behavior",
    "tool_change":    "Color-selection overhead",
    "resize":         "Grid-size adjustments",
    "description":    "Written annotations",
    "other":          "Miscellaneous",
}
for cat, (rho, p) in comp_trends.items():
    trend_lines.append(
        f"| {cat} | {rho:+.3f} | {fmt_p(p)} | {'Yes' if p < 0.05 else 'No'} | "
        f"{interpretations_comp.get(cat, '')} |"
    )

trend_lines += [
    "",
    "### Session duration",
    f"Spearman ρ (task# vs mean_duration): ρ = {rho_dur_task:.3f}, p = {fmt_p(p_dur_task)}{sig(p_dur_task)}  ",
    f"Spearman ρ (attempt# vs mean_duration): ρ = {rho_dur:.3f}, p = {fmt_p(p_dur)}{sig(p_dur)}",
    "",
]

if p_dur_task < 0.05 and rho_dur_task < 0:
    trend_lines.append("**Finding:** Participants spend less time per puzzle as they progress through the task sequence, consistent with efficiency gains.")
elif p_dur_task < 0.05 and rho_dur_task > 0:
    trend_lines.append("**Finding:** Session duration increases with task position, suggesting later puzzles require more time.")
else:
    trend_lines.append("**Finding:** No significant linear change in session duration across task positions.")

trend_lines += ["", "---", "", "## 3. Summary of trends", ""]

all_findings = []
if p_slope_within < 0.05:
    direction = "decreases" if mean_slope_within < 0 else "increases"
    all_findings.append(
        f"**Within-task action count {direction}** across repeated attempts "
        f"(mean slope {mean_slope_within:+.2f}/attempt, {pct_negative:.0f}% of pairs negative, "
        f"p = {fmt_p(p_slope_within)})."
    )
if p_solve < 0.05:
    direction = "increases" if rho_solve > 0 else "decreases"
    all_findings.append(
        f"**Solve rate {direction}** with attempt number (ρ = {rho_solve:.2f}, p = {fmt_p(p_solve)})."
    )
if p_slope_across < 0.05:
    direction = "decreases" if mean_slope_across < 0 else "increases"
    all_findings.append(
        f"**Across-task action count {direction}** with task sequence position "
        f"(mean slope {mean_slope_across:+.2f}/task, p = {fmt_p(p_slope_across)})."
    )
if p_task_solve < 0.05:
    direction = "increases" if rho_task_solve > 0 else "decreases"
    all_findings.append(
        f"**Solve rate {direction}** across task positions (ρ = {rho_task_solve:.2f}, p = {fmt_p(p_task_solve)})."
    )
sig_comp = [(cat, rho, p) for cat, (rho, p) in comp_trends.items() if p < 0.05]
for cat, rho, p in sig_comp:
    direction = "increases" if rho > 0 else "decreases"
    all_findings.append(
        f"**'{cat}' action fraction {direction}** across task positions "
        f"(ρ = {rho:.2f}, p = {fmt_p(p)})."
    )

if all_findings:
    for f in all_findings:
        trend_lines.append(f"- {f}")
else:
    trend_lines.append("No statistically significant trends were detected.")

trend_lines += [
    "",
    "### Effect sizes and predictability",
    "",
    "| Trend | Spearman ρ | Strength | Predictability |",
    "|-------|-----------|----------|----------------|",
]
effect_table = [
    ("Within-task action count", rho_within, p_within),
    ("Within-task solve rate",   rho_solve,   p_solve),
    ("Across-task action count", rho_across,  p_across),
    ("Across-task solve rate",   rho_task_solve, p_task_solve),
    ("Across-task duration",     rho_dur_task, p_dur_task),
]
for label, rho, p in effect_table:
    strength = "strong" if abs(rho) > 0.5 else ("moderate" if abs(rho) > 0.3 else "weak")
    predictability = "high" if abs(rho) > 0.5 else ("moderate" if abs(rho) > 0.3 else "low")
    trend_lines.append(f"| {label} | {rho:+.3f} | {strength} | {predictability} |")

(OUT_DIR / "learning_trends_report.md").write_text("\n".join(trend_lines), encoding="utf-8")
print("  → learning_trends_report.md written")

# ── 2g. Task-type breakdown (training vs. evaluation) ─────────────────────
def run_tasktype_trends(label, summary_sub, agg_sub, dur_merged_sub):
    """Return dict of key trend stats for a task-type subset."""
    # Within-task
    within_sub = summary_sub[summary_sub["complete"]].copy()
    multi_att = within_sub.groupby(["hashed_id", "task_name"]).filter(lambda g: len(g) >= 2)
    wm = (multi_att.groupby("attempt_number")["num_actions"]
          .agg(["mean", "count"]).reset_index()
          .rename(columns={"mean": "mean_actions", "count": "n"}))
    wm = wm[wm["n"] >= 10]
    rho_w, p_w = spearmanr(wm["attempt_number"], wm["mean_actions"]) if len(wm) >= 3 else (np.nan, np.nan)
    sl_w = []
    for (_, __), grp in multi_att.groupby(["hashed_id", "task_name"]):
        g = grp.sort_values("attempt_number")
        if len(g) >= 2:
            sl_w.append(np.polyfit(g["attempt_number"], g["num_actions"], 1)[0])
    sl_w = np.array(sl_w)
    w_stat_w, p_slope_w = stats.wilcoxon(sl_w) if len(sl_w) >= 10 else (np.nan, np.nan)

    # Across-task
    first_sub = summary_sub[(summary_sub["complete"]) & (summary_sub["attempt_number"] == 1)].copy()
    multi_t = first_sub.groupby("hashed_id").filter(lambda g: len(g) >= 3)
    tm = (multi_t.groupby("task_number")["num_actions"]
          .agg(["mean", "count"]).reset_index()
          .rename(columns={"mean": "mean_actions", "count": "n"}))
    tm = tm[tm["n"] >= 10]
    ts = multi_t.groupby("task_number")["solved"].mean().reset_index().rename(columns={"solved": "solve_rate"})
    ts = ts[ts["task_number"].isin(tm["task_number"])]
    rho_a, p_a = spearmanr(tm["task_number"], tm["mean_actions"]) if len(tm) >= 3 else (np.nan, np.nan)
    rho_s, p_s = spearmanr(ts["task_number"], ts["solve_rate"]) if len(ts) >= 3 else (np.nan, np.nan)
    sl_a = []
    for _, grp in multi_t.groupby("hashed_id"):
        g = grp.sort_values("task_number")
        if len(g) >= 3:
            sl_a.append(np.polyfit(g["task_number"], g["num_actions"], 1)[0])
    sl_a = np.array(sl_a)
    _, p_slope_a = stats.wilcoxon(sl_a) if len(sl_a) >= 10 else (np.nan, np.nan)

    # Duration
    dur_a = (dur_merged_sub[dur_merged_sub["attempt_number"] == 1]
             .groupby("task_number")["duration_min"].agg(["mean", "count"]).reset_index())
    dur_a = dur_a[(dur_a["count"] >= 10) & (dur_a["task_number"].isin(tm["task_number"]))]
    rho_d, p_d = spearmanr(dur_a["task_number"], dur_a["mean"]) if len(dur_a) >= 3 else (np.nan, np.nan)

    # Action composition
    first_comp_sub = agg_sub[agg_sub["attempt_number"] == 1].copy()
    multi_comp_sub = first_comp_sub.groupby("hashed_id").filter(lambda g: len(g) >= 3)
    comp_t = (multi_comp_sub.groupby("task_number")[[f"frac_{c}" for c in cats if f"frac_{c}" in multi_comp_sub.columns]]
              .mean().reset_index())
    comp_t = comp_t[comp_t["task_number"].isin(tm["task_number"])]
    comp_rhos = {}
    for cat in cats:
        col = f"frac_{cat}"
        if col in comp_t.columns and len(comp_t) >= 3:
            r, p = spearmanr(comp_t["task_number"], comp_t[col])
            comp_rhos[cat] = (r, p)

    return {
        "label": label,
        "n_participants_within": multi_att["hashed_id"].nunique(),
        "n_participants_across": multi_t["hashed_id"].nunique(),
        "rho_within": rho_w, "p_within": p_w,
        "mean_slope_within": float(sl_w.mean()) if len(sl_w) else np.nan,
        "p_slope_within": p_slope_w,
        "rho_across": rho_a, "p_across": p_a,
        "rho_solve": rho_s, "p_solve": p_s,
        "mean_slope_across": float(sl_a.mean()) if len(sl_a) else np.nan,
        "p_slope_across": p_slope_a,
        "rho_dur": rho_d, "p_dur": p_d,
        "comp_rhos": comp_rhos,
        "tm": tm, "ts": ts, "wm": wm, "dur_a": dur_a,
    }

def fmt_p2(p):
    if p is None or (isinstance(p, float) and math.isnan(p)): return "n/a"
    return "< 0.001" if p < 0.001 else f"{p:.4f}"

# Build task_type-filtered subsets
tt_results = {}
for tt in ["training", "evaluation"]:
    summary_tt = summary[summary["task_type"] == tt].copy()
    agg_tt = agg[agg["task_type"] == tt].copy()
    agg_tt["total"] = agg_tt[[c for c in cats if c in agg_tt.columns]].sum(axis=1)
    for cat in cats:
        if cat in agg_tt.columns:
            agg_tt[f"frac_{cat}"] = agg_tt[cat] / agg_tt["total"].replace(0, np.nan)
    dur_tt = dur_merged[dur_merged["task_type"] == tt] if "task_type" in dur_merged.columns else dur_merged.iloc[0:0]
    tt_results[tt] = run_tasktype_trends(tt, summary_tt, agg_tt, dur_tt)
    r = tt_results[tt]
    print(f"\n[{tt}] within ρ={r['rho_within']:.3f} p={fmt_p2(r['p_within'])} | "
          f"across ρ={r['rho_across']:.3f} p={fmt_p2(r['p_across'])} | "
          f"solve ρ={r['rho_solve']:.3f} p={fmt_p2(r['p_solve'])} | "
          f"dur ρ={r['rho_dur']:.3f} p={fmt_p2(r['p_dur'])}")

# Task-type comparison figure
fig3, axes3 = plt.subplots(2, 4, figsize=(20, 10))
fig3.patch.set_facecolor(BG)
tt_colors = {"training": BLUE, "evaluation": ACCENT}

def style3(ax):
    ax.set_facecolor(BG)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(labelsize=8)

panel_labels = iter("ABCDEFGH")
for row_i, tt in enumerate(["training", "evaluation"]):
    r = tt_results[tt]
    col = tt_colors[tt]
    label = tt.capitalize()

    # Col 0: actions per attempt (within-task)
    ax = axes3[row_i, 0]; style3(ax)
    wm = r["wm"]
    ax.errorbar(wm["attempt_number"], wm["mean_actions"], color=col, marker="o", linewidth=1.8, capsize=3)
    ax.set_xlabel("Attempt number", fontsize=8); ax.set_ylabel("Mean actions", fontsize=8)
    ax.set_title(f"{next(panel_labels)}  {label}: within-task actions\n(ρ={r['rho_within']:.2f}, p={fmt_p2(r['p_within'])})",
                 fontweight="bold", loc="left", fontsize=8)

    # Col 1: actions per task (across-task)
    ax = axes3[row_i, 1]; style3(ax)
    tm = r["tm"]
    ax.errorbar(tm["task_number"], tm["mean_actions"], color=col, marker="o", linewidth=1.8, capsize=3, markersize=4)
    ax.set_xlabel("Task position", fontsize=8); ax.set_ylabel("Mean actions (1st attempt)", fontsize=8)
    ax.set_title(f"{next(panel_labels)}  {label}: across-task actions\n(ρ={r['rho_across']:.2f}, p={fmt_p2(r['p_across'])})",
                 fontweight="bold", loc="left", fontsize=8)

    # Col 2: solve rate across tasks
    ax = axes3[row_i, 2]; style3(ax)
    ts = r["ts"]
    ax.plot(ts["task_number"], ts["solve_rate"] * 100, color=GREEN, marker="o", linewidth=1.8, markersize=4)
    ax.set_xlabel("Task position", fontsize=8); ax.set_ylabel("Solve rate (%)", fontsize=8)
    ax.set_title(f"{next(panel_labels)}  {label}: solve rate\n(ρ={r['rho_solve']:.2f}, p={fmt_p2(r['p_solve'])})",
                 fontweight="bold", loc="left", fontsize=8)

    # Col 3: duration across tasks
    ax = axes3[row_i, 3]; style3(ax)
    da = r["dur_a"]
    ax.plot(da["task_number"], da["mean"], color=col, marker="o", linewidth=1.8, markersize=4)
    ax.set_xlabel("Task position", fontsize=8); ax.set_ylabel("Mean duration (min)", fontsize=8)
    ax.set_title(f"{next(panel_labels)}  {label}: session duration\n(ρ={r['rho_dur']:.2f}, p={fmt_p2(r['p_dur'])})",
                 fontweight="bold", loc="left", fontsize=8)

fig3.suptitle("Learning trends: training vs. evaluation tasks",
              fontsize=13, fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(OUT_DIR / "learning_tasktype_comparison.png", dpi=150, bbox_inches="tight",
            facecolor=fig3.get_facecolor())
plt.close()
print("  → learning_tasktype_comparison.png written")

# Append task-type section to report
tt_section = [
    "",
    "---",
    "",
    "## 4. Training vs. evaluation task breakdown",
    "",
    "| Metric | Training | Evaluation |",
    "|--------|----------|------------|",
]
for key, label in [
    ("rho_within",     "Within-task action count ρ"),
    ("p_within",       "Within-task action count p"),
    ("mean_slope_within", "Mean within-task slope (actions/attempt)"),
    ("rho_across",     "Across-task action count ρ"),
    ("p_across",       "Across-task action count p"),
    ("rho_solve",      "Across-task solve rate ρ"),
    ("p_solve",        "Across-task solve rate p"),
    ("rho_dur",        "Across-task duration ρ"),
    ("p_dur",          "Across-task duration p"),
]:
    tr_v = tt_results["training"][key]
    ev_v = tt_results["evaluation"][key]
    fmt_v = lambda v: fmt_p2(v) if "p_" in key else (f"{v:+.3f}" if isinstance(v, float) and not math.isnan(v) else "n/a")
    tt_section.append(f"| {label} | {fmt_v(tr_v)} | {fmt_v(ev_v)} |")

tt_section += ["", "### Action-type composition ρ (across-task, first attempts)", ""]
tt_section.append("| Action type | Training ρ | Training p | Evaluation ρ | Evaluation p |")
tt_section.append("|-------------|-----------|-----------|-------------|-------------|")
for cat in cats:
    tr_r = tt_results["training"]["comp_rhos"].get(cat, (np.nan, np.nan))
    ev_r = tt_results["evaluation"]["comp_rhos"].get(cat, (np.nan, np.nan))
    tt_section.append(f"| {cat} | {tr_r[0]:+.3f} | {fmt_p2(tr_r[1])} | {ev_r[0]:+.3f} | {fmt_p2(ev_r[1])} |")

with open(OUT_DIR / "learning_trends_report.md", "a", encoding="utf-8") as f:
    f.write("\n".join(tt_section))
print("  → task-type section appended to learning_trends_report.md")

# ══════════════════════════════════════════════════════════════════════════
# PART 3 — Materials & Methods
# ══════════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("PART 3 — Writing Materials & Methods")
print("=" * 60)

# Pull summary numbers for M&M narrative
n_all_participants  = summary["hashed_id"].nunique()
n_complete          = summary[summary["complete"]]["hashed_id"].nunique()
n_solved_complete   = filtered["hashed_id"].nunique()
n_p90               = len(p90_df)
n_total_rows_sum    = len(summary)
n_total_actions     = len(raw)

mm_lines = [
    "# Materials and Methods",
    "",
    "## 1. Participants and data collection",
    "",
    f"Data were collected from {n_all_participants:,} participants who engaged with an online "
    "experiment in which they were asked to solve tasks from the Abstraction and Reasoning "
    "Corpus (ARC-AGI; François Chollet, 2019). Participants interacted with a custom web-based "
    "interface that recorded every user action at millisecond resolution. Raw data were stored "
    "in two comma-separated files: `data.csv`, containing one row per action "
    f"({n_total_actions:,} rows total), and `summary_data.csv`, containing one row per "
    f"participant-task-attempt combination ({n_total_rows_sum:,} rows total). "
    "A supplementary `demographics.csv` captured self-reported participant characteristics "
    "(age, gender, education, vision, language), and `feedback.csv` contained open-ended "
    "reflections collected at session end.",
    "",
    "## 2. Task set",
    "",
    "Participants were presented with tasks drawn from the ARC-AGI benchmark (Chollet, 2019), "
    "comprising 400 training tasks and 400 evaluation tasks. Each task consists of a small "
    "number of input-output grid pairs (training demonstrations) and one or two test grids "
    "for which the participant must produce the correct output. Grids range from 1×1 to 30×30 "
    "cells, with integer values 0–9 representing ten possible colours. The benchmark is "
    "designed to require abstract reasoning and cannot be solved by simple pattern memorisation.",
    "",
    "## 3. Action recording and data structure",
    "",
    "Every interaction was logged as a timestamped action row in `data.csv`. Relevant fields "
    "include: participant identifier (`hashed_id`), task name, task sequence position "
    "(`task_number`), within-task attempt number (`attempt_number`), action type (`action`), "
    "target grid coordinates (`action_x`, `action_y`), the colour symbol applied "
    "(`selected_symbol`), and the full test-output grid state at each step. "
    "Summary statistics per attempt — including total action count (`num_actions`), solve status "
    "(`solved`), and experiment-completion flag (`complete`) — were stored in `summary_data.csv`.",
    "",
    "## 4. Data filtering and primary analysis sample",
    "",
    "Unless otherwise stated, all analyses were restricted to participants who completed the "
    "full experiment (`complete = true`) and to attempts in which the puzzle was eventually "
    f"solved (`solved = true`). This yielded {n_solved_complete:,} unique participants across "
    "their qualifying attempts. For analyses examining the first-attempt trajectory only, "
    "rows with `attempt_number = 1` were selected. For within-task learning analyses, all "
    "attempts (irrespective of `solved`) from complete participants were retained.",
    "",
    "## 5. Identification of high-click participants",
    "",
    "### 5.1 Normalised click-intensity index (existing subpopulation criterion)",
    "To account for task-specific difficulty, click counts were normalised within each puzzle "
    "by dividing each participant's `num_actions` by the mean `num_actions` for that puzzle "
    "across all eligible participants. A participant-level click-intensity index was computed "
    "as the mean of these normalised values across tasks (`mean_normalized_num_actions`). "
    "A high-click subpopulation was operationally defined as participants with "
    "`mean_normalized_num_actions ≥ 2.0`, yielding 15 participants from the full cohort of "
    "1,393 (n = 7,871 participant-task units).",
    "",
    "### 5.2 95th-percentile criterion (present study)",
    f"A complementary criterion identified participants in the top 5% of mean action count "
    f"across their solved, complete attempts, restricted to those who completed at least four "
    f"distinct puzzles. The 95th-percentile threshold was "
    f"**{p90_threshold:.1f} actions per attempt** (mean `num_actions`), yielding "
    f"**{n_p90} participants**. These participants are listed in rank order in "
    "`Analysis/results/p95_high_clickers.md`.",
    "",
    "## 6. Off-path step classification",
    "",
    "### 6.1 Required-change grid",
    "For each task, a *required-change grid* was constructed by comparing the ARC task's "
    "canonical test-input grid to its test-output grid. Cells that differ between the two "
    "constitute the required changes; all other cells retain the value `null` in this "
    "representation. This grid encodes both *where* and *what colour* a participant must "
    "paint to solve the puzzle.",
    "",
    "### 6.2 Step-level alignment classification",
    "All action-level rows were processed by `build_solution_paths_summary.py`. "
    "For each solved attempt, actions were sorted by `action_id` and filtered to those "
    "that produced a grid-state change. Passive actions (`copy_from_input`, `reset_grid`) "
    "were excluded from classification. For each remaining `edit` or `floodfill` action, "
    "the clicked cell was looked up in the required-change map. A step was classified as "
    "**aligned** (on-path) if the painted colour matched the required output colour for that "
    "cell, or the cell's original input colour (i.e., a valid undo). Otherwise it was "
    "classified as **off-path** and assigned one of the following reason codes: "
    "*wrong color* (correct cell, incorrect colour), *wrong coordinate* (cell not in the "
    "required-change set), or *missing coordinate* (incomplete action metadata). "
    "Two bugs in the initial implementation were identified and corrected during the present "
    "study: (i) grid coordinates (`action_x`, `action_y`) were stored as float strings "
    '(e.g., `"3.0"`) that Python\'s `int()` silently collapsed to zero, causing all lookups '
    "to resolve to cell (0, 0); and (ii) the row and column axes were transposed in the "
    "key-construction formula (`action_y:action_x` was used instead of `action_x:action_y`). "
    "Both were corrected in the production pipeline before all reported analyses were run.",
    "",
    "### 6.3 JavaScript validation (off-path play-by-play)",
    "A complementary client-side check was implemented in the web viewer "
    "(`frameMatchesChangesOnly`). The initial version compared the participant's full grid "
    "state after an action against all required-change cells simultaneously, returning false "
    "for any intermediate step where not all required changes had yet been made. This was "
    "corrected to compare only the *delta* between `grid_before` and `grid_after` — the "
    "cells actually changed by that specific action — against the required-change grid.",
    "",
    "## 7. Off-path meaningfulness analysis",
    "",
    "To determine whether off-path behaviour reflects structured problem-solving or random "
    "noise, three metrics were computed for each off-path edit step (see "
    "`Analysis/offpath_analysis.py`):",
    "",
    "**Mistake-type distribution.** Steps were categorised as *wrong-color* (correct cell, "
    "wrong colour) or *wrong-coordinate* (cell outside the required-change set). The "
    "dominant category identifies whether participants have acquired spatial knowledge of "
    "the puzzle (right cell) but are uncertain about colour, or whether they lack spatial "
    "knowledge entirely.",
    "",
    "**Colour relevance.** For each off-path edit step, we recorded whether the applied "
    "colour belonged to the set of required output colours for that task. A per-task random "
    "baseline was computed as the expected fraction of solution-relevant colours under uniform "
    "sampling from the nine non-background colours. Observed relevance was compared to the "
    "baseline using a Wilcoxon signed-rank test on per-participant colour deltas.",
    "",
    "**Spatial proximity.** The Manhattan distance from the clicked cell to the nearest "
    "required-change cell was computed for each step. A per-task Monte Carlo baseline "
    "(2,000 uniformly random cells) provided the expected distance under random placement. "
    "A Wilcoxon signed-rank test on per-participant distance deltas assessed whether "
    "off-path clicks were systematically closer to target cells than chance.",
    "",
    "**Cross-puzzle consistency.** A one-way random-effects intraclass correlation "
    "coefficient (ICC(1,1)) was computed on the per-participant, per-task off-path rate "
    "(off-path steps / required-change cells). An ICC substantially above zero indicates "
    "that off-path behaviour is a stable individual trait rather than task-specific noise.",
    "",
    "**High vs. low off-path comparison.** Participants were split at the median total "
    "off-path step count. Mann-Whitney U tests compared colour delta, distance delta, and "
    "wrong-colour fraction between the two groups.",
    "",
    "## 8. Learning-curve and action-pattern trend analysis",
    "",
    "### 8.1 Within-task learning",
    "For participant-task pairs with two or more recorded attempts, we computed the "
    "linear slope of `num_actions` over `attempt_number` using ordinary least squares. "
    "A Wilcoxon signed-rank test assessed whether the distribution of slopes differed "
    "from zero. Solve rate and mean session duration were also regressed on attempt "
    "number; Spearman correlations quantified the monotonic relationship. "
    "Action-type composition (fraction of edit, reset, copy-from-input, resize, and "
    "tool-change actions per attempt) was examined for each category using Spearman "
    "correlation with attempt number.",
    "",
    "### 8.2 Across-task learning",
    "Restricting to first attempts from participants who completed three or more tasks, "
    "we computed per-participant slopes of `num_actions` over `task_number` (the sequence "
    "position of the task in the participant's session). Wilcoxon and Spearman tests "
    "assessed the direction, magnitude, and statistical reliability of the trend. "
    "Solve rate, session duration, and action-type composition were examined analogously. "
    "Effect strength was characterised using the magnitude of the Spearman ρ: "
    "|ρ| > 0.5 = strong, 0.3–0.5 = moderate, < 0.3 = weak.",
    "",
    "## 9. Sequence-randomization analysis (existing framework)",
    "",
    "A solved-only sequence-randomization analysis was conducted on `data.csv` restricted "
    "to first, complete attempts that reached solved status. For each solved attempt, three "
    "metrics were computed on the ordered click sequence: (1) *mean step distance* "
    "(mean Euclidean distance between consecutive clicks), (2) *local move rate* (proportion "
    "of consecutive steps with distance ≤ 1.5 cells), and (3) *focus drop* (coordinate "
    "entropy in the first half minus the second half, operationalising broad-to-focused "
    "transitions). Within each trial, 250 surrogate sequences were generated by permuting "
    "click order while preserving clicked locations. Observed-minus-shuffled deltas (Δ) were "
    "computed per trial, averaged per participant, and tested against zero using one-sample "
    "sign-flip permutation tests (5,000 flips).",
    "",
    "## 10. Structure-only framework",
    "",
    "To characterise click behaviour independently of solve outcome, the three sequence "
    "metrics above were applied to all completed first attempts (solved and unsolved). "
    "Within-trial shuffling (250 surrogates) controlled for click count and visited positions. "
    "Participant-level mean deltas were permutation-tested (5,000 sign flips). Cross-trial "
    "consistency was assessed via odd-even split-half Spearman correlation with permutation "
    "inference.",
    "",
    "## 11. Outcome modelling",
    "",
    "Logistic generalised linear models were fitted with solve probability as the outcome "
    "and click intensity as the primary predictor, including task fixed effects and "
    "participant-clustered standard errors. Linear, quadratic, cubic, and piecewise-linear "
    "spline specifications were compared by AIC and likelihood-ratio test. The spline model "
    "provided the best fit (AIC = 9,992.30 vs. linear AIC = 10,184.96). Augmented models "
    "incorporated structure-derived predictors (Δ metrics from Section 9) to test whether "
    "temporal click organisation explained solve probability beyond click volume alone.",
    "",
    "## 12. Interactive web visualisation",
    "",
    "A self-contained static web application was developed in HTML5, CSS3, and vanilla "
    "JavaScript (ES6+) to enable interactive inspection of participant behaviour "
    "(`high_click_viewer/`). The application includes:",
    "",
    "- **Off-path play-by-play** (`off_path_playbyplay.html`): for each task, displays all "
    "  participants who solved it, their off-path steps in chronological order, and a "
    "  frame-by-frame replay showing the task input, solved output, participant's current "
    "  grid state, and required-change overlay. Tasks are sorted by total off-path steps "
    "  (descending).",
    "- **High off-path clickers** (`high_offpath_clickers.html`): ranks all participants "
    "  with `complete = true` by total off-path steps across all solved puzzles. Clicking a "
    "  participant reveals their puzzle-by-puzzle breakdown with the same playthrough "
    "  interface, sorted by per-puzzle off-path count.",
    "",
    "Data for the viewer is generated by `build_solution_paths_summary.py`, which produces "
    "`solution_paths.json` encoding per-participant off-path step sequences with full grid "
    "state before and after each action.",
    "",
    "## 13. Software and reproducibility",
    "",
    "All analyses were implemented in Python 3 using NumPy 2.1.3, Pandas 2.2.3, "
    "SciPy 1.14.1, and Matplotlib 3.9.2, running under the `fmri_env` Conda environment. "
    "The web viewer requires no external dependencies and is served via Python's built-in "
    "`http.server`. All analysis scripts are contained in the `Analysis/` directory; "
    "output artefacts (CSVs, Markdown reports, PNG figures) are written to "
    "`Analysis/results/`. Raw data files (`data.csv`, `summary_data.csv`) are not "
    "distributed with the repository due to participant privacy.",
]

mm_text = "\n".join(mm_lines)
(OUT_DIR / "materials_and_methods.md").write_text(mm_text, encoding="utf-8")
print("  → materials_and_methods.md written")
print()
print("All done. Outputs in:", OUT_DIR)
