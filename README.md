# oci-ootb-flow-log-search

Search VCN flow logs the way OCI's built-in features do - offline, on synthetic records.

## The OOTB mapping

OCI ships this flow out of the box, no extra services to buy:

1. **VCN Flow Logs** - a subnet-level feature that records ACCEPT/REJECT traffic metadata (source/destination address and port, protocol, bytes, packets) into OCI Logging.
2. **OCI Logging** - the built-in log store. Flow logs land in a log group you pick when you enable them.
3. **Logging Search** - the built-in query UI/engine over those logs (`search "..." | where ... | sort by ...` style pipelines).

This repo reproduces step 3 locally: a real search engine over flow-log-shaped records, with a deterministic synthetic generator standing in for steps 1 and 2 so everything runs free and offline.

## Cost grounding (free tier)

OCI Logging pricing lists log storage with a free allowance, quoted verbatim from the Oracle pricing page (checked 2026-10-30):

> First 10 gigabytes log storage per month: Free

Source: https://www.oracle.com/application-development/logging/pricing/

VCN Flow Logs themselves are a VCN feature; the cost is the Logging storage above. 10 GB/month is far more than a small demo VCN produces. **This repo itself provisions nothing and talks to no tenancy** - it runs entirely on local synthetic data, so running it costs nothing.

## Usage

```
PYTHONPATH=src python -m flowlog_search.demo            # generate records + run example queries
python scripts/validate.py                              # assert every example query returns rows
```

The demo prints real result tables, e.g. denied SSH attempts from a scanner host:

```
query> search "flowlogs" | where dst_port = 22 and action = 'REJECT' | sort by time asc | head 8
  time        src_host  dst_host  dst_port  dst_port_name  action  bytes
  ----------  --------  --------  --------  -------------  ------  -----
  1793318469  scanner   app-1     22        ssh            REJECT  76
  ...
```

## Query subset

One pipeline per query (see `examples/queries.txt`):

```
search "flowlogs" [| where <field> <op> <value> [and/or ...]] [| sort by <field> [asc|desc]] [| head N]
```

- Operators: `=`, `!=`, `>`, `>=`, `<`, `<=`. Strings quoted, numbers bare.
- `and` binds tighter than `or`. `sort by` defaults to descending; `head N` limits rows.
- Record fields mirror OCI flow-log fields: `time`, `src_ip`, `src_port`, `dst_ip`, `dst_port`, `protocol`, `action`, `bytes`, `packets` (plus friendly `src_host`/`dst_host`/`dst_port_name` for readability).
- Unknown fields, bad operators, or unsupported stages fail with a clear error.

## Honest limits

- **Offline only.** No OCI SDK, credentials, or tenancy. The generator (`src/flowlog_search/generator.py`) produces the records; nothing is read from a real VCN.
- **Synthetic data.** Hosts, IPs (documentation ranges 198.51.100.0/24, 203.0.113.0/24) and traffic are invented and deterministic (fixed seed).
- **Teaching subset** of the Logging Search grammar. Real Logging Search supports more stages, functions, and the full query language; port these queries to the console by name, but expect to adapt syntax.
- To go live you would enable Flow Logs on a subnet in the OCI Console, then run equivalent queries in Logging Search - those steps need your tenancy and are not done here.

## Tests

```
PYTHONPATH=src python -m unittest discover -s tests
```

13 tests: generator determinism and shape, query parsing/eval/boolean precedence/sort/head, error paths, every bundled example query, demo end-to-end, and the validate script. CI runs the suite, `scripts/validate.py`, and the full demo on every push.

## License

MIT
