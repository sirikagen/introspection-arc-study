(async function initIndex() {
  const container = document.getElementById("participants");

  if (window.location.protocol === "file:") {
    container.innerHTML = `
      <div class="tile-link" style="cursor:default;">
        <p class="id-line">Open via the launcher</p>
        <p class="meta-line">This viewer loads participant data with fetch(), so opening index.html directly from Finder will fail.</p>
        <p class="meta-line">Use <strong>high_click_viewer/launch_webpage.command</strong> to start the local server, then open the viewer in your browser.</p>
      </div>
    `;
    return;
  }

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function fetchParticipantsRobust() {
    const candidates = ["data/participants.json", "./data/participants.json", "participants.json"];
    const tried = [];
    const errors = [];

    for (const path of candidates) {
      // Retry each candidate a few times because local server startup can race page load.
      for (let attempt = 1; attempt <= 4; attempt += 1) {
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

        if (attempt < 4) {
          await delay(300);
        }
      }
    }

    throw new Error(
      `Could not load participants.json (tried: ${tried.join(", ")}; errors: ${errors.join(" | ")})`
    );
  }

  try {
    const participants = await fetchParticipantsRobust();
    participants.forEach((p) => {
      const href = `participant.html?participant=${encodeURIComponent(p.participant_id)}`;
      const tile = document.createElement("a");
      tile.className = "tile-link";
      tile.href = href;

      const idLine = document.createElement("p");
      idLine.className = "id-line";
      idLine.textContent = p.participant_id;

      const metaLine = document.createElement("p");
      metaLine.className = "meta-line";
      const meanNormalized =
        typeof p.mean_normalized_clicks === "number"
          ? p.mean_normalized_clicks.toFixed(3)
          : "N/A";
      metaLine.textContent = `Solved puzzles: ${p.solved_puzzles.length}`;

      const selectionMean =
        typeof p.selection_mean_normalized_clicks === "number"
          ? p.selection_mean_normalized_clicks.toFixed(3)
          : "N/A";

      const selectionLine = document.createElement("p");
      selectionLine.className = "meta-line";
      selectionLine.textContent = `Selection metric (top-10% mean): ${selectionMean}`;

      const normalizedLine = document.createElement("p");
      normalizedLine.className = "meta-line";
      normalizedLine.textContent = `Mean normalized clicks (all puzzles): ${meanNormalized}`;

      tile.appendChild(idLine);
      tile.appendChild(metaLine);
      tile.appendChild(selectionLine);
      tile.appendChild(normalizedLine);
      container.appendChild(tile);
    });
  } catch (err) {
    container.textContent = `Error loading participant list: ${err.message}`;
  }
})();
