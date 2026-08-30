PoE Combine EV

A batch data pipeline that detects pricing inefficiencies in a live marketplace.

Path of Exile has an in-game economy where players trade different currencies at floating, player-set prices. 

Scarabs can be combined through a vendor recipe: trade in three of one item, receive one random item of the same type back. The outputs are random but the odds are calculated, so each input item has a computable expected value. Since prices float freely, items regularly trade below that expected value.

Essences are re-rolled into another essence of the same category using Harvest lifeforce. Outcomes here are uniform within a category (normal essences only roll into normal essences, and so on), so EV is simply the average price across that category. A buying opportunity is available whenever the essence cost + lifeforce cost < expected output value


This pipeline ingests live market prices every 15 minutes, computes EV per item, and surfaces the mispriced ones on a dashboard.

Live dashboard: https://poe-combine-ev-7474656356418861.aws.databricksapps.com

Architecture
poe.ninja API
     │
     ▼
Python ingestion  ──────────►  Unity Catalog Volume  (raw JSON, current + historical)
     │                                   │
     │                                   ▼
     │                          PySpark transform      (flatten, join weights, compute EV)
     │                                   │
     │                                   ▼
     │                          Delta Lake tables       (scarab_ev, essence_ev)
     │                                   │
     └── Databricks Job ─────────────────┘
         (chained tasks, every 15 min)   │
                                         ▼
                              Streamlit dashboard
                              (Databricks Apps, service principal auth)

Stack: Python · PySpark · Delta Lake · Unity Catalog · Databricks Jobs · Databricks Apps · Streamlit

How it works

1. Ingest (ingest.py) pulls current prices from the poe.ninja API for scarabs, essences and currency, plus a static scarab drop-weight reference dataset. This file writes the raw JSON to a Unity Catalog Volume, and includes both a current snapshot and a timestamped historical copy so price history can accumulate over time.

2. Transform (PySpark notebook in Databricks) flattens the nested API response and current joins the scarab / essence prices against their respective weights to convert into probabilities, and subsequently get the EV of an output. The results are written to Delta tables in Unity Catalog.

3. Orchestration (Databricks Jobs) Ingest and Transform are run as two tasks in a single job scheduled every 15 mins, with transform dependent on ingestion succeeding.

4. Dashboard (Streamlit on Databricks Apps). Databricks Apps reads `app.py` and `app.yaml` directly from GitHub repo, which defines the launch command and the SQL warehouse path. We also ise SQL editor to grant (`USE CATALOG`, `USE SCHEMA`, `SELECT`) so that it can read the Delta tables.


A note on the drop-weight data

The EV calculation depends on knowing how likely each output item is. These probabilities are not published by the game's developer, and come from a community-maintained dataset built by aggregating hundreds of thousands of player-submitted vendor results. The weights are statistically inferred, and the actual weights could differ significantly. The weights dataset is also a point-in-time snapshot and is not re-fetched on the pipeline's schedule, which can cause inaccuracy if balance patches change drop pools.


Prices, by contrast, are pulled live from poe.ninja on every run and are as current as the source allows.

Repo layout
ingest/
  ingest.py          # API pull → Unity Catalog Volume
dashboard/
  app.py             # Streamlit dashboard
  app.yaml           # Databricks Apps runtime config
  requirements.txt

Secrets are not committed. The deployed app authenticates via a Databricks service principal; local development uses a gitignored .env.