#!/usr/bin/env python3
"""Build summary data for the Participant solutions page."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_CSV_PATH = ROOT / "Data files" / "data.csv"
ARC_DATA_DIR = ROOT / "ARC-AGI-master" / "data"
OUT_PATH = ROOT / "high_click_viewer" / "data" / "participant_solutions.json"


def parse_int(value: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def attempt_flags(rows: list[dict[str, str]]) -> dict[str, bool]:
    return {
        "complete": any(parse_bool(row.get("complete", "false")) for row in rows),
        "solved": any(parse_bool(row.get("solved", "false")) for row in rows),
    }


def load_task_names() -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for task_type in ("training", "evaluation"):
        for path in sorted((ARC_DATA_DIR / task_type).glob("*.json")):
            tasks.append({"task_type": task_type, "task_name": path.name})
    return tasks


def main() -> None:
    rows_by_attempt: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    participants_by_task: dict[tuple[str, str], set[str]] = defaultdict(set)
    paths_by_task: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    with DATA_CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["task_type"], row["task_name"], row["hashed_id"], row["attempt_number"])
            rows_by_attempt[key].append(row)

    for (task_type, task_name, hashed_id, attempt_number), rows in rows_by_attempt.items():
        ordered_rows = sorted(rows, key=lambda row: parse_int(row.get("action_id", "0")))
        flags = attempt_flags(ordered_rows)
        if not flags["solved"]:
            continue

        participants_by_task[(task_type, task_name)].add(hashed_id)

        actions: list[str] = []
        for row in ordered_rows:
            actions.append(row.get("action", ""))

        paths_by_task[(task_type, task_name)].append(
            {
                "hashed_id": hashed_id,
                "attempt_number": parse_int(attempt_number),
                "complete": flags["complete"],
                "solved": flags["solved"],
                "action_count": len(actions),
                "actions": actions,
            }
        )

    tasks: list[dict[str, Any]] = []
    for task in load_task_names():
        task_key = (task["task_type"], task["task_name"])
        participant_ids = sorted(participants_by_task.get(task_key, set()))
        solution_paths = sorted(
            paths_by_task.get(task_key, []),
            key=lambda item: (item["attempt_number"], item["hashed_id"]),
        )
        tasks.append(
            {
                "task_type": task["task_type"],
                "task_name": task["task_name"],
                "participant_count": len(participant_ids),
                "participant_ids": participant_ids,
                "solution_paths": solution_paths,
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump({"tasks": tasks}, f, separators=(",", ":"))

    print(f"Wrote {OUT_PATH} with {len(tasks)} tasks.")


if __name__ == "__main__":
    main()