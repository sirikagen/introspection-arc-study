# Off-path click analysis: meaningful vs. random behaviour

## 1. Overview

| | |
|---|---|
| Participants (complete = true) | 1275 |
| Participants with ≥ 1 off-path step | 1046 |
| Total off-path steps | 11332 |
| Edit / floodfill steps (position + color analysable) | 11332 |
| Median off-path steps per participant | 4 |
| Max off-path steps (single participant) | 251 |

---

## 2. Mistake type distribution

Off-path steps fall into two main categories:

- **Wrong color** — the participant clicked on a cell that *does* need to change, but applied the wrong colour. This indicates spatial awareness (they found the right cell) but an incorrect colour hypothesis.
- **Wrong coordinate** — the participant painted a cell that is *not* in the required-change set. This could reflect exploratory behaviour, misidentifying the pattern, or fidgeting.

| Reason category | Count | % of edit steps |
|-----------------|-------|-----------------|
| wrong_color | 11280 | 99.5% |
| wrong_coordinate | 52 | 0.5% |
| missing_coord | 0 | 0.0% |
| other | 0 | 0.0% |

The dominant error type is **wrong_color** (99.5% of edit steps).

---

## 3. Color relevance — are participants using solution colours?

For each off-path edit step, we test whether the colour painted is one of the colours required in the task's solved output (i.e., a colour that *should* appear somewhere in the grid). We compare this against a per-task random baseline (expected fraction if the participant sampled uniformly from the 9 non-background colours).

| Metric | Value |
|--------|-------|
| Mean observed colour relevance | 0.753 |
| Mean random baseline | 0.345 |
| Mean delta (observed − baseline) | 0.408 |
| Wilcoxon W (per-participant deltas vs. 0) | 28926.5 |
| p-value | < 0.001 |

**Interpretation:** Off-path steps use solution-relevant colours significantly more than chance would predict. Even when making a mistake, participants are drawing from the correct colour palette — a hallmark of purposeful, informed behaviour.

---

## 4. Spatial proximity — are off-path clicks near required-change cells?

For each off-path edit step, we compute the Manhattan distance from the clicked cell to the nearest required-change cell. A per-task random baseline is estimated by sampling 2,000 uniformly random cells from the same grid and averaging their distances to the nearest target cell. **A positive delta means off-path clicks are closer to target cells than random placement.**

| Metric | Value |
|--------|-------|
| Mean observed distance to nearest target cell | 1.06 grid cells |
| Mean random baseline distance | 3.24 grid cells |
| Mean delta (baseline − observed) | 2.18 |
| Wilcoxon W (per-participant deltas vs. 0) | 32715.5 |
| p-value | < 0.001 |

**Interpretation:** Off-path clicks are significantly closer to required-change cells than a uniformly random placement would predict. Participants are working in the right spatial neighbourhood — their mistakes are not scattered randomly across the grid.

---

## 5. High vs. low off-path participants

Participants split at median total off-path steps (4):
- **High off-path group**: 595 participants
- **Low off-path group**: 680 participants

| Metric | High off-path | Low off-path | Mann-Whitney U | p |
|--------|--------------|-------------|----------------|---|
| Mean colour Δ | 0.427 | 0.436 | 108753.0 | 0.0093 |
| Mean distance Δ | 2.083 | 2.331 | 112742.5 | 0.1146 |
| Frac wrong-color | 0.993 | 0.999 | 118534.0 | 0.0431 |

**Interpretation:** If high off-path participants show higher colour deltas and distance deltas than low off-path participants, their extra clicks reflect the same purposeful (if imprecise) strategy — they are not simply adding random noise.

---

## 6. Cross-puzzle consistency (ICC)

The intraclass correlation coefficient (one-way random effects, ICC(1,1)) partitions variance in off-path rate (off-path steps / required-change cells) into between-participant and within-participant components.

| Metric | Value |
|--------|-------|
| ICC(1,1) | -0.120 |

**Interpretation:** ICC = -0.120 indicates **low** between-participant consistency. Off-path behaviour varies considerably across puzzles within participants, suggesting task difficulty or puzzle-specific features drive deviations more than individual style.

---

## 7. Top participants by total off-path steps

| Rank | Participant ID | Total off-path | Tasks | Avg/task | Colour Δ | Dist Δ | % wrong-color | % wrong-coord |
|------|---------------|----------------|-------|----------|---------|--------|--------------|--------------|
| 1 | `95f395373062c6d5…` | 251 | 5 | 50.2 | 0.260 | 1.36 | 100% | 0% |
| 2 | `061f06908316d683…` | 191 | 3 | 63.7 | 0.664 | 1.25 | 100% | 0% |
| 3 | `b26c49180b83bf94…` | 131 | 4 | 32.8 | -0.111 | 0.15 | 100% | 0% |
| 4 | `0954867f72ce8586…` | 112 | 5 | 22.4 | 0.629 | 6.88 | 100% | 0% |
| 5 | `23609d6e8ff2ec85…` | 110 | 5 | 22.0 | 0.667 | 5.26 | 100% | 0% |
| 6 | `c0841ccd8b2c5b64…` | 105 | 9 | 11.7 | 0.162 | -0.86 | 97% | 3% |
| 7 | `b9038fbf53e1925b…` | 95 | 4 | 23.8 | 0.772 | 1.07 | 100% | 0% |
| 8 | `22fabcb92d8909e7…` | 94 | 4 | 23.5 | 0.416 | -0.20 | 100% | 0% |
| 9 | `70d343789ca526b9…` | 87 | 5 | 17.4 | 0.407 | 3.46 | 100% | 0% |
| 10 | `7ed9ec4ca6d7e3c4…` | 81 | 5 | 16.2 | 0.599 | 0.23 | 100% | 0% |
| 11 | `4b9ff461bcb8a879…` | 78 | 4 | 19.5 | 0.363 | 1.05 | 100% | 0% |
| 12 | `e2de7b05ed553c54…` | 73 | 4 | 18.2 | 0.771 | 0.97 | 100% | 0% |
| 13 | `048022a60c2cf8ae…` | 70 | 2 | 35.0 | 0.061 | 2.07 | 100% | 0% |
| 14 | `4d3abff8640f8871…` | 66 | 3 | 22.0 | 0.778 | 0.40 | 100% | 0% |
| 15 | `8d7c56529be9303b…` | 65 | 6 | 10.8 | 0.611 | 6.16 | 100% | 0% |
| 16 | `2a9f88a280e5a494…` | 65 | 8 | 8.1 | -0.104 | -0.75 | 100% | 0% |
| 17 | `7426449648c92ad3…` | 64 | 5 | 12.8 | 0.315 | 0.93 | 100% | 0% |
| 18 | `16cc2e4ab0e117ad…` | 64 | 5 | 12.8 | 0.722 | 3.75 | 100% | 0% |
| 19 | `1337f45837efc234…` | 61 | 4 | 15.2 | 0.778 | -1.59 | 100% | 0% |
| 20 | `e709577bc7380f4f…` | 60 | 5 | 12.0 | 0.611 | 0.08 | 100% | 0% |

---

## 8. Summary

- **Colour relevance** is significantly above the random baseline (Δ = +0.408, p = < 0.001).
- **Spatial proximity**: off-path clicks are significantly closer to target cells than random (Δ = +2.18 cells, p = < 0.001).
- **Cross-puzzle consistency** is low (ICC = -0.120), suggesting off-path behaviour varies primarily by task.
- The dominant error type is **wrong_color** (99.5% of edit steps), indicating participants generally identify the correct cells but struggle with colour selection.

---

## 9. Training vs. evaluation task breakdown

All key metrics were re-computed separately for training and evaluation task types.

| Metric | Training | Evaluation |
|--------|----------|------------|
| Participants with off-path steps | 644 | 631 |
| Total off-path edit steps | 4938 | 6394 |
| Mean colour relevance (observed) | 0.720 | 0.778 |
| Mean colour Δ (observed − baseline) | 0.436 | 0.426 |
| Colour relevance Wilcoxon p | < 0.001 | < 0.001 |
| Mean distance to nearest target (cells) | see dist_delta | see dist_delta |
| Mean spatial proximity Δ | 1.88 | 2.45 |
| Spatial proximity Wilcoxon p | < 0.001 | < 0.001 |
| % wrong-color errors | 99.3% | 99.8% |
| % wrong-coordinate errors | 0.7% | 0.2% |
| ICC(1,1) cross-puzzle consistency | -0.039 | -0.276 |

Comparison figure saved to `offpath_tasktype_comparison.png`.