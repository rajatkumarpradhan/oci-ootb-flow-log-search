#!/usr/bin/env python3
"""Validate the repo: run every bundled example query and require non-empty results."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flowlog_search import generator, query  # noqa: E402


def main() -> int:
    records = generator.generate()
    lines = [l.strip() for l in (Path(__file__).resolve().parents[1] / "examples" / "queries.txt").read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    failed = 0
    for line in lines:
        try:
            rows = query.run(line, {"flowlogs": records})
        except query.QueryError as e:
            print(f"FAIL  {line}\n      {e}")
            failed += 1
            continue
        status = "ok  " if rows else "FAIL"
        if not rows:
            failed += 1
        print(f"{status}  ({len(rows):3d} rows)  {line}")
    if failed:
        print(f"validate: {failed} query/queries failed")
        return 1
    print(f"validate: OK ({len(lines)} queries, {len(records)} synthetic records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
