(async function initParticipantPage() {
  const participantId = getQueryParam("participant");
  const titleEl = document.getElementById("participantTitle");
  const puzzlesEl = document.getElementById("puzzles");

  if (!participantId) {
    titleEl.textContent = "Missing participant ID";
    return;
  }

  titleEl.textContent = participantId;

  try {
    const participants = await fetchParticipants();
    const participant = participants.find((p) => p.participant_id === participantId);

    if (!participant) {
      puzzlesEl.textContent = "Participant not found in generated data.";
      return;
    }

    if (participant.solved_puzzles.length === 0) {
      puzzlesEl.textContent = "No solved puzzles recorded for this participant.";
      return;
    }

    // Sort puzzles chronologically by time
    const sortedPuzzles = [...participant.solved_puzzles].sort((a, b) => {
      const timeA = a.time ? new Date(a.time).getTime() : Infinity;
      const timeB = b.time ? new Date(b.time).getTime() : Infinity;
      return timeA - timeB;
    });

    sortedPuzzles.forEach((puzzle, index) => {
      const href =
        `puzzle.html?participant=${escapeQueryValue(participantId)}` +
        `&task=${escapeQueryValue(puzzle.task_name)}` +
        `&attempt=${escapeQueryValue(puzzle.attempt_number)}` +
        `&file=${escapeQueryValue(puzzle.puzzle_file)}`;

      const tile = document.createElement("a");
      tile.className = "tile-link";
      tile.href = href;

      // Apply task type as class for styling
      if (puzzle.task_type) {
        tile.classList.add(puzzle.task_type.toLowerCase());
      }

      const taskLine = document.createElement("p");
      taskLine.className = "id-line";
      taskLine.textContent = puzzle.task_name;

      const attemptsLine = document.createElement("p");
      attemptsLine.className = "meta-line";
      attemptsLine.textContent = `Attempt ${puzzle.attempt_number} | Frames ${puzzle.total_frames}`;

      const orderLine = document.createElement("p");
      orderLine.className = "meta-line order-badge";
      orderLine.textContent = `#${index + 1} (${puzzle.task_type || "unknown"})`;

      tile.appendChild(taskLine);
      tile.appendChild(attemptsLine);
      tile.appendChild(orderLine);

      // Add normalized clicks comparison if available.
      if (puzzle.puzzle_stats) {
        const puzzleStats = puzzle.puzzle_stats;
        const comparisonLine = document.createElement("p");
        comparisonLine.className = "meta-line";

        if (puzzleStats.unique_participants === 1) {
          comparisonLine.textContent = "You were the only solver of this puzzle";
        } else if (typeof puzzle.participant_normalized_clicks === "number") {
          const participantNorm = puzzle.participant_normalized_clicks;
          const diffFromMean = (participantNorm - puzzleStats.mean).toFixed(3);
          const sign = diffFromMean >= 0 ? "+" : "";
          comparisonLine.textContent =
            `Your normalized clicks: ${participantNorm.toFixed(3)} (peer mean: ${puzzleStats.mean.toFixed(3)} ${sign}${diffFromMean})`;
        }

        tile.appendChild(comparisonLine);
      } else {
        const noDataLine = document.createElement("p");
        noDataLine.className = "meta-line";
        noDataLine.textContent = "No peer comparison data available";
        tile.appendChild(noDataLine);
      }

      puzzlesEl.appendChild(tile);
    });
  } catch (err) {
    puzzlesEl.textContent = `Error loading puzzles: ${err.message}`;
  }
})();
