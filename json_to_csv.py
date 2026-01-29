#!/usr/bin/env python

"""
Simple ETL: Pokerogue RogueDex JSON -> runs.csv, encounters.csv & encounter_participants.csv

- Input:  all *.json files in DATA_RAW_DIR
- Output: runs.csv, encounters.csv, and encounter_participants.csv in DATA_PROCESSED_DIR

Assumed JSON structure per file (v1 with team snapshot):

{
  "run": {
    "run_id": "run_2026-01-28T21-15-03",
    "start_timestamp": "2026-01-28T21:15:03Z",
    "end_timestamp": "2026-01-28T21:42:19Z",
    "result": "Loss",
    "final_stage": "Gym 4",
    "final_boss": "Gym Leader 4",
    "starter_species": 1,
    "total_battles": 7,
    "run_tag": "Rain team"
  },
  "encounters": [
    {
      "encounter_id": "run_2026-01-28T21-15-03_000",
      "battle_index": 0,
      "enemy_species": 16,
      "enemy_type1": null,
      "enemy_type2": null,
      "enemy_level": 5,
      "is_boss": false,
      "encounter_result": "Win",
      "enemy_ended_run": false,
      "notes": null,

      "team_species_ids": [4, 7, 1],
      "team_levels": [8, 7, 6],
      "team_size": 3
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
PARTICIPANTS_CSV = DATA_PROCESSED_DIR / "encounter_participants.csv"  # NEW


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
    participant_rows = []  # NEW

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

        # --- ENCOUNTER-LEVEL + PARTICIPANTS PROCESSING ---
        for idx, enc in enumerate(encounters):
            # Use provided encounter_id or synthesize from run_id + index
            encounter_id = enc.get("encounter_id")
            if not encounter_id:
                encounter_id = f"{run_id}_{idx:03d}"

            # Team snapshot: arrays of species IDs and levels, plus team_size
            team_species = enc.get("team_species_ids") or []
            team_levels = enc.get("team_levels") or []
            team_size = enc.get("team_size")

            # Helper to safely get index i from a list
            def _at(lst, i):
                return lst[i] if i < len(lst) else None

            # Wide encounter row (kept for v1 compatibility)
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

                # Team snapshot fields (wide)
                "team_size": team_size,
                "ally1_species_id": _at(team_species, 0),
                "ally2_species_id": _at(team_species, 1),
                "ally3_species_id": _at(team_species, 2),
                "ally4_species_id": _at(team_species, 3),
                "ally5_species_id": _at(team_species, 4),
                "ally6_species_id": _at(team_species, 5),
                "ally1_level": _at(team_levels, 0),
                "ally2_level": _at(team_levels, 1),
                "ally3_level": _at(team_levels, 2),
                "ally4_level": _at(team_levels, 3),
                "ally5_level": _at(team_levels, 4),
                "ally6_level": _at(team_levels, 5),
            })

            # --- NEW: tall participant rows ---

            # Enemy as a participant
            enemy_species = enc.get("enemy_species")
            if enemy_species is not None:
                participant_rows.append({
                    "encounter_id": encounter_id,
                    "run_id": run_id,
                    "side": "enemy",
                    "slot_index": 0,
                    "species_id": enemy_species,
                    "level": enc.get("enemy_level"),
                })

            # Allies as participants (one row per ally slot)
            for slot_idx, species_id in enumerate(team_species):
                if species_id is None:
                    continue
                level = team_levels[slot_idx] if slot_idx < len(team_levels) else None
                participant_rows.append({
                    "encounter_id": encounter_id,
                    "run_id": run_id,
                    "side": "ally",
                    "slot_index": slot_idx,
                    "species_id": species_id,
                    "level": level,
                })

    # Define column order explicitly to match schema_v1 (with team fields)
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
        "team_size",
        "ally1_species_id",
        "ally2_species_id",
        "ally3_species_id",
        "ally4_species_id",
        "ally5_species_id",
        "ally6_species_id",
        "ally1_level",
        "ally2_level",
        "ally3_level",
        "ally4_level",
        "ally5_level",
        "ally6_level",
    ]

    participant_fieldnames = [  # NEW
        "encounter_id",
        "run_id",
        "side",
        "slot_index",
        "species_id",
        "level",
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

    # Write encounter_participants.csv
    with PARTICIPANTS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=participant_fieldnames)
        writer.writeheader()
        writer.writerows(participant_rows)

    print(f"Wrote {len(run_rows)} runs to {RUNS_CSV}")
    print(f"Wrote {len(encounter_rows)} encounters to {ENCOUNTERS_CSV}")
    print(f"Wrote {len(participant_rows)} participants to {PARTICIPANTS_CSV}")


if __name__ == "__main__":
    main()
