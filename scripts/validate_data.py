#!/usr/bin/env python3
"""Validate dashboard data before publishing."""

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TEAMS = 34


def main() -> None:
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    records = data["records"]
    coverage = data["coverage"]

    assert len(coverage) == EXPECTED_TEAMS, f"coverage={len(coverage)}"
    assert all(item["records"] > 0 for item in coverage), "team with no records"
    assert len(records) >= 1300, f"record count unexpectedly low: {len(records)}"

    keys = [(r["team"], r["date"], r["event"], r["place"]) for r in records]
    assert len(keys) == len(set(keys)), "duplicate records"
    assert all(r["prize"] >= 0 for r in records), "negative prize"

    annual = defaultdict(lambda: defaultdict(float))
    direct = defaultdict(float)
    for row in records:
        annual[row["team"]][row["date"][:4]] += row["prize"]
        direct[row["team"]] += row["prize"]
    assert len(annual) == EXPECTED_TEAMS, f"annual coverage={len(annual)}"
    for team, years in annual.items():
        assert abs(sum(years.values()) - direct[team]) < 0.01, team

    js = (ROOT / "data.js").read_text(encoding="utf-8")
    assert js == "window.dashboardData = " + json.dumps(
        data, ensure_ascii=False, indent=2
    ) + ";\n", "data.js does not match data.json"

    print(
        f"validation passed: teams={len(annual)} "
        f"records={len(records)} prize=${sum(direct.values()):,.0f}"
    )


if __name__ == "__main__":
    main()
