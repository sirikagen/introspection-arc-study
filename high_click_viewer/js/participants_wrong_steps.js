const ARC_COLORS = [
  "#111111",
  "#0a84ff",
  "#ff4136",
  "#2ecc40",
  "#ffdc00",
  "#aaaaaa",
  "#f58231",
  "#7fdbff",
  "#b10dc9",
  "#870c25",
];

function colorFor(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || n >= ARC_COLORS.length) {
    return "#ffffff";
  }
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

  if (!rows || !cols) {
    container.textContent = "No grid data";
    return;
  }

  container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
  container.style.gridTemplateRows = `repeat(${rows}, 1fr)`;

  matrix.forEach((row) => {
    row.forEach((value) => {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.style.background = colorFor(value);
      container.appendChild(cell);
    });
  });
}

function taskKey(taskType, taskName) {
  return `${taskType}:${taskName}`;
}

function arcTaskUrl(task) {
  const directory = task.task_type === "evaluation" ? "evaluation" : "training";
  return `../ARC-AGI-master/data/${directory}/${task.task_name}`;
}

async function fetchSolutionSummary() {
  const res = await fetch("data/solution_paths.json", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Unable to load solution_paths.json (${res.status})`);
  }
  return res.json();
}

async function fetchTaskJson(task) {
  const res = await fetch(arcTaskUrl(task), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Unable to load ARC task JSON for ${task.task_name}`);
  }
  return res.json();
}

function createChip(text, className = "participant-chip") {
  const chip = document.createElement("span");
  chip.className = className;
  chip.textContent = text;
  return chip;
}

function createOffPathChip(text, reason) {
  const chip = document.createElement("span");
  chip.className = "offpath-chip";
  chip.textContent = reason ? `${text} · ${reason}` : text;
  return chip;
}

function renderTestPairs(detailEl, payload) {
  const tests = Array.isArray(payload.test) ? payload.test : [];

  const heading = document.createElement("h3");
  heading.textContent = "Test pairs";
  detailEl.appendChild(heading);

  if (tests.length === 0) {
    const empty = document.createElement("p");
    empty.className = "playbyplay-empty";
    empty.textContent = "No test pairs available.";
    detailEl.appendChild(empty);
    return;
  }

  tests.forEach((pair, index) => {
    const card = document.createElement("div");
    card.className = "example-card";

    const title = document.createElement("p");
    title.className = "example-title";
    title.textContent = `Test ${index + 1}`;

    const grids = document.createElement("div");
    grids.className = "example-grids";

    const inWrap = document.createElement("div");
    const outWrap = document.createElement("div");
    const inLabel = document.createElement("p");
    inLabel.className = "example-grid-label";
    inLabel.textContent = "Input";
    const outLabel = document.createElement("p");
    outLabel.className = "example-grid-label";
    outLabel.textContent = "Output";
    const inGrid = document.createElement("div");
    inGrid.className = "mini-arc-grid";
    const outGrid = document.createElement("div");
    outGrid.className = "mini-arc-grid";
    drawGrid(inGrid, pair.input || []);
    drawGrid(outGrid, pair.output || []);
    inWrap.appendChild(inLabel);
    inWrap.appendChild(inGrid);
    outWrap.appendChild(outLabel);
    outWrap.appendChild(outGrid);
    grids.appendChild(inWrap);
    grids.appendChild(outWrap);

    card.appendChild(title);
    card.appendChild(grids);
    detailEl.appendChild(card);
  });
}

function renderTimeline(steps, activeIndex, timelineEl) {
  timelineEl.innerHTML = "";

  if (!steps.length) {
    const empty = document.createElement("p");
    empty.className = "playbyplay-empty";
    empty.textContent = "No off-path steps were recorded for this participant.";
    timelineEl.appendChild(empty);
    return;
  }

  steps.forEach((step, index) => {
    const item = document.createElement("div");
    item.className = `playbyplay-step${index === activeIndex ? " is-active" : ""}`;

    const head = document.createElement("div");
    head.className = "playbyplay-step-head";

    const idx = document.createElement("span");
    idx.className = "playbyplay-step-index";
    idx.textContent = `Frame ${index + 1}`;

    const label = document.createElement("span");
    label.className = "playbyplay-step-label";
    label.textContent = step.label || step.action || "unknown";

    head.appendChild(idx);
    head.appendChild(label);

    const reason = document.createElement("p");
    reason.className = "playbyplay-step-reason";
    reason.textContent = step.reason || "off-path";

    item.appendChild(head);
    item.appendChild(reason);
    timelineEl.appendChild(item);
  });
}

(async function initOffPathPlayByPlayPage() {
  const statusEl = document.getElementById("playStatus");
  const searchEl = document.getElementById("playSearch");
  const filterButtons = [...document.querySelectorAll(".filter-button")];
  const participantFilterButtons = [...document.querySelectorAll("[data-participant-filter]")];
  const gridEl = document.getElementById("playGrid");
  const detailEl = document.getElementById("playDetail");

  const taskCache = new Map();
  let tasks = [];
  let filteredSet = "all";
  let searchTerm = "";
  let selectedTaskKey = null;
  let selectedTask = null;

  const participantFilters = {
    complete: false,
    solved: false,
    attemptOne: false,
  };

  function updateParticipantFilterButtons() {
    participantFilterButtons.forEach((button) => {
      const key = button.dataset.participantFilter || "";
      const active = Boolean(participantFilters[key]);
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  function getPathParticipantId(path) {
    return path.participant_id || path.hashed_id || "";
  }

  function matchesParticipantFilters(path) {
    return (!participantFilters.complete || Boolean(path.complete))
      && (!participantFilters.solved || Boolean(path.solved))
      && (!participantFilters.attemptOne || Number(path.attempt_number) === 1);
  }

  function getVisiblePaths(task) {
    return (task.solution_paths || []).filter(matchesParticipantFilters);
  }

  function summarizeTask(task) {
    const paths = getVisiblePaths(task);
    const participantIds = [...new Set(paths.map(getPathParticipantId).filter(Boolean))];
    const wrongStepTotal = paths.reduce((sum, path) => sum + Number(path.wrong_step_count || 0), 0);
    return { paths, participantIds, wrongStepTotal };
  }

  async function loadPayload(task) {
    const key = taskKey(task.task_type, task.task_name);
    let payload = taskCache.get(key);
    if (!payload) {
      payload = await fetchTaskJson(task);
      taskCache.set(key, payload);
    }
    return payload;
  }

  function renderTaskCard(task, summaryData) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "task-card";
    card.dataset.taskKey = taskKey(task.task_type, task.task_name);

    const title = document.createElement("p");
    title.className = "task-card-title";
    title.textContent = task.task_name;

    const meta = document.createElement("p");
    meta.className = "task-card-meta";
    meta.textContent = `${task.task_type === "evaluation" ? "Evaluation" : "Training"} set`;

    const count = document.createElement("p");
    count.className = "task-card-meta";
    count.textContent = `Completed by ${summaryData.participantIds.length} participant${summaryData.participantIds.length === 1 ? "" : "s"}`;

    const wrong = document.createElement("p");
    wrong.className = "task-card-meta";
    wrong.textContent = `${summaryData.wrongStepTotal} off-path step${summaryData.wrongStepTotal === 1 ? "" : "s"}`;

    const chips = document.createElement("div");
    chips.className = "chip-row";
    summaryData.participantIds.slice(0, 3).forEach((id) => chips.appendChild(createChip(id)));
    if (summaryData.participantIds.length > 3) {
      chips.appendChild(createChip(`+${summaryData.participantIds.length - 3} more`));
    }

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(count);
    card.appendChild(wrong);
    card.appendChild(chips);
    return card;
  }

  function buildPlayer(task, payload) {
    selectedTask = task;
    selectedTaskKey = taskKey(task.task_type, task.task_name);
    detailEl.innerHTML = "";

    const summaryData = summarizeTask(task);
    const visiblePaths = summaryData.paths;
    const firstTest = Array.isArray(payload.test) && payload.test.length > 0 ? payload.test[0] : {};
    const testInputGrid = firstTest.input || [];
    const testOutputGrid = firstTest.output || [];

    const header = document.createElement("div");
    header.className = "task-detail-header";

    const title = document.createElement("h3");
    title.textContent = task.task_name;

    const badges = document.createElement("div");
    badges.className = "task-badge-row";
    badges.appendChild(createChip(task.task_type === "evaluation" ? "Evaluation" : "Training", "task-badge"));
    badges.appendChild(createChip(`${summaryData.participantIds.length} participant${summaryData.participantIds.length === 1 ? "" : "s"}`, "task-badge"));
    badges.appendChild(createChip(`${summaryData.wrongStepTotal} off-path step${summaryData.wrongStepTotal === 1 ? "" : "s"}`, "task-badge"));

    const subtitle = document.createElement("p");
    subtitle.className = "subtitle";
    subtitle.textContent = "Use the controls below to play through only the recorded off-path steps.";

    header.appendChild(title);
    header.appendChild(badges);
    header.appendChild(subtitle);
    detailEl.appendChild(header);

    renderTestPairs(detailEl, payload);

    const participantLabel = document.createElement("p");
    participantLabel.className = "semantic-label";
    participantLabel.textContent = "Participants who completed this puzzle";
    detailEl.appendChild(participantLabel);

    const participantRow = document.createElement("div");
    participantRow.className = "chip-row";
    if (summaryData.participantIds.length === 0) {
      participantRow.appendChild(createChip("None yet"));
    } else {
      summaryData.participantIds.forEach((id) => participantRow.appendChild(createChip(id)));
    }
    detailEl.appendChild(participantRow);

    const playerShell = document.createElement("section");
    playerShell.className = "card";
    playerShell.style.marginTop = "0.75rem";

    const participantHeading = document.createElement("h3");
    participantHeading.textContent = visiblePaths[0] ? getPathParticipantId(visiblePaths[0]) : "No participant";

    const participantMeta = document.createElement("p");
    participantMeta.className = "task-card-meta";

    const participantChipRow = document.createElement("div");
    participantChipRow.className = "chip-row";

    const visualWrap = document.createElement("div");
    visualWrap.className = "offpath-replay-grid-wrap";

    const inputPane = document.createElement("div");
    const inputTitle = document.createElement("h3");
    inputTitle.textContent = "Task input";
    const inputGridEl = document.createElement("div");
    inputGridEl.className = "arc-grid";
    inputPane.appendChild(inputTitle);
    inputPane.appendChild(inputGridEl);

    const outputPane = document.createElement("div");
    const outputTitle = document.createElement("h3");
    outputTitle.textContent = "Participant off-path frame";
    const outputGridEl = document.createElement("div");
    outputGridEl.className = "arc-grid";
    outputPane.appendChild(outputTitle);
    outputPane.appendChild(outputGridEl);

    const targetPane = document.createElement("div");
    const targetTitle = document.createElement("h3");
    targetTitle.textContent = "Solved target output";
    const targetGridEl = document.createElement("div");
    targetGridEl.className = "arc-grid";
    targetPane.appendChild(targetTitle);
    targetPane.appendChild(targetGridEl);

    visualWrap.appendChild(inputPane);
    visualWrap.appendChild(outputPane);
    visualWrap.appendChild(targetPane);

    const currentStepPanel = document.createElement("div");
    currentStepPanel.className = "playbyplay-step is-active";

    const timeline = document.createElement("div");
    timeline.className = "playbyplay-timeline";

    const controls = document.createElement("section");
    controls.className = "controls";

    const timelineRow = document.createElement("div");
    timelineRow.className = "timeline-row";

    const sliderEl = document.createElement("input");
    sliderEl.type = "range";
    sliderEl.min = "0";
    sliderEl.max = "0";
    sliderEl.step = "1";

    const frameLabelEl = document.createElement("p");
    frameLabelEl.id = "frameLabel";

    timelineRow.appendChild(sliderEl);
    timelineRow.appendChild(frameLabelEl);

    const buttonRow = document.createElement("div");
    buttonRow.className = "button-row";

    const firstBtn = document.createElement("button");
    firstBtn.textContent = "First";
    const prevBtn = document.createElement("button");
    prevBtn.textContent = "Prev";
    const playPauseBtn = document.createElement("button");
    playPauseBtn.textContent = "Play";
    const nextBtn = document.createElement("button");
    nextBtn.textContent = "Next";
    const lastBtn = document.createElement("button");
    lastBtn.textContent = "Last";

    buttonRow.appendChild(firstBtn);
    buttonRow.appendChild(prevBtn);
    buttonRow.appendChild(playPauseBtn);
    buttonRow.appendChild(nextBtn);
    buttonRow.appendChild(lastBtn);

    const speedRow = document.createElement("div");
    speedRow.className = "speed-row";

    const speedLabel = document.createElement("label");
    speedLabel.htmlFor = "playSpeedSelect";
    speedLabel.textContent = "Speed";

    const speedSelect = document.createElement("select");
    speedSelect.id = "playSpeedSelect";
    speedSelect.innerHTML = `
      <option value="900">0.5x</option>
      <option value="550" selected>1x</option>
      <option value="300">2x</option>
      <option value="180">3x</option>
    `;

    speedRow.appendChild(speedLabel);
    speedRow.appendChild(speedSelect);

    const actionInfoEl = document.createElement("p");
    actionInfoEl.id = "actionInfo";

    const playerBody = document.createElement("div");
    playerBody.className = "gallery-detail";
    playerBody.appendChild(participantHeading);
    playerBody.appendChild(participantMeta);
    playerBody.appendChild(participantChipRow);
    playerBody.appendChild(visualWrap);
    playerBody.appendChild(controls);
    playerBody.appendChild(timeline);

    controls.appendChild(timelineRow);
    controls.appendChild(buttonRow);
    controls.appendChild(speedRow);
    controls.appendChild(actionInfoEl);
    controls.appendChild(currentStepPanel);

    playerShell.appendChild(playerBody);
    detailEl.appendChild(playerShell);

    let activeParticipantIndex = 0;
    let currentFrameIndex = 0;
    let activeSteps = [];
    let playbackTimer = null;

    drawGrid(inputGridEl, testInputGrid);
    drawGrid(targetGridEl, testOutputGrid);

    function stopPlayback() {
      if (playbackTimer) {
        clearInterval(playbackTimer);
        playbackTimer = null;
      }
      playPauseBtn.textContent = "Play";
    }

    function renderFrame() {
      const frame = activeSteps[currentFrameIndex];
      frameLabelEl.textContent = activeSteps.length
        ? `Frame ${currentFrameIndex + 1} / ${activeSteps.length}`
        : "Frame 0 / 0";

      if (!frame) {
        actionInfoEl.textContent = "No off-path steps available.";
        currentStepPanel.innerHTML = "";
        currentStepPanel.className = "playbyplay-step is-active";
        currentStepPanel.textContent = "No off-path step selected.";
        drawGrid(outputGridEl, testInputGrid);
        renderTimeline(activeSteps, -1, timeline);
        return;
      }

      actionInfoEl.textContent = `${frame.action_id}. ${frame.label}${frame.reason ? ` | ${frame.reason}` : ""}`;
      drawGrid(outputGridEl, frame.grid_after || frame.grid || []);

      currentStepPanel.innerHTML = "";
      currentStepPanel.className = "playbyplay-step is-active";
      const head = document.createElement("div");
      head.className = "playbyplay-step-head";
      const idx = document.createElement("span");
      idx.className = "playbyplay-step-index";
      idx.textContent = `Frame ${currentFrameIndex + 1}`;
      const label = document.createElement("span");
      label.className = "playbyplay-step-label";
      label.textContent = frame.label || frame.action || "unknown";
      head.appendChild(idx);
      head.appendChild(label);
      const reason = document.createElement("p");
      reason.className = "playbyplay-step-reason";
      reason.textContent = frame.reason || "off-path";
      currentStepPanel.appendChild(head);
      currentStepPanel.appendChild(reason);

      renderTimeline(activeSteps, currentFrameIndex, timeline);
      sliderEl.value = String(currentFrameIndex);
    }

    function loadParticipant(index) {
      stopPlayback();
      activeParticipantIndex = index;
      currentFrameIndex = 0;

      const record = visiblePaths[index];
      activeSteps = record?.off_path_steps || [];

      participantHeading.textContent = record ? getPathParticipantId(record) : "No participant";
      participantMeta.textContent = record
        ? `Attempt ${record.attempt_number} | ${record.wrong_step_count} off-path step${record.wrong_step_count === 1 ? "" : "s"}`
        : "";

      participantChipRow.innerHTML = "";
      if (record && activeSteps.length > 0) {
        activeSteps.forEach((step) => participantChipRow.appendChild(createOffPathChip(step.label, step.reason)));
      } else {
        participantChipRow.appendChild(createChip("No off-path steps", "participant-chip"));
      }

      sliderEl.min = "0";
      sliderEl.max = String(Math.max(0, activeSteps.length - 1));
      sliderEl.value = "0";

      const participantCards = [...playerBody.querySelectorAll(".playbyplay-card")];
      participantCards.forEach((card, idx) => card.classList.toggle("is-active", idx === activeParticipantIndex));

      const disabled = activeSteps.length === 0;
      sliderEl.disabled = disabled;
      playPauseBtn.disabled = disabled;
      firstBtn.disabled = disabled;
      prevBtn.disabled = disabled;
      nextBtn.disabled = disabled;
      lastBtn.disabled = disabled;

      renderFrame();
    }

    const participantListWrap = document.createElement("div");
    participantListWrap.className = "playbyplay-cards";

    if (visiblePaths.length === 0) {
      const empty = document.createElement("p");
      empty.className = "playbyplay-empty";
      empty.textContent = "No completed solution paths match the active participant filters.";
      participantListWrap.appendChild(empty);
    } else {
      visiblePaths.forEach((path, idx) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = `playbyplay-card${idx === 0 ? " is-active" : ""}`;

        const cardHeader = document.createElement("div");
        cardHeader.className = "playbyplay-card-header";

        const title = document.createElement("span");
        title.className = "playbyplay-title";
        title.textContent = getPathParticipantId(path);

        cardHeader.appendChild(title);
        cardHeader.appendChild(createChip(`Attempt ${path.attempt_number}`, "task-badge"));
        cardHeader.appendChild(createChip(`${path.wrong_step_count} off-path step${path.wrong_step_count === 1 ? "" : "s"}`, "task-badge"));

        const summary = document.createElement("p");
        summary.className = "task-card-meta";
        summary.textContent = `${path.off_path_steps.length} frame${path.off_path_steps.length === 1 ? "" : "s"} in the timeline`;

        card.appendChild(cardHeader);
        card.appendChild(summary);

        card.addEventListener("click", () => {
          [...participantListWrap.querySelectorAll(".playbyplay-card")].forEach((item) => item.classList.remove("is-active"));
          card.classList.add("is-active");
          loadParticipant(idx);
        });

        participantListWrap.appendChild(card);
      });
    }

    playerBody.insertBefore(participantListWrap, playerBody.firstChild);

    sliderEl.addEventListener("input", () => {
      stopPlayback();
      currentFrameIndex = Number(sliderEl.value);
      renderFrame();
    });

    firstBtn.addEventListener("click", () => {
      stopPlayback();
      currentFrameIndex = 0;
      renderFrame();
    });

    prevBtn.addEventListener("click", () => {
      stopPlayback();
      currentFrameIndex = Math.max(0, currentFrameIndex - 1);
      renderFrame();
    });

    nextBtn.addEventListener("click", () => {
      stopPlayback();
      currentFrameIndex = Math.min(activeSteps.length - 1, currentFrameIndex + 1);
      renderFrame();
    });

    lastBtn.addEventListener("click", () => {
      stopPlayback();
      currentFrameIndex = Math.max(0, activeSteps.length - 1);
      renderFrame();
    });

    playPauseBtn.addEventListener("click", () => {
      if (!activeSteps.length) {
        return;
      }

      if (playbackTimer) {
        stopPlayback();
        return;
      }

      playPauseBtn.textContent = "Pause";
      playbackTimer = setInterval(() => {
        if (currentFrameIndex >= activeSteps.length - 1) {
          stopPlayback();
          return;
        }
        currentFrameIndex += 1;
        renderFrame();
      }, Number(speedSelect.value));
    });

    speedSelect.addEventListener("change", () => {
      if (playbackTimer) {
        stopPlayback();
      }
    });

    loadParticipant(0);
  }

  function renderGrid() {
    const needle = searchTerm.trim().toLowerCase();
    gridEl.innerHTML = "";

    tasks.forEach((task) => {
      const key = taskKey(task.task_type, task.task_name);
      const summaryData = summarizeTask(task);
      const matchesSet = filteredSet === "all" || task.task_type === filteredSet;
      const matchesSearch = !needle || task.task_name.toLowerCase().includes(needle);
      if (!(matchesSet && matchesSearch && summaryData.paths.length > 0)) {
        return;
      }

      const card = renderTaskCard(task, summaryData);
      card.classList.toggle("is-active", selectedTaskKey === key);
      card.addEventListener("click", async () => {
        try {
          selectedTaskKey = key;
          const payload = task.payload || await loadPayload(task);
          task.payload = payload;
          buildPlayer(task, payload);
          renderGrid();
        } catch (err) {
          detailEl.innerHTML = `<p class="playbyplay-empty">Unable to load ${task.task_name}: ${err.message}</p>`;
        }
      });
      gridEl.appendChild(card);
    });
  }

  async function refreshSelectedTask() {
    if (!selectedTask) {
      return;
    }

    try {
      const payload = selectedTask.payload || await loadPayload(selectedTask);
      selectedTask.payload = payload;
      buildPlayer(selectedTask, payload);
      renderGrid();
    } catch (err) {
      detailEl.innerHTML = `<p class="playbyplay-empty">Unable to load ${selectedTask.task_name}: ${err.message}</p>`;
    }
  }

  try {
    const summary = await fetchSolutionSummary();
    tasks = (summary.tasks || []).slice().sort((a, b) => {
      if (a.task_type !== b.task_type) {
        return a.task_type.localeCompare(b.task_type);
      }
      return a.task_name.localeCompare(b.task_name, undefined, { numeric: true, sensitivity: "base" });
    });

    statusEl.textContent = `Loaded ${tasks.length} tasks with off-path play-by-play summaries.`;

    filterButtons.forEach((button) => {
      button.addEventListener("click", () => {
        filteredSet = button.dataset.filter || "all";
        filterButtons.forEach((item) => item.classList.toggle("is-active", item === button));
        renderGrid();
        refreshSelectedTask();
      });
    });

    participantFilterButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.dataset.participantFilter || "";
        participantFilters[key] = !participantFilters[key];
        updateParticipantFilterButtons();
        renderGrid();
        refreshSelectedTask();
      });
    });

    searchEl.addEventListener("input", () => {
      searchTerm = searchEl.value;
      renderGrid();
      refreshSelectedTask();
    });

    updateParticipantFilterButtons();
    renderGrid();

    if (tasks.length > 0) {
      const firstTask = tasks[0];
      selectedTaskKey = taskKey(firstTask.task_type, firstTask.task_name);
      const payload = await loadPayload(firstTask);
      firstTask.payload = payload;
      buildPlayer(firstTask, payload);
      renderGrid();
    }
  } catch (err) {
    statusEl.textContent = `Error loading off-path play-by-play: ${err.message}`;
    detailEl.innerHTML = `<p class="playbyplay-empty">${err.message}</p>`;
  }
})();