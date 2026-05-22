const ARC_COLORS = [
  "#111111", "#0a84ff", "#ff4136", "#2ecc40", "#ffdc00",
  "#aaaaaa", "#f58231", "#7fdbff", "#b10dc9", "#870c25",
];

function colorFor(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || n >= ARC_COLORS.length) return "#ffffff";
  return ARC_COLORS[n];
}

function gridSize(matrix) {
  const rows = Array.isArray(matrix) ? matrix.length : 0;
  const cols = rows > 0 && Array.isArray(matrix[0]) ? matrix[0].length : 0;
  return { rows, cols };
}

function drawGrid(container, matrix) {
  container.innerHTML = "";
  const { rows, cols } = gridSize(matrix);
  if (!rows || !cols) { container.textContent = "No grid data"; return; }
  container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
  container.style.gridTemplateRows = `repeat(${rows}, 1fr)`;
  matrix.forEach((row) => row.forEach((value) => {
    const cell = document.createElement("div");
    cell.className = "cell";
    cell.style.background = colorFor(value);
    container.appendChild(cell);
  }));
}

function drawChangesGrid(container, matrix) {
  container.innerHTML = "";
  const { rows, cols } = gridSize(matrix);
  if (!rows || !cols) { container.textContent = "No change data"; return; }
  container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
  container.style.gridTemplateRows = `repeat(${rows}, 1fr)`;
  matrix.forEach((row) => row.forEach((value) => {
    const cell = document.createElement("div");
    cell.className = value == null ? "cell diff-empty" : "cell diff-filled";
    cell.style.background = value == null ? "rgba(31, 34, 48, 0.04)" : colorFor(value);
    container.appendChild(cell);
  }));
}

function buildChangesOnlyGrid(inputGrid, outputGrid) {
  const inputSize = gridSize(inputGrid);
  const outputSize = gridSize(outputGrid);
  const rows = Math.max(inputSize.rows, outputSize.rows);
  const cols = Math.max(inputSize.cols, outputSize.cols);
  const diffGrid = [];
  for (let r = 0; r < rows; r++) {
    const row = [];
    for (let c = 0; c < cols; c++) {
      const inputValue = inputGrid?.[r]?.[c];
      const outputValue = outputGrid?.[r]?.[c];
      row.push(inputValue !== outputValue && outputValue !== undefined ? outputValue : null);
    }
    diffGrid.push(row);
  }
  return diffGrid;
}

function frameMatchesChangesOnly(frame, changesOnly) {
  const gridBefore = frame.grid_before || [];
  const gridAfter = frame.grid_after || frame.grid || [];
  const afterSize = gridSize(gridAfter);
  const changesSize = gridSize(changesOnly);
  const rows = Math.max(afterSize.rows, changesSize.rows);
  const cols = Math.max(afterSize.cols, changesSize.cols);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const before = gridBefore[r]?.[c] ?? null;
      const after = gridAfter[r]?.[c] ?? null;
      if (before === after) continue;
      const required = changesOnly[r]?.[c] ?? null;
      if (after !== required) return false;
    }
  }
  return true;
}

function createChip(text, className = "participant-chip") {
  const chip = document.createElement("span");
  chip.className = className;
  chip.textContent = text;
  return chip;
}

async function fetchSolutionSummary() {
  const res = await fetch("data/solution_paths.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`Unable to load solution_paths.json (${res.status})`);
  return res.json();
}

const taskPayloadCache = new Map();

async function fetchTaskPayload(taskType, taskName) {
  const key = `${taskType}:${taskName}`;
  if (taskPayloadCache.has(key)) return taskPayloadCache.get(key);
  const directory = taskType === "evaluation" ? "evaluation" : "training";
  const res = await fetch(`../ARC-AGI-master/data/${directory}/${taskName}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Unable to load ${taskName}`);
  const payload = await res.json();
  taskPayloadCache.set(key, payload);
  return payload;
}

// Builds a playthrough player inside containerEl for one task record.
// Returns a stopPlayback function so the caller can clean up timers.
function buildPlayer(containerEl, taskRecord, testInputGrid, testOutputGrid) {
  const steps = taskRecord.off_path_steps || [];
  const changesOnlyGrid = buildChangesOnlyGrid(testInputGrid, testOutputGrid);
  let currentFrameIndex = 0;
  let playbackTimer = null;

  containerEl.innerHTML = "";

  const header = document.createElement("div");
  header.className = "task-detail-header";
  const title = document.createElement("h3");
  title.textContent = taskRecord.task_name;
  const badges = document.createElement("div");
  badges.className = "task-badge-row";
  badges.appendChild(createChip(taskRecord.task_type === "evaluation" ? "Evaluation" : "Training", "task-badge"));
  badges.appendChild(createChip(`Attempt ${taskRecord.attempt_number}`, "task-badge"));
  badges.appendChild(createChip(`${taskRecord.wrong_step_count} off-path step${taskRecord.wrong_step_count === 1 ? "" : "s"}`, "task-badge"));
  header.appendChild(title);
  header.appendChild(badges);
  containerEl.appendChild(header);

  if (steps.length === 0) {
    const empty = document.createElement("p");
    empty.className = "playbyplay-empty";
    empty.textContent = "No off-path steps for this puzzle — all moves were on the solution path.";
    containerEl.appendChild(empty);
    return () => {};
  }

  // Grid visuals
  const visualWrap = document.createElement("div");
  visualWrap.className = "offpath-replay-grid-wrap";

  function makePane(labelText) {
    const pane = document.createElement("div");
    const h = document.createElement("h3");
    h.textContent = labelText;
    const grid = document.createElement("div");
    grid.className = "arc-grid";
    pane.appendChild(h);
    pane.appendChild(grid);
    return { pane, grid };
  }

  const { pane: inputPane, grid: inputGridEl } = makePane("Task input");
  const { pane: solvedPane, grid: solvedGridEl } = makePane("Solved output");
  const { pane: outputPane, grid: outputGridEl } = makePane("Participant frame");
  const { pane: changesPane, grid: changesGridEl } = makePane("Required changes");

  visualWrap.appendChild(inputPane);
  visualWrap.appendChild(solvedPane);
  visualWrap.appendChild(outputPane);
  visualWrap.appendChild(changesPane);

  drawGrid(inputGridEl, testInputGrid);
  drawGrid(solvedGridEl, testOutputGrid);

  // Controls
  const controls = document.createElement("section");
  controls.className = "controls";

  const timelineRow = document.createElement("div");
  timelineRow.className = "timeline-row";
  const sliderEl = document.createElement("input");
  sliderEl.type = "range";
  sliderEl.min = "0";
  sliderEl.max = String(Math.max(0, steps.length - 1));
  sliderEl.step = "1";
  sliderEl.value = "0";
  const frameLabelEl = document.createElement("p");
  timelineRow.appendChild(sliderEl);
  timelineRow.appendChild(frameLabelEl);

  const buttonRow = document.createElement("div");
  buttonRow.className = "button-row";
  const firstBtn = document.createElement("button"); firstBtn.textContent = "First";
  const prevBtn = document.createElement("button"); prevBtn.textContent = "Prev";
  const playPauseBtn = document.createElement("button"); playPauseBtn.textContent = "Play";
  const nextBtn = document.createElement("button"); nextBtn.textContent = "Next";
  const lastBtn = document.createElement("button"); lastBtn.textContent = "Last";
  [firstBtn, prevBtn, playPauseBtn, nextBtn, lastBtn].forEach((b) => buttonRow.appendChild(b));

  const speedRow = document.createElement("div");
  speedRow.className = "speed-row";
  const speedLabel = document.createElement("label");
  speedLabel.textContent = "Speed";
  const speedSelect = document.createElement("select");
  speedSelect.innerHTML = `
    <option value="900">0.5x</option>
    <option value="550" selected>1x</option>
    <option value="300">2x</option>
    <option value="180">3x</option>
  `;
  speedRow.appendChild(speedLabel);
  speedRow.appendChild(speedSelect);

  const actionInfoEl = document.createElement("p");
  const currentStepPanel = document.createElement("div");
  currentStepPanel.className = "playbyplay-step is-active";

  const timeline = document.createElement("div");
  timeline.className = "playbyplay-timeline";

  controls.appendChild(timelineRow);
  controls.appendChild(buttonRow);
  controls.appendChild(speedRow);
  controls.appendChild(actionInfoEl);
  controls.appendChild(currentStepPanel);

  containerEl.appendChild(visualWrap);
  containerEl.appendChild(controls);
  containerEl.appendChild(timeline);

  function stopPlayback() {
    if (playbackTimer) { clearInterval(playbackTimer); playbackTimer = null; }
    playPauseBtn.textContent = "Play";
  }

  function renderFrame() {
    const frame = steps[currentFrameIndex];
    frameLabelEl.textContent = `Frame ${currentFrameIndex + 1} / ${steps.length}`;
    if (!frame) return;

    const isOnPath = frameMatchesChangesOnly(frame, changesOnlyGrid);
    const derivedReason = frame.reason || (isOnPath ? "" : "deviates from required changes");

    actionInfoEl.textContent = `${frame.action_id}. ${frame.label}${derivedReason ? ` | ${derivedReason}` : ""}`;
    drawGrid(outputGridEl, frame.grid_after || frame.grid || []);
    drawChangesGrid(changesGridEl, changesOnlyGrid);

    currentStepPanel.innerHTML = "";
    currentStepPanel.className = "playbyplay-step is-active";
    const head = document.createElement("div");
    head.className = "playbyplay-step-head";
    const idx = document.createElement("span");
    idx.className = "playbyplay-step-index";
    idx.textContent = `Frame ${currentFrameIndex + 1}`;
    const lbl = document.createElement("span");
    lbl.className = "playbyplay-step-label";
    lbl.textContent = frame.label || frame.action || "unknown";
    head.appendChild(idx);
    head.appendChild(lbl);
    const reasonEl = document.createElement("p");
    reasonEl.className = "playbyplay-step-reason";
    reasonEl.textContent = derivedReason || "follows required changes path";
    currentStepPanel.appendChild(head);
    currentStepPanel.appendChild(reasonEl);

    sliderEl.value = String(currentFrameIndex);

    timeline.innerHTML = "";
    steps.forEach((step, i) => {
      const item = document.createElement("div");
      item.className = `playbyplay-step${i === currentFrameIndex ? " is-active" : ""}`;
      const h = document.createElement("div");
      h.className = "playbyplay-step-head";
      const si = document.createElement("span");
      si.className = "playbyplay-step-index";
      si.textContent = `Frame ${i + 1}`;
      const sl = document.createElement("span");
      sl.className = "playbyplay-step-label";
      sl.textContent = step.label || step.action || "unknown";
      h.appendChild(si);
      h.appendChild(sl);
      const sr = document.createElement("p");
      sr.className = "playbyplay-step-reason";
      sr.textContent = step.reason || "off-path";
      item.appendChild(h);
      item.appendChild(sr);
      timeline.appendChild(item);
    });
  }

  sliderEl.addEventListener("input", () => { stopPlayback(); currentFrameIndex = Number(sliderEl.value); renderFrame(); });
  firstBtn.addEventListener("click", () => { stopPlayback(); currentFrameIndex = 0; renderFrame(); });
  prevBtn.addEventListener("click", () => { stopPlayback(); currentFrameIndex = Math.max(0, currentFrameIndex - 1); renderFrame(); });
  nextBtn.addEventListener("click", () => { stopPlayback(); currentFrameIndex = Math.min(steps.length - 1, currentFrameIndex + 1); renderFrame(); });
  lastBtn.addEventListener("click", () => { stopPlayback(); currentFrameIndex = Math.max(0, steps.length - 1); renderFrame(); });
  playPauseBtn.addEventListener("click", () => {
    if (playbackTimer) { stopPlayback(); return; }
    playPauseBtn.textContent = "Pause";
    playbackTimer = setInterval(() => {
      if (currentFrameIndex >= steps.length - 1) { stopPlayback(); return; }
      currentFrameIndex += 1;
      renderFrame();
    }, Number(speedSelect.value));
  });
  speedSelect.addEventListener("change", () => { if (playbackTimer) stopPlayback(); });

  renderFrame();
  return stopPlayback;
}

(async function initHighOffPathPage() {
  const statusEl = document.getElementById("hopStatus");
  const participantListEl = document.getElementById("hopParticipantList");
  const detailEl = document.getElementById("hopDetail");

  let stopCurrentPlayback = null;

  try {
    const summary = await fetchSolutionSummary();

    // Aggregate per participant across all tasks
    const participantMap = new Map();
    for (const task of (summary.tasks || [])) {
      for (const path of (task.solution_paths || [])) {
        if (!path.complete) continue;
        const pid = path.participant_id;
        if (!participantMap.has(pid)) {
          participantMap.set(pid, { totalWrongSteps: 0, taskCount: 0, tasks: [] });
        }
        const entry = participantMap.get(pid);
        entry.totalWrongSteps += path.wrong_step_count;
        entry.taskCount += 1;
        entry.tasks.push({
          task_type: task.task_type,
          task_name: task.task_name,
          attempt_number: path.attempt_number,
          wrong_step_count: path.wrong_step_count,
          off_path_steps: path.off_path_steps,
        });
      }
    }

    const participants = [...participantMap.entries()]
      .map(([pid, data]) => ({ participant_id: pid, ...data }))
      .sort((a, b) => b.totalWrongSteps - a.totalWrongSteps);

    statusEl.textContent = `${participants.length} participants across ${(summary.tasks || []).length} tasks loaded.`;

    function buildParticipantDetail(participant) {
      if (stopCurrentPlayback) { stopCurrentPlayback(); stopCurrentPlayback = null; }
      detailEl.innerHTML = "";

      // Header
      const header = document.createElement("div");
      header.className = "task-detail-header";
      const title = document.createElement("h3");
      title.textContent = participant.participant_id;
      const badges = document.createElement("div");
      badges.className = "task-badge-row";
      badges.appendChild(createChip(`${participant.totalWrongSteps} total off-path steps`, "task-badge"));
      badges.appendChild(createChip(`${participant.taskCount} puzzle${participant.taskCount === 1 ? "" : "s"} solved`, "task-badge"));
      const avg = participant.taskCount > 0 ? (participant.totalWrongSteps / participant.taskCount).toFixed(1) : "0";
      badges.appendChild(createChip(`avg ${avg} per puzzle`, "task-badge"));
      header.appendChild(title);
      header.appendChild(badges);
      detailEl.appendChild(header);

      const label = document.createElement("p");
      label.className = "semantic-label";
      label.textContent = "Puzzles completed — sorted by off-path steps";
      detailEl.appendChild(label);

      const taskListWrap = document.createElement("div");
      taskListWrap.className = "playbyplay-cards";

      const playerContainer = document.createElement("div");
      playerContainer.className = "card";
      playerContainer.style.marginTop = "0.75rem";

      detailEl.appendChild(taskListWrap);
      detailEl.appendChild(playerContainer);

      const sortedTasks = [...participant.tasks].sort((a, b) => b.wrong_step_count - a.wrong_step_count);

      async function loadTask(index) {
        if (stopCurrentPlayback) { stopCurrentPlayback(); stopCurrentPlayback = null; }

        [...taskListWrap.querySelectorAll(".playbyplay-card")].forEach((c, i) => {
          c.classList.toggle("is-active", i === index);
        });

        const taskRecord = sortedTasks[index];
        playerContainer.innerHTML = `<p class="playbyplay-empty">Loading ${taskRecord.task_name}…</p>`;

        try {
          const payload = await fetchTaskPayload(taskRecord.task_type, taskRecord.task_name);
          const firstTest = Array.isArray(payload.test) && payload.test.length > 0 ? payload.test[0] : {};
          const testInputGrid = firstTest.input || [];
          const testOutputGrid = firstTest.output || [];
          stopCurrentPlayback = buildPlayer(playerContainer, taskRecord, testInputGrid, testOutputGrid);
        } catch (err) {
          playerContainer.innerHTML = `<p class="playbyplay-empty">Unable to load ${taskRecord.task_name}: ${err.message}</p>`;
        }
      }

      sortedTasks.forEach((taskRecord, idx) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = `playbyplay-card${idx === 0 ? " is-active" : ""}`;

        const cardHeader = document.createElement("div");
        cardHeader.className = "playbyplay-card-header";
        const taskTitle = document.createElement("span");
        taskTitle.className = "playbyplay-title";
        taskTitle.textContent = taskRecord.task_name;
        cardHeader.appendChild(taskTitle);
        cardHeader.appendChild(createChip(taskRecord.task_type === "evaluation" ? "Eval" : "Train", "task-badge"));
        cardHeader.appendChild(createChip(`${taskRecord.wrong_step_count} off-path`, "task-badge"));

        const meta = document.createElement("p");
        meta.className = "task-card-meta";
        meta.textContent = `Attempt ${taskRecord.attempt_number} · ${taskRecord.off_path_steps.length} frame${taskRecord.off_path_steps.length === 1 ? "" : "s"} in timeline`;

        card.appendChild(cardHeader);
        card.appendChild(meta);
        card.addEventListener("click", () => loadTask(idx));
        taskListWrap.appendChild(card);
      });

      loadTask(0);
    }

    // Render participant list
    participants.forEach((participant, rank) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "playbyplay-card";

      const cardHeader = document.createElement("div");
      cardHeader.className = "playbyplay-card-header";
      cardHeader.appendChild(createChip(`#${rank + 1}`, "task-badge"));
      const idSpan = document.createElement("span");
      idSpan.className = "playbyplay-title";
      idSpan.textContent = participant.participant_id;
      cardHeader.appendChild(idSpan);

      const meta = document.createElement("p");
      meta.className = "task-card-meta";
      const avg = participant.taskCount > 0 ? (participant.totalWrongSteps / participant.taskCount).toFixed(1) : "0";
      meta.textContent = `${participant.totalWrongSteps} off-path steps · ${participant.taskCount} puzzle${participant.taskCount === 1 ? "" : "s"} · avg ${avg}`;

      card.appendChild(cardHeader);
      card.appendChild(meta);
      card.addEventListener("click", () => {
        [...participantListEl.querySelectorAll(".playbyplay-card")].forEach((c) => c.classList.remove("is-active"));
        card.classList.add("is-active");
        buildParticipantDetail(participant);
      });
      participantListEl.appendChild(card);
    });

    // Load the top participant by default
    if (participants.length > 0) {
      participantListEl.querySelector(".playbyplay-card")?.classList.add("is-active");
      buildParticipantDetail(participants[0]);
    }

  } catch (err) {
    statusEl.textContent = `Error loading data: ${err.message}`;
    detailEl.innerHTML = `<p class="playbyplay-empty">${err.message}</p>`;
  }
})();
