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
  {
    key: "training",
    label: "Training",
    directory: "../ARC-AGI-master/data/training/",
  },
  {
    key: "evaluation",
    label: "Evaluation",
    directory: "../ARC-AGI-master/data/evaluation/",
  },
];

function colorFor(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || n >= ARC_COLORS.length) {
    return "#ffffff";
  }
  return ARC_COLORS[n];
}

function drawGrid(container, matrix) {
  container.innerHTML = "";
  const rows = matrix.length;
  const cols = rows > 0 ? matrix[0].length : 0;

  if (rows === 0 || cols === 0) {
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

function gridSize(matrix) {
  const rows = Array.isArray(matrix) ? matrix.length : 0;
  const cols = rows > 0 && Array.isArray(matrix[0]) ? matrix[0].length : 0;
  return `${rows}x${cols}`;
}

function uniqueKey(task) {
  return `${task.setKey}:${task.taskId}`;
}

function buildTaskId(fileName) {
  return String(fileName || "").replace(/\.json$/i, "");
}

async function fetchDirectoryListing(directoryUrl) {
  const indexUrl = directoryUrl.replace(/\/?$/, "/") + "index.json";
  const res = await fetch(indexUrl, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Unable to load directory index for ${directoryUrl} (HTTP ${res.status})`);
  }
  const files = await res.json();
  return files.filter((f) => f.toLowerCase().endsWith(".json") && f !== "index.json");
}

async function fetchTaskPayload(task) {
  const res = await fetch(task.url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Unable to load ${task.taskId} (${task.setLabel})`);
  }
  return res.json();
}

function createMiniGrid(label, matrix) {
  const wrap = document.createElement("div");
  wrap.className = "task-preview-item";

  const labelEl = document.createElement("p");
  labelEl.className = "task-preview-label";
  labelEl.textContent = label;

  const grid = document.createElement("div");
  grid.className = "mini-arc-grid";
  drawGrid(grid, matrix || []);

  wrap.appendChild(labelEl);
  wrap.appendChild(grid);
  return wrap;
}

function createPreviewShell() {
  const previewGrid = document.createElement("div");
  previewGrid.className = "task-preview-grid";

  const placeholders = ["Train in", "Train out", "Test in"].map((label) => {
    const wrap = document.createElement("div");
    wrap.className = "task-preview-item";

    const labelEl = document.createElement("p");
    labelEl.className = "task-preview-label";
    labelEl.textContent = label;

    const loading = document.createElement("p");
    loading.className = "task-preview-loading";
    loading.textContent = "Loading...";

    wrap.appendChild(labelEl);
    wrap.appendChild(loading);
    return wrap;
  });

  placeholders.forEach((item) => previewGrid.appendChild(item));
  return previewGrid;
}

function renderTaskCardPreview(card, payload) {
  const preview = card.querySelector(".task-preview-grid");
  if (!preview) {
    return;
  }

  preview.innerHTML = "";
  const trainPair = Array.isArray(payload.train) && payload.train.length > 0 ? payload.train[0] : null;
  const testPair = Array.isArray(payload.test) && payload.test.length > 0 ? payload.test[0] : null;

  preview.appendChild(createMiniGrid("Train in", trainPair?.input || []));
  preview.appendChild(createMiniGrid("Train out", trainPair?.output || []));
  preview.appendChild(createMiniGrid("Test in", testPair?.input || []));
}

function renderTaskDetail(detailEl, task, payload) {
  detailEl.innerHTML = "";

  const header = document.createElement("div");
  header.className = "task-detail-header";

  const title = document.createElement("h3");
  title.textContent = task.taskId;

  const badges = document.createElement("div");
  badges.className = "task-badge-row";

  const setBadge = document.createElement("span");
  setBadge.className = "task-badge";
  setBadge.textContent = task.setLabel;

  const trainBadge = document.createElement("span");
  trainBadge.className = "task-badge";
  trainBadge.textContent = `${payload.train?.length || 0} training pair(s)`;

  const testBadge = document.createElement("span");
  testBadge.className = "task-badge";
  testBadge.textContent = `${payload.test?.length || 0} test pair(s)`;

  const rawLink = document.createElement("a");
  rawLink.className = "inline-link";
  rawLink.href = task.url;
  rawLink.textContent = "Open raw JSON";

  badges.appendChild(setBadge);
  badges.appendChild(trainBadge);
  badges.appendChild(testBadge);

  const summary = document.createElement("p");
  summary.className = "subtitle";
  const firstTrain = Array.isArray(payload.train) && payload.train.length > 0 ? payload.train[0] : null;
  const firstTest = Array.isArray(payload.test) && payload.test.length > 0 ? payload.test[0] : null;
  summary.textContent = firstTrain && firstTest
    ? `First train pair: ${gridSize(firstTrain.input)} → ${gridSize(firstTrain.output)}. First test pair: ${gridSize(firstTest.input)} → ${gridSize(firstTest.output)}.`
    : "Task details loaded.";

  header.appendChild(title);
  header.appendChild(badges);
  header.appendChild(summary);
  header.appendChild(rawLink);

  detailEl.appendChild(header);

  const trainHeading = document.createElement("h4");
  trainHeading.textContent = "Training pairs";
  detailEl.appendChild(trainHeading);

  const trainGrid = document.createElement("div");
  trainGrid.className = "task-grid";
  (payload.train || []).forEach((pair, idx) => {
    const card = document.createElement("div");
    card.className = "example-card";

    const titleEl = document.createElement("p");
    titleEl.className = "example-title";
    titleEl.textContent = `Train ${idx + 1}`;

    const grids = document.createElement("div");
    grids.className = "example-grids";
    const inputWrap = document.createElement("div");
    const outputWrap = document.createElement("div");
    const inputLabel = document.createElement("p");
    inputLabel.className = "example-grid-label";
    inputLabel.textContent = "Input";
    const outputLabel = document.createElement("p");
    outputLabel.className = "example-grid-label";
    outputLabel.textContent = "Output";
    const inputGrid = document.createElement("div");
    inputGrid.className = "mini-arc-grid";
    const outputGrid = document.createElement("div");
    outputGrid.className = "mini-arc-grid";
    drawGrid(inputGrid, pair.input || []);
    drawGrid(outputGrid, pair.output || []);
    inputWrap.appendChild(inputLabel);
    inputWrap.appendChild(inputGrid);
    outputWrap.appendChild(outputLabel);
    outputWrap.appendChild(outputGrid);
    grids.appendChild(inputWrap);
    grids.appendChild(outputWrap);

    card.appendChild(titleEl);
    card.appendChild(grids);
    trainGrid.appendChild(card);
  });
  detailEl.appendChild(trainGrid);

  const testHeading = document.createElement("h4");
  testHeading.textContent = "Test pairs";
  detailEl.appendChild(testHeading);

  const testGrid = document.createElement("div");
  testGrid.className = "task-grid";
  (payload.test || []).forEach((pair, idx) => {
    const card = document.createElement("div");
    card.className = "example-card";

    const titleEl = document.createElement("p");
    titleEl.className = "example-title";
    titleEl.textContent = `Test ${idx + 1}`;

    const grids = document.createElement("div");
    grids.className = "example-grids";
    const inputWrap = document.createElement("div");
    const outputWrap = document.createElement("div");
    const inputLabel = document.createElement("p");
    inputLabel.className = "example-grid-label";
    inputLabel.textContent = "Input";
    const outputLabel = document.createElement("p");
    outputLabel.className = "example-grid-label";
    outputLabel.textContent = "Output";
    const inputGrid = document.createElement("div");
    inputGrid.className = "mini-arc-grid";
    const outputGrid = document.createElement("div");
    outputGrid.className = "mini-arc-grid";
    drawGrid(inputGrid, pair.input || []);
    drawGrid(outputGrid, pair.output || []);
    inputWrap.appendChild(inputLabel);
    inputWrap.appendChild(inputGrid);
    outputWrap.appendChild(outputLabel);
    outputWrap.appendChild(outputGrid);
    grids.appendChild(inputWrap);
    grids.appendChild(outputWrap);

    card.appendChild(titleEl);
    card.appendChild(grids);
    testGrid.appendChild(card);
  });
  detailEl.appendChild(testGrid);
}

(async function initArcGallery() {
  const statusEl = document.getElementById("galleryStatus");
  const searchEl = document.getElementById("taskSearch");
  const filterButtons = [...document.querySelectorAll(".filter-button")];
  const gridEl = document.getElementById("taskGrid");
  const detailEl = document.getElementById("taskDetail");

  const payloadCache = new Map();
  const cardByTaskKey = new Map();
  let tasks = [];
  let activeFilter = "all";
  let searchTerm = "";
  let selectedTaskKey = null;

  const previewObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }
        const card = entry.target;
        previewObserver.unobserve(card);
        const taskKey = card.dataset.taskKey;
        const task = tasks.find((item) => uniqueKey(item) === taskKey);
        if (task) {
          loadPreview(task, card).catch((err) => {
            const preview = card.querySelector(".task-preview-grid");
            if (preview) {
              preview.innerHTML = `<p class="task-preview-empty">Preview unavailable: ${err.message}</p>`;
            }
          });
        }
      });
    },
    { rootMargin: "300px 0px" }
  );

  function applyFilters() {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    cardByTaskKey.forEach((card, taskKey) => {
      const task = tasks.find((item) => uniqueKey(item) === taskKey);
      if (!task) {
        return;
      }
      const matchesFilter = activeFilter === "all" || task.setKey === activeFilter;
      const matchesSearch = !normalizedSearch || task.taskId.toLowerCase().includes(normalizedSearch);
      card.classList.toggle("is-hidden", !(matchesFilter && matchesSearch));
      card.classList.toggle("is-active", selectedTaskKey === taskKey);
    });
  }

  async function loadPreview(task, card) {
    const taskKey = uniqueKey(task);
    let payload = payloadCache.get(taskKey);
    if (!payload) {
      payload = await fetchTaskPayload(task);
      payloadCache.set(taskKey, payload);
    }
    renderTaskCardPreview(card, payload);
    if (selectedTaskKey === taskKey) {
      renderTaskDetail(detailEl, task, payload);
    }
  }

  async function selectTask(task) {
    selectedTaskKey = uniqueKey(task);
    applyFilters();
    const card = cardByTaskKey.get(selectedTaskKey);
    if (card && !card.classList.contains("is-hidden")) {
      card.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }

    let payload = payloadCache.get(selectedTaskKey);
    if (!payload) {
      detailEl.innerHTML = '<p class="gallery-detail-empty">Loading task details...</p>';
      payload = await fetchTaskPayload(task);
      payloadCache.set(selectedTaskKey, payload);
    }
    renderTaskDetail(detailEl, task, payload);
  }

  function createTaskCard(task) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "task-card";
    card.dataset.taskKey = uniqueKey(task);

    const title = document.createElement("p");
    title.className = "task-card-title";
    title.textContent = task.taskId;

    const meta = document.createElement("p");
    meta.className = "task-card-meta";
    meta.textContent = `${task.setLabel} set`;

    const preview = createPreviewShell();

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(preview);

    card.addEventListener("click", () => {
      selectTask(task).catch((err) => {
        detailEl.innerHTML = `<p class="gallery-detail-empty">Could not load ${task.taskId}: ${err.message}</p>`;
      });
    });

    cardByTaskKey.set(uniqueKey(task), card);
    previewObserver.observe(card);
    return card;
  }

  try {
    const perSetTasks = await Promise.all(
      ARC_SETS.map(async (setInfo) => {
        const fileNames = await fetchDirectoryListing(setInfo.directory);
        return fileNames.map((fileName) => ({
          setKey: setInfo.key,
          setLabel: setInfo.label,
          taskId: buildTaskId(fileName),
          fileName,
          url: new URL(fileName, new URL(setInfo.directory, window.location.href)).toString(),
        }));
      })
    );

    tasks = perSetTasks.flat();
    tasks.sort((a, b) => {
      if (a.setKey !== b.setKey) {
        return a.setKey.localeCompare(b.setKey);
      }
      return a.taskId.localeCompare(b.taskId, undefined, { numeric: true, sensitivity: "base" });
    });

    tasks.forEach((task) => {
      gridEl.appendChild(createTaskCard(task));
    });

    statusEl.textContent = `Loaded ${tasks.length} tasks from ${ARC_SETS.map((set) => set.label).join(" and ")}.`;

    if (tasks.length > 0) {
      selectTask(tasks[0]).catch((err) => {
        detailEl.innerHTML = `<p class="gallery-detail-empty">Unable to load the first task: ${err.message}</p>`;
      });
    }
  } catch (err) {
    statusEl.textContent = `Error loading ARC task list: ${err.message}`;
    detailEl.innerHTML = `<p class="gallery-detail-empty">${err.message}</p>`;
    return;
  }

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter || "all";
      filterButtons.forEach((item) => item.classList.toggle("is-active", item === button));
      applyFilters();
    });
  });

  searchEl.addEventListener("input", () => {
    searchTerm = searchEl.value;
    applyFilters();
  });
})();