#!/usr/bin/env python3
"""Build summary data for the Solution Paths page from data.csv."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_CSV_PATH = ROOT / "Data files" / "data.csv"
ARC_DATA_DIR = ROOT / "ARC-AGI-master" / "data"
OUT_PATH = ROOT / "high_click_viewer" / "data" / "solution_paths.json"


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def attempt_flags(rows: list[dict[str, str]]) -> dict[str, bool]:
    return {
        "complete": any(parse_bool(row.get("complete", "false")) for row in rows),
        "solved": any(parse_bool(row.get("solved", "false")) for row in rows),
    }


def parse_int(value: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        try:
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return 0


def parse_grid(grid_str: str, size_x: str, size_y: str) -> list[list[int]]:
    if not grid_str:
        return []

    rows = [row for row in str(grid_str).split("|") if row != ""]
    matrix: list[list[int]] = []
    for row in rows:
        try:
            matrix.append([int(ch) for ch in row])
        except ValueError:
            return []

    sx = parse_int(size_x) if str(size_x).strip().isdigit() else len(matrix)
    sy = parse_int(size_y) if str(size_y).strip().isdigit() and matrix else (len(matrix[0]) if matrix and matrix[0] else 0)

    if len(matrix) != sx and sx > 0:
        matrix = matrix[:sx]
    if matrix and sy > 0:
        matrix = [r[:sy] for r in matrix]

    return matrix


def grid_size(matrix: list[list[int]]) -> tuple[int, int]:
    rows = len(matrix)
    cols = len(matrix[0]) if rows and matrix[0] else 0
    return rows, cols


def grid_to_key(matrix: list[list[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(row) for row in matrix)


def grid_changed(current: list[list[int]], previous: list[list[int]]) -> bool:
    return grid_to_key(current) != grid_to_key(previous)


def load_task_names() -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for task_type in ("training", "evaluation"):
        for path in sorted((ARC_DATA_DIR / task_type).glob("*.json")):
            tasks.append({"task_type": task_type, "task_name": path.name})
    return tasks


def load_task_test_pair(task_type: str, task_name: str) -> tuple[list[list[int]], list[list[int]]]:
    task_path = ARC_DATA_DIR / task_type / task_name
    if not task_path.exists():
        return [], []

    try:
        with task_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], []

    tests = payload.get("test") if isinstance(payload, dict) else None
    if not isinstance(tests, list) or not tests:
        return [], []

    first_test = tests[0] if isinstance(tests[0], dict) else {}
    input_grid = first_test.get("input") if isinstance(first_test.get("input"), list) else []
    output_grid = first_test.get("output") if isinstance(first_test.get("output"), list) else []
    return input_grid, output_grid


def build_target_map(input_grid: list[list[int]], output_grid: list[list[int]]) -> dict[str, int]:
    target_changes: dict[str, int] = {}
    rows = max(len(input_grid), len(output_grid))
    cols = max(len(input_grid[0]) if input_grid else 0, len(output_grid[0]) if output_grid else 0)

    for row_index in range(rows):
        for col_index in range(cols):
            input_value = input_grid[row_index][col_index] if row_index < len(input_grid) and col_index < len(input_grid[row_index]) else None
            output_value = output_grid[row_index][col_index] if row_index < len(output_grid) and col_index < len(output_grid[row_index]) else None
            if input_value != output_value and output_value is not None:
                target_changes[f"{row_index}:{col_index}"] = output_value

    return target_changes


def build_input_map(input_grid: list[list[int]]) -> dict[str, int]:
    input_values: dict[str, int] = {}
    for row_index, row in enumerate(input_grid):
        for col_index, value in enumerate(row):
            input_values[f"{row_index}:{col_index}"] = value
    return input_values


def classify_step(
    frame: dict[str, Any],
    previous_grid: list[list[int]],
    target_output: list[list[int]],
    target_changes: dict[str, int],
    input_values: dict[str, int],
) -> dict[str, Any] | None:
    action = str(frame.get("action", "")).strip()
    current_grid = frame.get("grid") if isinstance(frame.get("grid"), list) else []

    # Skip passive organizational actions - they don't represent actual puzzle-solving work
    if action in {"copy_from_input", "reset_grid"}:
        return None

    if action not in {"edit", "floodfill", "change_width", "change_height"}:
        return None

    if not grid_changed(current_grid, previous_grid):
        return None

    current_rows, current_cols = grid_size(current_grid)
    target_rows, target_cols = grid_size(target_output)
    size_matches = current_rows == target_rows and current_cols == target_cols
    target_is_all_zero = all(value == 0 for row in target_output for value in row)

    action_x = frame.get("action_x")
    action_y = frame.get("action_y")
    selected_symbol = frame.get("selected_symbol")

    reason = "step is not on the solution path"
    label = action

    if action in {"edit", "floodfill"}:
        if action_x in {"", None} or action_y in {"", None} or selected_symbol in {"", None}:
            reason = "missing coordinate/color"
        else:
            key = f"{parse_int(action_x)}:{parse_int(action_y)}"
            allowed_values = set()
            if key in target_changes:
                allowed_values.add(str(target_changes[key]))
            if key in input_values:
                allowed_values.add(str(input_values[key]))

            if not allowed_values:
                reason = "wrong coordinate"
            elif str(selected_symbol).strip() not in allowed_values:
                if len(allowed_values) == 1:
                    expected = next(iter(allowed_values))
                    reason = f"wrong color (expected {expected})"
                else:
                    expected = "/".join(sorted(allowed_values))
                    reason = f"wrong color (expected one of {expected})"
            else:
                return {"label": f"r{parse_int(action_x)}c{parse_int(action_y)}={selected_symbol}", "reason": "", "aligned": True}
            label = f"r{parse_int(action_x)}c{parse_int(action_y)}={selected_symbol}"
    elif action in {"change_width", "change_height"}:
        previous_rows, previous_cols = grid_size(previous_grid)
        previous_distance = abs(previous_rows - target_rows) + abs(previous_cols - target_cols)
        current_distance = abs(current_rows - target_rows) + abs(current_cols - target_cols)
        if current_distance < previous_distance or size_matches:
            return {"label": f"resize to {current_rows}x{current_cols}", "reason": "", "aligned": True}
        reason = f"size change moved away from target ({target_rows}x{target_cols})"
        label = f"resize to {current_rows}x{current_cols}"

    return {"label": label, "reason": reason, "aligned": False}


def clone_grid(matrix: list[list[int]]) -> list[list[int]]:
    return [list(row) for row in matrix]


def build_changes_only_grid(input_grid: list[list[int]], output_grid: list[list[int]]) -> list[list[int | None]]:
    """Build a grid showing only the cells that changed from input to output.
    
    Cells that changed show the output value; cells that didn't change show None.
    """
    rows = max(len(input_grid), len(output_grid))
    cols = max(len(input_grid[0]) if input_grid else 0, len(output_grid[0]) if output_grid else 0)
    
    changes_grid: list[list[int | None]] = []
    for row_index in range(rows):
        row = []
        for col_index in range(cols):
            input_value = input_grid[row_index][col_index] if row_index < len(input_grid) and col_index < len(input_grid[row_index]) else None
            output_value = output_grid[row_index][col_index] if row_index < len(output_grid) and col_index < len(output_grid[row_index]) else None
            if input_value != output_value and output_value is not None:
                row.append(output_value)
            else:
                row.append(None)
        changes_grid.append(row)
    
    return changes_grid


def main() -> None:
    rows_by_attempt: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)

    with DATA_CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["task_type"], row["task_name"], row["hashed_id"], row["attempt_number"])
            rows_by_attempt[key].append(row)

    participants_by_task: dict[tuple[str, str], set[str]] = defaultdict(set)
    attempts_by_task: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for (task_type, task_name, hashed_id, attempt_number), rows in rows_by_attempt.items():
        ordered_rows = sorted(rows, key=lambda row: parse_int(row.get("action_id", "0")))
        flags = attempt_flags(ordered_rows)
        if not flags["solved"]:
            continue

        participants_by_task[(task_type, task_name)].add(hashed_id)

        input_grid: list[list[int]] = []
        final_grid: list[list[int]] = []
        frame_rows: list[dict[str, Any]] = []

        for row in ordered_rows:
            current_grid = parse_grid(row.get("test_output_grid", ""), row.get("test_output_size_x", ""), row.get("test_output_size_y", ""))
            if not input_grid:
                input_grid = parse_grid(row.get("test_input_grid", ""), row.get("test_input_size_x", ""), row.get("test_input_size_y", ""))
            final_grid = current_grid
            frame_rows.append(
                {
                    "action_id": parse_int(row.get("action_id", "0")),
                    "action": row.get("action", ""),
                    "action_x": row.get("action_x", ""),
                    "action_y": row.get("action_y", ""),
                    "selected_symbol": row.get("selected_symbol", ""),
                    "selected_tool": row.get("selected_tool", ""),
                    "grid": current_grid,
                }
            )

        arc_input_grid, arc_output_grid = load_task_test_pair(task_type, task_name)
        target_input_grid = arc_input_grid if arc_input_grid else input_grid
        target_output_grid = arc_output_grid if arc_output_grid else final_grid

        target_changes = build_target_map(target_input_grid, target_output_grid)
        input_values = build_input_map(target_input_grid)
        changes_only_grid = build_changes_only_grid(target_input_grid, target_output_grid)
        off_path_steps: list[dict[str, Any]] = []
        previous_grid: list[list[int]] = []
        for frame in frame_rows:
            grid_before = clone_grid(previous_grid)
            classification = classify_step(frame, previous_grid, target_output_grid, target_changes, input_values)
            previous_grid = frame["grid"]
            if classification is None or classification["aligned"]:
                continue
            off_path_steps.append(
                {
                    "action_id": frame["action_id"],
                    "action": frame["action"],
                    "action_x": frame["action_x"],
                    "action_y": frame["action_y"],
                    "selected_symbol": frame["selected_symbol"],
                    "label": classification["label"],
                    "reason": classification["reason"],
                    "grid_before": grid_before,
                    "grid_after": clone_grid(frame["grid"]),
                    "changes_only": changes_only_grid,
                }
            )

        attempts_by_task[(task_type, task_name)].append(
            {
                "participant_id": hashed_id,
                "attempt_number": parse_int(attempt_number),
                "complete": flags["complete"],
                "solved": flags["solved"],
                "wrong_step_count": len(off_path_steps),
                "off_path_steps": off_path_steps,
            }
        )

    tasks: list[dict[str, Any]] = []
    for task in load_task_names():
        key = (task["task_type"], task["task_name"])
        participant_ids = sorted(participants_by_task.get(key, set()))
        solution_paths = sorted(
            attempts_by_task.get(key, []),
            key=lambda item: (item["attempt_number"], item["participant_id"]),
        )
        tasks.append(
            {
                "task_type": task["task_type"],
                "task_name": task["task_name"],
                "participant_count": len(participant_ids),
                "participant_ids": participant_ids,
                "wrong_step_total": sum(path["wrong_step_count"] for path in solution_paths),
                "solution_paths": solution_paths,
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump({"tasks": tasks}, f, separators=(",", ":"))

    print(f"Wrote {OUT_PATH} with {len(tasks)} tasks.")


if __name__ == "__main__":
    main()