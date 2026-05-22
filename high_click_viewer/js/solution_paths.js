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

const ARC_SETS = [
  { key: "training", label: "Training", directory: "../ARC-AGI-master/data/training/" },
  { key: "evaluation", label: "Evaluation", directory: "../ARC-AGI-master/data/evaluation/" },
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

function drawChangesGrid(container, matrix) {
  container.innerHTML = "";
  const { rows, cols } = gridSize(matrix);

  if (!rows || !cols) {
    container.textContent = "No change data";
    return;
  }

  container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
  container.style.gridTemplateRows = `repeat(${rows}, 1fr)`;

  matrix.forEach((row) => {
    row.forEach((value) => {
      const cell = document.createElement("div");
      cell.className = value == null ? "cell diff-empty" : "cell diff-filled";
      cell.style.background = value == null ? "rgba(31, 34, 48, 0.04)" : colorFor(value);
      container.appendChild(cell);
    });
  });
}

function createChip(text, className = "participant-chip") {
  const chip = document.createElement("span");
  chip.className = className;
  chip.textContent = text;
  return chip;
}

function createStepChip(text, isResize = false) {
  const chip = document.createElement("span");
  chip.className = `step-chip${isResize ? " is-resize" : ""}`;
  chip.textContent = text;
  return chip;
}

function createOffPathChip(text, reason) {
  const chip = document.createElement("span");
  chip.className = "offpath-chip";
  chip.textContent = reason ? `${text} · ${reason}` : text;
  return chip;
}

function taskKey(taskType, taskName) {
  return `${taskType}:${taskName}`;
}

function arcTaskUrl(task) {
  const directory = task.task_type === "evaluation" ? "evaluation" : "training";
  return `../ARC-AGI-master/data/${directory}/${task.task_name}`;
}

function computePath(inputGrid, outputGrid) {
  const inputSize = gridSize(inputGrid);
  const outputSize = gridSize(outputGrid);
  const rows = Math.max(inputSize.rows, outputSize.rows);
  const cols = Math.max(inputSize.cols, outputSize.cols);

  const changes = [];
  const diffGrid = [];

  for (let rowIndex = 0; rowIndex < rows; rowIndex += 1) {
    const diffRow = [];
    for (let colIndex = 0; colIndex < cols; colIndex += 1) {
      const inputValue = inputGrid?.[rowIndex]?.[colIndex];
      const outputValue = outputGrid?.[rowIndex]?.[colIndex];
      if (inputValue !== outputValue && outputValue !== undefined) {
        diffRow.push(outputValue);
        changes.push({ row: rowIndex + 1, col: colIndex + 1, value: outputValue });
      } else {
        diffRow.push(null);
      }
    }
    diffGrid.push(diffRow);
  }

  return {
    sizeStep: outputSize.rows === inputSize.rows && outputSize.cols === inputSize.cols
      ? `size ${outputSize.rows}x${outputSize.cols}`
      : `resize to ${outputSize.rows}x${outputSize.cols}`,
    diffGrid,
    changes,
  };
}

function renderTestPair(detailEl, pair, index) {
  const card = document.createElement("div");
  card.className = "example-card";

  const title = document.createElement("p");
  title.className = "example-title";
  title.textContent = `Test ${index + 1}`;

  const grids = document.createElement("div");
  grids.className = "solution-grid-three";

  const labels = ["Input", "Solved output", "Changes only"];
  const matrices = [pair.input || [], pair.output || [], pair.diffGrid || []];
  const renderers = [drawGrid, drawGrid, drawChangesGrid];

  labels.forEach((label, labelIndex) => {
    const wrap = document.createElement("div");
    const labelEl = document.createElement("p");
    labelEl.className = "example-grid-label";
    labelEl.textContent = label;
    const grid = document.createElement("div");
    grid.className = "mini-arc-grid";
    renderers[labelIndex](grid, matrices[labelIndex]);
    wrap.appendChild(labelEl);
    wrap.appendChild(grid);
    grids.appendChild(wrap);
  });

  const stepLabel = document.createElement("p");
  stepLabel.className = "semantic-label";
  stepLabel.textContent = "Correct solution path";

  const stepRow = document.createElement("div");
  stepRow.className = "chip-row";
  stepRow.appendChild(createStepChip(pair.sizeStep, true));
  pair.steps.forEach((step) => {
    stepRow.appendChild(createStepChip(`r${step.row}c${step.col}=${step.value}`));
  });

  card.appendChild(title);
  card.appendChild(grids);
  card.appendChild(stepLabel);
  card.appendChild(stepRow);
  detailEl.appendChild(card);
}

function renderParticipantCard(detailEl, record, index) {
  const card = document.createElement("div");
  card.className = "solution-path-card";

  const header = document.createElement("div");
  header.className = "solution-path-header";

  const title = document.createElement("span");
  title.className = "solution-path-title";
  title.textContent = record.participant_id;

  header.appendChild(title);
  header.appendChild(createChip(`Attempt ${record.attempt_number}`, "task-badge"));
  header.appendChild(createChip(`${record.wrong_step_count} wrong step${record.wrong_step_count === 1 ? "" : "s"}`, "task-badge"));

  const summary = document.createElement("p");
  summary.className = "meta-line";
  summary.textContent = `Off-path steps for participant #${index + 1}.`;

  const chipRow = document.createElement("div");
  chipRow.className = "chip-row";
  if (!record.off_path_steps || record.off_path_steps.length === 0) {
    chipRow.appendChild(createChip("No off-path steps", "participant-chip"));
  } else {
    record.off_path_steps.forEach((step) => {
      const text = step.label.includes("=") ? `${step.action_id}. ${step.label}` : `${step.action_id}. ${step.label}`;
      chipRow.appendChild(createOffPathChip(text, step.reason));
    });
  }

  card.appendChild(header);
  card.appendChild(summary);
  card.appendChild(chipRow);
  detailEl.appendChild(card);
}

function renderTestPairs(detailEl, payload) {
  const tests = Array.isArray(payload.test)
    ? payload.test.map((pair) => {
        const summary = computePath(pair.input || [], pair.output || []);
        return {
          input: pair.input || [],
          output: pair.output || [],
          diffGrid: summary.diffGrid,
          sizeStep: summary.sizeStep,
          steps: summary.changes,
        };
      })
    : [];

  const heading = document.createElement("h3");
  heading.textContent = "Test pairs";
  detailEl.appendChild(heading);

  if (tests.length === 0) {
    const empty = document.createElement("p");
    empty.className = "solution-empty";
    empty.textContent = "No test pairs available.";
    detailEl.appendChild(empty);
    return tests;
  }

  tests.forEach((pair, index) => renderTestPair(detailEl, pair, index));
  return tests;
}

async function fetchDirectoryListing(directoryUrl) {
  const res = await fetch(directoryUrl, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Unable to load directory listing for ${directoryUrl} (HTTP ${res.status})`);
  }

  const html = await res.text();
  const doc = new DOMParser().parseFromString(html, "text/html");
  return [...doc.querySelectorAll("a[href]")]
    .map((anchor) => anchor.getAttribute("href") || "")
    .filter((href) => href.toLowerCase().endsWith(".json"))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }));
}

async function fetchTaskJson(task) {
  const taskUrl = arcTaskUrl(task);
  const res = await fetch(taskUrl, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Unable to load ARC task JSON for ${task.task_name}`);
  }
  return res.json();
}

async function fetchSolutionSummary() {
  const res = await fetch("data/solution_paths.json", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Unable to load solution_paths.json (${res.status})`);
  }
  return res.json();
}

(async function initSolutionPathsPage() {
  const statusEl = document.getElementById("taskStatus");
  const searchEl = document.getElementById("taskSearch");
  const filterButtons = [...document.querySelectorAll(".filter-button")];
  const participantFilterButtons = [...document.querySelectorAll("[data-participant-filter]")];
  const gridEl = document.getElementById("taskGrid");
  const detailEl = document.getElementById("taskDetail");

  const taskCache = new Map();
  let tasks = [];
  let selectedKey = null;
  let selectedTask = null;
  let filteredSet = "all";
  let searchTerm = "";

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

  function renderTaskDetail(task, payload) {
    selectedTask = task;
    selectedKey = taskKey(task.task_type, task.task_name);
    detailEl.innerHTML = "";

    const summaryData = summarizeTask(task);

    const header = document.createElement("div");
    header.className = "task-detail-header";

    const title = document.createElement("h3");
    title.textContent = task.task_name;

    const badges = document.createElement("div");
    badges.className = "task-badge-row";
    badges.appendChild(createChip(task.task_type === "evaluation" ? "Evaluation" : "Training", "task-badge"));
    badges.appendChild(createChip(`${summaryData.participantIds.length} participant${summaryData.participantIds.length === 1 ? "" : "s"}`, "task-badge"));
    badges.appendChild(createChip(`${summaryData.wrongStepTotal} wrong step${summaryData.wrongStepTotal === 1 ? "" : "s"}`, "task-badge"));
    badges.appendChild(createChip(`${payload.test?.length || 0} test pair${(payload.test?.length || 0) === 1 ? "" : "s"}`, "task-badge"));

    const subtitle = document.createElement("p");
    subtitle.className = "subtitle";
    subtitle.textContent = "Only test pairs appear here. Off-path participant steps are counted from data.csv and compared against the solved output grid.";

    const rawLink = document.createElement("a");
    rawLink.className = "inline-link";
    rawLink.href = arcTaskUrl(task);
    rawLink.textContent = "Open raw JSON";

    header.appendChild(title);
    header.appendChild(badges);
    header.appendChild(subtitle);
    header.appendChild(rawLink);
    detailEl.appendChild(header);

    renderTestPairs(detailEl, payload);

    const participantHeading = document.createElement("h3");
    participantHeading.textContent = "Participants who completed this puzzle";
    detailEl.appendChild(participantHeading);

    const participantWrap = document.createElement("div");
    participantWrap.className = "chip-row";
    if (summaryData.participantIds.length === 0) {
      participantWrap.appendChild(createChip("None yet"));
    } else {
      summaryData.participantIds.forEach((id) => participantWrap.appendChild(createChip(id)));
    }
    detailEl.appendChild(participantWrap);

    const pathHeading = document.createElement("h3");
    pathHeading.textContent = "Steps off the solution path";
    detailEl.appendChild(pathHeading);

    const pathsWrap = document.createElement("div");
    pathsWrap.className = "solution-paths";

    if (summaryData.paths.length === 0) {
      const empty = document.createElement("p");
      empty.className = "solution-empty";
      empty.textContent = "No completed solution paths match the active participant filters.";
      pathsWrap.appendChild(empty);
    } else {
      summaryData.paths.forEach((path) => {
        const pathCard = document.createElement("div");
        pathCard.className = "solution-path-card";

        const pathHeader = document.createElement("div");
        pathHeader.className = "solution-path-header";

        const pathTitle = document.createElement("span");
        pathTitle.className = "solution-path-title";
        pathTitle.textContent = getPathParticipantId(path);

        pathHeader.appendChild(pathTitle);
        pathHeader.appendChild(createChip(`Attempt ${path.attempt_number}`, "task-badge"));
        pathHeader.appendChild(createChip(`${path.wrong_step_count} wrong step${path.wrong_step_count === 1 ? "" : "s"}`, "task-badge"));

        const flagRow = document.createElement("div");
        flagRow.className = "chip-row";
        if (path.complete) {
          flagRow.appendChild(createChip("Complete", "task-badge"));
        }
        if (path.solved) {
          flagRow.appendChild(createChip("Solved", "task-badge"));
        }
        if (Number(path.attempt_number) === 1) {
          flagRow.appendChild(createChip("Attempt 1", "task-badge"));
        }

        const actionRow = document.createElement("div");
        actionRow.className = "chip-row";
        if (!path.off_path_steps || path.off_path_steps.length === 0) {
          actionRow.appendChild(createChip("No off-path steps", "participant-chip"));
        } else {
          path.off_path_steps.forEach((step) => {
            const chipText = step.label.includes("=") ? `${step.action_id}. ${step.label}` : `${step.action_id}. ${step.label}`;
            actionRow.appendChild(createOffPathChip(chipText, step.reason));
          });
        }

        pathCard.appendChild(pathHeader);
        if (flagRow.childElementCount > 0) {
          pathCard.appendChild(flagRow);
        }
        pathCard.appendChild(actionRow);
        pathsWrap.appendChild(pathCard);
      });
    }

    detailEl.appendChild(pathsWrap);
  }

  function renderCard(task, summaryData) {
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

    const wrongStepCount = document.createElement("p");
    wrongStepCount.className = "task-card-meta";
    wrongStepCount.textContent = `${summaryData.wrongStepTotal} wrong step${summaryData.wrongStepTotal === 1 ? "" : "s"}`;

    const chips = document.createElement("div");
    chips.className = "chip-row";
    summaryData.participantIds.slice(0, 3).forEach((id) => chips.appendChild(createChip(id)));
    if (summaryData.participantIds.length > 3) {
      chips.appendChild(createChip(`+${summaryData.participantIds.length - 3} more`));
    }

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(count);
    card.appendChild(wrongStepCount);
    card.appendChild(chips);

    card.addEventListener("click", async () => {
      try {
        const payload = task.payload || (await loadPayload(task));
        task.payload = payload;
        renderTaskDetail(task, payload);
        renderGrid();
      } catch (err) {
        detailEl.innerHTML = `<p class="solution-empty">Unable to load ${task.task_name}: ${err.message}</p>`;
      }
    });

    return card;
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

      const card = renderCard(task, summaryData);
      card.classList.toggle("is-active", selectedKey === key);
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
      renderTaskDetail(selectedTask, payload);
      renderGrid();
    } catch (err) {
      detailEl.innerHTML = `<p class="solution-empty">Unable to load ${selectedTask.task_name}: ${err.message}</p>`;
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

    statusEl.textContent = `Loaded ${tasks.length} tasks with participant off-path summaries.`;

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
      selectedTask = tasks[0];
      const payload = await loadPayload(tasks[0]);
      tasks[0].payload = payload;
      renderTaskDetail(tasks[0], payload);
      renderGrid();
    }
  } catch (err) {
    statusEl.textContent = `Error loading solution paths: ${err.message}`;
    detailEl.innerHTML = `<p class="solution-empty">${err.message}</p>`;
  }
})();