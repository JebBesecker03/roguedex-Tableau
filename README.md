# Pokerogue × Tableau Analytics  
### v1 – JSON Logger, ETL Pipeline, and Tableau Data Model

This project extends the original **Rogue Dex** browser extension into a full analytics pipeline for **Pokerogue**, combining a browser extension, JSON-based event capture, a Python ETL workflow, and a Tableau-ready data model.

The objective is to convert a Pokerogue session into structured, analyzable datasets suitable for deeper insight, exploration, and visualization.

---

# Rogue Dex Browser Extension (Original Project)

## Description
Rogue Dex is a browser extension that connects to Pokerogue and displays real-time Pokémon information using PokeAPI. This includes type weaknesses, resistances, immunities, abilities, natures, IVs, and related metadata.

This fork preserves all original overlay functionality while adding a complete run-logging subsystem to enable analytics.

## Original Features
- Real-time Pokémon weaknesses, resistances, and immunities  
- Ability, IV, nature, and type-effectiveness details  
- Automatic overlay that responds to game updates  
- Designed to enhance Pokerogue strategy and player decision-making

## Installation
1. Clone this repository  
2. Load the extension in Developer Mode (Chrome or Firefox)  
3. Open https://pokerogue.net  
4. The overlay activates automatically when a game session loads

---

# Additions in This Fork: Analytics Extensions (v1)

## 1. Run Tracking
The extension now supports manual start/end run events through the popup interface.  
Each run produces a structured JSON file containing:

- Run metadata (start/end timestamps, session info, total battles)  
- Ordered encounter logs  
- Wave-deduped detection using Pokerogue’s internal `waveIndex`  
- Optional metadata (run tags, final stage, final boss)

Downloaded files are saved into:
- data/raw_runs/


---

## 2. Encounter Logging
For every encounter, the logger captures:

- Enemy species (numeric Pokédex ID)  
- Enemy level  
- Battle index (0, 1, 2, ...)  
- Boss flag (future expansion)  
- Encounter result placeholders  
- Deduplication of repeated frame updates  
- Final run aggregation on run completion  

The v1 logging model focuses on stable, reproducible event capture with minimal overhead.

---

## 3. Python ETL Pipeline
Script: `etl/json_to_csv.py`

Converts all raw JSON logs into clean, analysis-ready CSV files:
- data/processed/runs.csv
- data/processed/encounters.csv


The ETL performs:

- ISO timestamp normalization  
- Derived fields (date, day-of-week, time-of-day buckets)  
- Run-level and encounter-level normalization  
- Graceful handling of missing or null values  
- Strict schema consistency across output files

---

## 4. Tableau Data Model
This repository includes a schema suitable for Tableau or any analytics workflow.

Datasets created:

- `runs.csv` – one row per Pokerogue run  
- `encounters.csv` – one row per encounter event  
- Optional: external Pokédex dataset for enriched joins  

The model supports dashboards such as:

- Session timelines  
- Encounter sequencing  
- Enemy species frequency analysis  
- Type-exposure analysis  
- Run outcomes and performance trends

---

# Directory Structure
pokerogue-tableau/
├── extension/
│ ├── manifest.json
│ ├── background.js
│ ├── content.js
│ └── libs/
│
├── etl/
│ ├── json_to_csv.py
│ └── requirements.txt
│
├── data/
│ ├── raw_runs/
│ ├── processed/
│ └── external/
│ └── pokedex.csv
│
└── docs/
└── schema_v1.md

---

# Usage Workflow

## Step 1 — Play Pokerogue
- Navigate to https://pokerogue.net  
- Open the extension popup  
- Click **Start Run**  
- Play normally  
- Click **End Run**  

A JSON run log will be created automatically.

## Step 2 — Run ETL

From the repository root:
- python etl/json_to_csv.py


Outputs are written to `data/processed/`.

## Step 3 — Analyze in Tableau
Connect the processed CSVs (and optional external Pokédex dataset) in Tableau.

---

# Contribution Guidelines
Contributions are welcome in the areas of:

- Additional event types (moves used, damage events, turn-level logs)  
- Boss detection and classification logic  
- Expanded metadata capture  
- Enhanced or incremental ETL pipelines  
- Tableau dashboards and analytical templates  

Fork the repository, create a feature branch, and submit a pull request.

---

# Credits
This work builds upon the original Rogue Dex browser extension.  
All credit for the overlay, Pokémon data features, and extension foundation belongs to the original authors.

Thanks also to:  
- PokeAPI for Pokémon metadata resources  
- Pokerogue for providing the gameplay and APIs used by the overlay  

---

# License
This project is released under the MIT License.  
See `LICENSE` for full details.

---

# Privacy Notice
This software does not transmit or store any personal data.  
All logging, processing, and analysis occur locally on the user's device.

No gameplay information is sent to external servers.

---

# Data Schema (v1)
Detailed table and field definitions are located in:
- docs/schema_v1.md
