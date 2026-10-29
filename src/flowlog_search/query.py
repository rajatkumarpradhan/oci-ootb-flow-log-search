"""A small, documented subset of OCI Logging Search syntax.

Supported grammar (one pipeline per query):

    search "<source>" [| where <cond> [and <cond> ...]] [| sort by <field> [asc|desc]] [| head N]

- `search "<source>"` selects the record set; the only source in this offline
  engine is "flowlogs".
- `where` conditions compare a record field to a literal with =, !=, >, >=,
  <, <=. String literals may be single- or double-quoted; numbers are bare.
  Conditions combine with `and` / `or` (`and` binds tighter).
- `sort by <field>` orders results (desc default for numeric convenience:
  pass `asc` explicitly for ascending).
- `head N` keeps the first N results.

This is a teaching subset, not the full service grammar; see README limits.
"""
import re

_COND_RE = re.compile(r"^([a-z_]+)\s*(=|!=|>=|<=|>|<)\s*(.+)$")
_TOKEN_RE = re.compile(r'\s+(and|or)\s+', re.IGNORECASE)


class QueryError(ValueError):
    pass


def _literal(raw: str):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] in "'\"" and raw[-1] == raw[0]:
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        raise QueryError(f"unsupported literal: {raw!r} (quote strings, numbers are bare)")


def _parse_cond(text: str):
    m = _COND_RE.match(text.strip())
    if not m:
        raise QueryError(f"cannot parse condition: {text!r} (expected <field> <op> <value>)")
    field, op, raw = m.group(1), m.group(2), m.group(3)
    return (field, op, _literal(raw))


def _eval_cond(cond, record):
    field, op, val = cond
    if field not in record:
        raise QueryError(f"unknown field: {field!r} (have: {sorted(record)})")
    got = record[field]
    try:
        if op == "=":
            return got == val
        if op == "!=":
            return got != val
        if op == ">":
            return got > val
        if op == ">=":
            return got >= val
        if op == "<":
            return got < val
        if op == "<=":
            return got <= val
    except TypeError:
        raise QueryError(f"cannot compare field {field!r} value {got!r} with {val!r}")
    raise QueryError(f"unknown operator: {op}")


def _eval_where(tree, record):
    if isinstance(tree, tuple) and tree and tree[0] in ("and", "or"):
        _, left, right = tree
        if tree[0] == "and":
            return _eval_where(left, record) and _eval_where(right, record)
        return _eval_where(left, record) or _eval_where(right, record)
    return _eval_cond(tree, record)


def _parse_bool_expr(text: str):
    # split on top-level or, then and (and binds tighter)
    or_parts = re.split(r"\s+or\s+", text, flags=re.IGNORECASE)
    tree = None
    for part in or_parts:
        and_parts = re.split(r"\s+and\s+", part, flags=re.IGNORECASE)
        sub = None
        for piece in and_parts:
            cond = _parse_cond(piece)
            sub = cond if sub is None else ("and", sub, cond)
        tree = sub if tree is None else ("or", tree, sub)
    return tree


def run(query: str, sources: dict[str, list[dict]]) -> list[dict]:
    """Run one query against named record sources. Returns matching records."""
    stages = [s.strip() for s in query.strip().split("|")]
    if not stages or not stages[0].lower().startswith("search "):
        raise QueryError("query must start with: search \"<source>\"")
    m = re.match(r'^search\s+"([^"]+)"$', stages[0], re.IGNORECASE)
    if not m:
        raise QueryError('search stage must be: search "<source>"')
    source = m.group(1)
    if source not in sources:
        raise QueryError(f"unknown source {source!r} (have: {sorted(sources)})")
    rows = list(sources[source])
    for stage in stages[1:]:
        low = stage.lower()
        if low.startswith("where "):
            tree = _parse_bool_expr(stage[6:])
            rows = [r for r in rows if _eval_where(tree, r)]
        elif low.startswith("sort by "):
            parts = stage[8:].split()
            if not parts or parts[0] not in (rows[0] if rows else {}):
                raise QueryError(f"cannot sort: {stage!r}")
            field = parts[0]
            order = parts[1].lower() if len(parts) > 1 else "desc"
            if order not in ("asc", "desc"):
                raise QueryError(f"sort order must be asc or desc, got {parts[1]!r}")
            rows.sort(key=lambda r: r[field], reverse=(order == "desc"))
        elif low.startswith("head "):
            try:
                n = int(stage[5:].strip())
            except ValueError:
                raise QueryError(f"cannot parse head count: {stage!r}")
            rows = rows[:n]
        else:
            raise QueryError(f"unsupported stage: {stage!r} (have: where, sort by, head)")
    return rows
