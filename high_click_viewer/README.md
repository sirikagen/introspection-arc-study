# High-Click Participant Replay Viewer

## What this site includes
- Main page with the 15 high-click participant IDs.
- One subpage per participant listing puzzle IDs they solved.
- One replay page per solved puzzle with frame-by-frame visualization.
- Playback controls: play, pause, first, prev, next, last, scrub slider, and speed control.
- An ARC-AGI gallery page for browsing the training and evaluation tasks visually.
- A Participant solutions page with solved attempts, participant IDs, and action paths.
- A Solution Paths page that shows only test pairs, the final change-only path steps, and participant off-path steps.
- An Off-path play-by-play page that shows participant timelines of only the steps that stray from the solution path.

## Regenerate data from CSV
Run from the repository root:

```bash
/Users/sirikagen/miniconda3/envs/fmri_env/bin/python high_click_viewer/scripts/build_viewer_data.py
```

To regenerate the participant-solutions summary used by the Participant solutions page:

```bash
/Users/sirikagen/miniconda3/envs/fmri_env/bin/python high_click_viewer/scripts/build_solution_paths_data.py
```

To regenerate the solution-path summary used by the Solution Paths page:

```bash
/Users/sirikagen/miniconda3/envs/fmri_env/bin/python high_click_viewer/scripts/build_solution_paths_summary.py
```

## Run locally
From the repository root:

```bash
python -m http.server 8000 --directory .
```

Then open:
- `http://localhost:8000/high_click_viewer/index.html`

The ARC gallery is linked from the homepage, and it loads task JSON files directly from `ARC-AGI-master/data/`.
