#!/usr/bin/env python

"""
Simple ETL: Pokerogue RogueDex JSON -> runs.csv & encounters.csv

- Input:  all *.json files in DATA_RAW_DIR
- Output: runs.csv and encounters.csv in DATA_PROCESSED_DIR

Assumed JSON structure per file:

{
  "run": {
    "run_id": "run_2026-01-28T21-15-03",
    "start_timestamp": "2026-01-28T21:15:03Z",
    "end_timestamp": "2026-01-28T21:42:19Z",
    "result": "Loss",
    "final_stage": "Gym 4",
    "final_boss": "Gym Leader 4",
    "starter_species": "Bulbasaur",
    "total_battles": 7,
    "run_tag": "Rain team"
  },
  "encounters": [
    {
      "encounter_id": "run_2026-01-28T21-15-03_000",
      "battle_index": 0,
      "enemy_species": "Pidgey",
      "enemy_type1": "Normal",
      "enemy_type2": "Flying",
      "enemy_level": 5,
      "is_boss": false,
      "encounter_result": "Win",
      "enemy_ended_run": false,
      "notes": null
    },
    ...
  ]
}

Missing fields are handled gracefully and filled with defaults/None.
"""

import csv
import json
from pathlib import Path
from datetime import datetime


# ---------- CONFIG ----------

# Folder containing per-run JSON downloads from the extension
DATA_RAW_DIR = Path("data/raw_runs")

# Folder where output CSVs will be written
DATA_PROCESSED_DIR = Path("data/processed")

RUNS_CSV = DATA_PROCESSED_DIR / "runs.csv"
ENCOUNTERS_CSV = DATA_PROCESSED_DIR / "encounters.csv"


# ---------- HELPERS ----------

def parse_timestamp(ts: str):
    """Parse ISO-ish timestamp (handles trailing 'Z'). Returns datetime or None."""
    if not ts:
        return None
    ts = ts.strip()
    # Remove trailing 'Z' if present
    if ts.endswith("Z"):
        ts = ts[:-1]
    # fromisoformat handles 'YYYY-MM-DDTHH:MM:SS' and variants with microseconds
    return datetime.fromisoformat(ts)


def time_of_day_bucket(dt: datetime):
    """Return a simple time-of-day bucket label from a datetime."""
    if dt is None:
        return None
    hour = dt.hour
    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 22:
        return "Evening"
    else:
        return "Late Night"


def load_run_file(path: Path):
    """Load a single JSON file and return (run_dict, encounters_list)."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    run = data.get("run", {})
    encounters = data.get("encounters", [])
    return run, encounters


# ---------- MAIN ETL ----------

def main():
    # Ensure output dir exists
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    run_rows = []
    encounter_rows = []

    json_files = sorted(DATA_RAW_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {DATA_RAW_DIR.resolve()}")
        return

    for jf in json_files:
        run, encounters = load_run_file(jf)

        # --- RUN-LEVEL PROCESSING ---
        run_id = run.get("run_id")
        if not run_id:
            # Fallback: derive from filename if run_id missing
            run_id = jf.stem

        start_ts_raw = run.get("start_timestamp")
        end_ts_raw = run.get("end_timestamp")

        start_dt = parse_timestamp(start_ts_raw)
        end_dt = parse_timestamp(end_ts_raw)

        session_date = start_dt.date().isoformat() if start_dt else None
        session_dow = start_dt.isoweekday() if start_dt else None
        tod_bucket = time_of_day_bucket(start_dt) if start_dt else None

        total_battles = run.get("total_battles")
        if total_battles is None and encounters:
            total_battles = len(encounters)

        run_rows.append({
            "run_id": run_id,
            "start_timestamp": start_dt.isoformat() if start_dt else None,
            "end_timestamp": end_dt.isoformat() if end_dt else None,
            "result": run.get("result"),
            "final_stage": run.get("final_stage"),
            "final_boss": run.get("final_boss"),
            "starter_species": run.get("starter_species"),
            "total_battles": total_battles,
            "session_date": session_date,
            "session_day_of_week": session_dow,
            "time_of_day_bucket": tod_bucket,
            "run_tag": run.get("run_tag"),
        })

        # --- ENCOUNTER-LEVEL PROCESSING ---
        for idx, enc in enumerate(encounters):
            # Use provided encounter_id or synthesize from run_id + index
            encounter_id = enc.get("encounter_id")
            if not encounter_id:
                encounter_id = f"{run_id}_{idx:03d}"

            encounter_rows.append({
                "encounter_id": encounter_id,
                "run_id": run_id,
                "battle_index": enc.get("battle_index", idx),
                "enemy_species": enc.get("enemy_species"),
                "enemy_type1": enc.get("enemy_type1"),
                "enemy_type2": enc.get("enemy_type2"),
                "enemy_level": enc.get("enemy_level"),
                "is_boss": enc.get("is_boss"),
                "encounter_result": enc.get("encounter_result"),
                "enemy_ended_run": enc.get("enemy_ended_run"),
                "notes": enc.get("notes"),
            })

    # Define column order explicitly to match schema_v1
    run_fieldnames = [
        "run_id",
        "start_timestamp",
        "end_timestamp",
        "result",
        "final_stage",
        "final_boss",
        "starter_species",
        "total_battles",
        "session_date",
        "session_day_of_week",
        "time_of_day_bucket",
        "run_tag",
    ]

    encounter_fieldnames = [
        "encounter_id",
        "run_id",
        "battle_index",
        "enemy_species",
        "enemy_type1",
        "enemy_type2",
        "enemy_level",
        "is_boss",
        "encounter_result",
        "enemy_ended_run",
        "notes",
    ]

    # Write runs.csv
    with RUNS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=run_fieldnames)
        writer.writeheader()
        writer.writerows(run_rows)

    # Write encounters.csv
    with ENCOUNTERS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=encounter_fieldnames)
        writer.writeheader()
        writer.writerows(encounter_rows)

    print(f"Wrote {len(run_rows)} runs to {RUNS_CSV}")
    print(f"Wrote {len(encounter_rows)} encounters to {ENCOUNTERS_CSV}")


if __name__ == "__main__":
    main()
