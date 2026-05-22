# Learning-curve and action-pattern trend analysis

## Data
- `summary_data.csv`: 15,736 rows total; 13,861 complete rows used for within/across-task analyses.
- `data.csv`: 586,266 action rows; 483,863 from complete participants used for action-type analysis.

---

## 1. Within-task learning (attempt 1 → 2 → …)

### Action count
Participant-task pairs with ≥ 2 attempts: **3,487**  
Mean slope across pairs: **+21.70 actions/attempt**  
Proportion with negative slope (improving): **0.1%**  
Wilcoxon signed-rank (slopes vs 0): W = 239.0, p = < 0.001 ✓  
Spearman ρ (attempt# vs mean_actions): ρ = 1.000, p = < 0.001 ✓

**Finding:** Participants use significantly **more actions** on later attempts of the same puzzle, suggesting that initial failures lead to more elaborate exploration strategies.

### Solve rate
Spearman ρ (attempt# vs solve rate): ρ = 0.500, p = 0.6667

Solve rates by attempt number:

| Attempt | Solve rate |
|---------|-----------|
| 1 | 0.1% |
| 2 | 28.2% |
| 3 | 11.9% |

**Finding:** No significant trend in solve rate across within-task attempts.

### Action-type composition (within-task)

Spearman ρ between attempt_number and mean fraction of each action category:

| Action type | ρ | p | Significant? |
|-------------|---|---|-------------|
| edit | -1.000 | < 0.001 | Yes |
| copy_from_input | -1.000 | < 0.001 | Yes |
| reset | -1.000 | < 0.001 | Yes |
| resize | -1.000 | < 0.001 | Yes |
| tool_change | -0.500 | 0.6667 | No |
| submit | +1.000 | < 0.001 | Yes |
| description | +0.500 | 0.6667 | No |
| other | -0.500 | 0.6667 | No |

---

## 2. Across-task learning (task 1 → 2 → …, first attempts only)

Participants with ≥ 3 solved tasks: **1,392**  
Mean slope across participants: **-0.38 actions/task**  
Proportion with negative slope: **53.7%**  
Wilcoxon signed-rank: W = 458757.5, p = 0.0830  
Spearman ρ (task# vs mean_actions): ρ = -0.891, p = < 0.001 ✓  
Spearman ρ (task# vs solve_rate):   ρ = 0.796, p = 0.0058 ✓

**Finding:** No significant linear change in action count across task positions.

### Action-type composition (across-task)

| Action type | ρ | p | Significant? | Interpretation |
|-------------|---|---|-------------|----------------|
| edit | +0.091 | 0.8028 | No | Core solving actions |
| copy_from_input | +0.709 | 0.0217 | Yes | Template strategy (copies input as starting point) |
| reset | +0.782 | 0.0075 | Yes | Undo/restart behavior |
| resize | -0.152 | 0.6761 | No | Grid-size adjustments |
| tool_change | +0.721 | 0.0186 | Yes | Color-selection overhead |
| submit | +0.818 | 0.0038 | Yes |  |
| description | +0.830 | 0.0029 | Yes | Written annotations |
| other | -0.952 | < 0.001 | Yes | Miscellaneous |

### Session duration
Spearman ρ (task# vs mean_duration): ρ = -0.927, p = < 0.001 ✓  
Spearman ρ (attempt# vs mean_duration): ρ = -1.000, p = < 0.001 ✓

**Finding:** Participants spend less time per puzzle as they progress through the task sequence, consistent with efficiency gains.

---

## 3. Summary of trends

- **Within-task action count increases** across repeated attempts (mean slope +21.70/attempt, 0% of pairs negative, p = < 0.001).
- **Solve rate increases** across task positions (ρ = 0.80, p = 0.0058).
- **'copy_from_input' action fraction increases** across task positions (ρ = 0.71, p = 0.0217).
- **'reset' action fraction increases** across task positions (ρ = 0.78, p = 0.0075).
- **'tool_change' action fraction increases** across task positions (ρ = 0.72, p = 0.0186).
- **'submit' action fraction increases** across task positions (ρ = 0.82, p = 0.0038).
- **'description' action fraction increases** across task positions (ρ = 0.83, p = 0.0029).
- **'other' action fraction decreases** across task positions (ρ = -0.95, p = < 0.001).

### Effect sizes and predictability

| Trend | Spearman ρ | Strength | Predictability |
|-------|-----------|----------|----------------|
| Within-task action count | +1.000 | strong | high |
| Within-task solve rate | +0.500 | moderate | moderate |
| Across-task action count | -0.891 | strong | high |
| Across-task solve rate | +0.796 | strong | high |
| Across-task duration | -0.927 | strong | high |
---

## 4. Training vs. evaluation task breakdown

| Metric | Training | Evaluation |
|--------|----------|------------|
| Within-task action count ρ | +1.000 | +1.000 |
| Within-task action count p | < 0.001 | < 0.001 |
| Mean within-task slope (actions/attempt) | +19.395 | +23.964 |
| Across-task action count ρ | -0.842 | -0.700 |
| Across-task action count p | 0.0022 | 0.1881 |
| Across-task solve rate ρ | +0.492 | +0.667 |
| Across-task solve rate p | 0.1482 | 0.2189 |
| Across-task duration ρ | -0.879 | -1.000 |
| Across-task duration p | < 0.001 | < 0.001 |

### Action-type composition ρ (across-task, first attempts)

| Action type | Training ρ | Training p | Evaluation ρ | Evaluation p |
|-------------|-----------|-----------|-------------|-------------|
| edit | +0.600 | 0.0667 | +0.600 | 0.2848 |
| copy_from_input | +0.285 | 0.4250 | +0.700 | 0.1881 |
| reset | +0.709 | 0.0217 | +0.300 | 0.6238 |
| resize | -0.709 | 0.0217 | -1.000 | < 0.001 |
| tool_change | +0.794 | 0.0061 | +0.600 | 0.2848 |
| submit | +0.855 | 0.0016 | +0.600 | 0.2848 |
| description | +0.842 | 0.0022 | +0.600 | 0.2848 |
| other | -0.952 | < 0.001 | -1.000 | < 0.001 |