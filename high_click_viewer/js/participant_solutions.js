(async function initParticipantSolutionsPage() {
  const statusEl = document.getElementById("solutionStatus");
  const searchEl = document.getElementById("solutionSearch");
  const filterButtons = [...document.querySelectorAll(".filter-button")];
  const participantFilterButtons = [...document.querySelectorAll("[data-participant-filter]")];
  const gridEl = document.getElementById("solutionGrid");
  const detailEl = document.getElementById("solutionDetail");

  let tasks = [];
  let filteredSet = "all";
  let searchTerm = "";
  let selectedKey = null;
  let selectedTask = null;

  const participantFilters = {
    complete: false,
    solved: false,
    attemptOne: false,
  };

  async function fetchSummary() {
    const res = await fetch("data/participant_solutions.json", { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`Unable to load participant_solutions.json (${res.status})`);
    }
    return res.json();
  }

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
    return { paths, participantIds };
  }

  function renderDetail(task) {
    selectedTask = task;
    selectedKey = `${task.task_type}:${task.task_name}`;
    detailEl.innerHTML = "";

    const summaryData = summarizeTask(task);
    const visiblePaths = summaryData.paths;
    const visibleParticipantIds = summaryData.participantIds;

    const header = document.createElement("div");
    header.className = "task-detail-header";

    const title = document.createElement("h3");
    title.textContent = task.task_name;

    const row = document.createElement("div");
    row.className = "task-badge-row";
    row.appendChild(createChip(task.task_type === "evaluation" ? "Evaluation" : "Training", "task-badge"));
    row.appendChild(createChip(`${visibleParticipantIds.length} participant${visibleParticipantIds.length === 1 ? "" : "s"}`, "task-badge"));
    row.appendChild(createChip(`${visiblePaths.length} solution path${visiblePaths.length === 1 ? "" : "s"}`, "task-badge"));

    const summary = document.createElement("p");
    summary.className = "subtitle";
    summary.textContent = visiblePaths.length > 0
      ? `${visiblePaths.length} solution path${visiblePaths.length === 1 ? "" : "s"} match the active participant filters.`
      : "No completed solution path matches the active participant filters.";

    const participantLabel = document.createElement("p");
    participantLabel.className = "semantic-label";
    participantLabel.textContent = "Participant hashed_id(s)";

    const participantRow = document.createElement("div");
    participantRow.className = "chip-row";
    if (visibleParticipantIds.length > 0) {
      visibleParticipantIds.forEach((id) => participantRow.appendChild(createChip(id)));
    } else {
      participantRow.appendChild(createChip("None yet"));
    }

    header.appendChild(title);
    header.appendChild(row);
    header.appendChild(summary);
    detailEl.appendChild(header);
    detailEl.appendChild(participantLabel);
    detailEl.appendChild(participantRow);

    const pathHeading = document.createElement("h3");
    pathHeading.textContent = "Successful solution paths";
    detailEl.appendChild(pathHeading);

    const pathsWrap = document.createElement("div");
    pathsWrap.className = "solution-paths";

    if (visiblePaths.length === 0) {
      const empty = document.createElement("p");
      empty.className = "solution-empty";
      empty.textContent = "No successful solutions match the active participant filters.";
      pathsWrap.appendChild(empty);
    } else {
      visiblePaths.forEach((path) => {
        const pathCard = document.createElement("div");
        pathCard.className = "solution-path-card";

        const pathHeader = document.createElement("div");
        pathHeader.className = "solution-path-header";

        const pathTitle = document.createElement("span");
        pathTitle.className = "solution-path-title";
        pathTitle.textContent = getPathParticipantId(path);

        pathHeader.appendChild(pathTitle);
        pathHeader.appendChild(createChip(`Attempt ${path.attempt_number}`, "task-badge"));
        pathHeader.appendChild(createChip(`${path.action_count} actions`, "task-badge"));

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
        path.actions.forEach((action, index) => {
          const chip = createChip(`${index + 1}. ${action}`, "action-chip");
          actionRow.appendChild(chip);
        });

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
    card.dataset.taskKey = `${task.task_type}:${task.task_name}`;

    const title = document.createElement("p");
    title.className = "task-card-title";
    title.textContent = task.task_name;

    const meta = document.createElement("p");
    meta.className = "task-card-meta";
    meta.textContent = `${task.task_type === "evaluation" ? "Evaluation" : "Training"} set`;

    const count = document.createElement("p");
    count.className = "task-card-meta";
    count.textContent = `Completed by ${summaryData.participantIds.length} participant${summaryData.participantIds.length === 1 ? "" : "s"}`;

    const pathCount = document.createElement("p");
    pathCount.className = "task-card-meta";
    pathCount.textContent = `${summaryData.paths.length} successful solution path${summaryData.paths.length === 1 ? "" : "s"}`;

    const chips = document.createElement("div");
    chips.className = "chip-row";
    summaryData.participantIds.slice(0, 3).forEach((id) => chips.appendChild(createChip(id)));
    if (summaryData.participantIds.length > 3) {
      chips.appendChild(createChip(`+${summaryData.participantIds.length - 3} more`));
    }

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(count);
    card.appendChild(pathCount);
    card.appendChild(chips);

    card.addEventListener("click", () => {
      renderDetail(task);
      renderGrid();
    });

    return card;
  }

  function renderGrid() {
    const needle = searchTerm.trim().toLowerCase();
    gridEl.innerHTML = "";

    tasks.forEach((task) => {
      const key = `${task.task_type}:${task.task_name}`;
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

  function refreshSelectedTask() {
    if (!selectedTask) {
      return;
    }
    renderDetail(selectedTask);
  }

  try {
    const summary = await fetchSummary();
    tasks = summary.tasks || [];

    statusEl.textContent = `Loaded ${tasks.length} tasks with participant solution summaries.`;

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
      renderDetail(tasks[0]);
      renderGrid();
    }
  } catch (err) {
    statusEl.textContent = `Error loading participant solutions: ${err.message}`;
  }
})();