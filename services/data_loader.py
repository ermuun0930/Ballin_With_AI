from __future__ import annotations

from functools import lru_cache
import sqlite3
from typing import Any

import pandas as pd
from flask import current_app


DISPLAY_COLUMNS = [
    "type",
    "number",
    "congress",
    "title",
    "policyArea",
    "introducedDate",
    "latestAction",
    "legislationUrl",
    "gics_sectors",
    "confidence",
    "stage_score",
    "cosponsor_score",
    "recency_score",
    "bipartisan_score",
    "risk_score",
    "risk_label",
]


@lru_cache(maxsize=1)
def load_bills() -> pd.DataFrame:
    path = current_app.config["BILLS_WITH_RISK_PATH"]
    frame = pd.read_parquet(path, columns=DISPLAY_COLUMNS)
    frame = frame.copy()
    frame["risk_score"] = pd.to_numeric(frame["risk_score"], errors="coerce").fillna(0)
    for column in ["stage_score", "cosponsor_score", "recency_score", "bipartisan_score", "confidence"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    frame["sector_list"] = frame["gics_sectors"].apply(split_sectors)
    frame["policy_area_name"] = frame["policyArea"].apply(policy_area_name)
    frame["latest_action_text"] = frame["latestAction"].apply(latest_action_text)
    frame["latest_action_date"] = frame["latestAction"].apply(latest_action_date)
    frame["bill_id"] = frame.apply(
        lambda row: f"{str(row['type']).lower()}-{row['number']}-{row['congress']}",
        axis=1,
    )
    return frame


@lru_cache(maxsize=1)
def load_database_context() -> dict[str, Any]:
    path = current_app.config.get("ANALYTICS_DATABASE_PATH", current_app.config["DATABASE_PATH"])
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        tickers = {
            row["ticker"].upper(): dict(row)
            for row in connection.execute("select * from ticker_industries").fetchall()
        }
        actions = grouped_rows(
            connection,
            "select bill_id, action_date, action_text from bill_actions order by action_date desc, id desc",
            "bill_id",
        )
        subjects = grouped_rows(
            connection,
            "select bill_id, subject_name from bill_subjects order by subject_name",
            "bill_id",
        )
        sponsors = grouped_rows(
            connection,
            """
            select bill_id, full_name, party, state, is_primary_sponsor, nominate_dim1, nominate_dim2
            from bill_sponsors
            order by is_primary_sponsor desc, full_name
            """,
            "bill_id",
        )
        bills = {
            row["bill_id"]: dict(row)
            for row in connection.execute(
                """
                select bill_id, title, policy_area, latest_action_text, latest_action_date,
                       legislation_url, sponsor_name, sponsor_party, sponsor_state,
                       classified_industry, classification_confidence, classification_method
                from bills
                """
            ).fetchall()
        }

    return {
        "tickers": tickers,
        "actions": actions,
        "subjects": subjects,
        "sponsors": sponsors,
        "bills": bills,
    }


def grouped_rows(connection: sqlite3.Connection, query: str, key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in connection.execute(query).fetchall():
        record = dict(row)
        grouped.setdefault(record.pop(key), []).append(record)
    return grouped


def backend_analytics() -> dict[str, Any]:
    bills = load_bills()
    sector_rows = []
    for _, row in bills.iterrows():
        for sector in row["sector_list"]:
            sector_rows.append(
                {
                    "sector": sector,
                    "risk_score": row["risk_score"],
                    "stage_score": row["stage_score"],
                    "cosponsor_score": row["cosponsor_score"],
                    "recency_score": row["recency_score"],
                    "bipartisan_score": row["bipartisan_score"],
                }
            )
    sector_frame = pd.DataFrame(sector_rows)
    if sector_frame.empty:
        sector_risk = []
        sector_activity = []
    else:
        sector_risk = (
            sector_frame.groupby("sector")["risk_score"]
            .agg(["mean", "count"])
            .sort_values("mean", ascending=False)
            .head(5)
            .reset_index()
            .to_dict("records")
        )
        sector_activity = (
            sector_frame["sector"].value_counts().head(5).rename_axis("sector").reset_index(name="count").to_dict("records")
        )

    return {
        "bill_count": int(len(bills)),
        "classified_count": int(bills["gics_sectors"].fillna("").astype(str).str.len().gt(0).sum()),
        "risk_mean": round(float(bills["risk_score"].mean()), 1),
        "risk_max": round(float(bills["risk_score"].max()), 1),
        "component_averages": {
            "Legislative Stage": round(float(bills["stage_score"].mean()), 1),
            "Cosponsors": round(float(bills["cosponsor_score"].mean()), 1),
            "Recency": round(float(bills["recency_score"].mean()), 1),
            "Bipartisan Support": round(float(bills["bipartisan_score"].mean()), 1),
        },
        "sector_risk": [
            {"sector": row["sector"], "risk": round(float(row["mean"]), 1), "count": int(row["count"])}
            for row in sector_risk
        ],
        "sector_activity": [
            {"sector": row["sector"], "count": int(row["count"])}
            for row in sector_activity
        ],
    }


def split_sectors(value: Any) -> list[str]:
    if value is None or str(value).strip() == "":
        return []
    return [part.strip() for part in str(value).replace(",", "|").split("|") if part.strip()]


def policy_area_name(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("name", "Unspecified")
    if value:
        return str(value)
    return "Unspecified"


def latest_action_text(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("text") or "No action text available"
    return str(value) if value else "No action text available"


def latest_action_date(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("actionDate") or ""
    return ""
