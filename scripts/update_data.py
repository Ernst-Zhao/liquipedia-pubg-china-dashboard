#!/usr/bin/env python3
"""Fetch Liquipedia team results and build dashboard data atomically."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://liquipedia.net/pubg/api.php"
TEAMS = [
    "1246", "17 Gaming", "All Gamers", "Anyone's Legend", "Black Ananas",
    "Change The Game", "China", "Crystal Luster", "DD Team", "EDward Gaming",
    "Four Angry Men", "Games Forever Young", "Infantry", "JD Gaming",
    "KaiXin Esports", "LGD Gaming", "LinGan e-Sports", "Luminous Stars",
    "Multi Circle Gaming", "NewHappy", "Oh My God", "Petrichor Road",
    "QM Gaming", "Royal Never Give Up", "Still Moving Under Gunfire",
    "Super Survivor Squad", "TakeMeAway Gaming", "Tianba",
    "Triumphant Song Gaming", "TYLOO", "VC Gaming", "ViCi Gaming",
    "Victory Five", "Weibo Gaming",
]
OVERVIEW_TEAMS = {"EDward Gaming", "JD Gaming"}


def prize_value(text: str) -> float:
    match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", text)
    return float(match.group(1).replace(",", "")) if match else 0


def fetch_page(session: requests.Session, team: str, delay: int) -> tuple[str, str]:
    is_overview = team in OVERVIEW_TEAMS
    page = team if is_overview else f"{team}/Results"
    response = session.get(
        API_URL,
        params={"action": "parse", "page": page, "prop": "text", "format": "json"},
        timeout=60,
    )
    if response.status_code == 429:
        raise RuntimeError("Liquipedia returned HTTP 429; old data was preserved")
    response.raise_for_status()
    payload = response.json()
    if "error" in payload or not payload.get("parse", {}).get("text", {}).get("*"):
        raise RuntimeError(f"{team}: missing or empty page")
    if delay:
        time.sleep(delay)
    return payload["parse"]["text"]["*"], "overview" if is_overview else "ok"


def parse_results(team: str, html: str, status: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for tr in soup.select("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) < 6:
            continue
        event_date = cells[0].get_text(" ", strip=True)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", event_date):
            continue
        event_cell = cells[4]
        event_link = event_cell.find("a", href=True)
        href = event_link["href"] if event_link else ""
        event_url = f"https://liquipedia.net{href}" if href.startswith("/") else href
        prize_raw = cells[5].get_text(" ", strip=True) or "-"
        records.append(
            {
                "date": event_date,
                "team": team,
                "place": cells[1].get_text(" ", strip=True),
                "tier": cells[2].get_text(" ", strip=True),
                "event": event_cell.get_text(" ", strip=True),
                "prize": prize_value(prize_raw),
                "prizeRaw": prize_raw,
                "eventUrl": event_url,
                "source": "https://liquipedia.net/pubg/"
                + quote(team.replace(" ", "_"), safe="_'-")
                + ("/Results" if status == "ok" else ""),
            }
        )
    if not records:
        raise RuntimeError(f"{team}: parsed zero result rows")
    return records


def validate_candidate(candidate: dict, previous: dict | None) -> None:
    records = candidate["records"]
    coverage = candidate["coverage"]
    covered = {item["team"] for item in coverage if item["records"] > 0}
    if covered != set(TEAMS):
        raise RuntimeError(f"coverage mismatch: {sorted(set(TEAMS) - covered)}")

    keys = [(r["team"], r["date"], r["event"], r["place"]) for r in records]
    if len(keys) != len(set(keys)):
        raise RuntimeError("duplicate result rows detected")
    if any(r["prize"] < 0 for r in records):
        raise RuntimeError("negative prize detected")

    if previous:
        old_count = len(previous.get("records", []))
        if len(records) < old_count * 0.95:
            raise RuntimeError(
                f"record count fell from {old_count} to {len(records)} (>5%)"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--delay",
        type=int,
        default=int(os.getenv("LIQUIPEDIA_REQUEST_DELAY", "31")),
        help="seconds between API requests",
    )
    args = parser.parse_args()

    user_agent = os.getenv(
        "LIQUIPEDIA_USER_AGENT",
        "ChinaPUBGPrizeDashboard/1.0 "
        "(https://github.com/Ernst-Zhao/liquipedia-pubg-china-dashboard)",
    )
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip",
            "Accept": "application/json",
        }
    )

    previous_path = ROOT / "data.json"
    previous = (
        json.loads(previous_path.read_text(encoding="utf-8"))
        if previous_path.exists()
        else None
    )
    team_totals = previous.get("teamTotals", {}) if previous else {}

    records: list[dict] = []
    coverage: list[dict] = []
    for index, team in enumerate(TEAMS, 1):
        print(f"[{index:02d}/{len(TEAMS)}] {team}", flush=True)
        html, status = fetch_page(
            session, team, args.delay if index < len(TEAMS) else 0
        )
        team_records = parse_results(team, html, status)
        records.extend(team_records)
        coverage.append(
            {"team": team, "status": status, "records": len(team_records), "page": team}
        )

    records.sort(key=lambda row: (row["date"], row["team"]), reverse=True)
    candidate = {
        "generatedAt": date.today().isoformat(),
        "teamTotalsSnapshot": previous.get("teamTotalsSnapshot", "") if previous else "",
        "teamTotals": team_totals,
        "annualOverrides": {},
        "records": records,
        "coverage": coverage,
    }
    validate_candidate(candidate, previous)

    serialized = json.dumps(candidate, ensure_ascii=False, indent=2)
    with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
        temp = Path(temp_dir)
        json_temp = temp / "data.json"
        js_temp = temp / "data.js"
        json_temp.write_text(serialized, encoding="utf-8")
        js_temp.write_text(
            "window.dashboardData = " + serialized + ";\n", encoding="utf-8"
        )
        json_temp.replace(ROOT / "data.json")
        js_temp.replace(ROOT / "data.js")

    print(f"updated records={len(records)} teams={len(coverage)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
