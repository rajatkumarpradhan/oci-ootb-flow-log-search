"""Demo: generate synthetic flow logs, run the bundled example queries, print real result tables."""
import argparse
import json
from pathlib import Path

from . import generator, query

FIELDS = ["time", "src_host", "dst_host", "dst_port", "dst_port_name", "action", "bytes"]


def print_table(rows, fields=FIELDS):
    if not rows:
        print("  (no matching records)")
        return
    widths = [max(len(f), *(len(str(r[f])) for r in rows)) for f in fields]
    print("  " + "  ".join(f.ljust(w) for f, w in zip(fields, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for r in rows:
        print("  " + "  ".join(str(r[f]).ljust(w) for f, w in zip(fields, widths)))
    print(f"  ({len(rows)} record(s))")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="flowlog-search-demo",
                                 description="Offline Logging Search demo over synthetic VCN flow-log records.")
    ap.add_argument("--queries", default=str(Path(__file__).resolve().parents[2] / "examples" / "queries.txt"),
                    help="file with one query per line (blank lines and # comments skipped)")
    ap.add_argument("--count", type=int, default=400, help="number of synthetic records to generate")
    ap.add_argument("--dump", help="also write the generated records to this JSON file")
    a = ap.parse_args(argv)
    records = generator.generate(count=a.count)
    print(f"generated {len(records)} synthetic flow-log records (deterministic seed)")
    if a.dump:
        Path(a.dump).write_text(json.dumps(records, indent=2) + "\n")
        print(f"wrote records to {a.dump}")
    for line in Path(a.queries).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        print(f"\nquery> {line}")
        try:
            rows = query.run(line, {"flowlogs": records})
        except query.QueryError as e:
            print(f"  query error: {e}")
            return 1
        print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
