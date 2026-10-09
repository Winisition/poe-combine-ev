from databricks.sdk import WorkspaceClient
import requests
import json
from datetime import datetime, timezone

def get_current_league():

    headers = {"User-Agent": "poe_user"}

    resp = requests.get(
        "https://poe.ninja/poe1/api/economy/leagues",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    leagues = resp.json()
    return leagues[0]["id"]

def ingest_poe_data(league, item_type: list[str]):

    ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    headers = {"User-Agent": "poe_combine_ev"}
    w = WorkspaceClient()
    w.files.create_directory("/Volumes/workspace/poe_economy/raw_data/historical/")

    for item in item_type:

        databricks_latest_dir = f"/Volumes/workspace/poe_economy/raw_data/{item}.json"
        databricks_hist_dir = f"/Volumes/workspace/poe_economy/raw_data/historical/{item}_{ingested_at}.json"

        resp = requests.get(
            "https://poe.ninja/poe1/api/economy/exchange/current/overview",
            params={"league": league, "type": item},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()['lines']

        for row in data:
            row["ingested_at"] = ingested_at
            row["current_league"] = league

        with open(databricks_latest_dir, "w") as f:
            json.dump(data, f)
            print(f"Saved to Databricks: {databricks_latest_dir}")

        with open(databricks_hist_dir, "w") as f:
            json.dump(data, f)
            print(f"Saved to Databricks: {databricks_hist_dir}")

# Gather scarab weights from xddbsns.com, which is open-source

def get_scarab_weights(league):

    ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    headers = {"User-Agent": "poe_combine_ev"}
    databricks_latest_dir = "/Volumes/workspace/poe_economy/raw_data/Scarab_Weights.json"

    resp = requests.get(
        "https://xddbsns.com/data/allflame/scarab-calculator.json",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()['categories']
    for row in data:
        row["ingested_at"] = ingested_at
        row["current_league"] = league

    with open(databricks_latest_dir, "w") as f:
        json.dump(data, f)
        print(f"Saved to Databricks: {databricks_latest_dir}")


league = get_current_league()
ingest_poe_data(league, item_type=["Scarab", "Essence", "Currency"])
get_scarab_weights(league)

