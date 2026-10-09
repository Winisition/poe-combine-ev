#!/usr/bin/env python
# coding: utf-8

# In[1]:

from dotenv import load_dotenv
import os
from databricks.sdk import WorkspaceClient
import requests
import json
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "raw")
HIST_DIR = os.path.join(DATA_DIR, "historical")

load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

DATABRICKS_HOST = os.environ["DATABRICKS_HOST"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]


# In[2]:


def get_current_league():

    headers = {
            "User-Agent": "poe_user"
        }
    
    resp = requests.get(
        "https://poe.ninja/poe1/api/economy/leagues",
        headers=headers,
    )
    resp.raise_for_status()
    leagues = resp.json()
    return leagues[0]["id"]  # first entry = current challenge league


# In[ ]:


def ingest_poe_data(league, item_type: list[str]):

    ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    headers = {"User-Agent": "poe_combine_ev"}
    w = WorkspaceClient()

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(HIST_DIR, exist_ok=True)
    w.files.create_directory("/Volumes/workspace/poe_economy/raw_data/historical/")

    for item in item_type:

        # Set directory for local and cloud

        local_latest_dir = os.path.join(DATA_DIR, f"{item}.json")
        local_hist_dir = os.path.join(HIST_DIR, f"{item}_historical_{ingested_at}.json")

        databricks_latest_dir = f"/Volumes/workspace/poe_economy/raw_data/{item}.json"
        databricks_hist_dir = f"/Volumes/workspace/poe_economy/raw_data/historical/{item}_{ingested_at}.json"

        resp = requests.get(
            "https://poe.ninja/poe1/api/economy/exchange/current/overview",
            params={"league": league, "type": item},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()['lines']

        for row in data:
            row["ingested_at"] = ingested_at

        with open(local_latest_dir, "w") as f:
            json.dump(data, f)
            print(f"Saved to Local: {local_latest_dir}")

        with open(local_hist_dir, "w") as f:
            json.dump(data, f)
            print(f"Saved to Local: {local_hist_dir}")

        with open(local_latest_dir, "rb") as f:
            w.files.upload(databricks_latest_dir, f, overwrite=True)
            print(f"Saved to Databricks: {databricks_latest_dir}")

        with open(local_hist_dir, "rb") as f:
            w.files.upload(databricks_hist_dir, f, overwrite=True)
            print(f"Saved to Databricks: {databricks_hist_dir}")


# In[ ]:


# Gather scarab weights from xddbsns.com, which is open-source

def get_scarab_weights():

    ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    headers = {"User-Agent": "poe_combine_ev"}
    w = WorkspaceClient()

    os.makedirs(DATA_DIR, exist_ok=True)

    local_latest_dir = os.path.join(DATA_DIR, "Scarab_Weights.json")
    databricks_latest_dir = "/Volumes/workspace/poe_economy/raw_data/Scarab_Weights.json"

    resp = requests.get(
        "https://xddbsns.com/data/allflame/scarab-calculator.json",
        headers=headers,
    )
    resp.raise_for_status()
    data = resp.json()['categories']

    for row in data:
        row["ingested_at"] = ingested_at

    with open(local_latest_dir, "w") as f:
        json.dump(data, f)
        print(f"Saved to Local: {local_latest_dir}")

    with open(local_latest_dir, "rb") as f:
        w.files.upload(databricks_latest_dir, f, overwrite=True)
        print(f"Saved to Databricks: {databricks_latest_dir}")


if __name__ == "__main__":
    league = get_current_league()
    ingest_poe_data(league, item_type=["Scarab", "Essence", "Currency"])
    get_scarab_weights()

