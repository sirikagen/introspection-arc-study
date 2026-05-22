#!/usr/bin/env python3
"""Build compact JSON files for the high-click participant replay website."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOP15_PATH = ROOT / "Analysis" / "results" / "p95_high_clickers.csv"
NORMALIZED_SUMMARY_PATH = ROOT / "Summary_data files" / "summary_data_filtered_normalized.csv"
SUMMARY_DATA_PATH = ROOT / "Data files" / "summary_data.csv"
DATA_CSV_PATH = ROOT / "Data files" / "data.csv"
SITE_ROOT = ROOT / "high_click_viewer"
DATA_DIR = SITE_ROOT / "data"
PUZZLES_DIR = DATA_DIR / "puzzles"
ARC_TASK_DIR_CANDIDATES = [
    ROOT / "arc_tasks",
    ROOT / "ARC" / "data" / "training",
    ROOT / "ARC" / "data" / "evaluation",
    ROOT / "data" / "training",
    ROOT / "data" / "evaluation",
]


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def parse_grid(grid_str: str, size_x: str, size_y: str) -> list[list[int]]:
    """Parse a grid string like |000|105| into a matrix of ints."""
    if not grid_str:
        return []

    parts = [row for row in grid_str.split("|") if row != ""]
    if not parts:
        return []

    matrix: list[list[int]] = []
    for row in parts:
        matrix.append([int(ch) for ch in row])

    sx = int(size_x) if str(size_x).strip().isdigit() else len(matrix)
    sy = int(size_y) if str(size_y).strip().isdigit() and matrix else len(matrix[0]) if matrix and matrix[0] else 0

    # Normalize dimensions if metadata is inconsistent.
    if len(matrix) != sx and sx > 0:
        matrix = matrix[:sx]
    if matrix and sy > 0:
        matrix = [r[:sy] for r in matrix]

    return matrix


def load_puzzle_normalized_stats(path: Path) -> dict[str, dict[str, Any]]:
    """Load per-puzzle normalized click statistics from solved attempts."""
    puzzle_data: dict[str, dict[str, Any]] = defaultdict(lambda: {"values": [], "attempts_by_pid": defaultdict(list)})
    
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            task = row.get("task_name", "").strip()
            pid = row.get("hashed_id", "").strip()
            norm = row.get("normalized_num_actions", "").strip()
            attempt = row.get("attempt_number", "").strip()
            solved = str(row.get("solved", "")).strip().lower() == "true"
            
            if not (task and pid and norm and solved):
                continue
            try:
                norm_float = float(norm)
                puzzle_data[task]["values"].append(norm_float)
                puzzle_data[task]["attempts_by_pid"][pid].append(norm_float)
            except (TypeError, ValueError):
                continue
    
    stats: dict[str, dict[str, Any]] = {}
    for task, data in puzzle_data.items():
        values = data["values"]
        if not values:
            continue
        values_sorted = sorted(values)
        stats[task] = {
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "count": len(values),
            "unique_participants": len(data["attempts_by_pid"]),
        }
    return stats

def parse_grid(grid_str: str, size_x: str, size_y: str) -> list[list[int]]:
    """Parse a grid string like |000|105| into a matrix of ints."""
    if not grid_str:
        return []

    parts = [row for row in grid_str.split("|") if row != ""]
    if not parts:
        return []

    matrix: list[list[int]] = []
    for row in parts:
        matrix.append([int(ch) for ch in row])

    sx = int(size_x) if str(size_x).strip().isdigit() else len(matrix)
    sy = int(size_y) if str(size_y).strip().isdigit() and matrix else len(matrix[0]) if matrix and matrix[0] else 0

    # Normalize dimensions if metadata is inconsistent.
    if len(matrix) != sx and sx > 0:
        matrix = matrix[:sx]
    if matrix and sy > 0:
        matrix = [r[:sy] for r in matrix]

    return matrix


def load_top15_ids(path: Path) -> list[str]:
    ids: list[str] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["hashed_id"].strip()
            if pid:
                ids.append(pid)
    if not ids:
        raise ValueError("No participants found in p95 high-clickers file.")
    return ids


def load_selection_metric(path: Path, participant_ids: list[str]) -> dict[str, float]:
    participant_set = set(participant_ids)
    metrics: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("hashed_id", "").strip()
            if pid not in participant_set or pid in metrics:
                continue
            raw = row.get("mean_num_actions", "")
            try:
                metrics[pid] = float(raw)
            except (TypeError, ValueError):
                continue
    return metrics


def load_mean_normalized_clicks(path: Path, participant_ids: list[str]) -> dict[str, float]:
    participant_set = set(participant_ids)
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("hashed_id", "")
            if pid not in participant_set:
                continue
            value = row.get("normalized_num_actions", "")
            try:
                normalized = float(value)
            except (TypeError, ValueError):
                continue

            sums[pid] += normalized
            counts[pid] += 1

    means: dict[str, float] = {}
    for pid in participant_ids:
        if counts.get(pid, 0) > 0:
            means[pid] = sums[pid] / counts[pid]
    return means


def pick_best_input_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the most likely puzzle test-input row from an attempt."""
    def _area(row: dict[str, Any]) -> int:
        sx = int(row["test_input_size_x"]) if str(row.get("test_input_size_x", "")).isdigit() else 0
        sy = int(row["test_input_size_y"]) if str(row.get("test_input_size_y", "")).isdigit() else 0
        return sx * sy

    candidates: list[dict[str, Any]] = []
    non_zero_candidates: list[dict[str, Any]] = []

    for row in rows:
        grid_str = (row.get("test_input_grid") or "").strip()
        if not grid_str:
            continue
        candidates.append(row)
        all_zero = all(ch in "|0" for ch in grid_str)
        if not all_zero:
            non_zero_candidates.append(row)

    if non_zero_candidates:
        return max(non_zero_candidates, key=_area)
    if candidates:
        return max(candidates, key=_area)
    return rows[0] if rows else None


def load_arc_example_pairs(task_name: str) -> list[dict[str, Any]]:
    """Load ARC train input-output pairs for a task if its JSON is available."""
    for base in ARC_TASK_DIR_CANDIDATES:
        candidate = base / task_name
        if not candidate.exists():
            continue

        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        train_pairs = payload.get("train", []) if isinstance(payload, dict) else []
        result: list[dict[str, Any]] = []
        for pair in train_pairs:
            if not isinstance(pair, dict):
                continue
            in_grid = pair.get("input")
            out_grid = pair.get("output")
            if isinstance(in_grid, list) and isinstance(out_grid, list):
                result.append({"input": in_grid, "output": out_grid})
        return result

    return []


def load_semantic_descriptions(path: Path, participant_ids: list[str]) -> dict[tuple[str, str, str], dict[str, str]]:
    """Load first/last written semantic descriptions from summary_data.csv."""
    participant_set = set(participant_ids)
    descriptions: dict[tuple[str, str, str], dict[str, str]] = {}

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = (row.get("hashed_id") or "").strip()
            if pid not in participant_set:
                continue

            task_name = (row.get("task_name") or "").strip()
            attempt_number = str((row.get("attempt_number") or "")).strip()
            if not task_name or not attempt_number:
                continue

            key = (pid, task_name, attempt_number)
            descriptions[key] = {
                "first_written_description": (row.get("first_written_solution") or "").strip(),
                "last_written_description": (row.get("last_written_solution") or "").strip(),
            }

    return descriptions


def load_task_types_by_task_name(path: Path) -> dict[str, str]:
    """Load task_type by task_name from summary_data.csv."""
    task_types: dict[str, str] = {}

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            task_name = (row.get("task_name") or "").strip()
            task_type = (row.get("task_type") or "").strip().lower()
            if not task_name or not task_type:
                continue

            # Keep the first seen value for deterministic behavior.
            task_types.setdefault(task_name, task_type)

    return task_types


def main() -> None:
    participant_ids = load_top15_ids(TOP15_PATH)
    participants_set = set(participant_ids)
    selection_metric = load_selection_metric(TOP15_PATH, participant_ids)
    mean_normalized_clicks = load_mean_normalized_clicks(NORMALIZED_SUMMARY_PATH, participant_ids)
    puzzle_stats = load_puzzle_normalized_stats(NORMALIZED_SUMMARY_PATH)
    semantic_descriptions = load_semantic_descriptions(SUMMARY_DATA_PATH, participant_ids)
    task_types_by_task_name = load_task_types_by_task_name(SUMMARY_DATA_PATH)
    
    # Load per-puzzle-per-participant normalized values from summary.
    puzzle_participant_norms: dict[tuple[str, str], float] = {}
    puzzle_task_info: dict[tuple[str, str], dict[str, Any]] = {}
    
    with NORMALIZED_SUMMARY_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("hashed_id", "").strip()
            task = row.get("task_name", "").strip()
            norm = row.get("normalized_num_actions", "").strip()
            time_str = row.get("time", "").strip()
            solved = str(row.get("solved", "")).strip().lower() == "true"
            if pid in participants_set and task and norm and solved:
                try:
                    puzzle_participant_norms[(pid, task)] = float(norm)
                    if (pid, task) not in puzzle_task_info:
                        puzzle_task_info[(pid, task)] = {
                            "time": time_str,
                        }
                except (TypeError, ValueError):
                    pass
    
    # Load solved attempts and action rows from data.csv
    solved_attempts: dict[str, set[tuple[str, str]]] = defaultdict(set)
    attempt_rows: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    puzzle_first_time: dict[tuple[str, str], str] = {}
    
    with DATA_CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["hashed_id"]
            if pid not in participants_set:
                continue

            task_name = row["task_name"]
            attempt_number = row["attempt_number"]
            key = (pid, task_name, attempt_number)
            attempt_rows[key].append(row)
            
            # Capture first occurrence of time for this (pid, task_name)
            puzzle_key = (pid, task_name)
            if puzzle_key not in puzzle_first_time and row.get("time", "").strip():
                puzzle_first_time[puzzle_key] = row["time"].strip()

            if parse_bool(row["solved"]):
                solved_attempts[pid].add((task_name, attempt_number))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PUZZLES_DIR.mkdir(parents=True, exist_ok=True)

    participants_payload: list[dict[str, Any]] = []

    for pid in participant_ids:
        puzzle_entries: list[dict[str, Any]] = []
        solved_for_pid = sorted(
            solved_attempts.get(pid, set()),
            key=lambda x: (x[0], int(x[1]) if str(x[1]).isdigit() else x[1]),
        )

        for task_name, attempt_number in solved_for_pid:
            rows = attempt_rows[(pid, task_name, attempt_number)]
            rows.sort(key=lambda r: int(r["action_id"]) if str(r["action_id"]).isdigit() else 0)

            frames: list[dict[str, Any]] = []
            for idx, row in enumerate(rows):
                frames.append(
                    {
                        "frame_index": idx,
                        "action_id": row["action_id"],
                        "time": row["time"],
                        "action": row["action"],
                        "action_x": row["action_x"],
                        "action_y": row["action_y"],
                        "selected_symbol": row["selected_symbol"],
                        "selected_tool": row["selected_tool"],
                        "solved": parse_bool(row["solved"]),
                        "done": parse_bool(row["done"]),
                        "grid": parse_grid(
                            row["test_output_grid"],
                            row["test_output_size_x"],
                            row["test_output_size_y"],
                        ),
                    }
                )

            puzzle_slug = f"{task_name.replace('.json', '')}__attempt_{attempt_number}"
            puzzle_file = f"puzzles/{pid}__{puzzle_slug}.json"

            reference_row = pick_best_input_row(rows)
            input_grid = (
                parse_grid(
                    reference_row.get("test_input_grid", ""),
                    reference_row.get("test_input_size_x", ""),
                    reference_row.get("test_input_size_y", ""),
                )
                if reference_row
                else []
            )

            example_pairs = load_arc_example_pairs(task_name)

            puzzle_payload = {
                "participant_id": pid,
                "task_name": task_name,
                "attempt_number": attempt_number,
                "total_frames": len(frames),
                "frames": frames,
                "input_grid": input_grid,
                "input_grid_first_frame": input_grid,
                "example_pairs": example_pairs,
                "semantic_descriptions": semantic_descriptions.get(
                    (pid, task_name, str(attempt_number)),
                    {
                        "first_written_description": "",
                        "last_written_description": "",
                    },
                ),
            }

            out_path = DATA_DIR / puzzle_file
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(puzzle_payload, f)

            puzzle_entries.append(
                {
                    "task_name": task_name,
                    "attempt_number": attempt_number,
                    "total_frames": len(frames),
                    "puzzle_file": puzzle_file,
                    "participant_normalized_clicks": puzzle_participant_norms.get((pid, task_name)),
                    "puzzle_stats": puzzle_stats.get(task_name),
                    "task_type": task_types_by_task_name.get(task_name),
                    "time": puzzle_first_time.get((pid, task_name)),
                }
            )

        participants_payload.append(
            {
                "participant_id": pid,
                "selection_mean_normalized_clicks": selection_metric.get(pid),
                "mean_normalized_clicks": mean_normalized_clicks.get(pid),
                "solved_puzzles": puzzle_entries,
            }
        )

    with (DATA_DIR / "participants.json").open("w", encoding="utf-8") as f:
        json.dump(participants_payload, f)

    print(f"Wrote participant list and {sum(len(p['solved_puzzles']) for p in participants_payload)} solved puzzle entries.")


if __name__ == "__main__":
    main()
