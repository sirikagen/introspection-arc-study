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

function renderExamplePairs(container, pairs) {
  container.innerHTML = "";

  if (!Array.isArray(pairs) || pairs.length === 0) {
    const empty = document.createElement("p");
    empty.className = "examples-empty";
    empty.textContent =
      "Example pairs are not available in the current workspace data. " +
      "If ARC task JSON files are added, they will appear here automatically.";
    container.appendChild(empty);
    return;
  }

  pairs.forEach((pair, idx) => {
    const card = document.createElement("div");
    card.className = "example-card";

    const title = document.createElement("p");
    title.className = "example-title";
    title.textContent = `Example ${idx + 1}`;

    const gridsWrap = document.createElement("div");
    gridsWrap.className = "example-grids";

    const inWrap = document.createElement("div");
    const inLabel = document.createElement("p");
    inLabel.className = "example-grid-label";
    inLabel.textContent = "Input";
    const inGrid = document.createElement("div");
    inGrid.className = "mini-arc-grid";
    drawGrid(inGrid, pair.input || []);
    inWrap.appendChild(inLabel);
    inWrap.appendChild(inGrid);

    const outWrap = document.createElement("div");
    const outLabel = document.createElement("p");
    outLabel.className = "example-grid-label";
    outLabel.textContent = "Output";
    const outGrid = document.createElement("div");
    outGrid.className = "mini-arc-grid";
    drawGrid(outGrid, pair.output || []);
    outWrap.appendChild(outLabel);
    outWrap.appendChild(outGrid);

    gridsWrap.appendChild(inWrap);
    gridsWrap.appendChild(outWrap);

    card.appendChild(title);
    card.appendChild(gridsWrap);
    container.appendChild(card);
  });
}

function normalizePuzzleFilePath(puzzleFile) {
  const raw = String(puzzleFile || "").trim().replace(/\\/g, "/");
  if (!raw) {
    return "";
  }

  const noLeadingSlash = raw.replace(/^\/+/, "");
  if (noLeadingSlash.startsWith("data/")) {
    return noLeadingSlash;
  }
  return `data/${noLeadingSlash}`;
}

async function fetchPuzzlePayload(puzzleFile) {
  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  const normalized = normalizePuzzleFilePath(puzzleFile);
  const candidates = [];

  if (normalized) {
    candidates.push(normalized);
  }

  // Backward compatibility for data that may already include/omit prefixes.
  const raw = String(puzzleFile || "").trim().replace(/\\/g, "/").replace(/^\/+/, "");
  if (raw) {
    candidates.push(raw);
    if (!raw.startsWith("data/")) {
      candidates.push(`data/${raw}`);
    }
    if (!raw.startsWith("puzzles/")) {
      candidates.push(`data/puzzles/${raw}`);
    }
  }

  const tried = [];
  const errors = [];
  for (const path of [...new Set(candidates)]) {
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      tried.push(`${path} (attempt ${attempt})`);
      try {
        const res = await fetch(path, { cache: "no-store" });
        if (res.ok) {
          return res.json();
        }
        errors.push(`${path}: HTTP ${res.status}`);
      } catch (err) {
        errors.push(`${path}: ${err.message}`);
      }

      if (attempt < 3) {
        await delay(250);
      }
    }
  }

  throw new Error(`Cannot load puzzle replay data (tried: ${tried.join(", ")}; errors: ${errors.join(" | ")})`);
}

(async function initPuzzlePage() {
  const participantId = getQueryParam("participant");
  const taskName = getQueryParam("task");
  const attempt = getQueryParam("attempt");
  const puzzleFile = getQueryParam("file");

  const backLink = document.getElementById("participantBack");
  const titleEl = document.getElementById("puzzleTitle");
  const metaEl = document.getElementById("puzzleMeta");
  const examplesPaneEl = document.getElementById("examplesPane");
  const inputGridEl = document.getElementById("inputGrid");
  const outputGridEl = document.getElementById("outputGrid");
  const firstDescriptionEl = document.getElementById("firstDescription");
  const lastDescriptionEl = document.getElementById("lastDescription");
  const sliderEl = document.getElementById("frameSlider");
  const frameLabelEl = document.getElementById("frameLabel");
  const actionInfoEl = document.getElementById("actionInfo");

  const firstBtn = document.getElementById("firstBtn");
  const prevBtn = document.getElementById("prevBtn");
  const playPauseBtn = document.getElementById("playPauseBtn");
  const nextBtn = document.getElementById("nextBtn");
  const lastBtn = document.getElementById("lastBtn");
  const speedSelect = document.getElementById("speedSelect");

  if (!participantId || !taskName || !attempt || !puzzleFile) {
    titleEl.textContent = "Missing puzzle metadata in URL";
    return;
  }

  backLink.href = `participant.html?participant=${escapeQueryValue(participantId)}`;
  titleEl.textContent = taskName;
  metaEl.textContent = `Participant ${participantId} | Attempt ${attempt}`;

  let payload;
  try {
    payload = await fetchPuzzlePayload(puzzleFile);
  } catch (err) {
    actionInfoEl.textContent = `Error loading replay: ${err.message}`;
    return;
  }

  const frames = payload.frames || [];
  let frameIdx = 0;
  let timer = null;

  renderExamplePairs(examplesPaneEl, payload.example_pairs || []);
  drawGrid(inputGridEl, payload.input_grid || payload.input_grid_first_frame || []);
  const semantic = payload.semantic_descriptions || {};
  firstDescriptionEl.textContent = semantic.first_written_description || "No first description available.";
  lastDescriptionEl.textContent = semantic.last_written_description || "No last description available.";

  function renderFrame(idx) {
    if (frames.length === 0) {
      drawGrid(outputGridEl, []);
      frameLabelEl.textContent = "Frame 0 / 0";
      actionInfoEl.textContent = "No frames available.";
      return;
    }

    frameIdx = Math.max(0, Math.min(idx, frames.length - 1));
    const frame = frames[frameIdx];
    drawGrid(outputGridEl, frame.grid || []);

    sliderEl.value = String(frameIdx);
    frameLabelEl.textContent = `Frame ${frameIdx + 1} / ${frames.length}`;
    const solvedTag = frame.solved ? " | solved=true" : "";
    actionInfoEl.textContent =
      `action_id=${frame.action_id} | action=${frame.action}` +
      ` | x=${frame.action_x || "-"} | y=${frame.action_y || "-"}` +
      ` | symbol=${frame.selected_symbol || "-"}${solvedTag}`;
  }

  function stopPlayback() {
    if (timer) {
      clearInterval(timer);
      timer = null;
      playPauseBtn.textContent = "Play";
    }
  }

  function startPlayback() {
    if (timer || frames.length === 0) {
      return;
    }
    playPauseBtn.textContent = "Pause";
    timer = setInterval(() => {
      if (frameIdx >= frames.length - 1) {
        stopPlayback();
      } else {
        renderFrame(frameIdx + 1);
      }
    }, Number(speedSelect.value));
  }

  sliderEl.min = "0";
  sliderEl.max = String(Math.max(0, frames.length - 1));

  sliderEl.addEventListener("input", () => {
    stopPlayback();
    renderFrame(Number(sliderEl.value));
  });

  firstBtn.addEventListener("click", () => {
    stopPlayback();
    renderFrame(0);
  });

  prevBtn.addEventListener("click", () => {
    stopPlayback();
    renderFrame(frameIdx - 1);
  });

  nextBtn.addEventListener("click", () => {
    stopPlayback();
    renderFrame(frameIdx + 1);
  });

  lastBtn.addEventListener("click", () => {
    stopPlayback();
    renderFrame(frames.length - 1);
  });

  playPauseBtn.addEventListener("click", () => {
    if (timer) {
      stopPlayback();
    } else {
      startPlayback();
    }
  });

  speedSelect.addEventListener("change", () => {
    if (timer) {
      stopPlayback();
      startPlayback();
    }
  });

  renderFrame(0);
})();
