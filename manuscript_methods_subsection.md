## Identification of a high-click subpopulation and evaluation of strategic vs random clicking

### Data sources and preprocessing
We used two log-level datasets: `summary_data.csv` (attempt-level summaries) and `data.csv` (action-level click sequences). For all primary analyses, we restricted data to first attempts from participants who completed the experiment (`attempt_number = 1`, `complete = true`).

### 1. Demonstrating the existence of a high-click subpopulation
To account for task-specific difficulty, click counts were normalized within each puzzle by dividing each participant's number of actions on a given task by the average number of actions for that same task across eligible participants.

A participant-level click-intensity index was then computed as the mean of \(\text{normalized\_num\_actions}_{i,t}\) across that participant's tasks (`mean_normalized_num_actions`). We operationally defined a high-click subpopulation as participants with `mean_normalized_num_actions >= 2.0`.

In the analyzed cohort (`n = 1393` participants; `7871` participant-task units), this criterion identified `15` high-click participants.

### 2. Quantifying whether clicking reflects meaningful strategy versus random/fidgety behavior
To test whether observed click behavior among successful attempts was structured, we ran a solved-only sequence-randomization analysis using `data.csv`.

#### Solved-only sequence definition
We included first attempts from completed participants and selected participant-task attempts that reached solved status at least once (`solved = true` at any action in the attempt). For each such solved attempt, we retained the full ordered action sequence (`action_id` order).

#### Observed sequence metrics
For each solved sequence, we computed:

- Mean step distance: mean Euclidean distance between consecutive `(action_x, action_y)` clicks.
- Local move rate: proportion of consecutive steps with distance `<= 1.5` grid cells.
- Focus drop: entropy of clicked coordinates in the first half minus the second half of the sequence (positive values indicate broad-to-focused transition).

#### Random baseline construction
Within each trial, we generated `250` shuffled baselines by randomly permuting click order while preserving the set of clicked locations (and therefore total click volume). This preserves trial-specific click content while destroying temporal organization.

For each metric \(m\), we computed:

\[
\Delta_m = m_{\text{observed}} - \mathbb{E}[m_{\text{shuffled}}]
\]

#### Participant-level inference
Trial-level \(\Delta\) values were averaged per participant, and one-sample sign-flip permutation tests (`5000` flips) were used to test whether participant-mean \(\Delta\) differed from zero.

Solved-only sample size was `3933` solved trials from `1204` participants.

### Supplemental structure-only framework (independent of solve probability)
We used a structure-focused framework to characterize click behavior as a process using sequence-organization metrics rather than solve probability as the dependent variable. This analysis was conducted on all completed first attempts (`complete = true`, `attempt_number = 1`), including both solved and unsolved participant-task attempts. The framework tests whether temporal organization differs from chance while controlling for click count and visited positions via within-trial shuffling.

This analysis used action-level click streams from `data.csv`. We sorted actions by `action_id` and required at least `5` clicks with valid `(action_x, action_y)` coordinates per sequence. For each sequence, we generated `250` within-trial surrogate sequences by permuting click order while preserving clicked coordinates and total click count. We computed observed-minus-shuffled deltas for three implemented metrics: mean step distance, local move rate (step distance `<= 1.5`), and focus drop (first-half coordinate entropy minus second-half coordinate entropy), which operationalizes early-to-late phase organization relative to the shuffled baseline. Trial-level metrics were saved to `structure_only_trial_metrics.csv`; participant-level mean-delta permutation-test summaries (`5000` sign flips) were saved to `structure_only_summary.csv`; cross-trial consistency (odd-even split-half correlation with permutation inference) was saved to `structure_only_consistency_summary.csv`; and accompanying outputs were written to `structure_only_report.md` and `structure_only_effects.png`.

### Supplemental outcome-modeling framework
To test both approaches jointly, we used a complementary outcome-modeling framework that incorporated predictors from the structure-only analysis. First, we fit baseline logistic generalized linear models for solve probability as a function of click intensity, with task fixed effects (`C(task_name)`) and participant-clustered standard errors. We compared linear and non-linear intensity forms (quadratic, cubic, and piecewise linear spline) using AIC and likelihood-ratio tests.

We then fit augmented outcome models that included structure-derived predictors (observed-minus-shuffled sequence metrics) in addition to click intensity, allowing us to test whether temporal organization explained variance in solve probability beyond click volume alone. Model comparison between baseline and augmented specifications was performed with AIC and nested likelihood-ratio tests.

In this dataset, the spline model provided the best fit (`AIC = 9992.30`; linear model `AIC = 10184.96`), supporting a non-linear relationship between click intensity and solve probability.

### Reproducibility artifacts
Analysis outputs are available in:

- `introspection_participant_features.csv`
- `introspection_permutation_results.csv`
- `solved_strategy_vs_random_trial_metrics.csv`
- `solved_strategy_vs_random_summary.csv`
- `structure_only_trial_metrics.csv`
- `structure_only_summary.csv`
- `structure_only_consistency_summary.csv`
- `structure_only_report.md`
- `structure_only_effects.png`
- `nonlinear_model_comparison.csv`
- `nonlinear_probability_curves.csv`
