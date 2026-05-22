# Materials and Methods

## 1. Participants and data collection

Data were collected from 1,729 participants who engaged with an online experiment in which they were asked to solve tasks from the Abstraction and Reasoning Corpus (ARC-AGI; François Chollet, 2019). Participants interacted with a custom web-based interface that recorded every user action at millisecond resolution. Raw data were stored in two comma-separated files: `data.csv`, containing one row per action (586,266 rows total), and `summary_data.csv`, containing one row per participant-task-attempt combination (15,736 rows total). A supplementary `demographics.csv` captured self-reported participant characteristics (age, gender, education, vision, language), and `feedback.csv` contained open-ended reflections collected at session end.

## 2. Task set

Participants were presented with tasks drawn from the ARC-AGI benchmark (Chollet, 2019), comprising 400 training tasks and 400 evaluation tasks. Each task consists of a small number of input-output grid pairs (training demonstrations) and one or two test grids for which the participant must produce the correct output. Grids range from 1×1 to 30×30 cells, with integer values 0–9 representing ten possible colours. The benchmark is designed to require abstract reasoning and cannot be solved by simple pattern memorisation.

## 3. Action recording and data structure

Every interaction was logged as a timestamped action row in `data.csv`. Relevant fields include: participant identifier (`hashed_id`), task name, task sequence position (`task_number`), within-task attempt number (`attempt_number`), action type (`action`), target grid coordinates (`action_x`, `action_y`), the colour symbol applied (`selected_symbol`), and the full test-output grid state at each step. Summary statistics per attempt — including total action count (`num_actions`), solve status (`solved`), and experiment-completion flag (`complete`) — were stored in `summary_data.csv`.

## 4. Data filtering and primary analysis sample

Unless otherwise stated, all analyses were restricted to participants who completed the full experiment (`complete = true`) and to attempts in which the puzzle was eventually solved (`solved = true`). This yielded 1,275 unique participants across their qualifying attempts. For analyses examining the first-attempt trajectory only, rows with `attempt_number = 1` were selected. For within-task learning analyses, all attempts (irrespective of `solved`) from complete participants were retained.

## 5. Identification of high-click participants

### 5.1 Normalised click-intensity index (existing subpopulation criterion)
To account for task-specific difficulty, click counts were normalised within each puzzle by dividing each participant's `num_actions` by the mean `num_actions` for that puzzle across all eligible participants. A participant-level click-intensity index was computed as the mean of these normalised values across tasks (`mean_normalized_num_actions`). A high-click subpopulation was operationally defined as participants with `mean_normalized_num_actions ≥ 2.0`, yielding 15 participants from the full cohort of 1,393 (n = 7,871 participant-task units).

### 5.2 95th-percentile criterion (present study)
A complementary criterion identified participants in the top 5% of mean action count across their solved, complete attempts, restricted to those who completed at least four distinct puzzles. The 95th-percentile threshold was **118.8 actions per attempt** (mean `num_actions`), yielding **33 participants**. These participants are listed in rank order in `Analysis/results/p95_high_clickers.md`.

## 6. Off-path step classification

### 6.1 Required-change grid
For each task, a *required-change grid* was constructed by comparing the ARC task's canonical test-input grid to its test-output grid. Cells that differ between the two constitute the required changes; all other cells retain the value `null` in this representation. This grid encodes both *where* and *what colour* a participant must paint to solve the puzzle.

### 6.2 Step-level alignment classification
All action-level rows were processed by `build_solution_paths_summary.py`. For each solved attempt, actions were sorted by `action_id` and filtered to those that produced a grid-state change. Passive actions (`copy_from_input`, `reset_grid`) were excluded from classification. For each remaining `edit` or `floodfill` action, the clicked cell was looked up in the required-change map. A step was classified as **aligned** (on-path) if the painted colour matched the required output colour for that cell, or the cell's original input colour (i.e., a valid undo). Otherwise it was classified as **off-path** and assigned one of the following reason codes: *wrong color* (correct cell, incorrect colour), *wrong coordinate* (cell not in the required-change set), or *missing coordinate* (incomplete action metadata). Two bugs in the initial implementation were identified and corrected during the present study: (i) grid coordinates (`action_x`, `action_y`) were stored as float strings (e.g., `"3.0"`) that Python's `int()` silently collapsed to zero, causing all lookups to resolve to cell (0, 0); and (ii) the row and column axes were transposed in the key-construction formula (`action_y:action_x` was used instead of `action_x:action_y`). Both were corrected in the production pipeline before all reported analyses were run.

### 6.3 JavaScript validation (off-path play-by-play)
A complementary client-side check was implemented in the web viewer (`frameMatchesChangesOnly`). The initial version compared the participant's full grid state after an action against all required-change cells simultaneously, returning false for any intermediate step where not all required changes had yet been made. This was corrected to compare only the *delta* between `grid_before` and `grid_after` — the cells actually changed by that specific action — against the required-change grid.

## 7. Off-path meaningfulness analysis

To determine whether off-path behaviour reflects structured problem-solving or random noise, three metrics were computed for each off-path edit step (see `Analysis/offpath_analysis.py`):

**Mistake-type distribution.** Steps were categorised as *wrong-color* (correct cell, wrong colour) or *wrong-coordinate* (cell outside the required-change set). The dominant category identifies whether participants have acquired spatial knowledge of the puzzle (right cell) but are uncertain about colour, or whether they lack spatial knowledge entirely.

**Colour relevance.** For each off-path edit step, we recorded whether the applied colour belonged to the set of required output colours for that task. A per-task random baseline was computed as the expected fraction of solution-relevant colours under uniform sampling from the nine non-background colours. Observed relevance was compared to the baseline using a Wilcoxon signed-rank test on per-participant colour deltas.

**Spatial proximity.** The Manhattan distance from the clicked cell to the nearest required-change cell was computed for each step. A per-task Monte Carlo baseline (2,000 uniformly random cells) provided the expected distance under random placement. A Wilcoxon signed-rank test on per-participant distance deltas assessed whether off-path clicks were systematically closer to target cells than chance.

**Cross-puzzle consistency.** A one-way random-effects intraclass correlation coefficient (ICC(1,1)) was computed on the per-participant, per-task off-path rate (off-path steps / required-change cells). An ICC substantially above zero indicates that off-path behaviour is a stable individual trait rather than task-specific noise.

**High vs. low off-path comparison.** Participants were split at the median total off-path step count. Mann-Whitney U tests compared colour delta, distance delta, and wrong-colour fraction between the two groups.

## 8. Learning-curve and action-pattern trend analysis

### 8.1 Within-task learning
For participant-task pairs with two or more recorded attempts, we computed the linear slope of `num_actions` over `attempt_number` using ordinary least squares. A Wilcoxon signed-rank test assessed whether the distribution of slopes differed from zero. Solve rate and mean session duration were also regressed on attempt number; Spearman correlations quantified the monotonic relationship. Action-type composition (fraction of edit, reset, copy-from-input, resize, and tool-change actions per attempt) was examined for each category using Spearman correlation with attempt number.

### 8.2 Across-task learning
Restricting to first attempts from participants who completed three or more tasks, we computed per-participant slopes of `num_actions` over `task_number` (the sequence position of the task in the participant's session). Wilcoxon and Spearman tests assessed the direction, magnitude, and statistical reliability of the trend. Solve rate, session duration, and action-type composition were examined analogously. Effect strength was characterised using the magnitude of the Spearman ρ: |ρ| > 0.5 = strong, 0.3–0.5 = moderate, < 0.3 = weak.

## 9. Sequence-randomization analysis (existing framework)

A solved-only sequence-randomization analysis was conducted on `data.csv` restricted to first, complete attempts that reached solved status. For each solved attempt, three metrics were computed on the ordered click sequence: (1) *mean step distance* (mean Euclidean distance between consecutive clicks), (2) *local move rate* (proportion of consecutive steps with distance ≤ 1.5 cells), and (3) *focus drop* (coordinate entropy in the first half minus the second half, operationalising broad-to-focused transitions). Within each trial, 250 surrogate sequences were generated by permuting click order while preserving clicked locations. Observed-minus-shuffled deltas (Δ) were computed per trial, averaged per participant, and tested against zero using one-sample sign-flip permutation tests (5,000 flips).

## 10. Structure-only framework

To characterise click behaviour independently of solve outcome, the three sequence metrics above were applied to all completed first attempts (solved and unsolved). Within-trial shuffling (250 surrogates) controlled for click count and visited positions. Participant-level mean deltas were permutation-tested (5,000 sign flips). Cross-trial consistency was assessed via odd-even split-half Spearman correlation with permutation inference.

## 11. Outcome modelling

Logistic generalised linear models were fitted with solve probability as the outcome and click intensity as the primary predictor, including task fixed effects and participant-clustered standard errors. Linear, quadratic, cubic, and piecewise-linear spline specifications were compared by AIC and likelihood-ratio test. The spline model provided the best fit (AIC = 9,992.30 vs. linear AIC = 10,184.96). Augmented models incorporated structure-derived predictors (Δ metrics from Section 9) to test whether temporal click organisation explained solve probability beyond click volume alone.

## 12. Interactive web visualisation

A self-contained static web application was developed in HTML5, CSS3, and vanilla JavaScript (ES6+) to enable interactive inspection of participant behaviour (`high_click_viewer/`). The application includes:

- **Off-path play-by-play** (`off_path_playbyplay.html`): for each task, displays all   participants who solved it, their off-path steps in chronological order, and a   frame-by-frame replay showing the task input, solved output, participant's current   grid state, and required-change overlay. Tasks are sorted by total off-path steps   (descending).
- **High off-path clickers** (`high_offpath_clickers.html`): ranks all participants   with `complete = true` by total off-path steps across all solved puzzles. Clicking a   participant reveals their puzzle-by-puzzle breakdown with the same playthrough   interface, sorted by per-puzzle off-path count.

Data for the viewer is generated by `build_solution_paths_summary.py`, which produces `solution_paths.json` encoding per-participant off-path step sequences with full grid state before and after each action.

## 13. Software and reproducibility

All analyses were implemented in Python 3 using NumPy 2.1.3, Pandas 2.2.3, SciPy 1.14.1, and Matplotlib 3.9.2, running under the `fmri_env` Conda environment. The web viewer requires no external dependencies and is served via Python's built-in `http.server`. All analysis scripts are contained in the `Analysis/` directory; output artefacts (CSVs, Markdown reports, PNG figures) are written to `Analysis/results/`. Raw data files (`data.csv`, `summary_data.csv`) are not distributed with the repository due to participant privacy.